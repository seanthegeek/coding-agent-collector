"""Kilo Code sessions.

Validated against source, Kilo-Org/kilocode at 76bcfd4 (see
`analyzer/research/kilo-code.md`), with a synthetic fixture; no real install
was used. Kilo Code's CLI, TUI and server are an OpenCode fork with the same
SQLite and JSON storage, so this parser is `OpenCodeParser` (see
`opencode.py` for the tables, fields and row mapping) pointed at Kilo's
paths, plus the pre-migration task directories of the VS Code extension.

Files, relative to the home directory:

* `.local/share/kilo/kilo.db`, `kilo-<channel>.db`, or a pre-existing
  `opencode-<channel>.db` in the same directory, with WAL sidecars. Kilo
  writes both the V1 `message`/`part` tables and V2 `session_message`;
  V1 is read and V2 only for sessions with no V1 rows, as for OpenCode.
* `.local/share/kilo/storage/{session,message,part,project}/...` and the
  older `.local/share/kilo/project/<slug>/storage/session/...` JSON trees,
  laid out exactly as OpenCode's.
* `<VS Code user dir>/User/globalStorage/kilocode.kilo-code/tasks/<id>/
  api_conversation_history.json`: Roo-style tasks from before the move to
  the OpenCode core. Kilo's own importer reads this file
  (`packages/kilo-vscode/src/legacy-migration/task-store.ts`), so it is the
  one parsed here; `ui_messages.json` repeats the same turns for display.
  It is a JSON array of Anthropic `MessageParam` records: `role`, `content`
  (a string or blocks typed `text`, `image`, `tool_use` with `id`, `name`,
  `input`, `tool_result` with `tool_use_id`, `content`, `is_error`, and
  `thinking` or `reasoning`), plus Roo's `ts` (epoch ms), `isSummary`, and
  top-level `type: "reasoning"` records with `summary` or
  `reasoning_content`. The task's `workspace`, `task` and `ts` come from
  `history_item.json` in the same directory, else the matching entry of
  `tasks/_index.json` (`{entries: [HistoryItem]}`). The session id is the
  directory name. The history item, when found, becomes one `system` row
  with `source_line` 0. No model is recorded. Records without `ts` inherit the
  task's `ts`. `source_line` is the record's 1-based position in the array
  (Roo writes the array on one line). A file cut mid-write keeps every
  complete record before the cut and adds one `system` row. Tool calls
  written as XML inside text blocks, as older Roo prompts did, stay in the
  text of the `assistant` row; text blocks that are only
  `<environment_details>` are `system` rows.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, compact_json, text_of
from .opencode import OpenCodeParser, tool_summary

TASK_RX = re.compile(
    r"(?:^|/)User/globalStorage/kilocode\.kilo-code/tasks/([^/]+)/api_conversation_history\.json$"
)


def iter_json_array(raw: str) -> tuple[list[object], str | None]:
    """Decode a JSON array element by element so a file truncated mid-write
    still yields its complete leading elements. Returns (items, error)."""
    dec = json.JSONDecoder()
    items: list[object] = []
    i = 0
    n = len(raw)

    def skip(j: int) -> int:
        while j < n and raw[j] in " \t\r\n":
            j += 1
        return j

    i = skip(i)
    if i >= n or raw[i] != "[":
        return items, "not a JSON array"
    i = skip(i + 1)
    if i < n and raw[i] == "]":
        return items, None
    while i < n:
        try:
            obj, i = dec.raw_decode(raw, i)
        except ValueError as e:
            return items, "record %d: %s" % (len(items) + 1, e)
        items.append(obj)
        i = skip(i)
        if i < n and raw[i] == ",":
            i = skip(i + 1)
            continue
        if i < n and raw[i] == "]":
            if skip(i + 1) < n:
                return items, "unexpected data after the array"
            return items, None
        break
    return items, "record %d: unexpected end of file" % (len(items) + 1)


def _read_json(path: Path):
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


class KiloCodeParser(OpenCodeParser):
    agent = "kilo-code"
    name = "kilo-code"
    data_dir = ".local/share/kilo"
    db_prefixes = ("kilo", "opencode")

    def wants(self, artifact: Artifact) -> bool:
        return bool(TASK_RX.search(artifact.rel)) or super().wants(artifact)

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if TASK_RX.search(artifact.rel):
            yield from self._parse_task(artifact, opts)
        else:
            yield from super().parse(artifact, opts)

    # -- legacy Roo-style tasks -----------------------------------------------------
    @staticmethod
    def _history_item(task_dir: Path, task_id: str) -> dict:
        item = None
        f = task_dir / "history_item.json"
        if f.is_file() and not f.is_symlink():
            item = _read_json(f)
        if not isinstance(item, dict):
            idx = task_dir.parent / "_index.json"
            data = _read_json(idx) if idx.is_file() and not idx.is_symlink() else None
            entries = data.get("entries") if isinstance(data, dict) else None
            for e in entries if isinstance(entries, list) else []:
                if isinstance(e, dict) and e.get("id") == task_id:
                    item = e
                    break
        return item if isinstance(item, dict) else {}

    def _parse_task(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        task_dir = artifact.disk_path.parent
        task_id = task_dir.name
        item = self._history_item(task_dir, task_id)
        project = str(item.get("workspace") or "")
        task_ts = to_utc(item.get("ts"))
        if not task_ts and task_id.isdigit():
            task_ts = to_utc(int(task_id))

        def base(line: int, ts: str) -> Row:
            row = self.base_row(artifact)
            row.source_line = line
            row.session_id = task_id
            row.project_path = project
            row.timestamp_utc = ts
            return row

        if item:
            row = base(0, task_ts)
            row.turn_type = "system"
            row.text = compact(
                " ".join(
                    p
                    for p in (
                        "task:",
                        str(item.get("task") or ""),
                        "mode=%s" % item["mode"] if item.get("mode") else "",
                        "status=%s" % item["status"] if item.get("status") else "",
                        "parent=%s" % item["parentTaskId"] if item.get("parentTaskId") else "",
                    )
                    if p
                ),
                opts.max_text_length,
            )
            yield row

        with open(artifact.disk_path, "rb") as fh:
            raw = fh.read().decode("utf-8", errors="replace")
        items, error = iter_json_array(raw)
        for n, msg in enumerate(items, 1):
            if not isinstance(msg, dict):
                continue
            ts = to_utc(msg.get("ts")) or task_ts

            def mk(turn: str, text) -> Row:
                row = base(n, ts)
                row.turn_type = turn
                row.text = compact(text, opts.max_text_length)
                return row

            if msg.get("type") == "reasoning":
                if opts.include_thinking:
                    text = text_of(msg.get("summary")) or str(
                        msg.get("reasoning_content") or msg.get("text") or ""
                    )
                    if text:
                        yield mk("thinking", text)
                continue
            role = msg.get("role")
            content = msg.get("content")
            if msg.get("isSummary"):
                yield mk("system", "summary: " + text_of(content))
                continue
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if not isinstance(content, list):
                continue
            # The text blocks of one message become one row, placed where the
            # first of them was so it keeps its order relative to tool blocks.
            texts: list[str] = []
            text_at = -1
            out: list[Row] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype in ("text", "image"):
                    t = "[image]" if btype == "image" else (block.get("text") or "")
                    if t.lstrip().startswith("<environment_details>"):
                        out.append(mk("system", t))
                    elif t:
                        if text_at < 0:
                            text_at = len(out)
                        texts.append(t)
                elif btype == "tool_use":
                    row = mk("tool_use", tool_summary(block.get("input")))
                    row.tool_name = str(block.get("name") or "")
                    row.tool_use_id = str(block.get("id") or "")
                    out.append(row)
                elif btype == "tool_result":
                    text = text_of(block.get("content"))
                    row = mk("tool_result", ("[error] " + text) if block.get("is_error") else text)
                    row.tool_use_id = str(block.get("tool_use_id") or "")
                    out.append(row)
                elif btype in ("thinking", "reasoning"):
                    t = block.get("thinking") or block.get("text") or ""
                    if opts.include_thinking and t:
                        out.append(mk("thinking", t))
                else:
                    out.append(mk("system", "%s: %s" % (btype or "block", compact_json(block))))
            if texts:
                out.insert(
                    text_at,
                    mk(
                        "user"
                        if role == "user"
                        else "assistant"
                        if role == "assistant"
                        else "system",
                        "\n".join(texts),
                    ),
                )
            yield from out
        if error:
            row = base(len(items) + 1, "")
            row.turn_type = "system"
            row.text = "parser: %s; %d earlier record(s) kept" % (error, len(items))
            yield row
