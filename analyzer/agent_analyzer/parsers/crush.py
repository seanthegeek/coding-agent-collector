"""Crush sessions.

Crush (charmbracelet/crush, checked at ca6ae26) keeps one SQLite database per
project, written through sqlc with goose migrations. See
`analyzer/research/crush.md`.

Files:

* `<project>/.crush/crush.db`, with `-wal` and `-shm` sidecars
  (`journal_mode=WAL`, so recent messages may exist only in the sidecar).
  The collector gathers it through its project catalog, so `artifact.rel`
  is `.crush/crush.db` relative to the project directory; a database under a
  home (Crush run in `~`) has the same relative path. `project_path` is the
  directory holding `.crush`, taken from the original path, because the
  database records no working directory.
  - `sessions`: `id`, `parent_session_id`, `title`, `message_count`,
    `prompt_tokens`, `completion_tokens`, `cost`, `created_at` (epoch
    seconds).
  - `messages`: `id`, `session_id`, `role` (`user`, `assistant`, `system`,
    `tool`), `parts` (JSON array of `{"type", "data"}`), `model`,
    `provider`, `prism_model_id`, `created_at`, `finished_at` (seconds).
  - Part `data` keys: `text` {`text`, `hidden`}; `reasoning` {`thinking`,
    `started_at`}; `tool_call` {`id`, `name`, `input`}; `tool_result`
    {`tool_call_id`, `name`, `content`, `is_error`}; `finish` {`reason`,
    `time`, `message`, `details`}; `shell_command` {`command`, `output`,
    `exit_code`}; `image_url` {`url`}; `binary` {`Path`, `MIMEType`}.
* `.local/share/crush/projects.json` and `AppData/Local/crush/projects.json`:
  `{"projects": [{"path", "data_dir", "last_accessed"}]}`, the registry of
  every project Crush has opened.

Rows: one `system` row per session (title, parent, counts); one row per part,
`text` by message role (`tool` and `system` roles become `system`),
`reasoning` as `thinking` with `--include-thinking`, `tool_call` as
`tool_use`, `tool_result` as `tool_result` joined on `tool_call_id`, and
`shell_command` as `system`. A `finish` part becomes a `system` row only
when the turn ended abnormally (max_tokens, canceled, error,
content_filter, unknown) or carries a message, since every message ends with
one. Parts carry no timestamp of their own: they inherit the message's
`created_at`, except tool calls and results, which use `finished_at` or the
finish part's `time` when set. No git branch is recorded.
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
from .base import Options, Parser, compact_json

DB_RX = re.compile(r"(^|/)\.crush/crush\.db$")
PROJECTS_RX = re.compile(r"^(\.local/share/crush|AppData/Local/crush)/projects\.json$")
ORIGINAL_RX = re.compile(r"^(.*)[\\/]\.crush[\\/]crush\.db$")

NORMAL_FINISH = ("", "end_turn", "tool_use", "stop")


def _join(*parts: str) -> str:
    return " | ".join(x for x in parts if x)


def project_of(original: str) -> str:
    m = ORIGINAL_RX.match(original or "")
    return m.group(1) if m else ""


class CrushParser(Parser):
    agent = "crush"
    name = "crush"

    def wants(self, artifact: Artifact) -> bool:
        return bool(DB_RX.search(artifact.rel) or PROJECTS_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if PROJECTS_RX.match(artifact.rel):
            yield from self._parse_projects(artifact, opts)
        else:
            yield from self._parse_db(artifact, opts)

    def _system(self, artifact: Artifact, text: str, line: int = 0) -> Row:
        row = self.base_row(artifact)
        row.turn_type = "system"
        row.source_line = line
        row.text = text
        return row

    # -- projects.json ---------------------------------------------------------------
    def _parse_projects(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        try:
            with open(artifact.disk_path, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", errors="replace"))
        except ValueError as e:
            yield self._system(artifact, "parser: projects.json did not parse: %s" % e)
            return
        projects = data.get("projects") if isinstance(data, dict) else None
        for n, p in enumerate(projects if isinstance(projects, list) else [], 1):
            if not isinstance(p, dict):
                continue
            row = self._system(artifact, "", n)
            row.timestamp_utc = to_utc(p.get("last_accessed"))
            row.project_path = str(p.get("path") or "")
            row.text = compact(
                _join(
                    "crush project last accessed",
                    "data_dir=%s" % p["data_dir"] if p.get("data_dir") else "",
                ),
                opts.max_text_length,
            )
            yield row

    # -- .crush/crush.db ---------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        project_path = project_of(artifact.original)
        if not is_sqlite(artifact.disk_path):
            row = self._system(artifact, "parser: not a SQLite database")
            row.project_path = project_path
            yield row
            return
        try:
            with open_copy(artifact.disk_path) as con:
                tables = table_names(con)
                if "messages" not in tables:
                    return
                if "sessions" in tables:
                    for s in con.execute(
                        "select rowid as _rowid, * from sessions order by created_at, rowid"
                    ):
                        s = dict(s)
                        row = self._system(artifact, "", s["_rowid"])
                        row.session_id = str(s.get("id") or "")
                        row.project_path = project_path
                        row.timestamp_utc = to_utc(s.get("created_at"))
                        row.text = compact(
                            _join(
                                "session start",
                                s.get("title") or "",
                                "parent=%s" % s["parent_session_id"]
                                if s.get("parent_session_id")
                                else "",
                                "%s messages" % s["message_count"]
                                if s.get("message_count") is not None
                                else "",
                                "tokens in=%s out=%s"
                                % (s.get("prompt_tokens") or 0, s.get("completion_tokens") or 0),
                                "cost=%s" % s["cost"] if s.get("cost") else "",
                            ),
                            opts.max_text_length,
                        )
                        yield row
                for m in con.execute(
                    "select rowid as _rowid, * from messages order by created_at, rowid"
                ):
                    yield from self._message_rows(artifact, dict(m), project_path, opts)
        except sqlite3.DatabaseError as e:
            row = self._system(artifact, "parser: SQLite error: %s" % e)
            row.project_path = project_path
            yield row

    def _message_rows(
        self, artifact: Artifact, m: dict, project_path: str, opts: Options
    ) -> Iterator[Row]:
        role = str(m.get("role") or "")
        provider, model = m.get("provider") or "", m.get("model") or m.get("prism_model_id") or ""
        model = "%s/%s" % (provider, model) if provider and model else model
        created = to_utc(m.get("created_at"))

        def base(ts: str = "") -> Row:
            row = self.base_row(artifact)
            row.source_line = m["_rowid"]
            row.session_id = str(m.get("session_id") or "")
            row.project_path = project_path
            row.model = model
            row.timestamp_utc = ts or created
            return row

        try:
            parts = json.loads(m.get("parts") or "[]")
            if not isinstance(parts, list):
                raise ValueError("parts is not a list")
        except ValueError as e:
            row = base()
            row.turn_type = "system"
            row.text = "parser: message %s parts did not parse: %s" % (m.get("id"), e)
            yield row
            return
        finished = to_utc(m.get("finished_at")) if m.get("finished_at") else ""
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "finish":
                t = (p.get("data") or {}).get("time")
                if t and not finished:
                    finished = to_utc(t)
        text_type = role if role in ("user", "assistant") else "system"

        for p in parts:
            if not isinstance(p, dict):
                continue
            kind = p.get("type")
            d = p.get("data")
            if not isinstance(d, dict):
                d = {}
            row = base()
            if kind == "text":
                row.turn_type = text_type
                text = d.get("text") or ""
                if role not in ("user", "assistant"):
                    text = "%s: %s" % (role, text)
                if d.get("hidden"):
                    text = "[hidden] " + text
            elif kind == "reasoning":
                if not opts.include_thinking or not d.get("thinking"):
                    continue
                row.turn_type = "thinking"
                row.timestamp_utc = to_utc(d.get("started_at")) or created
                text = d.get("thinking")
            elif kind == "tool_call":
                row.turn_type = "tool_use"
                row.timestamp_utc = finished or created
                row.tool_name = str(d.get("name") or "")
                row.tool_use_id = str(d.get("id") or "")
                text = (
                    d.get("input")
                    if isinstance(d.get("input"), str)
                    else compact_json(d.get("input"))
                )
            elif kind == "tool_result":
                row.turn_type = "tool_result"
                row.timestamp_utc = finished or created
                row.tool_name = str(d.get("name") or "")
                row.tool_use_id = str(d.get("tool_call_id") or "")
                text = d.get("content") or ""
                if not text and d.get("mime_type"):
                    text = "[%s]" % d["mime_type"]
                if d.get("is_error"):
                    text = "[error] " + text
            elif kind == "finish":
                reason = str(d.get("reason") or "")
                if reason in NORMAL_FINISH and not d.get("message"):
                    continue
                row.turn_type = "system"
                row.timestamp_utc = to_utc(d.get("time")) if d.get("time") else created
                text = _join("finish: " + reason, d.get("message") or "", d.get("details") or "")
            elif kind == "shell_command":
                row.turn_type = "system"
                text = _join(
                    "shell: " + str(d.get("command") or ""),
                    "exit=%s" % d["exit_code"] if "exit_code" in d else "",
                    d.get("output") or "",
                )
            elif kind == "image_url":
                row.turn_type = text_type
                url = str(d.get("url") or "")
                text = "[image] " + (url.split(",", 1)[0] if url.startswith("data:") else url)
            elif kind == "binary":
                row.turn_type = text_type
                text = "[binary] " + _join(
                    str(d.get("Path") or d.get("path") or ""),
                    str(d.get("MIMEType") or d.get("mime_type") or ""),
                )
            else:
                row.turn_type = "system"
                text = "%s: %s" % (kind, compact_json(d))
            row.text = compact(text, opts.max_text_length)
            yield row
