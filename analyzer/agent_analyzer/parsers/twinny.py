"""Twinny chat conversations.

Validated against source, twinnydotdev/twinny at 9339bd10 (see
`analyzer/research/twinny.md`), with a synthetic fixture; no real install
was checked. Twinny keeps no transcript file of its own: every conversation
is inside the `ItemTable` row `key = 'rjmacarthy.twinny'` of the editor's
`<User dir>/globalStorage/state.vscdb`, whose JSON value is the extension's
whole global state. The catalog attributes that file to `vscode`, so this
parser lists `vscode` in `reads_agents`; a state.vscdb the catalog gives to
a fork with its own catalog name (Cursor, Windsurf, PearAI) is not offered.

Keys read from the value: `twinny.conversations` (an object keyed by
conversation id) and `twinny.active-conversation` (a copy of the open
conversation, used only when its id is missing from the first). Conversation
fields: `id`, `title`, `updatedAt` (epoch ms, absent in older builds),
`messages[]`. Message fields: `role` (`user` or `assistant`), `content` (a
string, reasoning inline as `<think>...</think>` or
`<thinking>...</thinking>`), `images`, `meta.model`, `meta.withheld`
(counts of credentials Twinny's secret shield masked) and `toolSteps[]`
(`id`, `name`, `summary`, `args`, `command`, `output`, `status`).

The same value holds `twinny.inference-providers` and the
`twinny.active-*-provider` objects, each with an `apiKey`: those keys are
never read, and nothing from the value is emitted except the conversation
fields above. `secret://` rows are never read (see `vscode_state.py`).

Messages carry no timestamp, so every row of a conversation inherits its
`updatedAt`, the time of the last save rather than of each turn; order
within a conversation is the order of `messages[]`. Each `toolSteps[]`
entry becomes a `tool_use` (`command`, else `args` as JSON, else
`summary`) and a `tool_result` (`output`, prefixed with the status when it
is not `done`) sharing the step `id`. `<think>` blocks become `thinking`
rows, opt-in, and are removed from the assistant text. There is no
project path, git branch or line number: `source_line` is 0.
"""
from __future__ import annotations

import re
from typing import Iterator, List

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from ..vscode_state import STATE_DB_RX, read_item
from .base import Options, Parser, compact_json, text_of

ITEM_KEY = "rjmacarthy.twinny"
CONVERSATIONS = "twinny.conversations"
ACTIVE = "twinny.active-conversation"
THINK_RX = re.compile(r"<(think|thinking)>(.*?)(?:</\1>|$)", re.S)


def split_think(content: str):
    """(text without reasoning blocks, [reasoning texts])."""
    thoughts: List[str] = []

    def keep(m):
        if m.group(2).strip():
            thoughts.append(m.group(2).strip())
        return ""
    return THINK_RX.sub(keep, content).strip(), thoughts


class TwinnyParser(Parser):
    agent = "twinny"
    name = "twinny"
    reads_agents = ("vscode",)

    def wants(self, artifact: Artifact) -> bool:
        return bool(STATE_DB_RX.search(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        state, problems = read_item(artifact.disk_path, ITEM_KEY)
        if isinstance(state, dict):
            convs = state.get(CONVERSATIONS)
            convs = list(convs.values()) if isinstance(convs, dict) else convs if isinstance(convs, list) else []
            convs = [c for c in convs if isinstance(c, dict)]
            active = state.get(ACTIVE)
            ids = {str(c.get("id")) for c in convs}
            if isinstance(active, dict) and active.get("messages") and str(active.get("id")) not in ids:
                convs.append(active)
            for conv in convs:
                yield from self._conversation(artifact, conv, opts)
        elif state is not None:
            problems = problems or ["%s value is not a JSON object" % ITEM_KEY]
        for p in problems:
            row = self.base_row(artifact)
            row.turn_type = "system"
            # never echo the value itself: it holds provider apiKeys
            row.text = "parser: " + p.split(" (", 1)[0]
            yield row

    def _conversation(self, artifact: Artifact, conv: dict, opts: Options) -> Iterator[Row]:
        ts = to_utc(conv.get("updatedAt"))
        sid = str(conv.get("id") or "")
        messages = conv.get("messages")
        messages = [m for m in messages if isinstance(m, dict)] if isinstance(messages, list) else []

        def row(turn: str, text, model: str = "", name: str = "", tid: str = "") -> Row:
            r = self.base_row(artifact)
            r.timestamp_utc = ts
            r.session_id = sid
            r.turn_type = turn
            r.model = model
            r.tool_name = name
            r.tool_use_id = tid
            r.text = compact(text, opts.max_text_length)
            return r

        yield row("system", "conversation: %s | messages=%d%s" % (
            conv.get("title") or "", len(messages), "" if ts else " | updatedAt unknown"))
        for msg in messages:
            role = msg.get("role")
            meta = msg.get("meta") if isinstance(msg.get("meta"), dict) else {}
            model = str(meta.get("model") or "")
            content = msg.get("content")
            text = content if isinstance(content, str) else text_of(content)
            text, thoughts = split_think(text)
            if opts.include_thinking:
                for t in thoughts:
                    yield row("thinking", t, model)
            images = msg.get("images")
            if isinstance(images, list) and images:
                text = ("%s\n[%d image(s)]" % (text, len(images))).strip()
            if text:
                turn = "user" if role == "user" else "assistant" if role == "assistant" else "system"
                yield row(turn, text if turn != "system" else "%s: %s" % (role or "unknown", text),
                          model if turn != "user" else "")
            for step in msg.get("toolSteps") or []:
                if not isinstance(step, dict):
                    continue
                name, tid = str(step.get("name") or ""), str(step.get("id") or "")
                args = step.get("args")
                body = step.get("command") or (compact_json(args) if args else "") or step.get("summary") or ""
                yield row("tool_use", body, model, name, tid)
                out = step.get("output")
                out = out if isinstance(out, str) else compact_json(out) if out is not None else ""
                status = str(step.get("status") or "")
                if status and status != "done":
                    out = "[%s] %s" % (status, out)
                yield row("tool_result", out, model, name, tid)
            withheld = meta.get("withheld")
            if withheld:
                yield row("system", "secret shield withheld: %s" % compact_json(withheld), model)


__all__ = ["TwinnyParser", "split_think"]
