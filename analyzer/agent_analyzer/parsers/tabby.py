"""Tabby server chat threads and completion events.

Tabby (TabbyML/tabby, checked at 21b2904) is a self-hosted completion and
chat server, so its transcripts live under the server account's home, not
the developer's: the `user` column is the account the server ran as, and the
person who chatted is named in the thread's `system` row. See
`analyzer/research/tabby.md`.

Files, relative to the home directory:

* `.tabby/ee/db.sqlite` (production builds) or `.tabby/ee/dev-db.sqlite`
  (source builds), with `-wal` and `-shm` sidecars (WAL mode). Read through
  `sqlite_util.open_copy`; only these columns are selected, each only if the
  table has it:
  - `users`: `id`, `email`, `name` (owner of a thread or event).
  - `threads`: `id`, `is_ephemeral`, `user_id`, `created_at`, `updated_at`,
    `relevant_questions` (JSON array of strings).
  - `thread_messages`: `id`, `thread_id`, `role` (`user`, `assistant`),
    `content` (Markdown), `code_source_id`, `attachment` (JSON with `code[]`
    {`git_url`, `commit`, `filepath`, `start_line`}, `client_code[]`
    {`filepath`, `start_line`}, `doc[]` {`title`, `link`, `page_link`,
    `sha`}, `code_file_list` {`file_list`}), `created_at`. Backups made before
    0.25 have no `attachment` column; their `code_attachments`,
    `client_code_attachments` and `doc_attachments` arrays are read instead.
  - `user_events`: `id`, `user_id`, `kind`, `created_at`, `payload` (the
    pretty-printed event, same shape as an event log line's `event`).
* `.tabby/ee/db.backup-YYYYMMDD.sqlite` and `dev-db.backup-YYYYMMDD.sqlite`:
  copies made before each schema migration. Parsed like the live database,
  with a leading `system` row saying the file is a backup, because ephemeral
  threads untouched for 7 days are deleted from the live database and may
  survive only here.
* `.tabby/events/YYYY-MM-DD.json`: JSON Lines, one `LogEntry` per line:
  `user` (encoded server user id or null), `ts` (Unix milliseconds), `event`
  (externally tagged): `completion` {`completion_id`, `language`, `prompt`,
  `segments` {`git_url`, `filepath`}, `choices[]` {`index`, `text`},
  `user_agent`}; `view`, `select`, `dismiss` {`completion_id`,
  `choice_index`, `view_id`, `elapsed`, `kind`}; `chat_completion` {}.

The database also stores plaintext secrets (`users.auth_token`,
`users.password_encrypted`, `registration_token`, `refresh_tokens`,
`integrations.access_token`, `email_setting.smtp_password`,
`oauth_credential.client_secret`, `ldap_credential.bind_password`). Those
tables and columns are never selected.

Rows: per thread one `system` row (owner email and name, ephemeral flag,
relevant questions) then one `user` or `assistant` row per message, with an
attachment summary appended to the text. `session_id` is the thread id;
`project_path` is the first `code[].git_url` attached anywhere in the thread
(a repository URL: Tabby records no local working directory). Per completion
event one `system` row (server user, language, file, client), one `user` row
with the full prompt and one `assistant` row per choice; `session_id` is the
`completion_id` and `project_path` is `segments.git_url`. View, select,
dismiss and chat-completion events are `system` rows. Database timestamps
are UTC text with second precision; event log times are milliseconds;
`user_events` rows carry the second-precision `created_at`. No model, tool
calls, thinking or git branch are recorded.
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
from .base import Options, Parser, compact_json, iter_jsonl

DB_RX = re.compile(r"^\.tabby/ee/(?:dev-)?db\.sqlite$")
BACKUP_RX = re.compile(r"^\.tabby/ee/(?:dev-)?db\.backup-[^/]+\.sqlite$")
EVENTS_RX = re.compile(r"^\.tabby/events/\d{4}-\d{2}-\d{2}\.json$")

# The only columns ever read. Secret-bearing tables are absent on purpose.
COLUMNS = {
    "users": ("id", "email", "name"),
    "threads": ("id", "is_ephemeral", "user_id", "created_at", "updated_at", "relevant_questions"),
    "thread_messages": (
        "id",
        "thread_id",
        "role",
        "content",
        "code_source_id",
        "attachment",
        "code_attachments",
        "client_code_attachments",
        "doc_attachments",
        "created_at",
    ),
    "user_events": ("id", "user_id", "kind", "created_at", "payload"),
}


def _json(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return default


def _join(*parts: str) -> str:
    return " | ".join(x for x in parts if x)


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _select(con: sqlite3.Connection, table: str, order: str) -> Iterator[dict]:
    """Rows of `table` restricted to the whitelisted columns it has."""
    have = {r[1] for r in con.execute("pragma table_info(%s)" % table)}
    cols = [c for c in COLUMNS[table] if c in have]
    if not cols:
        return
    order_cols = [c for c in order.split(",") if c.strip() in have]
    sql = "select %s from %s" % (", ".join(cols), table)
    if order_cols:
        sql += " order by " + ", ".join(order_cols)
    for r in con.execute(sql):
        yield dict(zip(cols, r, strict=False))


def _loc(filepath, start_line) -> str:
    fp = str(filepath or "")
    return "%s:%s" % (fp, start_line) if fp and start_line not in (None, "") else fp


def attachment_parts(att: dict) -> list[str]:
    """Short descriptions of what was attached to a message."""
    parts: list[str] = []
    for c in _list(att.get("code")):
        if isinstance(c, dict):
            repo = str(c.get("git_url") or "")
            if c.get("commit"):
                repo += "@" + str(c["commit"])
            parts.append(
                _join("code", repo, _loc(c.get("filepath"), c.get("start_line"))).replace(
                    " | ", " "
                )
            )
    for c in _list(att.get("client_code")):
        if isinstance(c, dict):
            parts.append(("client_code " + _loc(c.get("filepath"), c.get("start_line"))).strip())
    for d in _list(att.get("doc")):
        if isinstance(d, dict):
            label = d.get("title") or d.get("sha") or ""
            link = d.get("link") or d.get("page_link") or ""
            parts.append(_join("doc", str(label), str(link)).replace(" | ", " "))
    fl = att.get("code_file_list")
    if isinstance(fl, dict) and isinstance(fl.get("file_list"), list):
        parts.append("code_file_list %d files" % len(fl["file_list"]))
    return parts


def message_attachment(m: dict) -> dict:
    att = _json(m.get("attachment"), None)
    if isinstance(att, dict):
        return att
    # Pre-0.25 databases (threads.rs:34-38): separate columns, no `attachment`.
    return {
        "code": _json(m.get("code_attachments"), None),
        "client_code": _json(m.get("client_code_attachments"), None),
        "doc": _json(m.get("doc_attachments"), None),
    }


def first_git_url(att: dict) -> str:
    for c in _list(att.get("code")):
        if isinstance(c, dict) and c.get("git_url"):
            return str(c["git_url"])
    return ""


class TabbyParser(Parser):
    agent = "tabby"
    name = "tabby"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return bool(DB_RX.match(rel) or BACKUP_RX.match(rel) or EVENTS_RX.match(rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if EVENTS_RX.match(artifact.rel):
            yield from self._parse_events(artifact, opts)
        else:
            yield from self._parse_db(artifact, opts, bool(BACKUP_RX.match(artifact.rel)))

    def _row(
        self,
        artifact: Artifact,
        line: int,
        session_id: str = "",
        project_path: str = "",
        ts: str = "",
        turn_type: str = "system",
        text: str = "",
        opts: Options | None = None,
    ) -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.session_id = session_id
        row.project_path = project_path
        row.timestamp_utc = ts
        row.turn_type = turn_type
        row.text = compact(text, opts.max_text_length if opts else 0)
        return row

    # -- db.sqlite and its backups -------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options, backup: bool) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            yield self._row(artifact, 0, text="parser: not a SQLite database")
            return
        if backup:
            yield self._row(
                artifact,
                0,
                opts=opts,
                text=(
                    "backup database copied before a schema migration; it can hold threads and events "
                    "since deleted from the live database"
                ),
            )
        try:
            with open_copy(artifact.disk_path) as con:
                tables = table_names(con)
                users: dict[str, str] = {}
                if "users" in tables:
                    for u in _select(con, "users", "id"):
                        label = str(u.get("email") or "")
                        if u.get("name"):
                            label = "%s (%s)" % (label, u["name"]) if label else str(u["name"])
                        users[str(u.get("id"))] = label
                if "threads" in tables:
                    yield from self._threads(artifact, con, tables, users, opts)
                if "user_events" in tables:
                    yield from self._user_events(artifact, con, users, opts)
        except sqlite3.DatabaseError as e:
            yield self._row(artifact, 0, text="parser: SQLite error: %s" % e)

    def _threads(
        self,
        artifact: Artifact,
        con: sqlite3.Connection,
        tables: set,
        users: dict[str, str],
        opts: Options,
    ) -> Iterator[Row]:
        messages: dict[str, list[dict]] = {}
        if "thread_messages" in tables:
            for m in _select(con, "thread_messages", "thread_id,created_at,id"):
                messages.setdefault(str(m.get("thread_id")), []).append(m)
        threads = list(_select(con, "threads", "created_at,id"))
        known = {str(t.get("id")) for t in threads}
        # Messages whose thread row is gone still get parsed, under their thread id.
        threads += [{"id": tid} for tid in messages if tid not in known]
        for t in threads:
            tid = str(t.get("id"))
            msgs = messages.get(tid, [])
            atts = [message_attachment(m) for m in msgs]
            project = next((u for u in (first_git_url(a) for a in atts) if u), "")
            questions = [str(q) for q in _list(_json(t.get("relevant_questions"), None))]
            owner = users.get(str(t.get("user_id")), "")
            yield self._row(
                artifact,
                int(t["id"]) if str(t.get("id")).isdigit() else 0,
                tid,
                project,
                to_utc(t.get("created_at")),
                opts=opts,
                text=_join(
                    "thread start",
                    "owner %s" % owner
                    if owner
                    else (
                        "owner user_id=%s" % t["user_id"] if t.get("user_id") is not None else ""
                    ),
                    "ephemeral" if t.get("is_ephemeral") else "",
                    "thread row missing" if "user_id" not in t else "",
                    "relevant questions: " + "; ".join(questions) if questions else "",
                ),
            )
            for m, att in zip(msgs, atts, strict=False):
                role = str(m.get("role") or "")
                text = str(m.get("content") or "")
                parts = attachment_parts(att)
                if m.get("code_source_id"):
                    parts.insert(0, "code_source %s" % m["code_source_id"])
                if parts:
                    text = "%s [attachments: %s]" % (text, "; ".join(parts))
                if role not in ("user", "assistant"):
                    text = "%s: %s" % (role, text)
                yield self._row(
                    artifact,
                    m.get("id") or 0,
                    tid,
                    project,
                    to_utc(m.get("created_at")),
                    role if role in ("user", "assistant") else "system",
                    text,
                    opts,
                )

    def _user_events(
        self, artifact: Artifact, con: sqlite3.Connection, users: dict[str, str], opts: Options
    ) -> Iterator[Row]:
        for e in _select(con, "user_events", "created_at,id"):
            line = e.get("id") or 0
            ts = to_utc(e.get("created_at"))
            owner = "user=%s" % (users.get(str(e.get("user_id")), "") or e.get("user_id"))
            event = _json(e.get("payload"), None)
            if not isinstance(event, dict):
                yield self._row(
                    artifact,
                    line,
                    ts=ts,
                    opts=opts,
                    text="parser: user_event %s payload did not parse" % e.get("id"),
                )
                continue
            yield from self._event_rows(
                artifact, line, ts, owner, event, opts, str(e.get("kind") or "")
            )

    # -- events/YYYY-MM-DD.json ----------------------------------------------------------
    def _parse_events(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            user = rec.get("user")
            owner = "user=%s" % user if user not in (None, "") else ""
            event = rec.get("event")
            if not isinstance(event, dict):
                yield self._row(
                    artifact,
                    n,
                    ts=to_utc(rec.get("ts")),
                    opts=opts,
                    text="unknown log entry: " + compact_json(rec),
                )
                continue
            yield from self._event_rows(artifact, n, to_utc(rec.get("ts")), owner, event, opts)
        if errors:
            yield self._row(
                artifact,
                errors[0][0],
                text="parser: %d unparseable line(s), first at line %d"
                % (len(errors), errors[0][0]),
            )

    # -- one Event, from either store -----------------------------------------------------
    def _event_rows(
        self,
        artifact: Artifact,
        line: int,
        ts: str,
        owner: str,
        event: dict,
        opts: Options,
        kind: str = "",
    ) -> Iterator[Row]:
        if len(event) != 1:
            yield self._row(
                artifact,
                line,
                ts=ts,
                opts=opts,
                text=_join(kind or "event", owner, compact_json(event)),
            )
            return
        tag, body = next(iter(event.items()))
        body = body if isinstance(body, dict) else {}
        cid = str(body.get("completion_id") or "")
        if tag == "completion":
            seg = body.get("segments") if isinstance(body.get("segments"), dict) else {}
            project = str(seg.get("git_url") or "")
            yield self._row(
                artifact,
                line,
                cid,
                project,
                ts,
                opts=opts,
                text=_join(
                    "completion",
                    owner,
                    "language=%s" % body["language"] if body.get("language") else "",
                    "file=%s" % seg["filepath"] if seg.get("filepath") else "",
                    "client=%s" % body["user_agent"] if body.get("user_agent") else "",
                ),
            )
            yield self._row(
                artifact, line, cid, project, ts, "user", str(body.get("prompt") or ""), opts
            )
            for c in _list(body.get("choices")):
                if isinstance(c, dict):
                    yield self._row(
                        artifact,
                        line,
                        cid,
                        project,
                        ts,
                        "assistant",
                        str(c.get("text") or ""),
                        opts,
                    )
        elif tag in ("view", "select", "dismiss"):
            yield self._row(
                artifact,
                line,
                cid,
                ts=ts,
                opts=opts,
                text=_join(
                    "%s choice %s" % (tag, body.get("choice_index", "")),
                    owner,
                    "kind=%s" % body["kind"] if body.get("kind") else "",
                    "view=%s" % body["view_id"] if body.get("view_id") else "",
                    "elapsed=%sms" % body["elapsed"] if body.get("elapsed") is not None else "",
                ),
            )
        else:
            yield self._row(
                artifact,
                line,
                cid,
                ts=ts,
                opts=opts,
                text=_join(str(tag), owner, compact_json(body) if body else ""),
            )
