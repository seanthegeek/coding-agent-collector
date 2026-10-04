"""Cline transcripts, legacy task layout and SDK sessions.

Validated against source (cline/cline at 39ff2359, see
`analyzer/research/cline.md`) with a synthetic fixture; no real install.

Legacy task layout, under the VS Code extension's
`<editor>/User/globalStorage/saoudrizwan.claude-dev/` or `~/.cline/data/`
(CLI and JetBrains): `tasks/<taskId>/ui_messages.json`,
`api_conversation_history.json` and `task_metadata.json` are read by the
shared mapping in `cline_legacy.py`, whose docstring lists the fields. The
task id is a `Date.now()` millisecond string, which is also the session
timestamp that API history records (which carry no timestamp of their own)
inherit when `ui_messages.json` is missing.

* `state/taskHistory.json`: JSON array of `HistoryItem {id, ts, task,
  tokensIn, tokensOut, cacheWrites, cacheReads, totalCost, size,
  cwdOnTaskInitialization, modelId, apiProvider}`. One `system` row per
  task, kept because it survives deletion of the task directory; it is also
  where the task's project path and fallback model come from. Older VS Code
  builds kept this list in the editor's `state.vscdb`, which is not read.

SDK session layout, `~/.cline/data/sessions/<sessionId>/`:

* `<sessionId>.json` manifest: `session_id, source, pid, started_at,
  ended_at, exit_code, status, interactive, provider, model, cwd,
  workspace_root, prompt, metadata.title`. A `system` row for the start and,
  when `ended_at` is set, one for the end.
* `<sessionId>.messages.json` and subagent `<agentId>[__<teamTaskId>]
  .messages.json`: `{version, updated_at, agent, sessionId, messages:
  [{id, role, content, modelInfo: {id, provider}, metrics, ts}]}` with
  Anthropic-style content blocks (`text`, `tool_use {id, name, input}`,
  `tool_result {tool_use_id, name, content, is_error}`, `thinking`,
  `redacted_thinking`, `image`, `file {path}`). One row per block;
  `ts` is epoch milliseconds; a message without one takes the previous
  message's time, or for the first message the manifest `started_at` and
  then the file's `updated_at`. `session_id` is the session directory
  name, so subagent rows group with their lead session; `project_path` and
  the fallback model come from the manifest beside it.
* `~/.cline/data/db/sessions.db`, table `sessions` (`session_id, source,
  started_at, ended_at, status, provider, model, cwd, workspace_root,
  prompt, parent_session_id, is_subagent`): a `system` row only for a
  session whose manifest is not on disk, so deleted sessions still show.

Not read: `<sessionId>.compaction.json`, `sessions/sessions.index.json`,
`db/session-search.db` (a full-text copy of the transcripts),
`teams/teams.db` and `logs/hooks.jsonl`.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options
from .cline_legacy import (
    LegacyTaskParser,
    content_rows,
    error_row,
    iter_array_at,
    iter_json_array,
    load_json,
    read_text,
)

ROOT = r"(?:(?:.*/)?User/globalStorage/saoudrizwan\.claude-dev|\.cline/data)"
STATE_RX = re.compile(r"^%s/state/taskHistory\.json$" % ROOT, re.I)
MANIFEST_RX = re.compile(r"^\.cline/data/sessions/([^/]+)/\1\.json$")
MESSAGES_RX = re.compile(r"^\.cline/data/sessions/[^/]+/[^/]+\.messages\.json$")
SESSIONS_DB_REL = ".cline/data/db/sessions.db"
MESSAGES_KEY_RX = re.compile(r'"messages"\s*:\s*(?=\[)')


class ClineParser(LegacyTaskParser):
    agent = "cline"
    name = "cline"
    ROOT = ROOT
    PROJECT_KEY = "cwdOnTaskInitialization"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return bool(self.task_match(artifact) or STATE_RX.match(rel) or MANIFEST_RX.match(rel)
                    or MESSAGES_RX.match(rel)) or rel == SESSIONS_DB_REL

    def history_item(self, task_dir: Path, root: Path, task_id: str) -> dict | None:
        items = self.cached_json(root / "state" / "taskHistory.json")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and str(item.get("id")) == task_id:
                    return item
        return None

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        rel = artifact.rel
        if self.task_match(artifact):
            yield from self.parse_task_file(artifact, opts)
        elif STATE_RX.match(rel):
            yield from self._parse_task_history(artifact, opts)
        elif MANIFEST_RX.match(rel):
            yield from self._parse_manifest(artifact, opts)
        elif MESSAGES_RX.match(rel):
            yield from self._parse_messages(artifact, opts)
        elif rel == SESSIONS_DB_REL:
            yield from self._parse_sessions_db(artifact, opts)

    def _parse_task_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, item in iter_json_array(artifact.disk_path, errors):
            if isinstance(item, dict):
                yield self.history_row(artifact, item, n, opts)
        if errors:
            yield error_row(self, artifact, errors)

    # -- SDK sessions

    def _session_start(self, m: dict, artifact: Artifact, n: int, opts: Options, ts_key: str, label: str,
                       keys) -> Row:
        row = self.base_row(artifact)
        row.source_line = n
        row.timestamp_utc = to_utc(m.get(ts_key))
        row.session_id = str(m.get("session_id") or "")
        row.project_path = str(m.get("cwd") or m.get("workspace_root") or "")
        row.model = str(m.get("model") or "")
        row.turn_type = "system"
        detail = " ".join("%s=%s" % (k, m[k]) for k in keys if m.get(k) not in (None, ""))
        row.text = compact("%s: %s" % (label, detail), opts.max_text_length)
        return row

    START_KEYS = ("source", "provider", "model", "status", "interactive", "pid", "parent_session_id",
                  "is_subagent", "title", "prompt")
    END_KEYS = ("status", "exit_code")

    def _parse_manifest(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = load_json(artifact.disk_path)
        if not isinstance(m, dict):
            yield error_row(self, artifact, [(0, "session manifest is not a JSON object")],
                            artifact.disk_path.parent.name)
            return
        m = dict(m)
        m.setdefault("session_id", artifact.disk_path.parent.name)
        meta = m.get("metadata")
        if isinstance(meta, dict) and meta.get("title"):
            m["title"] = meta["title"]
        yield self._session_start(m, artifact, 0, opts, "started_at", "session start", self.START_KEYS)
        if m.get("ended_at"):
            yield self._session_start(m, artifact, 0, opts, "ended_at", "session end", self.END_KEYS)

    def _parse_messages(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        session_id = artifact.disk_path.parent.name
        manifest = load_json(artifact.disk_path.parent / (session_id + ".json"))
        manifest = manifest if isinstance(manifest, dict) else {}
        project = str(manifest.get("cwd") or manifest.get("workspace_root") or "")
        s = read_text(artifact.disk_path)
        errors: list = []
        payload = None
        if s is None:
            errors.append((0, "unreadable"))
        else:
            try:
                payload = json.loads(s)
            except ValueError:
                payload = None
        if isinstance(payload, dict):
            messages = enumerate(payload.get("messages") or [], 1)
            fallback = to_utc(manifest.get("started_at")) or to_utc(payload.get("updated_at"))
        elif s is not None:
            # Cut mid-write: walk the messages array as far as it parses.
            m = MESSAGES_KEY_RX.search(s)
            if m:
                messages = iter_array_at(s, m.end(), errors)
            else:
                errors.append((0, "messages file is not a JSON object"))
                messages = iter(())
            fallback = to_utc(manifest.get("started_at"))
        else:
            messages = iter(())
            fallback = ""
        for n, msg in messages:
            if not isinstance(msg, dict):
                continue
            ts = to_utc(msg.get("ts")) or fallback
            fallback = ts
            info = msg.get("modelInfo")
            model = str((info.get("id") if isinstance(info, dict) else "") or manifest.get("model") or "")
            role = msg.get("role")
            base_turn = "user" if role == "user" else "assistant" if role == "assistant" else "system"
            for turn, text, name, tid in content_rows(msg.get("content"), base_turn, opts.include_thinking):
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = ts
                row.session_id = session_id
                row.project_path = project
                row.model = model
                row.turn_type = turn
                row.tool_name = name
                row.tool_use_id = tid
                row.text = compact(text, opts.max_text_length)
                yield row
        if errors:
            yield error_row(self, artifact, errors, session_id, project)

    def _parse_sessions_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            yield error_row(self, artifact, [(0, "sessions.db is not a SQLite database")])
            return
        sessions_dir = artifact.disk_path.parent.parent / "sessions"
        try:
            with open_copy(artifact.disk_path) as con:
                if "sessions" not in table_names(con):
                    return
                rows = [dict(r) for r in con.execute("select rowid as _rowid, * from sessions")]
        except Exception as e:  # noqa: BLE001 - a damaged database must not stop the timeline
            yield error_row(self, artifact, [(0, "sessions.db unreadable (%s)" % e)])
            return
        for r in rows:
            sid = str(r.get("session_id") or "")
            if sid and (sessions_dir / sid / (sid + ".json")).is_file():
                continue
            if r.get("metadata_json"):
                meta = load_json_text(r["metadata_json"])
                if isinstance(meta, dict) and meta.get("title"):
                    r["title"] = meta["title"]
            yield self._session_start(r, artifact, int(r.get("_rowid") or 0), opts, "started_at",
                                      "session index", (*self.START_KEYS, "ended_at", "exit_code"))


def load_json_text(s):
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return None

