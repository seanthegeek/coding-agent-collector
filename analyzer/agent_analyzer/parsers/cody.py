"""Sourcegraph Cody chat history.

Validated against source, sourcegraph/cody-public-snapshot at 8e20ac6c (see
`analyzer/research/cody.md`), with a synthetic fixture; no real install was
checked. Every chat of every account lives in one JSON object,
`AccountKeyedChatHistory`, stored in two places:

* VS Code and its forks: the `ItemTable` row `key = 'sourcegraph.cody-ai'`
  of `<editor User dir>/globalStorage/state.vscdb`, whose JSON value is the
  extension's whole global state; the history is its
  `cody-local-chatHistory-v2` member. The catalog attributes that file to
  `vscode`, or to the fork (Cursor, Windsurf, PearAI, Kiro, Antigravity)
  whose `User/` directory it sits in, so this parser lists all of them,
  `vscode_state.EDITOR_AGENTS`, in `reads_agents`.
* The JetBrains plugin (Cody agent): the file
  `Cody-nodejs/[Data/]JetBrains-globalState/cody-local-chatHistory-v2`,
  whose whole content is the JSON history.

Shape: `{"<endpoint>-<username>": {"chat": {"<chatID>": transcript}}}`.
Transcript fields: `id`, `chatTitle`, `lastInteractionTimestamp`,
`interactions[]` of `{humanMessage, assistantMessage}`. Message fields:
`speaker` (`human`, `assistant`, `system`), `text`, `model`, `intent`,
`contextFiles[].uri.fsPath` (or `.path`), `error.message`, `content[]`
parts (`{type: "tool_call", tool_call: {id, name, arguments}}` on the
assistant, `{type: "tool_result", tool_result: {id, content}}` on the
human), and `processes[]` (`{type: "tool", id, title, content, state}`).

There is no per-message timestamp. The chat id is the chat's creation time
as `Date.toUTCString()` (`Fri, 03 Oct 2026 10:00:00 GMT`), and every row of
the chat inherits it; a non-date id (pre-migration UUIDs) falls back to
`lastInteractionTimestamp`, which is the same creation time. `session_id`
is the chat id, prefixed with `<account>/` only when the same id occurs
under two accounts of one store. No project path is recorded with a chat;
`project_path` stays empty and the user row lists the context files, since
the parent of one context file is not the project. `processes[]` tool
steps are emitted only when no `tool_call` part has the same id, so an
agentic call is not counted twice. `source_line` is 1 for the JetBrains
file (one JSON value) and 0 for the SQLite row. A history that does not
parse is walked chat by chat, and every interaction decoded before the
damage is still yielded, followed by one `system` row. No git branch.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from email.utils import parsedate_to_datetime

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from ..vscode_state import EDITOR_AGENTS, STATE_DB_RX, read_item
from .base import Options, Parser, compact_json, text_of
from .cline_legacy import iter_array_at, read_text

JETBRAINS_RX = re.compile(
    r"(?:^|/)Cody-nodejs/(?:[^/]+/)?JetBrains-globalState/cody-local-chatHistory-v2$"
)
ITEM_KEY = "sourcegraph.cody-ai"
HISTORY_KEY = "cody-local-chatHistory-v2"

_DATE_KEY = (
    r'"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT)"\s*:\s*\{'
)
_ACCOUNT_KEY = r'"([^"\\]+)"\s*:\s*\{\s*"chat"\s*:\s*\{'


def chat_time(chat_id: str, fallback) -> str:
    """UTC timestamp of a `toUTCString()` chat id, else of `fallback`."""
    for v in (chat_id, fallback):
        if isinstance(v, str) and v:
            try:
                return to_utc(parsedate_to_datetime(v).isoformat())
            except (TypeError, ValueError, IndexError):
                pass
            ts = to_utc(v)
            if ts:
                return ts
    return ""


def recover_history(text: str) -> tuple[dict, str]:
    """Rebuild what can be read from a damaged history text: each chat whose
    key is a `toUTCString()` date, with the interactions that decode."""
    out: dict[str, dict] = {}
    marks = [(m.start(), "account", m.group(1)) for m in re.finditer(_ACCOUNT_KEY, text)]
    marks += [(m.end(), "chat", m.group(1)) for m in re.finditer(_DATE_KEY, text)]
    marks.sort()
    account = ""
    chats = 0
    for i, (pos, kind, name) in enumerate(marks):
        if kind == "account":
            account = name
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        m = re.compile(r'"interactions"\s*:\s*').search(text, pos, end)
        interactions = []
        if m:
            errs: list = []
            interactions = [v for _, v in iter_array_at(text, m.end(), errs) if isinstance(v, dict)]
        title = re.compile(r'"chatTitle"\s*:\s*("(?:[^"\\]|\\.)*")').search(text, pos, end)
        chat = {"id": name, "interactions": interactions}
        if title:
            try:
                chat["chatTitle"] = json.loads(title.group(1))
            except ValueError:
                pass
        out.setdefault(account, {"chat": {}})["chat"][name] = chat
        chats += 1
    return out, "chat history did not parse; recovered %d chat(s)" % chats


def _fs_path(uri) -> str:
    if isinstance(uri, str):
        return uri
    if isinstance(uri, dict):
        for k in ("fsPath", "path", "external"):
            if isinstance(uri.get(k), str) and uri[k]:
                return uri[k]
    return ""


class CodyParser(Parser):
    agent = "cody"
    name = "cody"
    reads_agents = EDITOR_AGENTS

    def wants(self, artifact: Artifact) -> bool:
        return bool(STATE_DB_RX.search(artifact.rel) or JETBRAINS_RX.search(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        problems: list[str] = []
        if JETBRAINS_RX.search(artifact.rel):
            line = 1
            text = read_text(artifact.disk_path)
            if text is None:
                yield self._system(artifact, "parser: unreadable history file", line)
                return
            history = self._decode(text, problems)
        else:
            line = 0
            state, problems = read_item(artifact.disk_path, ITEM_KEY)
            if state is None:
                for p in problems:
                    yield self._system(artifact, "parser: " + p, line)
                return
            if isinstance(state, str):  # value did not parse; read_item noted it
                history = recover_history(state)[0]
            else:
                history = state.get(HISTORY_KEY) if isinstance(state, dict) else None
                if isinstance(history, str):
                    history = self._decode(history, problems)
        if isinstance(history, dict):
            yield from self._history_rows(artifact, history, line, opts)
        for p in problems:
            yield self._system(artifact, "parser: " + p, line)

    @staticmethod
    def _decode(text: str, problems: list[str]):
        try:
            return json.loads(text)
        except ValueError as e:
            history, problem = recover_history(text)
            problems.append("%s (%s)" % (problem, e))
            return history

    def _system(self, artifact: Artifact, text: str, line: int) -> Row:
        row = self.base_row(artifact)
        row.turn_type = "system"
        row.source_line = line
        row.text = text
        return row

    def _history_rows(
        self, artifact: Artifact, history: dict, line: int, opts: Options
    ) -> Iterator[Row]:
        seen: dict[str, int] = {}
        for acct in history.values():
            chats = acct.get("chat") if isinstance(acct, dict) else None
            for cid in chats if isinstance(chats, dict) else {}:
                seen[cid] = seen.get(cid, 0) + 1
        for account, acct in history.items():
            chats = acct.get("chat") if isinstance(acct, dict) else None
            if not isinstance(chats, dict):
                continue
            for cid, chat in chats.items():
                if not isinstance(chat, dict):
                    continue
                sid = str(chat.get("id") or cid)
                if seen.get(cid, 0) > 1:
                    sid = "%s/%s" % (account, sid)
                yield from self._chat_rows(artifact, account, sid, chat, line, opts)

    def _chat_rows(
        self, artifact: Artifact, account: str, sid: str, chat: dict, line: int, opts: Options
    ) -> Iterator[Row]:
        ts = chat_time(str(chat.get("id") or ""), chat.get("lastInteractionTimestamp"))
        interactions = chat.get("interactions")
        interactions = (
            [i for i in interactions if isinstance(i, dict)]
            if isinstance(interactions, list)
            else []
        )

        def row(turn: str, text, model: str = "", name: str = "", tid: str = "") -> Row:
            r = self.base_row(artifact)
            r.timestamp_utc = ts
            r.session_id = sid
            r.source_line = line
            r.turn_type = turn
            r.model = model
            r.tool_name = name
            r.tool_use_id = tid
            r.text = compact(text, opts.max_text_length)
            return r

        yield row(
            "system",
            "chat: %s | account=%s | interactions=%d"
            % (chat.get("chatTitle") or "", account, len(interactions)),
        )
        names: dict[str, str] = {}
        for it in interactions:
            for key in ("humanMessage", "assistantMessage"):
                msg = it.get(key)
                if isinstance(msg, dict):
                    yield from self._message_rows(msg, row, names)

    def _message_rows(self, msg: dict, row, names: dict[str, str]) -> Iterator[Row]:
        speaker = msg.get("speaker")
        model = str(msg.get("model") or "") if speaker == "assistant" else ""
        text = msg.get("text")
        text = text if isinstance(text, str) else text_of(text)
        parts = msg.get("content") if isinstance(msg.get("content"), list) else []
        if not text:
            text = "\n".join(
                str(p.get("text"))
                for p in parts
                if isinstance(p, dict) and p.get("type") == "text" and p.get("text")
            )
        if speaker == "human":
            files = [
                _fs_path(f.get("uri")) for f in msg.get("contextFiles") or [] if isinstance(f, dict)
            ]
            files = [f for f in files if f]
            if files:
                text = "%s\n[context: %s]" % (text, ", ".join(files))
            if text:
                yield row("user", text)
        elif text:
            yield row("assistant" if speaker == "assistant" else "system", text, model)
        call_ids = set()
        for p in parts:
            if not isinstance(p, dict):
                continue
            if p.get("type") == "tool_call" and isinstance(p.get("tool_call"), dict):
                tc = p["tool_call"]
                tid, name = str(tc.get("id") or ""), str(tc.get("name") or "")
                call_ids.add(tid)
                names[tid] = name
                args = tc.get("arguments")
                yield row(
                    "tool_use",
                    args if isinstance(args, str) else compact_json(args),
                    model,
                    name,
                    tid,
                )
            elif p.get("type") == "tool_result" and isinstance(p.get("tool_result"), dict):
                tr = p["tool_result"]
                tid = str(tr.get("id") or "")
                c = tr.get("content")
                yield row(
                    "tool_result",
                    c
                    if isinstance(c, str)
                    else text_of(c)
                    if isinstance(c, list)
                    else compact_json(c),
                    model,
                    names.get(tid, ""),
                    tid,
                )
        for proc in msg.get("processes") or []:
            if not isinstance(proc, dict) or proc.get("type") != "tool":
                continue
            tid = str(proc.get("id") or "")
            if tid and tid in call_ids:
                continue
            name = str(proc.get("title") or "")
            names[tid] = name
            body = proc.get("content")
            body = body if isinstance(body, str) else compact_json(body) if body is not None else ""
            if proc.get("state") and proc.get("state") != "success":
                body = "[%s] %s" % (proc["state"], body)
            yield row("tool_use", body, model, name, tid)
        err = msg.get("error")
        if isinstance(err, dict) and err.get("message"):
            yield row("system", "error: %s" % err["message"], model)


__all__ = ["CodyParser", "chat_time", "recover_history"]
