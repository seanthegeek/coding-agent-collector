"""Continue (IDE extensions and the `cn` CLI) sessions.

The module is not called `continue.py` because `continue` is a Python
keyword. Validated against source, continuedev/continue at 5522c6f
(`core/index.d.ts`, `core/util/history.ts`, `core/data/log.ts`,
`packages/config-yaml/src/schemas/data/`), with a synthetic fixture; see
`analyzer/research/continue.md`. Files, relative to the home directory:

* `.continue/sessions/<sessionId>.json`: one pretty-printed JSON session,
  keys `sessionId`, `title`, `workspaceDirectory`, `history[]`, `mode`,
  `chatModelTitle`, `usage` (`promptTokens`, `completionTokens`,
  `totalCost`). Each `history[]` item has `message` (`role` user, assistant,
  thinking, system or tool; `content` a string or a list of
  `{type:"text",text}` / `{type:"imageUrl",imageUrl:{url}}` parts;
  assistant `toolCalls[]` with `id` and `function.name`/`function.arguments`;
  tool `toolCallId`), `toolCallStates[]` (`toolCallId`, `toolCall`,
  `status`, `output[].content`), `promptLogs[].modelTitle` and `reasoning`
  (`text`, `startAt` in epoch milliseconds).
* `.continue/sessions/sessions.json`: the index, an array of
  `{sessionId, title, dateCreated, workspaceDirectory, messageCount}` with
  `dateCreated` a millisecond epoch as a string. It is read for the
  timestamp, never parsed into rows itself.
* `.continue/dev_data/<schema>/chatInteraction.jsonl` (and the unversioned
  legacy `dev_data/chatInteraction.jsonl`): `timestamp` ISO 8601,
  `sessionId`, `prompt`, `completion`, `modelTitle`, `modelName`.
* `.continue/dev_data/<schema>/toolUsage.jsonl`: `timestamp`,
  `toolCallId`, `functionName`, `functionParams`, `toolCallArgs`,
  `accepted`, `succeeded`, `output[].content`.

Session files carry no per-message timestamp: every row of a session
inherits the session's `dateCreated` from `sessions.json` (empty when the
index is missing or lacks the session), except thinking rows from
`reasoning.startAt`. Order within a session is the order of `history[]`,
and `source_line` is the 1-based position in `history[]` (0 for the session
row). The `dev_data` events do carry real timestamps; chatInteraction rows
are joined to the session's `workspaceDirectory` through `sessions.json`,
and toolUsage rows join the session's tool calls on `tool_use_id` but carry
no session id of their own. `logs/prompt.log` has no date or session id and
is not parsed. A truncated session file yields the turns decoded before the
cut plus one `system` row.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from ..inputs import Artifact, error_reason
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

SESSION_RX = re.compile(r"^(?:.*/)?\.continue/sessions/([^/]+)\.json$")
DEV_DATA_RX = re.compile(
    r"^(?:.*/)?\.continue/dev_data/(?:[^/]+/)?(chatInteraction|toolUsage)\.jsonl$"
)
INDEX_NAME = "sessions.json"
HEADER_KEYS = ("sessionId", "title", "workspaceDirectory", "mode", "chatModelTitle")


def message_text(content) -> str:
    """Flatten a ChatMessage content: image parts become `[image]`."""
    if isinstance(content, list):
        content = [
            {"type": "text", "text": "[image]"}
            if isinstance(p, dict) and p.get("type") == "imageUrl"
            else p
            for p in content
        ]
    return text_of(content)


def output_text(output) -> str:
    """Text of a ContextItem[] tool output."""
    if not isinstance(output, list):
        return text_of(output)
    parts = []
    for item in output:
        if isinstance(item, dict):
            c = item.get("content")
            parts.append(
                c
                if isinstance(c, str)
                else compact_json(c)
                if c is not None
                else str(item.get("name") or "")
            )
        else:
            parts.append(str(item))
    return "\n".join(p for p in parts if p)


def load_session(text: str) -> tuple[dict, str]:
    """Parse a session file. On failure, recover the header keys and every
    `history[]` item that decodes before the damage, and say what went wrong."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, ""
        return {}, "session file is not a JSON object"
    except ValueError as e:
        first_error = str(e)
    dec = json.JSONDecoder()
    start = text.find("{")
    if start >= 0:
        try:
            obj, end = dec.raw_decode(text, start)
            if isinstance(obj, dict):
                return obj, "trailing data after the session object at offset %d" % end
        except ValueError:
            pass
    out: dict = {}
    for key in HEADER_KEYS:
        m = re.search(r'"%s"\s*:\s*("(?:[^"\\]|\\.)*")' % key, text)
        if m:
            try:
                out[key] = json.loads(m.group(1))
            except ValueError:
                pass
    history: list[dict] = []
    m = re.search(r'"history"\s*:\s*\[', text)
    if m:
        pos = m.end()
        while True:
            while pos < len(text) and text[pos] in " \t\r\n,":
                pos += 1
            if pos >= len(text) or text[pos] == "]":
                break
            try:
                item, pos = dec.raw_decode(text, pos)
            except ValueError:
                break
            if isinstance(item, dict):
                history.append(item)
    out["history"] = history
    return out, "session file did not parse (%s); recovered %d history item(s)" % (
        first_error,
        len(history),
    )


class ContinueParser(Parser):
    agent = "continue"
    name = "continue"

    def __init__(self) -> None:
        self._index_cache: dict[str, dict[str, dict]] = {}

    def wants(self, artifact: Artifact) -> bool:
        m = SESSION_RX.match(artifact.rel)
        if m:
            return m.group(1) + ".json" != INDEX_NAME
        return bool(DEV_DATA_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = DEV_DATA_RX.match(artifact.rel)
        if m and m.group(1) == "chatInteraction":
            yield from self._parse_chat_interaction(artifact, opts)
        elif m:
            yield from self._parse_tool_usage(artifact, opts)
        else:
            yield from self._parse_session(artifact, opts)

    # ---- sessions.json --------------------------------------------------------

    def _index(self, sessions_dir) -> dict[str, dict]:
        """sessionId -> sessions.json entry for the index beside the session
        files; empty when it is absent or unreadable."""
        path = sessions_dir / INDEX_NAME
        key = str(path)
        if key in self._index_cache:
            return self._index_cache[key]
        out: dict[str, dict] = {}
        try:
            if path.is_file() and not path.is_symlink():
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                if isinstance(data, list):
                    for e in data:
                        # entries with session_id are a pre-1.0 format the extension filters out
                        if isinstance(e, dict) and e.get("sessionId"):
                            out[str(e["sessionId"])] = e
        except (OSError, ValueError):
            pass
        self._index_cache[key] = out
        return out

    # ---- session files --------------------------------------------------------

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        try:
            raw = artifact.disk_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.text = "parser: unreadable session file: %s" % error_reason(e)
            yield row
            return
        sess, problem = load_session(raw)
        session_id = sess.get("sessionId")
        if not session_id:
            m = SESSION_RX.match(artifact.rel)
            assert m is not None  # wants() accepted only matching paths
            session_id = m.group(1)
        session_id = str(session_id)
        entry = self._index(artifact.disk_path.parent).get(session_id, {})
        ts = to_utc(entry.get("dateCreated"))
        project = str(sess.get("workspaceDirectory") or entry.get("workspaceDirectory") or "")
        session_model = str(sess.get("chatModelTitle") or "")
        history = sess.get("history")
        if not isinstance(history, list):
            history = []

        def base(n: int, model: str = "") -> Row:
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = ts
            row.session_id = session_id
            row.project_path = project
            row.model = model
            return row

        row = base(0, session_model)
        row.turn_type = "system"
        usage = sess.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        bits = ["session start: %s" % (sess.get("title") or entry.get("title") or "")]
        if sess.get("mode"):
            bits.append("mode=%s" % sess["mode"])
        bits.append("items=%d" % len(history))
        for k in ("promptTokens", "completionTokens", "totalCost"):
            if usage.get(k) is not None:
                bits.append("%s=%s" % (k, usage[k]))
        if not ts:
            bits.append("dateCreated unknown")
        row.text = compact(" ".join(bits))
        yield row

        # Tool results normally arrive as a later `tool` message; a call that
        # never got one (canceled, errored) keeps its output in toolCallStates.
        answered = set()
        for item in history:
            msg = item.get("message") if isinstance(item, dict) else None
            if isinstance(msg, dict) and msg.get("role") == "tool" and msg.get("toolCallId"):
                answered.add(str(msg["toolCallId"]))
        names: dict[str, str] = {}

        for i, item in enumerate(history, 1):
            if not isinstance(item, dict):
                continue
            msg = item.get("message")
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            model = session_model
            logs = item.get("promptLogs")
            if isinstance(logs, list):
                for pl in logs:
                    if isinstance(pl, dict) and pl.get("modelTitle"):
                        model = str(pl["modelTitle"])
            reasoning = item.get("reasoning")
            if opts.include_thinking and isinstance(reasoning, dict) and reasoning.get("text"):
                row = base(i, model)
                row.turn_type = "thinking"
                row.timestamp_utc = to_utc(reasoning.get("startAt")) or ts
                yield self._fill(row, reasoning.get("text"), opts)
            text = message_text(msg.get("content"))
            if role == "user":
                if text:
                    row = base(i)
                    row.turn_type = "user"
                    yield self._fill(row, text, opts)
            elif role == "assistant":
                if text:
                    row = base(i, model)
                    row.turn_type = "assistant"
                    yield self._fill(row, text, opts)
                calls = msg.get("toolCalls")
                states = item.get("toolCallStates")
                states = (
                    [s for s in states if isinstance(s, dict)] if isinstance(states, list) else []
                )
                if not isinstance(calls, list) or not calls:
                    calls = [
                        s.get("toolCall") for s in states if isinstance(s.get("toolCall"), dict)
                    ]
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    fn = call.get("function")
                    if not isinstance(fn, dict):
                        fn = {}
                    call_id = str(call.get("id") or "")
                    name = str(fn.get("name") or "")
                    names[call_id] = name
                    args = fn.get("arguments")
                    row = base(i, model)
                    row.turn_type = "tool_use"
                    row.tool_name = name
                    row.tool_use_id = call_id
                    yield self._fill(
                        row,
                        args
                        if isinstance(args, str)
                        else compact_json(args)
                        if args is not None
                        else "",
                        opts,
                    )
                for st in states:
                    call_id = str(st.get("toolCallId") or "")
                    if not call_id or call_id in answered:
                        continue
                    out = output_text(st.get("output"))
                    status = str(st.get("status") or "")
                    if not out and status in ("", "done", "generated", "generating", "calling"):
                        continue
                    row = base(i, model)
                    row.turn_type = "tool_result"
                    row.tool_use_id = call_id
                    row.tool_name = names.get(call_id, "")
                    yield self._fill(
                        row, "[%s] %s" % (status, out) if status and status != "done" else out, opts
                    )
            elif role == "thinking":
                if opts.include_thinking and text:
                    row = base(i, model)
                    row.turn_type = "thinking"
                    yield self._fill(row, text, opts)
            elif role == "tool":
                call_id = str(msg.get("toolCallId") or "")
                row = base(i)
                row.turn_type = "tool_result"
                row.tool_use_id = call_id
                row.tool_name = names.get(call_id, "")
                yield self._fill(row, text, opts)
            elif text:
                row = base(i)
                row.turn_type = "system"
                yield self._fill(
                    row, "%s: %s" % (role or "unknown", text) if role != "system" else text, opts
                )

        if problem:
            row = base(0)
            row.turn_type = "system"
            row.text = "parser: " + problem
            yield row

    # ---- dev_data -------------------------------------------------------------

    def _dev_index(self, artifact: Artifact) -> dict[str, dict]:
        # .continue/dev_data/<schema>/x.jsonl or .continue/dev_data/x.jsonl
        d = artifact.disk_path.parent
        base = d.parent if d.parent.name == ".continue" else d.parent.parent
        return self._index(base / "sessions")

    def _parse_chat_interaction(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        index = self._dev_index(artifact)
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            sid = str(rec.get("sessionId") or "")
            entry = index.get(sid, {})
            for turn, key in (("user", "prompt"), ("assistant", "completion")):
                text = rec.get(key)
                if not text:
                    continue
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(rec.get("timestamp"))
                row.session_id = sid
                row.project_path = str(entry.get("workspaceDirectory") or "")
                row.turn_type = turn
                if turn == "assistant":
                    row.model = str(rec.get("modelTitle") or rec.get("modelName") or "")
                yield self._fill(row, text if isinstance(text, str) else compact_json(text), opts)
        yield from self._errors(artifact, errors)

    def _parse_tool_usage(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            ts = to_utc(rec.get("timestamp"))
            call_id = str(rec.get("toolCallId") or "")
            name = str(rec.get("functionName") or "")
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = ts
            row.turn_type = "tool_use"
            row.tool_name = name
            row.tool_use_id = call_id
            args = rec.get("toolCallArgs")
            if not args and rec.get("functionParams") is not None:
                args = compact_json(rec.get("functionParams"))
            yield self._fill(
                row,
                args if isinstance(args, str) else compact_json(args) if args is not None else "",
                opts,
            )
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = ts
            row.turn_type = "tool_result"
            row.tool_name = name
            row.tool_use_id = call_id
            yield self._fill(
                row,
                "accepted=%s succeeded=%s %s"
                % (
                    compact_json(rec.get("accepted")),
                    compact_json(rec.get("succeeded")),
                    output_text(rec.get("output")),
                ),
                opts,
            )
        yield from self._errors(artifact, errors)

    def _errors(self, artifact: Artifact, errors: list) -> Iterator[Row]:
        if errors:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.text = "parser: %d unparseable line(s), first at line %d" % (
                len(errors),
                errors[0][0],
            )
            yield row

    @staticmethod
    def _fill(row: Row, text, opts: Options) -> Row:
        row.text = compact(text)
        return row
