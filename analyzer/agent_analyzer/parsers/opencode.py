"""OpenCode sessions.

Validated against source, sst/opencode at 907b3bc (see
`analyzer/research/opencode.md`), with a synthetic fixture; no real install
was used. The same storage model is used by Kilo Code's CLI, which is an
OpenCode fork, so `KiloCodeParser` subclasses this one with its own paths.

Files, relative to the home directory (XDG paths on every OS):

* `.local/share/opencode/opencode.db`, or `opencode-<channel>.db`, with
  `-wal` and `-shm` sidecars (WAL mode, so the sidecar holds the newest
  rows). Opened through `sqlite_util.open_copy`. Tables read:
  - `session(id, project_id, parent_id, slug, directory, title, version,
    agent, time_created)`: `directory` is the cwd.
  - `project(id, worktree)`: repository root; `/` for the `global` project.
  - `message(id, session_id, time_created, data)`: `data` JSON is the V1
    message without `id` and `sessionID`: `role`, `time.created`, user
    `model.{providerID, modelID}`, assistant `providerID`, `modelID`,
    `path.cwd`, `error.{name, data.message}`.
  - `part(id, message_id, session_id, time_created, data)`: `data` JSON has
    a `type` discriminator: `text` (`text`, `synthetic`, `time.start`),
    `reasoning` (`text`, `time.start`), `tool` (`callID`, `tool`,
    `state.{status, input, output, error, title, time.{start, end}}`, the
    call and its result in one part), `step-start`, `step-finish` (`reason`,
    `cost`, `tokens`), `subtask` (`agent`, `description`, `prompt`),
    `compaction`, `file` (`filename`, `url`), `agent` (`name`), `retry`
    (`attempt`, `error`), `patch` (`files`), `snapshot`.
  - `session_message(id, session_id, type, seq, time_created, data)`: the
    newer V2 projection. It was wiped once by a migration, so it is read
    only for sessions that have no V1 `message` rows. `data` for `user`
    (`text`), `synthetic` and `system` (`text`), `shell` (`callID`,
    `command`, `output`), `compaction` (`summary`) and `assistant`
    (`model.{id or modelID, providerID}`, `content[]` of `text`,
    `reasoning` and `tool` items with `id`, `name`, `state.{status, input,
    content[], error.message}`, `time.{created, completed}`).
  The `credential`, `account` and `event` tables are not read.
* Legacy JSON tree `.local/share/opencode/storage/`: `session/<projectID>/
  <sessionID>.json` (`id`, `projectID`, `parentID`, `directory`, `title`,
  `version`, `time.created`), `message/<sessionID>/<messageID>.json` (the V1
  message with `id` and `sessionID` inline), `part/<messageID>/<partID>.json`
  and `project/<projectID>.json` (`worktree`).
* Older per-project tree `.local/share/opencode/project/<slug>/storage/
  session/`: `info/<sessionID>.json`, `message/<sessionID>/<messageID>.json`,
  `part/<sessionID>/<messageID>/<partID>.json`. The project root comes from
  the assistant message's `path.root`.

Rows. A session header (database row or session JSON file) becomes one
`system` row. A user message becomes one `user` row with its non-synthetic
text parts joined; every other part becomes its own row: assistant `text` is
`assistant`, `reasoning` is `thinking` (with `--include-thinking`), `tool` is
a `tool_use` row plus a `tool_result` row once the status is `completed` or
`error`, `step-finish`, `subtask`, `compaction`, `file`, `agent`, `retry`,
`patch` and synthetic text are `system`; `step-start` and `snapshot` carry
nothing but a snapshot hash and are skipped. A message-level `error` is a
`system` row. The model is `providerID/modelID`. Timestamps come from the
part's `time.start` (tool results: `state.time.end`), else the part row's
`time_created`, else the message's `time.created`; user text parts carry no
time of their own and inherit the message's. `project_path` is the
session's `directory` (the cwd, as in the other parsers), else the project
`worktree` unless it is `/`, else the message's `path.cwd`. No git branch is
recorded. `source_line` is the SQLite `rowid` of the record for databases
and 1 for the one-record JSON files.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json

# Which tool input field best identifies the action, in order of preference.
TOOL_KEYS = (
    "command",
    "filePath",
    "file_path",
    "pattern",
    "path",
    "url",
    "query",
    "description",
    "prompt",
)


def tool_summary(value) -> str:
    """The most identifying argument of a tool input, else the input as JSON."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in TOOL_KEYS:
            v = value.get(key)
            if isinstance(v, str) and v:
                if key == "pattern" and isinstance(value.get("path"), str) and value.get("path"):
                    return "%s | %s" % (v, value["path"])
                return v
    if value in (None, "", {}):
        return ""
    return compact_json(value)


def model_name(provider, model) -> str:
    provider = provider if isinstance(provider, str) else ""
    model = model if isinstance(model, str) else ""
    if provider and model:
        return "%s/%s" % (provider, model)
    return model or provider


def message_model(msg: dict) -> str:
    if msg.get("role") == "assistant":
        return model_name(msg.get("providerID"), msg.get("modelID"))
    m = msg.get("model")
    if isinstance(m, dict):
        return model_name(m.get("providerID"), m.get("modelID") or m.get("id"))
    return ""


def _d(value) -> dict:
    return value if isinstance(value, dict) else {}


def _loads(value) -> dict | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return None
    try:
        v = json.loads(value)
    except ValueError:
        return None
    return v if isinstance(v, dict) else None


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "rb") as fh:
            return _loads(fh.read())
    except OSError:
        return None


def _join(*parts) -> str:
    return " ".join(str(p) for p in parts if p not in (None, ""))


def _error_text(err) -> str:
    if isinstance(err, str):
        return err
    e = _d(err)
    data = _d(e.get("data"))
    msg = data.get("message") or e.get("message") or ""
    return _join(e.get("name") or "", msg) or (compact_json(err) if err else "")


class _Ctx:
    """Session-level values shared by every row of a session."""

    def __init__(self, session_id: str = "", project_path: str = ""):
        self.session_id = session_id
        self.project_path = project_path


class OpenCodeParser(Parser):
    agent = "opencode"
    name = "opencode"
    data_dir = ".local/share/opencode"
    db_prefixes: tuple[str, ...] = ("opencode",)

    def __init__(self) -> None:
        dd = re.escape(self.data_dir)
        prefixes = "|".join(re.escape(p) for p in self.db_prefixes)
        self.db_rx = re.compile(r"^%s/(?:%s)(?:-[^/]+)?\.db$" % (dd, prefixes))
        self.session_rx = re.compile(r"^%s/storage/session/([^/]+)/([^/]+)\.json$" % dd)
        self.message_rx = re.compile(r"^%s/storage/message/([^/]+)/([^/]+)\.json$" % dd)
        self.old_session_rx = re.compile(
            r"^%s/project/[^/]+/storage/session/info/([^/]+)\.json$" % dd
        )
        self.old_message_rx = re.compile(
            r"^%s/project/[^/]+/storage/session/message/([^/]+)/([^/]+)\.json$" % dd
        )

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return any(
            rx.match(rel)
            for rx in (
                self.db_rx,
                self.session_rx,
                self.message_rx,
                self.old_session_rx,
                self.old_message_rx,
            )
        )

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        rel = artifact.rel
        if self.db_rx.match(rel):
            yield from self._parse_db(artifact, opts)
        elif self.session_rx.match(rel) or self.old_session_rx.match(rel):
            yield from self._parse_session_file(artifact, opts)
        elif self.message_rx.match(rel):
            yield from self._parse_message_file(artifact, opts, old=False)
        elif self.old_message_rx.match(rel):
            yield from self._parse_message_file(artifact, opts, old=True)

    # -- shared row builders --------------------------------------------------------
    def _row(
        self, artifact: Artifact, ctx: _Ctx, source_file: str, line: int, ts: str, model: str = ""
    ) -> Row:
        row = self.base_row(artifact)
        if source_file:
            row.source_file = source_file
        row.source_line = line
        row.session_id = ctx.session_id
        row.project_path = ctx.project_path
        row.timestamp_utc = ts
        row.model = model
        return row

    def _session_row(
        self,
        artifact: Artifact,
        ctx: _Ctx,
        s: dict,
        created,
        line: int,
        opts: Options,
        source_file: str = "",
    ) -> Row:
        row = self._row(artifact, ctx, source_file, line, to_utc(created))
        row.turn_type = "system"
        row.text = compact(
            _join(
                "session start:",
                s.get("title") or "",
                "slug=%s" % s["slug"] if s.get("slug") else "",
                "version=%s" % s["version"] if s.get("version") else "",
                "agent=%s" % s["agent"] if s.get("agent") else "",
                "parent=%s" % (s.get("parent_id") or s.get("parentID"))
                if (s.get("parent_id") or s.get("parentID"))
                else "",
                "directory=%s" % s["directory"] if s.get("directory") else "",
            ),
            opts.max_text_length,
        )
        return row

    def _message_rows(
        self,
        artifact: Artifact,
        ctx: _Ctx,
        msg: dict,
        msg_src: tuple[str, int, object],
        parts: list[tuple[dict | None, str, int, object]],
        opts: Options,
    ) -> Iterator[Row]:
        """Rows for one V1 message and its parts. `msg_src` and each part
        entry carry (source_file, source_line, fallback time); a part whose
        data could not be decoded is passed as None and counted."""
        role = msg.get("role")
        model = message_model(msg)
        msg_file, msg_line, msg_time = msg_src
        msg_ts = to_utc(_d(msg.get("time")).get("created")) or to_utc(msg_time)
        if not ctx.project_path:
            ctx.project_path = str(_d(msg.get("path")).get("cwd") or "")
        bad = 0
        user_text: list[str] = []
        first_user: tuple[str, int, int] | None = None
        out: list[Row] = []
        for data, pfile, pline, ptime in parts:
            if data is None:
                bad += 1
                continue
            ptype = data.get("type")
            pts = to_utc(_d(data.get("time")).get("start")) or to_utc(ptime) or msg_ts

            def mk(turn: str, text, ts: str = "") -> Row:
                row = self._row(artifact, ctx, pfile, pline, ts or pts, model)
                row.turn_type = turn
                row.text = compact(text, opts.max_text_length)
                out.append(row)
                return row

            if ptype == "text":
                text = data.get("text") or ""
                if data.get("synthetic") or data.get("ignored"):
                    mk("system", _join("synthetic:" if data.get("synthetic") else "ignored:", text))
                elif role == "user":
                    if text:
                        user_text.append(text)
                        if first_user is None:
                            first_user = (pfile, pline, len(out))
                elif text:
                    mk("assistant", text)
            elif ptype == "reasoning":
                if opts.include_thinking and data.get("text"):
                    mk("thinking", data.get("text"))
            elif ptype == "tool":
                self._tool_rows(mk, data)
            elif ptype == "step-finish":
                tokens = _d(data.get("tokens"))
                mk(
                    "system",
                    _join(
                        "step-finish",
                        "reason=%s" % data["reason"] if data.get("reason") else "",
                        "cost=%s" % data["cost"] if data.get("cost") is not None else "",
                        "tokens_in=%s" % tokens["input"] if tokens.get("input") is not None else "",
                        "tokens_out=%s" % tokens["output"]
                        if tokens.get("output") is not None
                        else "",
                    ),
                )
            elif ptype == "subtask":
                mk(
                    "system",
                    _join(
                        "subtask",
                        "agent=%s" % data["agent"] if data.get("agent") else "",
                        (data.get("description") or "") + ":",
                        data.get("prompt") or "",
                    ),
                )
            elif ptype == "compaction":
                mk("system", _join("compaction", "auto" if data.get("auto") else ""))
            elif ptype == "file":
                mk("system", _join("file:", data.get("filename") or "", data.get("url") or ""))
            elif ptype == "agent":
                mk("system", _join("agent:", data.get("name") or ""))
            elif ptype == "retry":
                mk(
                    "system",
                    _join(
                        "retry",
                        "attempt=%s" % data["attempt"] if data.get("attempt") else "",
                        _error_text(data.get("error")),
                    ),
                )
            elif ptype == "patch":
                files = data.get("files")
                mk(
                    "system",
                    _join(
                        "patch:", " ".join(str(f) for f in files) if isinstance(files, list) else ""
                    ),
                )
            elif ptype in ("step-start", "snapshot"):
                continue
            else:
                mk("system", _join("%s:" % (ptype or "part"), compact_json(data)))
        if user_text and first_user:
            pfile, pline, at = first_user
            row = self._row(artifact, ctx, pfile, pline, msg_ts, model)
            row.turn_type = "user"
            row.text = compact("\n".join(user_text), opts.max_text_length)
            out.insert(at, row)
        yield from out
        if msg.get("error"):
            row = self._row(
                artifact,
                ctx,
                msg_file,
                msg_line,
                to_utc(_d(msg.get("time")).get("completed")) or msg_ts,
                model,
            )
            row.turn_type = "system"
            row.text = compact("error: " + _error_text(msg.get("error")), opts.max_text_length)
            yield row
        if bad:
            row = self._row(artifact, ctx, msg_file, msg_line, msg_ts, model)
            row.turn_type = "system"
            row.text = "parser: %d part(s) of message %s could not be decoded" % (
                bad,
                msg.get("id") or "",
            )
            yield row

    @staticmethod
    def _tool_rows(mk, data: dict) -> None:
        """Append a tool_use row, and a tool_result row once finished, via `mk`."""
        state = _d(data.get("state"))
        times = _d(state.get("time"))
        name = str(data.get("tool") or "")
        call_id = str(data.get("callID") or "")
        use = mk(
            "tool_use",
            tool_summary(state.get("input")) or state.get("title") or "",
            to_utc(times.get("start")),
        )
        use.tool_name, use.tool_use_id = name, call_id
        status = state.get("status")
        if status in ("completed", "error"):
            if status == "error":
                text = "[error] " + _error_text(state.get("error"))
            else:
                out = state.get("output")
                text = out if isinstance(out, str) else compact_json(out)
            res = mk("tool_result", text, to_utc(times.get("end")) or to_utc(times.get("start")))
            res.tool_name, res.tool_use_id = name, call_id

    # -- SQLite ---------------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            return
        rows: list[Row] = []
        try:
            with open_copy(artifact.disk_path) as con:
                for row in self._db_rows(con, artifact, opts):
                    rows.append(row)
        except sqlite3.DatabaseError as e:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.text = "parser: database could not be read: %s" % e
            rows.append(row)
        yield from rows

    def _db_rows(self, con: sqlite3.Connection, artifact: Artifact, opts: Options) -> Iterator[Row]:
        tables = table_names(con)
        projects: dict[str, dict] = {}
        if "project" in tables:
            for r in con.execute("select * from project"):
                projects[r["id"]] = dict(r)
        sessions: dict[str, tuple[int, dict]] = {}
        if "session" in tables:
            for r in con.execute(
                "select rowid as _rowid, * from session order by time_created, id"
            ):
                sessions[r["id"]] = (r["_rowid"], dict(r))
        ctxs: dict[str, _Ctx] = {}

        def ctx_for(sid: str) -> _Ctx:
            c = ctxs.get(sid)
            if c is None:
                s = sessions.get(sid, (0, {}))[1]
                path = s.get("directory") or ""
                if not path:
                    wt = projects.get(s.get("project_id"), {}).get("worktree") or ""
                    path = wt if wt != "/" else ""
                c = ctxs[sid] = _Ctx(sid, path)
            return c

        for sid, (rowid, s) in sessions.items():
            yield self._session_row(artifact, ctx_for(sid), s, s.get("time_created"), rowid, opts)

        bad = 0
        covered = set()
        if "message" in tables:
            has_parts = "part" in tables
            for m in con.execute(
                "select rowid as _rowid, id, session_id, time_created, data from message "
                "order by session_id, time_created, id"
            ).fetchall():
                sid = m["session_id"] or ""
                covered.add(sid)
                msg = _loads(m["data"])
                if msg is None:
                    bad += 1
                    continue
                msg.setdefault("id", m["id"])
                parts = []
                if has_parts:
                    for p in con.execute(
                        "select rowid as _rowid, time_created, data from part "
                        "where message_id = ? order by id",
                        (m["id"],),
                    ):
                        parts.append((_loads(p["data"]), "", p["_rowid"], p["time_created"]))
                yield from self._message_rows(
                    artifact, ctx_for(sid), msg, ("", m["_rowid"], m["time_created"]), parts, opts
                )
        if "session_message" in tables:
            for m in con.execute(
                "select rowid as _rowid, session_id, type, seq, time_created, data "
                "from session_message order by session_id, seq, time_created"
            ).fetchall():
                sid = m["session_id"] or ""
                if sid in covered:
                    continue
                data = _loads(m["data"])
                if data is None:
                    bad += 1
                    continue
                yield from self._v2_rows(
                    artifact,
                    ctx_for(sid),
                    m["type"] or data.get("type") or "",
                    data,
                    m["_rowid"],
                    m["time_created"],
                    opts,
                )
        if bad:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.text = "parser: %d record(s) with undecodable data" % bad
            yield row

    def _v2_rows(
        self,
        artifact: Artifact,
        ctx: _Ctx,
        mtype: str,
        data: dict,
        line: int,
        created,
        opts: Options,
    ) -> Iterator[Row]:
        ts = to_utc(_d(data.get("time")).get("created")) or to_utc(created)
        m = _d(data.get("model"))
        model = model_name(m.get("providerID"), m.get("modelID") or m.get("id"))

        def mk(turn: str, text, when: str = "") -> Row:
            row = self._row(artifact, ctx, "", line, when or ts, model)
            row.turn_type = turn
            row.text = compact(text, opts.max_text_length)
            return row

        if mtype == "user":
            yield mk("user", data.get("text") or "")
        elif mtype in ("synthetic", "system"):
            yield mk("system", _join("%s:" % mtype, data.get("text") or ""))
        elif mtype == "shell":
            call_id = str(data.get("callID") or "")
            times = _d(data.get("time"))
            use = mk("tool_use", data.get("command") or "")
            use.tool_name, use.tool_use_id = "shell", call_id
            yield use
            if data.get("output") is not None:
                res = mk("tool_result", data.get("output") or "", to_utc(times.get("completed")))
                res.tool_name, res.tool_use_id = "shell", call_id
                yield res
        elif mtype == "compaction":
            yield mk(
                "system", _join("compaction", data.get("reason") or "", data.get("summary") or "")
            )
        elif mtype == "assistant":
            for item in data.get("content") or []:
                item = _d(item)
                itype = item.get("type")
                if itype == "text" and item.get("text"):
                    yield mk("assistant", item["text"])
                elif itype == "reasoning":
                    if opts.include_thinking and item.get("text"):
                        yield mk("thinking", item["text"])
                elif itype == "tool":
                    state = _d(item.get("state"))
                    times = _d(item.get("time"))
                    name, call_id = str(item.get("name") or ""), str(item.get("id") or "")
                    use = mk(
                        "tool_use", tool_summary(state.get("input")), to_utc(times.get("created"))
                    )
                    use.tool_name, use.tool_use_id = name, call_id
                    yield use
                    status = state.get("status")
                    if status in ("completed", "error"):
                        if status == "error":
                            text = "[error] " + _error_text(state.get("error"))
                        else:
                            text = "\n".join(
                                str(c.get("text"))
                                for c in state.get("content") or []
                                if isinstance(c, dict) and c.get("text") is not None
                            )
                        res = mk(
                            "tool_result",
                            text,
                            to_utc(times.get("completed")) or to_utc(times.get("ran")),
                        )
                        res.tool_name, res.tool_use_id = name, call_id
                        yield res
            if data.get("error"):
                yield mk("system", "error: " + _error_text(data.get("error")))
        elif mtype:
            yield mk(
                "system",
                _join("%s:" % mtype, compact_json({k: v for k, v in data.items() if k != "time"})),
            )

    # -- legacy JSON tree -----------------------------------------------------------
    @staticmethod
    def _orig_root(artifact: Artifact, depth: int) -> tuple[str, str, Path]:
        """(original root, separator, disk root) for the directory `depth`
        levels above the artifact file. The original path is cut by the length
        of the relative tail, which is the same whatever the separator."""
        tail = "/".join(artifact.rel.split("/")[-depth:])
        orig = artifact.original
        sep = "\\" if orig.count("\\") > orig.count("/") else "/"
        root = orig[: len(orig) - len(tail)].rstrip("/\\")
        disk = artifact.disk_path
        for _ in range(depth):
            disk = disk.parent
        return root, sep, disk

    @staticmethod
    def _children(directory: Path) -> list[Path]:
        try:
            return sorted(
                p
                for p in directory.iterdir()
                if p.suffix == ".json" and not p.is_symlink() and p.is_file()
            )
        except OSError:
            return []

    def _session_ctx(self, root: Path, session_id: str, old: bool, msg: dict) -> tuple[_Ctx, dict]:
        s: dict | None = None
        if old:
            s = _read_json(root / "info" / (session_id + ".json"))
        else:
            sdir = root / "session"
            try:
                cands = sorted(
                    d / (session_id + ".json")
                    for d in sdir.iterdir()
                    if not d.is_symlink() and d.is_dir()
                )
            except OSError:
                cands = []
            for c in cands:
                if c.is_file() and not c.is_symlink():
                    s = _read_json(c)
                    if s is not None:
                        break
        s = s or {}
        path = s.get("directory") or ""
        if not path and not old and s.get("projectID"):
            wt = (_read_json(root / "project" / (str(s["projectID"]) + ".json")) or {}).get(
                "worktree"
            ) or ""
            path = wt if wt != "/" else ""
        if not path:
            p = _d(msg.get("path"))
            path = p.get("root") or p.get("cwd") or ""
        return _Ctx(session_id, str(path)), s

    def _parse_session_file(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        s = _read_json(artifact.disk_path)
        if s is None:
            row = self.base_row(artifact)
            row.source_line = 1
            row.session_id = artifact.disk_path.stem
            row.turn_type = "system"
            row.text = "parser: session file could not be decoded"
            yield row
            return
        path = s.get("directory") or ""
        if not path and s.get("projectID") and not self.old_session_rx.match(artifact.rel):
            proj = (
                artifact.disk_path.parent.parent.parent
                / "project"
                / (str(s["projectID"]) + ".json")
            )
            wt = (_read_json(proj) or {}).get("worktree") or ""
            path = wt if wt != "/" else ""
        ctx = _Ctx(str(s.get("id") or artifact.disk_path.stem), str(path))
        yield self._session_row(artifact, ctx, s, _d(s.get("time")).get("created"), 1, opts)

    def _parse_message_file(self, artifact: Artifact, opts: Options, old: bool) -> Iterator[Row]:
        # new: storage/message/<ses>/<msg>.json, root is storage/
        # old: project/<slug>/storage/session/message/<ses>/<msg>.json, root is storage/session/
        orig_root, sep, root = self._orig_root(artifact, 3)
        session_id = artifact.disk_path.parent.name
        msg = _read_json(artifact.disk_path)
        if msg is None:
            ctx, _ = self._session_ctx(root, session_id, old, {})
            row = self._row(artifact, ctx, "", 1, "")
            row.turn_type = "system"
            row.text = "parser: message file could not be decoded"
            yield row
            return
        session_id = str(msg.get("sessionID") or session_id)
        msg_id = str(msg.get("id") or artifact.disk_path.stem)
        msg.setdefault("id", msg_id)
        ctx, _ = self._session_ctx(root, session_id, old, msg)
        pdir_rel = ["part", session_id, msg_id] if old else ["part", msg_id]
        pdir = root.joinpath(*pdir_rel)
        parts = []
        for f in self._children(pdir):
            parts.append((_read_json(f), orig_root + sep + sep.join([*pdir_rel, f.name]), 1, None))
        yield from self._message_rows(artifact, ctx, msg, ("", 1, None), parts, opts)
