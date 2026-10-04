"""Codex CLI transcripts, and the rollout format shared with its forks.

Validated against a real install (Codex CLI, October 2026). Files, under
`~/.codex` for Codex (`RolloutParser.home_prefix` for a fork):

* `sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`, older releases
  wrote `sessions/rollout-*.jsonl`; `archived_sessions/` holds archived
  threads in the same layout (codex `rollout/src/lib.rs:87` at 3e23877).
  Cold rollouts may be zstd-compressed to `.jsonl.zst`
  (`rollout/src/compression.rs:29`); those need the `zstandard` package,
  imported lazily, and without it each becomes one `system` row. A
  truncated zstd frame yields the lines decoded before the cut. Each line is
  `{timestamp, ordinal, type, payload}` with `timestamp` ISO 8601 Z. Types:
  - `session_meta`: payload `id` (session id), `timestamp`, `cwd`,
    `originator`, `cli_version`, `model_provider`, optional `git`
    (`branch`, `commit_hash`, `repository_url`).
  - `turn_context`: payload `turn_id`, `cwd`, `model`, `approval_policy`,
    `sandbox_policy`; updates the current project path and model.
  - `response_item`: payload `type` is `message` (`role` user, assistant or
    developer; `content` blocks with `text`), `function_call` or
    `custom_tool_call` (`name`, `call_id`, `arguments` or `input`),
    `function_call_output` or `custom_tool_call_output` (`call_id`,
    `output`), `local_shell_call` (`action.command`), `web_search_call`,
    `reasoning` (`summary`).
  - `event_msg`: payload `type` task_started, task_complete, token_count,
    item_completed and others; task_started and task_complete become system
    rows, the rest are skipped because the response_item records already
    carry the content.
  - `world_state`, `token_usage_record`: skipped.
  Until `session_meta` is read, the session id is the UUID at the end of
  the file name, so a rollout cut before its first line is still attributed.
* `history.jsonl`: `{session_id, text, ts}` per prompt, `ts` epoch seconds.
* Forks only, when `ledger_name` is set: an import ledger
  `{"records": [{source_path, content_sha256, imported_thread_id,
  imported_at, source_modified_at?}]}` (times epoch seconds), one `system`
  row per record. See `open_interpreter.py`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

ROLLOUT_TMPL = r"^%s/(?:archived_)?sessions/(?:.*/)?rollout-[^/]*\.jsonl(?:\.zst)?$"
ROLLOUT_RX = re.compile(ROLLOUT_TMPL % re.escape(".codex"))
HISTORY_REL = ".codex/history.jsonl"
UUID_TAIL_RX = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    r"\.jsonl(?:\.zst)?$"
)

CALL_TYPES = ("function_call", "custom_tool_call", "local_shell_call", "web_search_call")
OUTPUT_TYPES = ("function_call_output", "custom_tool_call_output", "local_shell_call_output")


def call_summary(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        action = payload.get("action") or {}
        cmd = action.get("command")
        if isinstance(cmd, list):
            return " ".join(str(c) for c in cmd)
        return str(cmd or compact_json(action))
    if ptype == "web_search_call":
        action = payload.get("action") or {}
        return str(action.get("query") or compact_json(action))
    for key in ("arguments", "input"):
        v = payload.get(key)
        if v not in (None, ""):
            return v if isinstance(v, str) else compact_json(v)
    return compact_json(
        {k: v for k, v in payload.items() if k not in ("type", "id", "call_id", "name", "status")}
    )


def call_name(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        return "shell"
    if ptype == "web_search_call":
        return "web_search"
    return str(payload.get("name") or ptype or "")


def _zstd_module():
    """The `zstandard` module, or None when it is not installed."""
    try:
        import zstandard
    except ImportError:
        return None
    return zstandard


def _decode_line(n: int, raw: bytes, errors: list) -> dict | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        rec = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError as e:
        errors.append((n, str(e)))
        return None
    return rec if isinstance(rec, dict) else None


class TruncatedFrame(Exception):
    pass


def iter_zst_chunks(fh, zstd) -> Iterator[bytes]:
    """Decompressed bytes of every zstd frame in `fh`, streamed. Raises
    `zstd.ZstdError` on corrupt input and `TruncatedFrame` when the file ends
    inside a frame (the stream reader would end silently instead)."""
    dctx = zstd.ZstdDecompressor()
    dobj = dctx.decompressobj()
    open_frame = False
    while True:
        data = fh.read(1 << 16)
        if not data:
            break
        while data:
            out = dobj.decompress(data)
            open_frame = True
            if out:
                yield out
            if getattr(dobj, "eof", False):
                data = dobj.unused_data
                dobj = dctx.decompressobj()
                open_frame = False
            else:
                data = b""
    if open_frame and hasattr(dobj, "eof"):
        raise TruncatedFrame("file ends inside a zstd frame")


def iter_zst_jsonl(path, errors: list, zstd) -> Iterator[tuple[int, dict]]:
    """`iter_jsonl` over a zstd-compressed file, streamed. A corrupt or
    truncated frame becomes one entry in `errors`; the lines decoded before
    it are still yielded, and a line cut by the damage is a bad line."""
    n = 0
    buf = b""
    with open(path, "rb") as fh:
        try:
            for chunk in iter_zst_chunks(fh, zstd):
                buf += chunk
                lines = buf.split(b"\n")
                buf = lines.pop()
                for raw in lines:
                    n += 1
                    rec = _decode_line(n, raw, errors)
                    if rec is not None:
                        yield n, rec
        except (zstd.ZstdError, TruncatedFrame) as e:
            errors.append((n + 1, "zstd: %s" % e))
    if buf.strip():
        n += 1
        rec = _decode_line(n, buf, errors)
        if rec is not None:
            yield n, rec


class RolloutParser(Parser):
    """Codex rollouts and prompt history under `home_prefix`. Codex forks
    that keep the format subclass this with their own agent and home."""

    home_prefix = ".codex"
    ledger_name = ""  # import ledger file under home_prefix; empty when the agent has none

    def __init__(self) -> None:
        self.rollout_rx = re.compile(ROLLOUT_TMPL % re.escape(self.home_prefix))
        self.history_rel = self.home_prefix + "/history.jsonl"
        self.ledger_rel = self.home_prefix + "/" + self.ledger_name if self.ledger_name else ""

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return (
            rel == self.history_rel
            or bool(self.rollout_rx.match(rel))
            or bool(self.ledger_rel and rel == self.ledger_rel)
        )

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == self.history_rel:
            yield from self._parse_history(artifact, opts)
        elif self.ledger_rel and artifact.rel == self.ledger_rel:
            yield from self._parse_ledger(artifact, opts)
        else:
            yield from self._parse_rollout(artifact, opts)

    def _system(self, artifact: Artifact, text: str, session_id: str = "", line: int = 0) -> Row:
        row = self.base_row(artifact)
        row.turn_type = "system"
        row.session_id = session_id
        row.source_line = line
        row.text = text
        return row

    def _parse_ledger(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        try:
            with open(artifact.disk_path, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", errors="replace"))
        except (OSError, ValueError) as e:
            yield self._system(artifact, "parser: unreadable import ledger: %s" % e)
            return
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            yield self._system(artifact, "parser: import ledger has no records list")
            return
        for i, rec in enumerate(records, 1):
            if not isinstance(rec, dict):
                continue
            # source_line is the record's position in `records`, not a file line.
            row = self._system(artifact, "", str(rec.get("imported_thread_id") or ""), i)
            row.timestamp_utc = to_utc(rec.get("imported_at"))
            text = "imported session from %s sha256=%s" % (
                rec.get("source_path") or "",
                rec.get("content_sha256") or "",
            )
            modified = to_utc(rec.get("source_modified_at"))
            if modified:
                text += " source_modified=%s" % modified
            row.text = compact(text, opts.max_text_length)
            yield row

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("ts"))
            row.session_id = str(rec.get("session_id") or "")
            row.turn_type = "user"
            row.text = compact(rec.get("text"), opts.max_text_length)
            yield row

    def _parse_rollout(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        m = UUID_TAIL_RX.search(artifact.rel)
        session_id = m.group(1) if m else ""  # until session_meta says otherwise
        if artifact.rel.endswith(".zst"):
            zstd = _zstd_module()
            if zstd is None:
                yield self._system(
                    artifact,
                    "parser: compressed rollout not read: zstandard package not installed",
                    session_id,
                )
                return
            records = iter_zst_jsonl(artifact.disk_path, errors, zstd)
        else:
            records = iter_jsonl(artifact.disk_path, errors)
        cwd = ""
        model = ""
        branch = ""
        for n, rec in records:
            rtype = rec.get("type")
            payload = rec.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            def base() -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(rec.get("timestamp"))
                row.session_id = session_id
                row.project_path = cwd
                row.git_branch = branch
                row.model = model
                return row

            if rtype == "session_meta":
                session_id = str(payload.get("id") or payload.get("session_id") or session_id)
                cwd = str(payload.get("cwd") or cwd)
                git = payload.get("git") or {}
                if isinstance(git, dict):
                    branch = str(git.get("branch") or branch)
                row = base()
                row.timestamp_utc = to_utc(payload.get("timestamp") or rec.get("timestamp"))
                row.turn_type = "system"
                row.text = compact(
                    "session start: %s %s provider=%s cwd=%s"
                    % (
                        payload.get("originator") or "codex",
                        payload.get("cli_version") or "",
                        payload.get("model_provider") or "",
                        cwd,
                    ),
                    opts.max_text_length,
                )
                yield row
            elif rtype == "turn_context":
                cwd = str(payload.get("cwd") or cwd)
                model = str(payload.get("model") or model)
            elif rtype == "response_item":
                ptype = payload.get("type")
                if ptype == "message":
                    role = payload.get("role")
                    text = text_of(payload.get("content"))
                    if not text:
                        continue
                    row = base()
                    row.turn_type = (
                        "user"
                        if role == "user"
                        else "assistant"
                        if role == "assistant"
                        else "system"
                    )
                    if role not in ("user", "assistant"):
                        text = "%s: %s" % (role, text)
                    yield self._fill(row, text, opts)
                elif ptype in CALL_TYPES:
                    row = base()
                    row.turn_type = "tool_use"
                    row.tool_name = call_name(payload)
                    row.tool_use_id = str(payload.get("call_id") or payload.get("id") or "")
                    yield self._fill(row, call_summary(payload), opts)
                elif ptype in OUTPUT_TYPES:
                    row = base()
                    row.turn_type = "tool_result"
                    row.tool_use_id = str(payload.get("call_id") or "")
                    yield self._fill(row, text_of(payload.get("output")), opts)
                elif ptype == "reasoning" and opts.include_thinking:
                    row = base()
                    row.turn_type = "thinking"
                    yield self._fill(
                        row,
                        text_of(payload.get("summary")) or text_of(payload.get("content")),
                        opts,
                    )
            elif rtype == "event_msg":
                ptype = payload.get("type")
                if ptype == "task_started":
                    row = base()
                    row.turn_type = "system"
                    yield self._fill(
                        row, "task_started turn=%s" % (payload.get("turn_id") or ""), opts
                    )
                elif ptype == "task_complete":
                    row = base()
                    row.turn_type = "system"
                    yield self._fill(
                        row,
                        "task_complete turn=%s duration_ms=%s"
                        % (payload.get("turn_id") or "", payload.get("duration_ms") or ""),
                        opts,
                    )
        if errors:
            yield self._system(
                artifact,
                "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0]),
                session_id,
                errors[0][0],
            )

    @staticmethod
    def _fill(row: Row, text: str, opts: Options) -> Row:
        row.text = compact(text, opts.max_text_length)
        return row


class CodexParser(RolloutParser):
    agent = "codex-cli"
    name = "codex-cli"
    home_prefix = ".codex"
