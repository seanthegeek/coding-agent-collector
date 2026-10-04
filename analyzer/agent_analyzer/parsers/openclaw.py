"""OpenClaw (formerly Clawdbot and Moltbot) agent transcripts.

Validated against source, openclaw/openclaw at 3b16db7 (see
`analyzer/research/openclaw.md`), with a synthetic fixture; no real install
was checked. The state directory is `.openclaw`, a profile's
`.openclaw-<profile>`, or the legacy `.clawdbot` / `.moltbot`. Files:

* `agents/<agentId>/agent/openclaw-agent.sqlite` (WAL, opened through
  `sqlite_util`), the live store since mid-2026:
  - `transcript_events(session_id, seq, event_json, event_zstd,
    created_at)`: one entry per row. Rows of 1 KiB to 4 MiB may hold the
    entry as one zstd frame in `event_zstd` with `event_json` NULL; that
    needs the `zstandard` package, imported lazily, and without it each such
    row becomes one `system` row. `created_at` is epoch ms.
  - `session_windows(session_id, session_key, previous_session_id, reason,
    channel, account_id, chat_type, model_provider, model, started_at,
    parent_session_key, spawned_by, display_name)`: one row per transcript
    generation, read for the session-start row.
  - `session_transcript_archives(session_id, session_key, reason, encoding,
    archive_blob, archive_name, published_at)`: reset or deleted
    generations as JSONL (zstd when `encoding` is `zstd`). Archives not yet
    `published_at` exist only here and are parsed; published ones are also
    the `.jsonl.reset.*` / `.jsonl.deleted.*` file, which is parsed instead,
    so they become one `system` row naming that file.
  - `session_transcript_cold_archives(session_id, archive_name, storage,
    archive_blob)` with `storage` `sqlite`: a zstd JSONL envelope of
    `{"kind":"event","row":{"seq","event_json","created_at"}}` records
    (`src/config/sessions/session-cold-storage-codec.ts:48-100`, not in the
    research document). `storage` `file` means
    `agents/<id>/sessions/cold/<sha256>.jsonl.zst`, parsed as a file.
  - `auth_profile_store`, `auth_profile_state` and `session_suggestions`
    hold credentials and are never read.
* `agents/<agentId>/sessions/<sessionId>.jsonl` (and `sessions/` at the
  state root, the older single-agent layout): legacy transcripts not yet
  imported by `openclaw doctor`. `<sessionId>.jsonl.reset.<ts>[.<gen>][.zst]`
  and `.jsonl.deleted.<...>`: archives of reset or deleted sessions, one
  zstd frame when `.zst`. Same entry format. The sibling legacy
  `sessions.json`, `{<sessionKey>: {"sessionId", ...}}`
  (`src/infra/state-migrations.legacy-session-store.ts:202-205`), gives the
  session key. Checkpoint (`*.checkpoint.<uuid>.jsonl`), trajectory,
  `*.migrated*` and `*.bak` copies duplicate other transcripts and are
  skipped.

Entry fields: header `{type:"session", version, id, timestamp, cwd,
parentSession}`; then `type`, `id`, `parentId`, `timestamp` (ISO 8601) and
per type `message` (`message`), `model_change` (`provider`, `modelId`),
`thinking_level_change` (`thinkingLevel`), `compaction` (`summary`,
`tokensBefore`, `tokensAfter`), `reset` (`reason`), `branch_summary`
(`summary`), `custom` (`customType`, `data`), `custom_message`
(`customType`, `content`), `label` (`label`, `targetId`), `session_info`
(`name`). `message.role`: `user` (`content`, `runtimeContext`,
`runtimeContextCarrier`), `assistant` (`content` blocks `text`, `thinking`
{`thinking`, `redacted`}, `toolCall` {`id`, `name`, `arguments`}, `image`;
`model`, `responseModel`, `stopReason`, `errorMessage`), `toolResult`
(`toolCallId`, `toolName`, `content`, `isError`), `bashExecution`
(`command`, `output`, `exitCode`, `cancelled`), `custom`, `branchSummary`,
`compactionSummary` (`summary`); `message.timestamp` is epoch ms.

Rows: one `system` row per session carrying the session key
(`agent:<agentId>:<channel>:<accountId>:direct:<peerId>` names the external
sender), channel, account, chat type and parent; `session_id` is the
transcript id (`transcript_events.session_id`, the header `id`), and
`project_path` the header `cwd`. User messages flagged `runtimeContext` are
injected context, not human input, and become `system` rows. A
`bashExecution` (a `!` command the operator ran) becomes a `tool_use` row
named `bash` and a `tool_result` row, joined on the entry `id`. An assistant
message that ended with `stopReason` `error` or `aborted`, or carries an
`errorMessage`, adds a `system` row. Timestamps are the entry `timestamp`,
else the message's ms timestamp, else the row's `created_at`. `source_line`
is the `transcript_events` (or archive table) rowid, or the JSONL line. No
git branch is recorded.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, text_of
from .zed import _zstd_module, decompress

STATE = r"(?:\.openclaw(?:-[^/]+)?|\.clawdbot|\.moltbot)"
DB_RX = re.compile(r"^" + STATE + r"/agents/[^/]+/agent/openclaw-agent\.sqlite$")
SESSIONS = r"^" + STATE + r"/(?:agents/[^/]+/)?sessions/"
ARCHIVE_SUFFIX = r"\.jsonl\.(reset|deleted)\.\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d(?:\.\d{3})?Z(?:\.[0-9a-f]{32})?(?:\.zst)?"
JSONL_RX = re.compile(SESSIONS + r"(?P<name>[^/]+?)(?:(?P<archive>" + ARCHIVE_SUFFIX + r")|\.jsonl)$")
COLD_RX = re.compile(SESSIONS + r"cold/[0-9a-f]{64}\.jsonl\.zst$")
SKIP_NAME_RX = re.compile(r"\.checkpoint\.[0-9a-fA-F-]{36}$|\.trajectory$")
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def tool_args_text(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return args
    if isinstance(args, dict):
        for k in ("command", "path", "url"):
            if isinstance(args.get(k), str) and args[k]:
                return args[k]
    if args in (None, "", {}):
        return ""
    return compact_json(args)


def _maybe_zstd(blob: bytes) -> tuple[bytes | None, str]:
    """(data, error): zstd frames are decompressed, anything else returned."""
    blob = bytes(blob)
    if not blob.startswith(ZSTD_MAGIC):
        return blob, ""
    zstd = _zstd_module()
    if zstd is None:
        return None, "zstandard package not installed"
    try:
        return decompress(blob, zstd), ""
    except Exception as e:  # noqa: BLE001 - zstd.ZstdError; the module is imported lazily
        return None, "%s: %s" % (type(e).__name__, e)


def _iter_lines(data: bytes, errors: list) -> Iterator[tuple[int, dict]]:
    for n, raw in enumerate(data.split(b"\n"), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw.decode("utf-8", errors="replace"))
        except ValueError as e:
            errors.append((n, str(e)))
            continue
        if isinstance(rec, dict):
            yield n, rec


class _Session:
    """State carried across one transcript's entries."""

    def __init__(self, session_id: str = "", key: str = "", extra: str = "", model: str = ""):
        self.session_id = session_id
        self.key = key
        self.extra = extra
        self.model = model
        self.cwd = ""
        self.started = False


class OpenClawParser(Parser):
    agent = "openclaw"
    name = "openclaw"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        if DB_RX.match(rel) or COLD_RX.match(rel):
            return True
        m = JSONL_RX.match(rel)
        return bool(m) and not SKIP_NAME_RX.search(m.group("name"))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if DB_RX.match(artifact.rel):
            if is_sqlite(artifact.disk_path):
                yield from self._parse_db(artifact, opts)
        else:
            yield from self._parse_file(artifact, opts)

    # -- rows -------------------------------------------------------------------
    def _row(self, artifact: Artifact, s: _Session, line: int, ts: str, turn_type: str, text: str,
             opts: Options, model: str = "", tool_name: str = "", tool_use_id: str = "") -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.session_id = s.session_id
        row.project_path = s.cwd
        row.timestamp_utc = ts
        row.turn_type = turn_type
        row.model = model
        row.tool_name = tool_name
        row.tool_use_id = tool_use_id
        row.text = compact(text, opts.max_text_length)
        return row

    def _start(self, artifact: Artifact, s: _Session, line: int, ts: str, header: dict | None,
               opts: Options) -> Row:
        s.started = True
        header = header or {}
        if header.get("id") and not s.session_id:
            s.session_id = str(header["id"])
        if isinstance(header.get("cwd"), str):
            s.cwd = header["cwd"]
        parent = header.get("parentSession")
        text = " ".join(x for x in (
            "session start:",
            "key=%s" % s.key if s.key else "",
            s.extra,
            "version=%s" % header["version"] if header.get("version") is not None else "",
            "parent_session=%s" % parent if parent else "",
        ) if x)
        return self._row(artifact, s, line, ts or to_utc(header.get("timestamp")), "system", text, opts, s.model)

    def _entry_rows(self, artifact: Artifact, s: _Session, line: int, rec: dict, created_at,
                    opts: Options) -> Iterator[Row]:
        etype = rec.get("type")
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        ts = to_utc(rec.get("timestamp")) or to_utc(msg.get("timestamp")) or to_utc(created_at)
        if etype == "session":
            yield self._start(artifact, s, line, ts, rec, opts)
            return
        if not s.started:
            yield self._start(artifact, s, line, ts, None, opts)
        if etype == "message":
            yield from self._message_rows(artifact, s, line, ts, rec, msg, opts)
            return

        def system(text: str, model: str = "") -> Row:
            return self._row(artifact, s, line, ts, "system", text, opts, model)

        if etype == "model_change":
            s.model = str(rec.get("modelId") or "")
            yield system("model change: %s" % "/".join(str(x) for x in (rec.get("provider"), rec.get("modelId")) if x),
                         s.model)
        elif etype == "thinking_level_change":
            yield system("thinking level: %s" % (rec.get("thinkingLevel") or ""))
        elif etype == "compaction":
            tokens = " ".join(x for x in (
                "tokens_before=%s" % rec["tokensBefore"] if rec.get("tokensBefore") is not None else "",
                "tokens_after=%s" % rec["tokensAfter"] if rec.get("tokensAfter") is not None else "") if x)
            yield system("compaction%s: %s" % (" (%s)" % tokens if tokens else "", rec.get("summary") or ""))
        elif etype == "reset":
            yield system("reset: %s" % (rec.get("reason") or ""))
        elif etype == "branch_summary":
            yield system("branch summary: %s" % (rec.get("summary") or ""))
        elif etype == "custom":
            yield system("custom %s: %s" % (rec.get("customType") or "", compact_json(rec.get("data"))))
        elif etype == "custom_message":
            yield system("custom message %s: %s" % (rec.get("customType") or "", text_of(rec.get("content"))))
        elif etype == "label":
            yield system("label: %s (entry %s)" % (rec.get("label") or "", rec.get("targetId") or ""))
        elif etype == "session_info":
            yield system("session name: %s" % (rec.get("name") or ""))
        else:
            rest = {k: v for k, v in rec.items() if k not in ("type", "id", "parentId", "timestamp")}
            yield system("%s: %s" % (etype or "entry", compact_json(rest)))

    def _message_rows(self, artifact: Artifact, s: _Session, line: int, ts: str, rec: dict, msg: dict,
                      opts: Options) -> Iterator[Row]:
        role = msg.get("role")
        if role == "user":
            text = text_of(msg.get("content"))
            if msg.get("runtimeContext") or msg.get("runtimeContextCarrier"):
                yield self._row(artifact, s, line, ts, "system", "runtime context: " + text, opts)
            else:
                yield self._row(artifact, s, line, ts, "user", text, opts)
        elif role == "assistant":
            model = str(msg.get("responseModel") or msg.get("model") or s.model or "")
            if model:
                s.model = model
            content = msg.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text":
                    if b.get("text"):
                        yield self._row(artifact, s, line, ts, "assistant", str(b["text"]), opts, model)
                elif bt == "thinking":
                    if opts.include_thinking:
                        t = b.get("thinking") or ("[redacted thinking]" if b.get("redacted") else "")
                        if t:
                            yield self._row(artifact, s, line, ts, "thinking", str(t), opts, model)
                elif bt == "toolCall":
                    yield self._row(artifact, s, line, ts, "tool_use", tool_args_text(b.get("arguments")), opts,
                                    model, str(b.get("name") or ""), str(b.get("id") or ""))
                elif bt == "image":
                    yield self._row(artifact, s, line, ts, "assistant", "[image]", opts, model)
            stop = msg.get("stopReason")
            if stop in ("error", "aborted") or msg.get("errorMessage"):
                yield self._row(artifact, s, line, ts, "system", "assistant %s: %s" % (
                    stop or "error", msg.get("errorMessage") or ""), opts, model)
        elif role == "toolResult":
            text = text_of(msg.get("content"))
            if msg.get("isError"):
                text = "[error] " + text
            yield self._row(artifact, s, line, ts, "tool_result", text, opts, "",
                            str(msg.get("toolName") or ""), str(msg.get("toolCallId") or ""))
        elif role == "bashExecution":
            tid = str(rec.get("id") or "")
            yield self._row(artifact, s, line, ts, "tool_use", str(msg.get("command") or ""), opts, "", "bash", tid)
            status = "exit=%s" % msg.get("exitCode")
            if msg.get("cancelled"):
                status += " cancelled"
            if msg.get("truncated"):
                status += " truncated"
            yield self._row(artifact, s, line, ts, "tool_result", "[%s] %s" % (status, msg.get("output") or ""),
                            opts, "", "bash", tid)
        elif role in ("branchSummary", "compactionSummary"):
            label = "branch summary" if role == "branchSummary" else "compaction summary"
            yield self._row(artifact, s, line, ts, "system", "%s: %s" % (label, msg.get("summary") or ""), opts)
        elif role == "custom":
            yield self._row(artifact, s, line, ts, "system", "custom %s: %s" % (
                msg.get("customType") or "", text_of(msg.get("content"))), opts)
        else:
            yield self._row(artifact, s, line, ts, "system", "%s: %s" % (
                role or "message", text_of(msg.get("content")) or compact_json(msg)), opts)

    def _bad(self, artifact: Artifact, s: _Session, line: int, text: str, opts: Options, ts: str = "") -> Row:
        return self._row(artifact, s, line, ts, "system", "parser: " + text, opts)

    def _records(self, artifact: Artifact, s: _Session, records, opts: Options, fixed_line: int = 0) -> Iterator[Row]:
        """Rows from (line, record) pairs of a JSONL transcript or a cold
        archive envelope; `fixed_line` overrides the line for blobs."""
        for n, rec in records:
            line = fixed_line or n
            if "kind" in rec and "type" not in rec:
                kind = rec.get("kind")
                if kind == "header" and not s.session_id:
                    s.session_id = str(rec.get("sessionId") or "")
                if kind != "event" or not isinstance(rec.get("row"), dict):
                    continue
                inner = rec["row"]
                try:
                    entry = json.loads(inner.get("event_json") or "")
                except (TypeError, ValueError) as e:
                    yield self._bad(artifact, s, line, "cold archive event seq %s unreadable: %s" % (
                        inner.get("seq"), e), opts, to_utc(inner.get("created_at")))
                    continue
                if isinstance(entry, dict):
                    yield from self._entry_rows(artifact, s, line, entry, inner.get("created_at"), opts)
                continue
            yield from self._entry_rows(artifact, s, line, rec, None, opts)

    # -- JSONL files ----------------------------------------------------------------
    def _parse_file(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = JSONL_RX.match(artifact.rel)
        s = _Session(session_id=m.group("name") if m else "")
        if m and m.group("archive"):
            s.extra = "archive=%s" % m.group("archive")[len(".jsonl."):]
        if m:
            s.key = self._legacy_key(artifact, s.session_id)
        with open(artifact.disk_path, "rb") as fh:
            raw = fh.read()
        data, err = _maybe_zstd(raw)
        if data is None:
            yield self._bad(artifact, s, 1, "could not decompress (%s)" % err, opts)
            return
        errors: list = []
        yield from self._records(artifact, s, _iter_lines(data, errors), opts)
        if errors:
            yield self._bad(artifact, s, errors[0][0], "%d unparseable line(s), first at line %d" % (
                len(errors), errors[0][0]), opts)

    @staticmethod
    def _legacy_key(artifact: Artifact, session_id: str) -> str:
        store = artifact.disk_path.parent / "sessions.json"
        try:
            if store.is_symlink() or not store.is_file():
                return ""
            with open(store, encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return ""
        if isinstance(data, dict):
            for key, entry in data.items():
                if isinstance(entry, dict) and entry.get("sessionId") == session_id:
                    return str(key)
        return ""

    # -- SQLite store -------------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        with open_copy(artifact.disk_path) as con:
            tables = table_names(con)
            windows: dict[str, dict] = {}
            if "session_windows" in tables:
                for w in con.execute("select * from session_windows"):
                    w = dict(w)
                    windows[str(w.get("session_id"))] = w
            if "transcript_events" in tables:
                yield from self._db_events(artifact, con, windows, opts)
            if "session_transcript_archives" in tables:
                yield from self._db_archives(artifact, con, windows, opts)
            if "session_transcript_cold_archives" in tables:
                yield from self._db_cold(artifact, con, windows, opts)

    @staticmethod
    def _window_session(session_id: str, windows: dict[str, dict], key: str = "", extra: str = "") -> _Session:
        w = windows.get(session_id) or {}
        parts: list[str] = []
        for col in ("channel", "account_id", "chat_type", "reason", "previous_session_id",
                    "parent_session_key", "spawned_by", "display_name"):
            if w.get(col) not in (None, ""):
                parts.append("%s=%s" % (col, w[col]))
        if extra:
            parts.append(extra)
        if w.get("model_provider"):
            parts.append("model_provider=%s" % w["model_provider"])
        return _Session(session_id, key or str(w.get("session_key") or ""), " ".join(parts), str(w.get("model") or ""))

    def _db_events(self, artifact: Artifact, con, windows: dict[str, dict], opts: Options) -> Iterator[Row]:
        s: _Session | None = None
        for r in con.execute("select rowid as _rowid, session_id, seq, event_json, event_zstd, created_at "
                             "from transcript_events order by session_id, seq"):
            r = dict(r)
            sid = str(r.get("session_id") or "")
            if s is None or s.session_id != sid:
                s = self._window_session(sid, windows)
            line = r["_rowid"]
            raw = r.get("event_json")
            if raw is None and r.get("event_zstd") is not None:
                data, err = _maybe_zstd(r["event_zstd"])
                if data is None:
                    if not s.started:
                        yield self._start(artifact, s, line, to_utc(r.get("created_at")), None, opts)
                    yield self._bad(artifact, s, line, "event seq %s could not be decompressed (%s)" % (
                        r.get("seq"), err), opts, to_utc(r.get("created_at")))
                    continue
                raw = data.decode("utf-8", errors="replace")
            try:
                rec = json.loads(raw if isinstance(raw, str) else bytes(raw or b"").decode("utf-8", errors="replace"))
            except ValueError as e:
                rec = None
                err = str(e)
            if not isinstance(rec, dict):
                if not s.started:
                    yield self._start(artifact, s, line, to_utc(r.get("created_at")), None, opts)
                yield self._bad(artifact, s, line, "event seq %s unreadable: %s" % (
                    r.get("seq"), err if rec is None else "not a JSON object"), opts, to_utc(r.get("created_at")))
                continue
            yield from self._entry_rows(artifact, s, line, rec, r.get("created_at"), opts)

    def _db_archives(self, artifact: Artifact, con, windows: dict[str, dict], opts: Options) -> Iterator[Row]:
        for r in con.execute("select rowid as _rowid, session_id, session_key, reason, encoding, archive_name, "
                             "created_at, published_at, archive_blob from session_transcript_archives "
                             "order by created_at"):
            r = dict(r)
            sid = str(r.get("session_id") or "")
            extra = "archive=%s name=%s" % (r.get("reason") or "", r.get("archive_name") or "")
            s = self._window_session(sid, windows, str(r.get("session_key") or ""), extra)
            line = r["_rowid"]
            if r.get("published_at"):
                yield self._row(artifact, s, line, to_utc(r.get("created_at")), "system",
                                "session %s archive %s is in the sessions directory as %s; its rows come from that file"
                                % (r.get("reason") or "", sid, r.get("archive_name") or ""), opts)
                continue
            data, err = _maybe_zstd(r.get("archive_blob") or b"")
            if data is None:
                yield self._bad(artifact, s, line, "archive %s could not be decompressed (%s)" % (
                    r.get("archive_name") or sid, err), opts, to_utc(r.get("created_at")))
                continue
            errors: list = []
            yield from self._records(artifact, s, _iter_lines(data, errors), opts, fixed_line=line)
            if errors:
                yield self._bad(artifact, s, line, "archive %s: %d unparseable line(s)" % (
                    r.get("archive_name") or sid, len(errors)), opts)

    def _db_cold(self, artifact: Artifact, con, windows: dict[str, dict], opts: Options) -> Iterator[Row]:
        for r in con.execute("select rowid as _rowid, session_id, archive_name, archived_at, archive_blob "
                             "from session_transcript_cold_archives where storage = 'sqlite' order by archived_at"):
            r = dict(r)
            sid = str(r.get("session_id") or "")
            s = self._window_session(sid, windows, extra="cold_archive=%s" % (r.get("archive_name") or ""))
            line = r["_rowid"]
            data, err = _maybe_zstd(r.get("archive_blob") or b"")
            if data is None:
                yield self._bad(artifact, s, line, "cold archive %s could not be decompressed (%s)" % (
                    r.get("archive_name") or sid, err), opts, to_utc(r.get("archived_at")))
                continue
            errors: list = []
            yield from self._records(artifact, s, _iter_lines(data, errors), opts, fixed_line=line)
            if errors:
                yield self._bad(artifact, s, line, "cold archive %s: %d unparseable line(s)" % (
                    r.get("archive_name") or sid, len(errors)), opts)


__all__ = ["OpenClawParser", "tool_args_text"]
