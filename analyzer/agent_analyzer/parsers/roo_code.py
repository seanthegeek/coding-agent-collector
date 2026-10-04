"""Roo Code transcripts.

Validated against source (RooCodeInc/Roo-Code at b867ec91, see
`analyzer/research/roo-code.md`) with a synthetic fixture; no real install.

Roo Code forked Cline and keeps its per-task layout, so the transcript files
are read by the shared mapping in `cline_legacy.py`, whose docstring lists
the fields. Roots: the extension's
`<editor>/User/globalStorage/rooveterinaryinc.roo-cline/` and the CLI's
`~/.vscode-mock/global-storage/`. A root moved with the
`roo-cline.customStoragePath` setting is not found.

* `tasks/<taskId>/ui_messages.json`, `api_conversation_history.json` (or
  the pre-rename `claude_messages.json`) and `task_metadata.json`, as in
  Cline. Roo's differences: the task prompt is the first `say: "text"`
  record (there is no `say: "task"`), `condense_context` carries
  `contextCondense {summary, prevContextTokens, newContextTokens, cost}`,
  API history records carry their own `ts`, and `task_metadata.json` holds
  only `files_in_context` with `roo_read_date` and `roo_edit_date`. The task
  id is a UUID, so API history records without `ts` inherit the
  `HistoryItem.ts`.
* `tasks/<taskId>/history_item.json`: one `HistoryItem {id, ts, task,
  tokensIn, tokensOut, totalCost, size, workspace, mode, status,
  apiConfigName, parentTaskId, rootTaskId}`. One `system` row; `workspace`
  is the task's project path.
* `tasks/_index.json`: `{version, updatedAt, entries: HistoryItem[]}`. A
  `system` row only for entries whose `history_item.json` is not on disk,
  so a deleted task still shows without doubling the others.

No model name is recorded anywhere in Roo transcripts (`apiConfigName` is a
profile name), so `model` is always empty. No git branch is recorded.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row
from .base import Options
from .cline_legacy import LegacyTaskParser, error_row, load_json

ROOT = r"(?:(?:.*/)?User/globalStorage/rooveterinaryinc\.roo-cline|\.vscode-mock/global-storage)"
ITEM_RX = re.compile(r"^%s/tasks/[^/]+/history_item\.json$" % ROOT, re.I)
INDEX_RX = re.compile(r"^%s/tasks/_index\.json$" % ROOT, re.I)
ITEM_FILE = "history_item.json"


class RooCodeParser(LegacyTaskParser):
    agent = "roo-code"
    name = "roo-code"
    ROOT = ROOT
    PROJECT_KEY = "workspace"

    def wants(self, artifact: Artifact) -> bool:
        return bool(
            self.task_match(artifact) or ITEM_RX.match(artifact.rel) or INDEX_RX.match(artifact.rel)
        )

    def history_item(self, task_dir: Path, root: Path, task_id: str) -> dict | None:
        item = load_json(task_dir / ITEM_FILE)
        if isinstance(item, dict):
            return item
        index = self.cached_json(root / "tasks" / "_index.json")
        entries = index.get("entries") if isinstance(index, dict) else None
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict) and str(e.get("id")) == task_id:
                    return e
        return None

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if self.task_match(artifact):
            yield from self.parse_task_file(artifact, opts)
        elif ITEM_RX.match(artifact.rel):
            item = load_json(artifact.disk_path)
            if isinstance(item, dict):
                yield self.history_row(artifact, item, 1, opts)
            else:
                yield error_row(
                    self,
                    artifact,
                    [(0, "history_item.json is not a JSON object")],
                    artifact.disk_path.parent.name,
                )
        elif INDEX_RX.match(artifact.rel):
            yield from self._parse_index(artifact, opts)

    def _parse_index(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        index = load_json(artifact.disk_path)
        if not isinstance(index, dict) or not isinstance(index.get("entries"), list):
            yield error_row(self, artifact, [(0, "_index.json has no entries array")])
            return
        tasks = artifact.disk_path.parent
        for n, e in enumerate(index["entries"], 1):
            if not isinstance(e, dict):
                continue
            tid = str(e.get("id") or "")
            if tid and (tasks / tid / ITEM_FILE).is_file():
                continue
            yield self.history_row(artifact, e, n, opts)
