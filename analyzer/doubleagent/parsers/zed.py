"""Zed agent panel threads.

Validated against source, zed-industries/zed at a84689073d29 (see
`analyzer/research/zed.md`), with a synthetic fixture; no real install was
checked. Files, relative to the Zed data directory (`.local/share/zed`,
`Library/Application Support/Zed`, `AppData/Local/Zed`, or the Flatpak
`.var/app/dev.zed.Zed*/data/zed`):

* `threads/threads.db` (rollback journal, so a `-journal` may sit beside it):
  table `threads(id, summary, updated_at, data_type, data, parent_id,
  folder_paths, folder_paths_order, created_at)`. `id` is the session id,
  `folder_paths` the project paths joined by newlines, `updated_at` and
  `created_at` RFC 3339. `data` is zstd-compressed JSON when `data_type` is
  `zstd` (decoded with the `zstandard` package) and raw UTF-8 JSON when
  `json`.
  The thread JSON, `version` `0.3.0`: `title`, `updated_at`,
  `initial_project_snapshot.timestamp`,
  `initial_project_snapshot.worktree_snapshots[].worktree_path` and
  `.git_state.current_branch`, `model.provider`, `model.model`,
  `subagent_context.parent_thread_id`, and `messages[]`, externally tagged:
  - `{"User": {"id", "content": [{"Text"}, {"Mention": {"uri"}}, {"Image"}]}}`
  - `{"Agent": {"content": [{"Text"}, {"Thinking": {"text"}},
    {"RedactedThinking"}, {"ToolUse": {"id", "name", "raw_input",
    "input"}}], "tool_results": {<id>: {"tool_use_id", "tool_name",
    "is_error", "content": [{"Text"}]}}}}`
  - `"Resume"`, `{"Compaction": {"Summary"}}` or
    `{"Compaction": {"ProviderNative"}}`.
  Versions `0.1.0` and `0.2.0` (`messages[].role`, `segments[]` with
  `type` text/thinking/RedactedThinking, `tool_uses[]`, `tool_results[]`)
  and the unversioned legacy shape (`messages[].role`, `.text`) are read
  on a best-effort basis; their role spelling was not confirmed.
* `db/0-<channel>/db.sqlite` (WAL): table `sidebar_threads(session_id,
  agent_id, title, title_override, updated_at, interacted_at,
  folder_paths, archived)`. Rows with `agent_id` set are external ACP agent
  threads whose transcript is not in `threads.db`; each becomes one `system`
  row. Native rows (`agent_id` NULL) are skipped, their thread is parsed
  from `threads.db`.

There are no per-message timestamps. Every message row carries the thread's
`updated_at` (approximate: it is the last write, not the message time); the
thread-start row carries `initial_project_snapshot.timestamp`, falling back
to `created_at`. `source_line` is the SQLite `rowid` of the thread or
sidebar row. The git branch is the one captured at thread start.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Iterator

import zstandard

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json

DATA_DIR = r"(?:\.local/share/zed|Library/Application Support/Zed|AppData/Local/Zed|\.var/app/dev\.zed\.Zed[A-Za-z]*/data/zed)"
THREADS_RX = re.compile(r"^" + DATA_DIR + r"/threads/threads\.db$")
SIDEBAR_RX = re.compile(r"^" + DATA_DIR + r"/db/0-[^/]+/db\.sqlite$")


def decompress(blob: bytes) -> bytes:
    dctx = zstandard.ZstdDecompressor()
    try:
        return dctx.decompress(blob)
    except zstandard.ZstdError:
        # No content size in the frame header: stream it instead.
        out = io.BytesIO()
        with dctx.stream_reader(io.BytesIO(blob)) as reader:
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                out.write(chunk)
        return out.getvalue()


def content_text(content) -> str:
    """Text of a tool result `content`: a list of `{"Text": ...}` /
    `{"Image": ...}` items, a single such item, or a plain string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        content = [content]
    if not isinstance(content, list):
        return compact_json(content)
    parts = []
    for c in content:
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, dict):
            if isinstance(c.get("Text"), str):
                parts.append(c["Text"])
            elif "Image" in c:
                parts.append("[image]")
            elif isinstance(c.get("text"), str):
                parts.append(c["text"])
            else:
                parts.append(compact_json(c))
    return "\n".join(parts)


def mention_text(m) -> str:
    if not isinstance(m, dict):
        return "[mention]"
    uri = m.get("uri")
    return "[mention] " + (uri if isinstance(uri, str) else compact_json(uri))


def tool_input_text(tu: dict) -> str:
    inp = tu.get("input")
    if isinstance(inp, dict) and set(inp) <= {"type", "value"} and "value" in inp:
        inp = inp["value"]
    if inp not in (None, "", {}):
        return inp if isinstance(inp, str) else compact_json(inp)
    raw = tu.get("raw_input")
    return raw if isinstance(raw, str) else ""


def first_folder(folder_paths) -> str:
    if not isinstance(folder_paths, str):
        return ""
    for p in folder_paths.split("\n"):
        if p.strip():
            return p
    return ""


class ZedParser(Parser):
    agent = "zed"
    name = "zed"

    def wants(self, artifact: Artifact) -> bool:
        return bool(THREADS_RX.match(artifact.rel) or SIDEBAR_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            return
        if THREADS_RX.match(artifact.rel):
            yield from self._parse_threads(artifact, opts)
        else:
            yield from self._parse_sidebar(artifact, opts)

    # -- db/0-<channel>/db.sqlite -------------------------------------------------
    def _parse_sidebar(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        with open_copy(artifact.disk_path) as con:
            if "sidebar_threads" not in table_names(con):
                return
            for r in con.execute(
                "select rowid as _rowid, * from sidebar_threads order by updated_at"
            ):
                r = dict(r)
                if not r.get("agent_id"):
                    continue
                row = self.base_row(artifact)
                row.source_line = r["_rowid"]
                row.session_id = str(r.get("session_id") or "")
                row.timestamp_utc = to_utc(r.get("interacted_at") or r.get("updated_at"))
                row.project_path = first_folder(r.get("folder_paths"))
                row.turn_type = "system"
                row.text = compact(
                    "external agent thread (no transcript in threads.db): agent=%s title=%s%s"
                    % (
                        r["agent_id"],
                        r.get("title_override") or r.get("title") or "",
                        " archived" if r.get("archived") else "",
                    ),
                )
                yield row

    # -- threads/threads.db -------------------------------------------------------
    def _parse_threads(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        with open_copy(artifact.disk_path) as con:
            if "threads" not in table_names(con):
                return
            for r in con.execute("select rowid as _rowid, * from threads order by updated_at"):
                yield from self._thread_rows(artifact, dict(r), opts)

    def _thread_rows(self, artifact: Artifact, r: dict, opts: Options) -> Iterator[Row]:
        session_id = str(r.get("id") or "")
        project = first_folder(r.get("folder_paths"))
        updated = to_utc(r.get("updated_at"))

        def base(turn_type: str, text: str, ts: str = "", model: str = "", branch: str = "") -> Row:
            row = self.base_row(artifact)
            row.source_line = r["_rowid"]
            row.session_id = session_id
            row.project_path = project
            row.git_branch = branch
            row.timestamp_utc = ts or updated
            row.model = model
            row.turn_type = turn_type
            row.text = compact(text)
            return row

        thread, err = self._decode(r)
        if thread is None:
            yield base(
                "system",
                "thread %s could not be decoded (%s): %s"
                % (session_id, err, r.get("summary") or ""),
            )
            return

        snap = thread.get("initial_project_snapshot")
        if not isinstance(snap, dict):
            snap = {}
        worktrees = [w for w in (snap.get("worktree_snapshots") or []) if isinstance(w, dict)]
        if not project and worktrees:
            project = str(worktrees[0].get("worktree_path") or "")
        branches = [
            (w.get("worktree_path") == project, str(w["git_state"]["current_branch"]))
            for w in worktrees
            if isinstance(w.get("git_state"), dict) and w["git_state"].get("current_branch")
        ]
        branch = max(branches, key=lambda b: b[0])[1] if branches else ""
        m = thread.get("model")
        if not isinstance(m, dict):
            m = {}
        model = "/".join(str(x) for x in (m.get("provider"), m.get("model")) if x)
        if not updated:
            updated = to_utc(thread.get("updated_at"))

        parent = r.get("parent_id") or (
            (thread.get("subagent_context") or {}).get("parent_thread_id")
            if isinstance(thread.get("subagent_context"), dict)
            else ""
        )
        start_ts = to_utc(snap.get("timestamp")) or to_utc(r.get("created_at")) or updated
        yield base(
            "system",
            " ".join(
                x
                for x in (
                    "thread start:",
                    str(thread.get("title") or r.get("summary") or ""),
                    "version=%s" % thread["version"] if thread.get("version") else "",
                    "parent=%s" % parent if parent else "",
                )
                if x
            ),
            start_ts,
            model,
            branch,
        )

        for kind, text, tool_name, tool_id in self._messages(thread):
            if kind == "thinking" and not opts.include_thinking:
                continue
            if not text and kind not in ("tool_use", "tool_result"):
                continue
            row = base(kind, text, "", model, branch)
            row.tool_name = tool_name
            row.tool_use_id = tool_id
            yield row

    @staticmethod
    def _decode(r: dict) -> tuple[dict | None, str]:
        data = r.get("data")
        if data is None:
            return None, "no data"
        dtype = str(r.get("data_type") or "").lower()
        try:
            if dtype == "zstd":
                raw = decompress(bytes(data))
            else:
                raw = data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8")
            thread = json.loads(bytes(raw).decode("utf-8", errors="replace"))
        except Exception as e:  # noqa: BLE001 - zstandard.ZstdError, ValueError, ...
            return None, "%s: %s" % (type(e).__name__, e)
        if not isinstance(thread, dict):
            return None, "not a JSON object"
        return thread, ""

    def _messages(self, thread: dict) -> Iterator[tuple[str, str, str, str]]:
        """(turn_type, text, tool_name, tool_use_id) in transcript order."""
        for msg in thread.get("messages") or []:
            if isinstance(msg, str):
                yield "system", msg.lower(), "", ""
            elif not isinstance(msg, dict):
                continue
            elif "User" in msg:
                yield from self._user(msg["User"])
            elif "Agent" in msg:
                yield from self._agent(msg["Agent"])
            elif "Compaction" in msg:
                c = msg["Compaction"]
                if isinstance(c, dict) and isinstance(c.get("Summary"), str):
                    yield "system", "compaction: " + c["Summary"], "", ""
                else:
                    yield "system", "compaction: provider native", "", ""
            elif "role" in msg:
                yield from self._legacy(msg)

    @staticmethod
    def _user(u) -> Iterator[tuple[str, str, str, str]]:
        # One row per prompt: text, mentions and images of one User message
        # are joined so sessions.jsonl counts prompts, not content items.
        content = u.get("content") if isinstance(u, dict) else None
        if isinstance(content, (str, dict)):
            content = [content]
        parts = []
        for c in content or []:
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, dict):
                if isinstance(c.get("Text"), str):
                    parts.append(c["Text"])
                elif "Mention" in c:
                    parts.append(mention_text(c["Mention"]))
                elif "Image" in c:
                    parts.append("[image]")
                else:
                    parts.append(compact_json(c))
        yield "user", "\n".join(parts), "", ""

    @staticmethod
    def _agent(a) -> Iterator[tuple[str, str, str, str]]:
        if not isinstance(a, dict):
            return
        results = a.get("tool_results")
        if not isinstance(results, dict):
            results = {}
        done = set()

        def result(key, res):
            if not isinstance(res, dict):
                res = {}
            text = content_text(res.get("content"))
            if not text and res.get("output") is not None:
                text = (
                    content_text(res["output"])
                    if not isinstance(res["output"], dict)
                    else compact_json(res["output"])
                )
            if res.get("is_error"):
                text = "[error] " + text
            return (
                "tool_result",
                text,
                str(res.get("tool_name") or ""),
                str(res.get("tool_use_id") or key),
            )

        content = a.get("content")
        if isinstance(content, (str, dict)):
            content = [content]
        for c in content or []:
            if isinstance(c, str):
                yield "assistant", c, "", ""
            elif not isinstance(c, dict):
                continue
            elif isinstance(c.get("Text"), str):
                yield "assistant", c["Text"], "", ""
            elif "Thinking" in c:
                t = c["Thinking"]
                yield "thinking", (t.get("text") if isinstance(t, dict) else str(t)) or "", "", ""
            elif "RedactedThinking" in c:
                yield "thinking", "[redacted thinking]", "", ""
            elif isinstance(c.get("ToolUse"), dict):
                tu = c["ToolUse"]
                tid = str(tu.get("id") or "")
                yield "tool_use", tool_input_text(tu), str(tu.get("name") or ""), tid
                # The result follows its call, so the timeline reads in order.
                if tid in results:
                    done.add(tid)
                    yield result(tid, results[tid])
            elif "Image" in c:
                yield "assistant", "[image]", "", ""
        for key, res in results.items():
            if key not in done:
                yield result(key, res)

    @staticmethod
    def _legacy(msg: dict) -> Iterator[tuple[str, str, str, str]]:
        role = str(msg.get("role") or "").lower()
        kind = "user" if role == "user" else "assistant" if role == "assistant" else "system"
        if isinstance(msg.get("text"), str):
            yield kind, msg["text"] if kind != "system" else "%s: %s" % (role, msg["text"]), "", ""
        for seg in msg.get("segments") or []:
            if not isinstance(seg, dict):
                continue
            st = str(seg.get("type") or "").lower()
            if st == "text":
                yield kind, str(seg.get("text") or ""), "", ""
            elif st == "thinking":
                yield "thinking", str(seg.get("text") or ""), "", ""
            elif st == "redactedthinking":
                yield "thinking", "[redacted thinking]", "", ""
        for tu in msg.get("tool_uses") or []:
            if isinstance(tu, dict):
                yield (
                    "tool_use",
                    tool_input_text(tu),
                    str(tu.get("name") or ""),
                    str(tu.get("id") or ""),
                )
        for res in msg.get("tool_results") or []:
            if isinstance(res, dict):
                text = content_text(res.get("content"))
                if res.get("is_error"):
                    text = "[error] " + text
                yield "tool_result", text, "", str(res.get("tool_use_id") or "")


__all__ = ["ZedParser", "content_text", "decompress", "first_folder", "tool_input_text"]
