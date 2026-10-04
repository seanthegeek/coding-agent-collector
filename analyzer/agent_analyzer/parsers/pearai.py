"""PearAI chat sessions (Continue fork) and agent tasks (Roo Code fork).

Validated against source, trypear/pearai-submodule at 51eceef6 and
trypear/PearAI-Roo-Code at 0b6df736 (see `analyzer/research/pearai.md`),
with a synthetic fixture; no real install was checked. Both forks are older
snapshots of their upstreams, so the shapes differ from `continue_dev.py`
and `roo_code.py`.

Chat sessions, `.pearai/sessions/` (the Continue fork's global dir):

* `<sessionId>.json`: `sessionId`, `title`, `workspaceDirectory`,
  `history[]` and `perplexityHistory[]` ("PearAI Search" turns). Items:
  `message` (`role` user, assistant or system; `content` a string or
  `{type: "text", text}` / `{type: "imageUrl"}` parts), `contextItems[]`
  (`name`, `description`), `promptLogs[].completionOptions.model`,
  `citations[]` (`url`, `title`). There are no tool calls, tool messages or
  thinking in this fork.
* `sessions.json`: the index, `{sessionId, title, dateCreated (ms epoch as
  a string), workspaceDirectory, integrationType}`; read for the time, not
  parsed into rows.

Every row of a session inherits `dateCreated` (no per-message time).
`history[]` rows come first, then `perplexityHistory[]`; `source_line` is
the 1-based item position, continuing from `history[]` into
`perplexityHistory[]`, and 0 for the session row. User rows list the
context items (`description`, else `name`); assistant rows list citation
URLs. A truncated session file keeps the `history[]` items decoded before
the cut (via `continue_dev.load_session`) plus one `system` row;
`perplexityHistory[]` is not recovered from a damaged file.

Agent tasks, `<editor User dir>/globalStorage/pearai.pearai-roo-cline/tasks/
<taskId>/` (Roo Code 3.15): `ui_messages.json`, `api_conversation_history.json`
and `task_metadata.json`, read by the shared mapping in `cline_legacy.py`
exactly as for Roo Code, so `ui_messages.json` is preferred and the API
history is parsed only when it is absent. The task's project is
`taskHistory[].workspace` from the `pearai.pearai-roo-cline` row of the
`state.vscdb` beside the extension directory, when it was collected.

API history records carry `ts` (ms) and Anthropic content blocks, but tool
calls are XML inside assistant text: `<execute_command><command>npm
test</command></execute_command>`, tool names from `toolNames` in
`src/schemas/index.ts`. Each such tag becomes a `tool_use` row whose text
is the parameter values joined with ` | `; `<thinking>` blocks become
`thinking` rows (opt-in); the remaining text is an `assistant` row. Results
come back in the next user message as a text block
`[<tool> for '<arg>'] Result:` followed by the output blocks, or a
`Skipping tool [...]` / `Tool [...] was not executed` notice; each becomes a
`tool_result` row. Tool calls have no id, so `tool_use_id` is the
assistant message's position in the array (with `.2`, `.3` for further
tags in the same message) and a result takes the position of the message
before it; Roo runs one tool per message and the API history alternates
roles. `<environment_details>` blocks become `system` rows, and the
`<task>` wrapper of the first prompt is removed. No model or git branch is
recorded.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from ..vscode_state import read_item
from .base import Options
from .cline_legacy import LegacyTaskParser, content_rows, read_text
from .continue_dev import ContinueParser, load_session, message_text

ROOT = r"(?:.*/)?User/globalStorage/pearai\.pearai-roo-cline"
SESSION_RX = re.compile(r"^(?:.*/)?\.pearai/sessions/([^/]+)\.json$")
INDEX_NAME = "sessions.json"
EXTENSION_ID = "pearai.pearai-roo-cline"

TOOL_NAMES = ("execute_command", "read_file", "write_to_file", "apply_diff", "insert_content",
              "search_and_replace", "search_files", "list_files", "list_code_definition_names",
              "browser_action", "use_mcp_tool", "access_mcp_resource", "ask_followup_question",
              "attempt_completion", "switch_mode", "new_task", "fetch_instructions")
BLOCK_RX = re.compile(r"<(thinking|%s)>(.*?)(?:</\1>|$)" % "|".join(TOOL_NAMES), re.S)
PARAM_RX = re.compile(r"<([a-z_]+)>(.*?)(?:</\1>|$)", re.S)
RESULT_RX = re.compile(r"^\[([a-z_]+)\b.*\] Result:\s*$", re.S)
NOTICE_RX = re.compile(r"^(?:Skipping tool|Tool) \[([a-z_]+)")
TASK_RX = re.compile(r"^\s*<task>\s*(.*?)\s*</task>\s*$", re.S)


def xml_blocks(text: str, include_thinking: bool) -> Iterator[tuple[str, str, str]]:
    """(turn_type, text, tool_name) for Roo assistant text with XML tool tags."""
    pos = 0
    for m in BLOCK_RX.finditer(text):
        before = text[pos:m.start()].strip()
        if before:
            yield "assistant", before, ""
        pos = m.end()
        tag, body = m.group(1), m.group(2)
        if tag == "thinking":
            if include_thinking and body.strip():
                yield "thinking", body.strip(), ""
            continue
        params = [v.strip() for _, v in PARAM_RX.findall(body) if v.strip()]
        yield "tool_use", " | ".join(params) if params else body.strip(), tag
    rest = text[pos:].strip()
    if rest:
        yield "assistant", rest, ""


class PearAiParser(LegacyTaskParser):
    agent = "pearai"
    name = "pearai"
    ROOT = ROOT
    PROJECT_KEY = "workspace"

    def __init__(self) -> None:
        super().__init__()
        self._continue = ContinueParser()     # for its cached sessions.json reader
        self._state: dict[tuple, object] = {}

    def wants(self, artifact: Artifact) -> bool:
        m = SESSION_RX.match(artifact.rel)
        if m:
            return m.group(1) + ".json" != INDEX_NAME
        return bool(self.task_match(artifact))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if SESSION_RX.match(artifact.rel):
            yield from self._parse_session(artifact, opts)
        elif self.task_match(artifact):
            yield from self.parse_task_file(artifact, opts)

    # ---- agent tasks (Roo fork) ------------------------------------------------

    def history_item(self, task_dir: Path, root: Path, task_id: str) -> dict | None:
        db = root.parent / "state.vscdb"
        try:
            st = db.lstat()
        except OSError:
            return None
        key = (str(db), st.st_mtime_ns, st.st_size)
        if key not in self._state:
            self._state[key] = read_item(db, EXTENSION_ID)[0]
        state = self._state[key]
        items = state.get("taskHistory") if isinstance(state, dict) else None
        for e in items if isinstance(items, list) else []:
            if isinstance(e, dict) and str(e.get("id")) == task_id:
                return e
        return None

    def api_content_rows(self, msg: dict, n: int, base_turn: str,
                         include_thinking: bool) -> Iterator[tuple[str, str, str, str]]:
        content = msg.get("content")
        if base_turn == "assistant":
            k = 0
            for turn, text, name, tid in content_rows(content, base_turn, include_thinking):
                if turn != "assistant":
                    yield turn, text, name, tid
                    continue
                for t, body, tool in xml_blocks(text, include_thinking):
                    if t == "tool_use":
                        k += 1
                        tid = str(n) if k == 1 else "%d.%d" % (n, k)
                    yield t, body, tool, tid if t == "tool_use" else ""
            return
        if base_turn != "user" or not isinstance(content, list):
            yield from content_rows(content, base_turn, include_thinking)
            return
        result: list[str] | None = None
        name = ""

        def flush():
            if result is not None:
                return "tool_result", "\n".join(x for x in result if x), name, str(n - 1)
            return None

        for b in content:
            text = b.get("text") if isinstance(b, dict) and b.get("type") == "text" else None
            if isinstance(text, str):
                m = RESULT_RX.match(text.strip())
                notice = NOTICE_RX.match(text.strip())
                if m or notice:
                    r = flush()
                    if r:
                        yield r
                    name = (m or notice).group(1)
                    result = [] if m else [text.strip()]
                    continue
                if text.lstrip().startswith("<environment_details>"):
                    r = flush()
                    if r:
                        yield r
                    result = None
                    yield "system", text.strip(), "", ""
                    continue
                if result is not None:
                    result.append(text)
                    continue
                t = TASK_RX.match(text)
                if t:
                    text = t.group(1)
                if text.strip():
                    yield "user", text, "", ""
                continue
            rows = list(content_rows([b], base_turn, include_thinking))
            if result is not None:
                result.extend(r[1] for r in rows)
            else:
                yield from rows
        r = flush()
        if r:
            yield r

    # ---- chat sessions (Continue fork) -----------------------------------------

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        raw = read_text(artifact.disk_path)
        if raw is None:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.text = "parser: unreadable session file"
            yield row
            return
        sess, problem = load_session(raw)
        session_id = str(sess.get("sessionId") or SESSION_RX.match(artifact.rel).group(1))
        entry = self._continue._index(artifact.disk_path.parent).get(session_id, {})
        ts = to_utc(entry.get("dateCreated"))
        project = str(sess.get("workspaceDirectory") or entry.get("workspaceDirectory") or "")
        history = sess.get("history") if isinstance(sess.get("history"), list) else []
        search = sess.get("perplexityHistory") if isinstance(sess.get("perplexityHistory"), list) else []

        def base(n: int, turn: str, text, model: str = "") -> Row:
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = ts
            row.session_id = session_id
            row.project_path = project
            row.turn_type = turn
            row.model = model
            row.text = compact(text, opts.max_text_length)
            return row

        bits = ["session start: %s" % (sess.get("title") or entry.get("title") or "")]
        if entry.get("integrationType"):
            bits.append("integration=%s" % entry["integrationType"])
        bits.append("history=%d perplexityHistory=%d" % (len(history), len(search)))
        if not ts:
            bits.append("dateCreated unknown")
        yield base(0, "system", " | ".join(bits))

        for i, item in enumerate(history + search, 1):
            if not isinstance(item, dict) or not isinstance(item.get("message"), dict):
                continue
            msg = item["message"]
            role = msg.get("role")
            text = message_text(msg.get("content"))
            model = ""
            for pl in item.get("promptLogs") or []:
                co = pl.get("completionOptions") if isinstance(pl, dict) else None
                if isinstance(co, dict) and co.get("model"):
                    model = str(co["model"])
            if role == "user":
                ctx = [str(c.get("description") or c.get("name") or "") for c in item.get("contextItems") or []
                       if isinstance(c, dict)]
                ctx = [c for c in ctx if c]
                if ctx:
                    text = "%s\n[context: %s]" % (text, ", ".join(ctx))
                if text:
                    yield base(i, "user", text)
            elif role == "assistant":
                cites = [str(c.get("url") or c.get("title") or "") for c in item.get("citations") or []
                         if isinstance(c, dict)]
                cites = [c for c in cites if c]
                if cites:
                    text = "%s\n[citations: %s]" % (text, ", ".join(cites))
                if text:
                    yield base(i, "assistant", text, model)
            elif text:
                yield base(i, "system", text if role == "system" else "%s: %s" % (role or "unknown", text), model)

        if problem:
            yield base(0, "system", "parser: " + problem)


__all__ = ["PearAiParser", "xml_blocks"]
