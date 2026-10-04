"""Goose CLI and desktop sessions.

Goose (block/goose, checked at 591edd4) resolves its directories with
etcetera's app strategy: XDG paths on Linux and macOS, `AppData/Roaming/
Block/goose/{config,data}` on Windows, where state falls back to data. See
`analyzer/research/goose.md`.

Files, relative to the home directory (`<data>` is `.local/share/goose` or
`AppData/Roaming/Block/goose/data`, `<state>` is `.local/state/goose` or the
Windows data directory):

* `<data>/sessions/sessions.db`, with `-wal` and `-shm` sidecars (WAL mode),
  schema version 16. Older databases lack columns added by later
  migrations, so every column is read with a default.
  - `sessions`: `id`, `name`, `description`, `session_type`, `working_dir`,
    `created_at` (SQLite `CURRENT_TIMESTAMP` text or RFC 3339),
    `provider_name`, `model_config_json` (`model_name`),
    `parent_session_id`, `schedule_id`, `accumulated_total_tokens`.
  - `messages`: `id`, `session_id`, `role` (`user`, `assistant`),
    `content_json`, `created_timestamp` (epoch seconds; values above 1e10
    are milliseconds, as Goose itself normalises them),
    `metadata_json` (`userVisible`, `inference.provider`,
    `inference.requestedModel`, `inference.resolvedModel`).
* `<data>/sessions/<YYYYMMDD_HHMMSS>.jsonl`: legacy sessions, imported into
  the database once. Line 1 is metadata (`id`, `description`,
  `working_dir`, `created_at`); each later line is a message with `id`,
  `role`, `created` (epoch seconds) and `content`.
* `<state>/logs/llm_request.<N>.jsonl`: one file per provider call. A request
  line with `model_config.model_name` and `input.messages`, then response
  lines with `data` (a message: `role`, `created`, `content`) and `usage`.
* `<state>/history.txt` and the older `.config/goose/history.txt`: rustyline
  V2 history, `#V2` header then one prompt per line with `\\n` and `\\\\`
  escaped. No timestamps and no session id.

Content blocks (`type`, camelCase): `text` {`text`}; `image` {`mimeType`};
`document` {`name`, `mimeType`}; `toolRequest` {`id`, `toolCall`: {`status`,
`value`: {`name`, `arguments`} | `error`}}; `toolResponse` {`id`,
`toolResult`: {`status`, `value`: {`content`, `isError`} or a bare content
array | `error`}}; `thinking` {`thinking`}; `redactedThinking`;
`toolConfirmationRequest` {`toolName`, `arguments`, `prompt`};
`actionRequired` {`data`}; `systemNotification` {`notificationType`, `msg`};
`error` {`kind`, `message`}.

Rows: one `system` row per session; one row per content block: text by
role, `toolRequest` as `tool_use`, `toolResponse` as `tool_result` (the tool
name looked up from the request with the same id), thinking blocks only with
`--include-thinking`, the rest as `system`. Text the user never saw
(`userVisible: false`, such as compaction summaries) is prefixed
`[hidden]`. The model is `inference.provider/resolvedModel` (or
`requestedModel`) per message, falling back to the session's
`provider_name/model_config_json.model_name`. No git branch is recorded.
The request log has no session id or cwd: its request line becomes one
`system` row and each response message becomes rows like a transcript's,
timestamped by the response's `created`; the request row inherits the first
response's time. History entries carry no timestamp.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

DATA = r"(?:\.local/share/goose|AppData/Roaming/Block/goose/data)"
STATE = r"(?:\.local/state/goose|AppData/Roaming/Block/goose/data)"
DB_RX = re.compile(r"^%s/sessions/sessions\.db$" % DATA)
LEGACY_RX = re.compile(r"^%s/sessions/[^/]+\.jsonl$" % DATA)
LLM_RX = re.compile(r"^%s/logs/llm_request\.[^/]+\.jsonl$" % STATE)
HISTORY_RX = re.compile(r"^(?:%s|\.config/goose)/history\.txt$" % STATE)


def epoch(value) -> str:
    """`created_timestamp` is seconds, but some clients write milliseconds;
    Goose divides anything above 1e10 by 1000 (session_manager.rs:729-741)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 10_000_000_000:
        value = value / 1000.0
    return to_utc(value)


def _json(value, default):
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return default


def _join(*parts: str) -> str:
    return " | ".join(x for x in parts if x)


def _model(provider: str, name: str) -> str:
    return "%s/%s" % (provider, name) if provider and name else name or ""


def result_text(tool_result) -> tuple[str, bool]:
    """(text, is_error) of a toolResponse.toolResult."""
    if not isinstance(tool_result, dict):
        return compact_json(tool_result), False
    if tool_result.get("status") == "error":
        return str(tool_result.get("error") or ""), True
    value = tool_result.get("value")
    if isinstance(value, list):  # older rows: bare content array
        return text_of(value), False
    if isinstance(value, dict):
        text = text_of(value.get("content"))
        if not text and value.get("structuredContent") is not None:
            text = compact_json(value["structuredContent"])
        return text, bool(value.get("isError"))
    return "", False


def unescape_history(line: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            nxt = line[i + 1]
            out.append("\n" if nxt == "n" else nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


class GooseParser(Parser):
    agent = "goose"
    name = "goose"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return bool(
            DB_RX.match(rel) or LEGACY_RX.match(rel) or LLM_RX.match(rel) or HISTORY_RX.match(rel)
        )

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        rel = artifact.rel
        if DB_RX.match(rel):
            yield from self._parse_db(artifact, opts)
        elif LEGACY_RX.match(rel):
            yield from self._parse_legacy(artifact, opts)
        elif LLM_RX.match(rel):
            yield from self._parse_llm_log(artifact, opts)
        else:
            yield from self._parse_history(artifact, opts)

    def _row(
        self,
        artifact: Artifact,
        line: int,
        session_id: str = "",
        project_path: str = "",
        model: str = "",
        ts: str = "",
    ) -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.session_id = session_id
        row.project_path = project_path
        row.model = model
        row.timestamp_utc = ts
        return row

    # -- content blocks, shared by every store ------------------------------------------
    def _block_rows(
        self,
        artifact: Artifact,
        base: Row,
        role: str,
        content,
        user_visible: bool,
        tool_names: dict[str, str],
        opts: Options,
    ) -> Iterator[Row]:
        if isinstance(content, str):
            text_block: dict = {"type": "text", "text": content}
            content = [text_block]
        if not isinstance(content, list):
            return
        text_type = role if role in ("user", "assistant") else "system"
        for b in content:
            if not isinstance(b, dict):
                continue
            kind = b.get("type")
            row = Row(**base.__dict__)
            if kind == "text":
                row.turn_type = text_type
                text = b.get("text") or ""
                if role not in ("user", "assistant"):
                    text = "%s: %s" % (role, text)
                if not user_visible:
                    text = "[hidden] " + text
            elif kind in ("image", "document"):
                row.turn_type = text_type
                text = "[%s] %s" % (
                    kind,
                    _join(str(b.get("name") or ""), str(b.get("mimeType") or "")),
                )
            elif kind == "toolRequest":
                row.turn_type = "tool_use"
                row.tool_use_id = str(b.get("id") or "")
                call = b.get("toolCall") or {}
                if call.get("status") == "error":
                    text = "[error] " + str(call.get("error") or "")
                else:
                    value = call.get("value") or {}
                    row.tool_name = str(value.get("name") or "")
                    text = compact_json(value.get("arguments") or {})
                tool_names[row.tool_use_id] = row.tool_name
            elif kind == "toolResponse":
                row.turn_type = "tool_result"
                row.tool_use_id = str(b.get("id") or "")
                row.tool_name = tool_names.get(row.tool_use_id, "")
                text, is_error = result_text(b.get("toolResult"))
                if is_error:
                    text = "[error] " + text
            elif kind in ("thinking", "redactedThinking"):
                if not opts.include_thinking:
                    continue
                row.turn_type = "thinking"
                text = (b.get("thinking") or "") if kind == "thinking" else "[redacted thinking]"
            elif kind == "toolConfirmationRequest":
                row.turn_type = "system"
                row.tool_name = str(b.get("toolName") or "")
                row.tool_use_id = str(b.get("id") or "")
                text = _join(
                    "confirmation requested: " + row.tool_name,
                    str(b.get("prompt") or ""),
                    compact_json(b.get("arguments") or {}),
                )
            elif kind == "systemNotification":
                row.turn_type = "system"
                text = "%s: %s" % (b.get("notificationType") or "notification", b.get("msg") or "")
            elif kind == "error":
                row.turn_type = "system"
                text = "error %s: %s" % (b.get("kind") or "", b.get("message") or "")
            elif kind == "actionRequired":
                row.turn_type = "system"
                text = "action required: " + compact_json(b.get("data"))
            else:
                row.turn_type = "system"
                text = compact_json(b)
            row.text = compact(text, opts.max_text_length)
            yield row

    # -- sessions.db ---------------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            row = self._row(artifact, 0)
            row.turn_type = "system"
            row.text = "parser: not a SQLite database"
            yield row
            return
        try:
            with open_copy(artifact.disk_path) as con:
                tables = table_names(con)
                if "messages" not in tables:
                    return
                sessions: dict[str, dict] = {}
                if "sessions" in tables:
                    for s in con.execute(
                        "select rowid as _rowid, * from sessions order by created_at, rowid"
                    ):
                        s = dict(s)
                        cfg = _json(s.get("model_config_json"), {})
                        s["_model"] = _model(
                            s.get("provider_name") or "",
                            (cfg.get("model_name") if isinstance(cfg, dict) else "") or "",
                        )
                        sid = str(s.get("id") or "")
                        sessions[sid] = s
                        row = self._row(
                            artifact,
                            s["_rowid"],
                            sid,
                            s.get("working_dir") or "",
                            s["_model"],
                            to_utc(s.get("created_at")),
                        )
                        row.turn_type = "system"
                        row.text = compact(
                            _join(
                                "session start",
                                s.get("name") or "",
                                s.get("description") or "",
                                "type=%s" % s["session_type"] if s.get("session_type") else "",
                                "parent=%s" % s["parent_session_id"]
                                if s.get("parent_session_id")
                                else "",
                                "schedule=%s" % s["schedule_id"] if s.get("schedule_id") else "",
                                "archived=%s" % s["archived_at"] if s.get("archived_at") else "",
                            ),
                            opts.max_text_length,
                        )
                        yield row
                tool_names: dict[str, str] = {}
                for m in con.execute(
                    "select * from messages order by session_id, created_timestamp, id"
                ):
                    m = dict(m)
                    sid = str(m.get("session_id") or "")
                    s = sessions.get(sid, {})
                    meta = _json(m.get("metadata_json"), {})
                    meta = meta if isinstance(meta, dict) else {}
                    inf = meta.get("inference") or {}
                    model = _model(
                        inf.get("provider") or "",
                        inf.get("resolvedModel") or inf.get("requestedModel") or "",
                    ) or s.get("_model", "")
                    base = self._row(
                        artifact,
                        m.get("id") or 0,
                        sid,
                        s.get("working_dir") or "",
                        model,
                        epoch(m.get("created_timestamp")) or to_utc(m.get("timestamp")),
                    )
                    content = _json(m.get("content_json"), None)
                    if content is None:
                        base.turn_type = "system"
                        base.text = "parser: message %s content_json did not parse" % m.get("id")
                        yield base
                        continue
                    yield from self._block_rows(
                        artifact,
                        base,
                        str(m.get("role") or ""),
                        content,
                        meta.get("userVisible", True) is not False,
                        tool_names,
                        opts,
                    )
        except sqlite3.DatabaseError as e:
            row = self._row(artifact, 0)
            row.turn_type = "system"
            row.text = "parser: SQLite error: %s" % e
            yield row

    # -- legacy sessions/<YYYYMMDD_HHMMSS>.jsonl ------------------------------------------
    def _parse_legacy(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_id = artifact.disk_path.name[: -len(".jsonl")]
        project_path = ""
        tool_names: dict[str, str] = {}
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            if "role" not in rec and "content" not in rec:
                session_id = str(rec.get("id") or session_id)
                project_path = str(rec.get("working_dir") or "")
                row = self._row(
                    artifact, n, session_id, project_path, ts=to_utc(rec.get("created_at"))
                )
                row.turn_type = "system"
                row.text = compact(
                    _join(
                        "session start (legacy)",
                        str(rec.get("description") or ""),
                        "%s messages" % rec["message_count"] if "message_count" in rec else "",
                    ),
                    opts.max_text_length,
                )
                yield row
                continue
            meta = rec.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
            base = self._row(artifact, n, session_id, project_path, ts=epoch(rec.get("created")))
            yield from self._block_rows(
                artifact,
                base,
                str(rec.get("role") or ""),
                rec.get("content"),
                meta.get("userVisible", True) is not False,
                tool_names,
                opts,
            )
        yield from self._errors(artifact, errors, session_id, project_path)

    def _errors(
        self, artifact: Artifact, errors: list, session_id: str = "", project_path: str = ""
    ) -> Iterator[Row]:
        if errors:
            row = self._row(artifact, errors[0][0], session_id, project_path)
            row.turn_type = "system"
            row.text = "parser: %d unparseable line(s), first at line %d" % (
                len(errors),
                errors[0][0],
            )
            yield row

    # -- logs/llm_request.*.jsonl ---------------------------------------------------------
    def _parse_llm_log(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        request: Row | None = None
        pending: list[Row] = []
        model = ""
        tool_names: dict[str, str] = {}
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            if "input" in rec or "model_config" in rec:
                cfg = rec.get("model_config") or {}
                inp = rec.get("input")
                if not isinstance(inp, dict):
                    inp = {}
                model = str(cfg.get("model_name") or inp.get("model") or "")
                msgs = inp.get("messages")
                if not isinstance(msgs, list):
                    msgs = []
                last_user = next(
                    (
                        text_of(m.get("content"))
                        for m in reversed(msgs)
                        if isinstance(m, dict) and m.get("role") == "user"
                    ),
                    "",
                )
                request = self._row(artifact, n, model=model)
                request.turn_type = "system"
                request.text = compact(
                    _join(
                        "llm request",
                        "%d messages" % len(msgs),
                        "last user: " + last_user if last_user else "",
                    ),
                    opts.max_text_length,
                )
                continue
            data = rec.get("data")
            if isinstance(data, dict) and "content" in data:
                base = self._row(artifact, n, model=model, ts=epoch(data.get("created")))
                if request is not None and not request.timestamp_utc:
                    request.timestamp_utc = base.timestamp_utc
                pending.extend(
                    self._block_rows(
                        artifact,
                        base,
                        str(data.get("role") or "assistant"),
                        data.get("content"),
                        True,
                        tool_names,
                        opts,
                    )
                )
            elif rec.get("error"):
                row = self._row(artifact, n, model=model)
                row.turn_type = "system"
                row.text = compact(
                    "llm error: "
                    + (
                        rec["error"]
                        if isinstance(rec["error"], str)
                        else compact_json(rec["error"])
                    ),
                    opts.max_text_length,
                )
                pending.append(row)
        if request is not None:
            yield request
        yield from pending
        yield from self._errors(artifact, errors)

    # -- history.txt ------------------------------------------------------------------------
    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        with open(artifact.disk_path, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line or (n == 1 and line.startswith("#V")):
                    continue
                row = self._row(artifact, n)
                row.turn_type = "user"
                row.text = compact(unescape_history(line), opts.max_text_length)
                yield row
