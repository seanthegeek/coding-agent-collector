"""Hermes Agent sessions.

Hermes (NousResearch/hermes-agent, checked at 8b66a51) keeps every
conversation of a profile, whatever the front end (CLI, TUI, desktop,
messaging gateway, cron, subagents), in one SQLite database in OpenAI
chat-completions message shape. See `analyzer/research/hermes.md`.

Files, relative to the home directory, where `<hermes>` is `.hermes`,
`.hermes_<suffix>`, `AppData/Local/hermes` or `AppData/Local/hermes_<suffix>`,
optionally followed by `profiles/<name>` (named profiles are complete homes):

* `<hermes>/state.db`, with `-wal` and `-shm` sidecars (WAL mode, schema
  version 31 at the checked commit). Migrations add columns in place, so
  every column is read with a default.
  - `sessions`: `id`, `source`, `model`, `parent_session_id`, `started_at`
    (epoch seconds), `end_reason`, `cwd`, `git_branch`, `git_repo_root`,
    `title`.
  - `messages`: `id` (write order), `session_id`, `role` (`user`,
    `assistant`, `tool`, `system`), `content` (text; list or dict content is
    stored as `"\\x00json:"` + JSON), `tool_calls` (JSON list of `{id,
    call_id, type, function: {name, arguments}}`, `arguments` a JSON
    string), `tool_call_id`, `tool_name`, `timestamp` (epoch seconds),
    `reasoning`, `reasoning_content`, `finish_reason`, `active`.
* `<hermes>/sessions/<session_id>.jsonl`: written only when `state.db` was
  replaced under a running process; one message dict per line with the same
  keys as a `messages` row (`tool_calls` may be a list rather than a string,
  `timestamp` may be absent). It records no working directory or model.

Rows: one `system` row per session (title, source, parent, end reason); per
message one `user`, `assistant`, `tool_result` (role `tool`, joined on
`tool_call_id`) or `system` row for non-empty content, a `thinking` row for
`reasoning`/`reasoning_content` with `--include-thinking`, and one `tool_use`
row per `tool_calls` entry whose text is the `command` or `path` argument,
else the arguments. Messages are ordered by `timestamp, id`. Rewind and
compaction keep the old rows with `active = 0` instead of deleting them (both
set the same flags, so the two cannot be told apart); those rows are still
evidence and are emitted with a `[rewound]` prefix on their text. The model
is the session's `model`; messages record none of their own. `project_path`
is `sessions.cwd`, else `git_repo_root`, and `git_branch` is
`sessions.git_branch`. The legacy `sessions/<id>.json` snapshots, `/save`
exports and `response_store.db` are not parsed.
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

HOME = r"(?:\.hermes(?:_[^/]+)?|AppData/Local/hermes(?:_[^/]+)?)(?:/profiles/[^/]+)?"
DB_RX = re.compile(r"^%s/state\.db$" % HOME)
JSONL_RX = re.compile(r"^%s/sessions/[^/]+\.jsonl$" % HOME)

JSON_PREFIX = "\x00json:"
ROLE_TYPES = {"user": "user", "assistant": "assistant", "tool": "tool_result", "system": "system"}


def decode_content(value):
    """`messages.content` as Hermes stored it: plain text, or list/dict
    multimodal parts behind the NUL-prefixed JSON sentinel."""
    if isinstance(value, str) and value.startswith(JSON_PREFIX):
        try:
            return json.loads(value[len(JSON_PREFIX):])
        except ValueError:
            return value[len(JSON_PREFIX):]
    return value


def content_text(value) -> str:
    content = decode_content(value)
    if isinstance(content, list):
        content = [{"type": "image"} if isinstance(b, dict) and b.get("type") in ("image_url", "input_image")
                   else b for b in content]
    return text_of(content)


def _json(value, default):
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return default


def call_summary(arguments) -> str:
    args = _json(arguments, arguments)
    if isinstance(args, dict):
        for k in ("command", "path", "file_path", "url", "query"):
            if args.get(k) not in (None, ""):
                return str(args[k])
        return compact_json(args)
    return args if isinstance(args, str) else compact_json(args)


def _join(*parts: str) -> str:
    return " | ".join(x for x in parts if x)


class HermesParser(Parser):
    agent = "hermes"
    name = "hermes"

    def wants(self, artifact: Artifact) -> bool:
        return bool(DB_RX.match(artifact.rel) or JSONL_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if DB_RX.match(artifact.rel):
            yield from self._parse_db(artifact, opts)
        else:
            yield from self._parse_jsonl(artifact, opts)

    def _row(self, artifact: Artifact, line: int, session: dict, ts: str = "") -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.session_id = str(session.get("id") or "")
        row.project_path = str(session.get("cwd") or session.get("git_repo_root") or "")
        row.git_branch = str(session.get("git_branch") or "")
        row.model = str(session.get("model") or "")
        row.timestamp_utc = ts
        return row

    def _system(self, artifact: Artifact, line: int, session: dict, text: str) -> Row:
        row = self._row(artifact, line, session)
        row.turn_type = "system"
        row.text = text
        return row

    def _message_rows(self, artifact: Artifact, m: dict, session: dict, line: int,
                      tool_names: dict[str, str], opts: Options) -> Iterator[Row]:
        ts = to_utc(m.get("timestamp"))
        role = str(m.get("role") or "")
        marker = "[rewound] " if m.get("active", 1) in (0, "0", False) else ""

        def mk(turn_type: str, text: str) -> Row:
            row = self._row(artifact, line, session, ts)
            row.turn_type = turn_type
            row.text = compact(marker + text, opts.max_text_length)
            return row

        if opts.include_thinking:
            reasoning = m.get("reasoning") or m.get("reasoning_content")
            if reasoning:
                yield mk("thinking", str(reasoning))
        text = content_text(m.get("content"))
        turn_type = ROLE_TYPES.get(role, "system")
        if turn_type == "tool_result":
            row = mk("tool_result", text)
            row.tool_use_id = str(m.get("tool_call_id") or "")
            row.tool_name = str(m.get("tool_name") or tool_names.get(row.tool_use_id, ""))
            yield row
        elif text:
            if turn_type == "system" and role not in ("", "system"):
                text = "%s: %s" % (role, text)
            yield mk(turn_type, text)
        calls = _json(m.get("tool_calls"), [])
        if isinstance(calls, dict):
            calls = [calls]
        if not isinstance(calls, list):
            yield mk("system", "parser: message %s tool_calls did not parse" % line)
            return
        for c in calls:
            if not isinstance(c, dict):
                continue
            fn = c.get("function") if isinstance(c.get("function"), dict) else {}
            row = mk("tool_use", call_summary(fn.get("arguments")))
            row.tool_use_id = str(c.get("id") or c.get("call_id") or "")
            row.tool_name = str(fn.get("name") or "")
            tool_names[row.tool_use_id] = row.tool_name
            yield row

    # -- state.db ------------------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            yield self._system(artifact, 0, {}, "parser: not a SQLite database")
            return
        try:
            with open_copy(artifact.disk_path) as con:
                tables = table_names(con)
                if "messages" not in tables:
                    return
                sessions: dict[str, dict] = {}
                if "sessions" in tables:
                    for s in con.execute("select rowid as _rowid, * from sessions order by started_at, rowid"):
                        s = dict(s)
                        sessions[str(s.get("id") or "")] = s
                        row = self._system(artifact, s["_rowid"], s, compact(_join(
                            "session start", str(s.get("title") or ""),
                            "source=%s" % s["source"] if s.get("source") else "",
                            "parent=%s" % s["parent_session_id"] if s.get("parent_session_id") else "",
                            "end=%s" % s["end_reason"] if s.get("end_reason") else "",
                        ), opts.max_text_length))
                        row.timestamp_utc = to_utc(s.get("started_at"))
                        yield row
                tool_names: dict[str, str] = {}
                for m in con.execute("select * from messages order by timestamp, id"):
                    m = dict(m)
                    sid = str(m.get("session_id") or "")
                    session = sessions.get(sid) or {"id": sid}
                    yield from self._message_rows(artifact, m, session, m.get("id") or 0, tool_names, opts)
        except sqlite3.DatabaseError as e:
            yield self._system(artifact, 0, {}, "parser: SQLite error: %s" % e)

    # -- sessions/<id>.jsonl -------------------------------------------------------------
    def _parse_jsonl(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list[tuple] = []
        session = {"id": artifact.disk_path.name[: -len(".jsonl")]}
        tool_names: dict[str, str] = {}
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            yield from self._message_rows(artifact, rec, session, n, tool_names, opts)
        if errors:
            yield self._system(artifact, errors[0][0], session,
                               "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0]))
