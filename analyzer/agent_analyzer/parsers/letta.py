"""Letta Code transcripts.

Validated against source, letta-ai/letta-code at 77faf36e (October 2026),
with a synthetic fixture; see `research/letta.md`. Letta keeps
conversations on the Letta server by default; three local stores are
parsed:

* `~/.letta/lc-local-backend/conversations/<base64url key>/messages.jsonl`
  (local backend only; the key is `conversation:<id>` or
  `default:<agent id>`). `manifest.json` `message_format`
  `pi-session-entry-jsonl` (schema 2): pi's session format, read with
  `pi.read_session` and `pi.entry_rows`. Header `id` (conversation id,
  falling back to the decoded directory name) and `cwd`; entries `message`
  and `compaction`. `message.id` starts `letta-msg-` and a message may be
  re-appended with the same `id` as a replacement snapshot, so only the
  last copy of each `message.id` is kept. Schema 1 files
  (`pi-ai-message-jsonl`, one bare message per line, no header) are read
  too, timed by `message.metadata.created_at` or `message.timestamp`.
* `~/.letta/transcripts/<agent>/<conversation>/transcript.jsonl` (both
  backends, appended after each turn): `kind` user, assistant, reasoning
  (a `thinking` row, opt-in) or error (system) with `text`; or
  `kind: "tool_call"` with `name`, `argsText`, `resultText`, `resultOk`,
  emitted as a tool_use and a tool_result with no tool id. Every line has
  `captured_at` (ISO 8601 Z, shared by a turn's lines). No model and no
  cwd: the session id is the conversation directory name and the project
  path is the `project` of the `sessions.jsonl` line with the same
  `agent_id` and the latest `timestamp` at or before `captured_at`, a
  heuristic. When the same conversation's `messages.jsonl` was collected,
  the transcript is not repeated: one system row points at it.
* `~/.letta/sessions.jsonl`: per CLI session, a start line and an exit
  line with `agent_id`, `session_id`, `timestamp` (ms), `project`,
  `model`, `provider`, and on exit `message_count`, `tool_call_count`,
  `exit_reason`, `duration.wall_ms`. One system row per line.

Not parsed: `logs/chunk-logs/` (stream chunks cut to 200 characters) and
the retired Letta server's `sqlite.db` (column encodings unverified).
"""
from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, iter_jsonl
from .pi import SessionFile, entry_rows, error_row, read_session

TRANSCRIPT_RX = re.compile(r"^\.letta/transcripts/([^/]+)/([^/]+)/transcript\.jsonl$")
LOCAL_RX = re.compile(r"^\.letta/lc-local-backend/conversations/([^/]+)/messages\.jsonl$")
SESSIONS_REL = ".letta/sessions.jsonl"
CONVERSATIONS_REL = ".letta/lc-local-backend/conversations"


def decode_key(name: str) -> str:
    """`conversation:<id>` or `default:<agent id>` from a base64url
    directory name, or empty."""
    try:
        return base64.urlsafe_b64decode(name + "=" * (-len(name) % 4)).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return ""


def sanitize(segment: str) -> str:
    """The transcript directory name Letta derives from an id."""
    s = re.sub(r"[^a-zA-Z0-9._-]", "_", segment).strip()
    return s or "unknown"


def _transcript_key(agent_dir: str, conv_dir: str, key: str) -> bool:
    kind, _, ident = key.partition(":")
    if kind == "conversation":
        return sanitize(ident) == conv_dir
    if kind == "default":
        return conv_dir == "default" and sanitize(ident) == agent_dir
    return False


def _bare_messages(session: SessionFile) -> SessionFile:
    """Schema 1: every line a bare pi-ai message. Wrapped as entries."""
    out = SessionFile()
    out.errors = session.errors
    for n, rec in session.entries:
        meta = rec.get("metadata") if isinstance(rec.get("metadata"), dict) else {}
        out.entries.append((n, {"type": "message", "timestamp": meta.get("created_at"), "message": rec}))
    return out


def _last_snapshots(session: SessionFile) -> SessionFile:
    """Keep only the last entry for each `message.id`."""
    last: dict[str, int] = {}
    for i, (_, rec) in enumerate(session.entries):
        msg = rec.get("message")
        if isinstance(msg, dict) and msg.get("id"):
            last[str(msg.get("id"))] = i
    out = SessionFile()
    out.header, out.header_line, out.errors = session.header, session.header_line, session.errors
    for i, (n, rec) in enumerate(session.entries):
        msg = rec.get("message")
        if isinstance(msg, dict) and msg.get("id") and last[str(msg.get("id"))] != i:
            continue
        out.entries.append((n, rec))
    return out


class LettaParser(Parser):
    agent = "letta"
    name = "letta"

    def wants(self, artifact: Artifact) -> bool:
        return (artifact.rel == SESSIONS_REL or bool(TRANSCRIPT_RX.match(artifact.rel))
                or bool(LOCAL_RX.match(artifact.rel)))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == SESSIONS_REL:
            yield from self._parse_sessions(artifact, opts)
            return
        m = LOCAL_RX.match(artifact.rel)
        if m:
            yield from self._parse_local(artifact, m.group(1), opts)
            return
        m = TRANSCRIPT_RX.match(artifact.rel)
        yield from self._parse_transcript(artifact, m.group(1), m.group(2), opts)

    # -- local backend ----------------------------------------------------

    def _parse_local(self, artifact: Artifact, dirname: str, opts: Options) -> Iterator[Row]:
        session = read_session(artifact.disk_path)
        key = decode_key(dirname)
        sid = str(session.header.get("id") or key.partition(":")[2])
        cwd = str(session.header.get("cwd") or "")
        if not session.header and session.entries and all(
                "role" in rec and rec.get("type") != "message" for _, rec in session.entries):
            session = _bare_messages(session)
        else:
            session = _last_snapshots(session)
        if session.header:
            row = self.base_row(artifact)
            row.source_line = session.header_line
            row.timestamp_utc = to_utc(session.header.get("timestamp"))
            row.session_id, row.project_path, row.turn_type = sid, cwd, "system"
            row.text = compact("letta local-backend conversation start: %s cwd=%s" % (key or sid, cwd),
                               opts.max_text_length)
            yield row
        yield from entry_rows(self, artifact, session, opts, sid, cwd)
        if session.errors:
            yield error_row(self, artifact, session.errors, sid, cwd)

    # -- reflection transcript ------------------------------------------

    def _local_twin(self, artifact: Artifact, agent_dir: str, conv_dir: str) -> Path | None:
        base = artifact.home.disk_path / CONVERSATIONS_REL
        if base.is_symlink() or not base.is_dir():
            return None
        for d in sorted(base.iterdir()):
            f = d / "messages.jsonl"
            if d.is_symlink() or f.is_symlink() or not f.is_file():
                continue
            if _transcript_key(agent_dir, conv_dir, decode_key(d.name)):
                return f
        return None

    def _sessions(self, artifact: Artifact, agent_dir: str) -> list[tuple[str, str]]:
        """(timestamp, project) of the sessions.jsonl lines for this agent,
        sorted by time."""
        f = artifact.home.disk_path / SESSIONS_REL
        if f.is_symlink() or not f.is_file() or (artifact.home.disk_path / ".letta").is_symlink():
            return []
        out = []
        for _, rec in iter_jsonl(f, []):
            if sanitize(str(rec.get("agent_id") or "")) == agent_dir and rec.get("project"):
                ts = to_utc(rec.get("timestamp"))
                if ts:
                    out.append((ts, str(rec.get("project"))))
        return sorted(out)

    def _parse_transcript(self, artifact: Artifact, agent_dir: str, conv_dir: str, opts: Options) -> Iterator[Row]:
        twin = self._local_twin(artifact, agent_dir, conv_dir)
        if twin is not None:
            row = self.base_row(artifact)
            row.session_id, row.turn_type = conv_dir, "system"
            row.text = compact("letta transcript for agent %s not repeated: the same conversation's "
                               "local-backend messages.jsonl was collected (%s)" % (
                                   agent_dir, twin.relative_to(artifact.home.disk_path).as_posix()),
                               opts.max_text_length)
            yield row
            return
        sessions = self._sessions(artifact, agent_dir)
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            ts = to_utc(rec.get("captured_at"))
            project = ""
            for sts, sproj in sessions:
                if ts and sts <= ts:
                    project = sproj
                elif ts:
                    break

            def base() -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = ts
                row.session_id = conv_dir
                row.project_path = project
                return row

            kind = rec.get("kind")
            text = str(rec.get("text") or "")
            if kind in ("user", "assistant"):
                row = base()
                row.turn_type = kind
                row.text = compact(text, opts.max_text_length)
                yield row
            elif kind == "reasoning":
                if opts.include_thinking:
                    row = base()
                    row.turn_type = "thinking"
                    row.text = compact(text, opts.max_text_length)
                    yield row
            elif kind == "error":
                row = base()
                row.turn_type = "system"
                row.text = compact("error: " + text, opts.max_text_length)
                yield row
            elif kind == "tool_call":
                name = str(rec.get("name") or "")
                row = base()
                row.turn_type, row.tool_name = "tool_use", name
                row.text = compact(rec.get("argsText"), opts.max_text_length)
                yield row
                if "resultText" in rec or "resultOk" in rec:
                    result = str(rec.get("resultText") or "")
                    if rec.get("resultOk") is False:
                        result = "[error] " + result
                    row = base()
                    row.turn_type, row.tool_name = "tool_result", name
                    row.text = compact(result, opts.max_text_length)
                    yield row
        if errors:
            yield error_row(self, artifact, errors, conv_dir)

    # -- sessions.jsonl --------------------------------------------------

    def _parse_sessions(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("timestamp"))
            row.session_id = str(rec.get("session_id") or "")
            row.project_path = str(rec.get("project") or "")
            row.model = str(rec.get("model") or "")
            row.turn_type = "system"
            dur = rec.get("duration") if isinstance(rec.get("duration"), dict) else {}
            if "exit_reason" in rec or "message_count" in rec:
                text = "letta session end: agent=%s exit_reason=%s messages=%s tool_calls=%s wall_ms=%s" % (
                    rec.get("agent_id") or "", rec.get("exit_reason") or "", rec.get("message_count", ""),
                    rec.get("tool_call_count", ""), dur.get("wall_ms", ""))
            else:
                text = "letta session start: agent=%s provider=%s model=%s project=%s" % (
                    rec.get("agent_id") or "", rec.get("provider") or "", row.model, row.project_path)
            row.text = compact(text, opts.max_text_length)
            yield row
        if errors:
            yield error_row(self, artifact, errors)
