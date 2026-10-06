"""Ollama desktop chats and REPL prompt history.

ollama/ollama at v0.35.1 (b0c1ca4), read from source with a synthetic
fixture; the desktop app does not exist on Linux, so no real `db.sqlite`
was checked. See `research/ollama.md`. Files, relative to the home:

* `Library/Application Support/Ollama/db.sqlite` (macOS) and
  `AppData/Local/Ollama/db.sqlite` (Windows, `%LOCALAPPDATA%`), written by
  the desktop app only, with `-wal` and `-shm` sidecars that `sqlite_util`
  reads beside the database. Schema versions 16 to 19 have the same
  transcript tables (the migrations add `settings` columns only), and no
  `settings` column is read.
  - `messages`: `id`, `chat_id`, `role` (`user`, `assistant`, `tool`,
    `system`), `content`, `thinking`, `model_name`, `created_at`,
    `tool_result` (JSON, the fallback text of a `tool` row).
  - `tool_calls`: `id`, `message_id`, `function_name`,
    `function_arguments` (a JSON string).
  - `attachments`: `message_id`, `filename`, and the byte length of
    `data`, computed in SQL so the file contents are never read.
  `created_at` is go-sqlite3's text form of a Go `time.Time`,
  `2006-01-02 15:04:05.999999999-07:00` (local time with an offset,
  trailing fraction zeros trimmed), converted to UTC.
* `.ollama/history`: the `ollama run` REPL's readline history, one entry
  per line, with no timestamp, session, working directory or model. Only
  the last 100 entries are kept, and a pasted multi-line prompt is written
  as several physical lines, so the file cannot tell one multi-line prompt
  from several prompts; each non-empty line is one row.

Rows from `db.sqlite`, ordered by `chat_id` then `messages.id` (the order
the app reads them; ids are reassigned on every save but the order is
kept): `user` rows, with `[attachment: <filename>, <n> bytes]` appended per
attachment; for an `assistant` message a `thinking` row (only with
`include_thinking`), an `assistant` row when `content` is non-empty, and
one `tool_use` row per `tool_calls` row, whose text is the `url` or
`query` argument when present, else the arguments; `tool` messages as
`tool_result`; `system` and unknown roles as `system`. An assistant
placeholder with no content, thinking or calls gives no row. There is no
call id: the n-th `tool` message after an assistant message pairs with that
message's n-th call, and `tool_use_id` is synthesised as
`<chat_id>:<tool_calls.id>`; an extra `tool` message takes the last call's
name and no id, as the app's reload does. `session_id` is the chat id,
`model` is `model_name` on assistant, thinking and tool_use rows, and
`project_path` and `git_branch` stay empty (the app has one global working
directory and no file tools). `source_line` is `messages.id`, or
`tool_calls.id` on `tool_use` rows. Messages whose chat row is gone are
still read. The `users` table (account name and email), `settings` and the
attachment bytes are never read.

Rows from `.ollama/history`: `user`, or `system` prefixed `slash command:`
for a line starting with `/`; `timestamp_utc` and `session_id` are empty,
so the rows sort after every dated row, drop out of `--since`/`--until`
unless `--keep-undated` is given, and are not in `sessions.jsonl`.
`source_line` is the line number.
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

DB_RX = re.compile(r"^(?:Library/Application Support/Ollama|AppData/Local/Ollama)/db\.sqlite$")
HISTORY_RX = re.compile(r"^\.ollama/history$")


def call_text(arguments) -> str:
    """The `url` or `query` argument of a desktop tool call, else the
    arguments as stored."""
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except ValueError:
        return str(arguments or "")
    if isinstance(args, dict):
        for key in ("url", "query"):
            v = args.get(key)
            if isinstance(v, str) and v:
                return v
        return compact_json(args)
    return str(arguments or "") if isinstance(arguments, str) else compact_json(args)


def _result_fallback(value) -> str:
    if value is None or value == "" or value == "null":
        return ""
    try:
        return compact_json(json.loads(value))
    except (TypeError, ValueError):
        return str(value)


class OllamaParser(Parser):
    agent = "ollama"
    name = "ollama"

    def wants(self, artifact: Artifact) -> bool:
        return bool(DB_RX.match(artifact.rel) or HISTORY_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if DB_RX.match(artifact.rel):
            yield from self._parse_db(artifact, opts)
        else:
            yield from self._parse_history(artifact)

    def _row(self, artifact: Artifact, line: int, session_id: str = "", ts: str = "") -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.session_id = session_id
        row.timestamp_utc = ts
        return row

    def _system(self, artifact: Artifact, text: str) -> Row:
        row = self._row(artifact, 0)
        row.turn_type = "system"
        row.text = text
        return row

    # -- db.sqlite ------------------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            yield self._system(artifact, "parser: not a SQLite database")
            return
        try:
            with open_copy(artifact.disk_path) as con:
                rows = list(self._db_rows(con, artifact, opts))
        except sqlite3.DatabaseError as e:
            yield self._system(artifact, "parser: SQLite error: %s" % e)
            return
        yield from rows

    def _db_rows(self, con: sqlite3.Connection, artifact: Artifact, opts: Options) -> Iterator[Row]:
        tables = table_names(con)
        if "messages" not in tables:
            return
        calls: dict[int, list[dict]] = {}
        if "tool_calls" in tables:
            for c in con.execute(
                "select id, message_id, function_name, function_arguments"
                " from tool_calls order by message_id, id"
            ):
                calls.setdefault(c["message_id"], []).append(dict(c))
        files: dict[int, list[tuple[str, int]]] = {}
        if "attachments" in tables:
            for a in con.execute(
                "select message_id, filename, length(data) as n from attachments"
                " order by message_id, id"
            ):
                files.setdefault(a["message_id"], []).append((a["filename"] or "", a["n"] or 0))

        chat = None
        pending: list[dict] = []  # calls of the last assistant message with calls
        used = 0
        for m in con.execute("select * from messages order by chat_id, id"):
            m = dict(m)
            mid = m.get("id") or 0
            sid = str(m.get("chat_id") or "")
            if sid != chat:
                chat, pending, used = sid, [], 0
            role = str(m.get("role") or "")
            ts = to_utc(m.get("created_at"))
            content = m.get("content") or ""
            model = m.get("model_name") or ""

            if role == "user":
                row = self._row(artifact, mid, sid, ts)
                row.turn_type = "user"
                parts = [content] + [
                    "[attachment: %s, %d bytes]" % (f, n) for f, n in files.get(mid, [])
                ]
                row.text = compact("\n".join(p for p in parts if p))
                yield row
            elif role == "assistant":
                thinking = m.get("thinking") or ""
                if thinking and opts.include_thinking:
                    row = self._row(artifact, mid, sid, ts)
                    row.turn_type = "thinking"
                    row.model = model
                    row.text = compact(thinking)
                    yield row
                if content:
                    row = self._row(artifact, mid, sid, ts)
                    row.turn_type = "assistant"
                    row.model = model
                    row.text = compact(content)
                    yield row
                mcalls = calls.get(mid, [])
                if mcalls:
                    pending, used = mcalls, 0
                for c in mcalls:
                    row = self._row(artifact, c["id"], sid, ts)
                    row.turn_type = "tool_use"
                    row.model = model
                    row.tool_name = c["function_name"] or ""
                    row.tool_use_id = "%s:%s" % (sid, c["id"])
                    row.text = compact(call_text(c["function_arguments"]))
                    yield row
            elif role == "tool":
                row = self._row(artifact, mid, sid, ts)
                row.turn_type = "tool_result"
                if used < len(pending):
                    c = pending[used]
                    row.tool_name = c["function_name"] or ""
                    row.tool_use_id = "%s:%s" % (sid, c["id"])
                elif pending:
                    row.tool_name = pending[-1]["function_name"] or ""
                used += 1
                row.text = compact(content or _result_fallback(m.get("tool_result")))
                yield row
            else:
                row = self._row(artifact, mid, sid, ts)
                row.turn_type = "system"
                row.text = compact(content if role == "system" else "%s: %s" % (role, content))
                yield row

    # -- .ollama/history ------------------------------------------------------------------
    def _parse_history(self, artifact: Artifact) -> Iterator[Row]:
        with open(artifact.disk_path, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                row = self._row(artifact, n)
                if line.startswith("/"):
                    row.turn_type = "system"
                    row.text = "slash command: " + line
                else:
                    row.turn_type = "user"
                    row.text = line
                yield row
