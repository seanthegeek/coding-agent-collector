"""Agent Zero chats.

Agent Zero (agent0ai/agent-zero, checked at e3051fb) saves each chat or task
context as one JSON file under the install directory's `usr/chats`. See
`analyzer/research/agent-zero.md`.

Files, relative to the home directory, where `<a0>` is `agent-zero`,
`agent-zero/<instance>` (installer and launcher layouts) or the same under
`Desktop/`:

* `<a0>/usr/chats/<ctxid>/chat.json`, rewritten whole and atomically on each
  save. Top-level keys: `id`, `name`, `created_at` (ISO 8601 with offset),
  `type` (`user` or `task`), `agent_profile`, `data.project`, `agents`,
  `log`.
  - `log.logs`: the last 1000 UI log items, each `no`, `id`, `type`,
    `heading`, `content` (cut at 15,000 characters, 250,000 for
    `response`), `kvps`, `timestamp` (epoch seconds), `agentno`. `user`
    items carry `kvps.attachments`; `agent` items carry the parsed response
    in `kvps` (`headline`, `thoughts`, `tool_name`, `tool_args`, and
    `reasoning`); `tool` items carry the tool arguments plus
    `kvps._tool_name`, with the result written into `content`.
  - `agents[].history`: a JSON string of `{bulks, topics, current}` holding
    `Message` records `{id, ai, content, metadata}` with full text and no
    timestamp. User messages are `{user_message, attachments?}`, tool
    results `{tool_name, tool_result, file?}`, assistant messages the raw
    model output (usually a `{headline, thoughts, tool_name, tool_args}`
    JSON string) with `metadata.responses.provider_model_key`. Compressed
    topics and bulks keep only a `summary`.
* `<a0>/usr/chats/<ctxid>/messages/<n>.txt`: the full text of a tool result
  of 500 characters or more, named by the history record's `file` key (an
  absolute path inside the container, matched here by file name). Read when
  `chat.json` is parsed, never on its own.
* `<a0>/usr/chats/<ctxid>.json` (v0.8.0) and `<a0>/tmp/chats/...`: older
  locations of the same document, which Agent Zero moves without
  conversion.

Log item ids equal history message ids for user messages, tool results
(`helpers/tool.py:56-61`) and assistant responses (`agent.py:529-534`, the
`agent` log item that streamed the generation). The research document's
fixture gives the `agent` item and the assistant message different ids;
the source shows they are the same.

Rows come from the log, which has the timestamps: `user` → `user` (full text
from the matching history message); `agent` → `assistant` with the headline
and thoughts (else the history or log text), the model from the matching
history message, and `kvps.reasoning` as `thinking` with
`--include-thinking`; `response` → `assistant`; `tool`, `mcp`, `code_exe`,
`browser` and `subagent` → `tool_use` (the `code`, `command`, `url`, `query`
or `path` argument, else the arguments; `tool_use_id` is the log item id)
then `tool_result` (the `messages/<n>.txt` file, else the history result,
else the possibly truncated log content); anything else → `system`. When the
log holds 1000 items it has been trimmed, so a `system` row says so and the
history messages and summaries that have no log item are emitted first,
without a timestamp. Rows of subordinate agents are prefixed `[agent N]`.
`project_path` is `/a0/usr/projects/<data.project>`, the path inside the
container, and is empty for chats outside a project. No git branch is
recorded. `source_line` is the log item's `no`. A `chat.json` that does not
parse yields one `system` row plus whatever complete log items can be
recovered from it, without the history.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, text_of

A0 = r"(?:Desktop/)?agent-zero/(?:[^/]+/)?(?:usr|tmp)/chats"
CHAT_RX = re.compile(r"^%s/[^/]+/chat\.json$" % A0)
LEGACY_RX = re.compile(r"^%s/[^/]+\.json$" % A0)

LOG_SIZE = 1000
TOOL_TYPES = ("tool", "mcp", "code_exe", "browser", "subagent")
ARG_KEYS = ("code", "command", "url", "query", "path")
ICON_RX = re.compile(r"icon://\S+\s*")
LOGS_RX = re.compile(r'"logs"\s*:\s*\[')


def walk_history(node, summaries: bool) -> Iterator[tuple[str, dict]]:
    """Yield ("message", Message) and, with `summaries`, ("summary", text) in
    chronological order: bulks, then topics, then the current topic."""
    if isinstance(node, list):
        for n in node:
            yield from walk_history(n, summaries)
        return
    if not isinstance(node, dict):
        return
    cls = node.get("_cls")
    if cls == "Message":
        yield "message", node
    elif cls == "History":
        for key in ("bulks", "topics", "current"):
            yield from walk_history(node.get(key), summaries)
    elif cls in ("Topic", "Bulk") or "messages" in node or "records" in node:
        if summaries and node.get("summary"):
            yield "summary", {"summary": node["summary"], "_cls": cls}
        yield from walk_history(node.get("messages") or node.get("records") or [], summaries)


def parse_ai(content) -> dict | None:
    """The assistant's raw output parsed as the agent's JSON response."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        s = content.strip()
        if s.startswith("{"):
            try:
                value = json.loads(s)
            except ValueError:
                return None
            return value if isinstance(value, dict) else None
    return None


def headline_text(d: dict) -> str:
    parts = []
    if d.get("headline"):
        parts.append(str(d["headline"]))
    thoughts = d.get("thoughts")
    if isinstance(thoughts, list):
        parts.extend(str(t) for t in thoughts if t)
    elif thoughts:
        parts.append(str(thoughts))
    return "\n".join(parts)


def args_summary(args) -> str:
    if isinstance(args, dict):
        visible = {k: v for k, v in args.items() if not str(k).startswith("_")}
        for k in ARG_KEYS:
            if visible.get(k) not in (None, ""):
                return str(visible[k])
        return compact_json(visible)
    return args if isinstance(args, str) else compact_json(args)


def model_of(message: dict | None) -> str:
    if not message:
        return ""
    meta = message.get("metadata")
    resp = meta.get("responses") if isinstance(meta, dict) else None
    return str(resp.get("provider_model_key") or "") if isinstance(resp, dict) else ""


def _content_text(value) -> str:
    if isinstance(value, (dict, list)) and not (isinstance(value, dict) and "text" in value):
        return text_of(value) if isinstance(value, list) else compact_json(value)
    return text_of(value)


def recover_logs(raw: str) -> list[dict]:
    """Complete log items before the point where a damaged file breaks off."""
    m = LOGS_RX.search(raw)
    if not m:
        return []
    dec = json.JSONDecoder()
    pos, out = m.end(), []
    while True:
        while pos < len(raw) and raw[pos] in " \t\r\n,":
            pos += 1
        try:
            item, pos = dec.raw_decode(raw, pos)
        except ValueError:
            return out
        if not isinstance(item, dict):
            return out
        out.append(item)


class AgentZeroParser(Parser):
    agent = "agent-zero"
    name = "agent-zero"

    def wants(self, artifact: Artifact) -> bool:
        return bool(CHAT_RX.match(artifact.rel) or LEGACY_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        path = artifact.disk_path
        legacy = not CHAT_RX.match(artifact.rel)
        fallback_id = path.stem if legacy else path.parent.name
        base = self.base_row(artifact)
        base.session_id = fallback_id
        raw = path.read_bytes().decode("utf-8", errors="replace")
        try:
            chat = json.loads(raw)
            if not isinstance(chat, dict):
                raise ValueError("top level is not an object")
        except ValueError as e:
            yield self._row(base, "system", "parser: chat.json did not parse (%s); log items recovered without history" % e,
                            opts)
            yield from self._log_rows(base, recover_logs(raw), {}, None, opts)
            return

        base.session_id = str(chat.get("id") or fallback_id)
        data = chat.get("data") if isinstance(chat.get("data"), dict) else {}
        if data.get("project"):
            base.project_path = "/a0/usr/projects/%s" % data["project"]
        start = self._row(base, "system", " | ".join(x for x in (
            "chat start", str(chat.get("name") or ""),
            "type=%s" % chat["type"] if chat.get("type") else "",
            "profile=%s" % chat["agent_profile"] if chat.get("agent_profile") else "",
            "project=%s" % data["project"] if data.get("project") else "",
        ) if x), opts)
        start.timestamp_utc = to_utc(chat.get("created_at"))
        yield start

        log = chat.get("log") if isinstance(chat.get("log"), dict) else {}
        logs = [i for i in (log.get("logs") or []) if isinstance(i, dict)]
        trimmed = len(logs) >= LOG_SIZE

        history: dict[str, tuple[int, dict]] = {}
        ordered: list[tuple[int, str, dict]] = []
        for i, ag in enumerate(chat.get("agents") or []):
            if not isinstance(ag, dict):
                continue
            agentno = ag.get("number", i)
            hist = ag.get("history")
            if isinstance(hist, str):
                try:
                    hist = json.loads(hist) if hist else {}
                except ValueError as e:
                    yield self._row(base, "system", "parser: history of agent %s did not parse (%s)" % (agentno, e), opts)
                    continue
            for kind, node in walk_history(hist, trimmed):
                ordered.append((agentno, kind, node))
                if kind == "message" and node.get("id"):
                    history.setdefault(str(node["id"]), (agentno, node))

        if trimmed:
            yield self._row(base, "system", "log trimmed to its last %d items; earlier turns follow from the agent "
                                            "history without timestamps" % LOG_SIZE, opts)
            log_ids = {str(i.get("id")) for i in logs if i.get("id")}
            for agentno, kind, node in ordered:
                if kind == "summary":
                    yield self._row(base, "system", self._prefix(agentno, "[summary] " + _content_text(node["summary"])), opts)
                elif str(node.get("id") or "") not in log_ids:
                    yield from self._history_rows(base, agentno, node, opts)

        yield from self._log_rows(base, logs, history, path.parent / "messages" if not legacy else None, opts)

    # -- helpers -----------------------------------------------------------------------
    @staticmethod
    def _prefix(agentno, text: str) -> str:
        return "[agent %s] %s" % (agentno, text) if agentno not in (0, None, "0") else text

    def _row(self, base: Row, turn_type: str, text: str, opts: Options, line: int = 0, ts: str = "") -> Row:
        row = Row(**base.__dict__)
        row.turn_type = turn_type
        row.text = compact(text, opts.max_text_length)
        row.source_line = line
        row.timestamp_utc = ts
        return row

    @staticmethod
    def _message_file(msg_dir, content) -> str:
        if msg_dir is None or not isinstance(content, dict) or not content.get("file"):
            return ""
        name = str(content["file"]).replace("\\", "/").rsplit("/", 1)[-1]
        f = msg_dir / name
        if not name or f.is_symlink() or not f.is_file():
            return ""
        return f.read_bytes().decode("utf-8", errors="replace")

    def _history_rows(self, base: Row, agentno, msg: dict, opts: Options) -> Iterator[Row]:
        content = msg.get("content")
        mid = str(msg.get("id") or "")
        if msg.get("ai"):
            parsed = parse_ai(content)
            model = model_of(msg)
            text = headline_text(parsed) if parsed else _content_text(content)
            if text:
                row = self._row(base, "assistant", self._prefix(agentno, text), opts)
                row.model = model
                yield row
            if parsed and parsed.get("tool_name"):
                row = self._row(base, "tool_use", self._prefix(agentno, args_summary(parsed.get("tool_args"))), opts)
                row.tool_name, row.model = str(parsed["tool_name"]), model
                yield row
        elif isinstance(content, dict) and "tool_result" in content:
            row = self._row(base, "tool_result", self._prefix(agentno, _content_text(content.get("tool_result"))), opts)
            row.tool_name, row.tool_use_id = str(content.get("tool_name") or ""), mid
            yield row
        elif isinstance(content, dict) and "user_message" in content:
            yield self._row(base, "user", self._prefix(agentno, _content_text(content.get("user_message"))), opts)
        else:
            yield self._row(base, "system", self._prefix(agentno, _content_text(content)), opts)

    def _log_rows(self, base: Row, logs: list[dict], history: dict[str, tuple[int, dict]], msg_dir,
                  opts: Options) -> Iterator[Row]:
        for item in logs:
            kind = str(item.get("type") or "")
            line = item.get("no") if isinstance(item.get("no"), int) else 0
            ts = to_utc(item.get("timestamp"))
            agentno = item.get("agentno", 0)
            kvps = item.get("kvps") if isinstance(item.get("kvps"), dict) else {}
            content = item.get("content") or ""
            item_id = str(item.get("id") or "")
            hist = history.get(item_id, (None, None))[1] if item_id else None
            hcontent = hist.get("content") if hist else None

            def mk(turn_type: str, text: str) -> Row:
                return self._row(base, turn_type, self._prefix(agentno, text), opts, line, ts)

            if kind == "user":
                text = _content_text(hcontent.get("user_message")) if isinstance(hcontent, dict) \
                    and "user_message" in hcontent else _content_text(content)
                att = kvps.get("attachments")
                if isinstance(att, list) and att:
                    text += " [attachments: %s]" % ", ".join(str(a) for a in att)
                yield mk("user", text)
            elif kind == "agent":
                model = model_of(hist)
                if opts.include_thinking and kvps.get("reasoning"):
                    row = mk("thinking", _content_text(kvps["reasoning"]))
                    row.model = model
                    yield row
                parsed = parse_ai(hcontent) if hist else None
                text = headline_text(kvps) or (headline_text(parsed) if parsed else "") \
                    or (_content_text(hcontent) if hist and not parsed else "") or _content_text(content)
                if text:
                    row = mk("assistant", text)
                    row.model = model
                    yield row
            elif kind == "response":
                yield mk("assistant", _content_text(content))
            elif kind in TOOL_TYPES:
                tool_name = str(kvps.get("_tool_name") or (hcontent.get("tool_name") if isinstance(hcontent, dict) else "")
                                or kind)
                tool_id = item_id or "log:%s" % line
                row = mk("tool_use", args_summary(kvps))
                row.tool_name, row.tool_use_id = tool_name, tool_id
                yield row
                result = self._message_file(msg_dir, hcontent)
                if not result and isinstance(hcontent, dict) and "tool_result" in hcontent:
                    result = _content_text(hcontent["tool_result"])
                if not result:
                    result = _content_text(content)
                if result or hist:
                    row = mk("tool_result", result)
                    row.tool_name, row.tool_use_id = tool_name, tool_id
                    yield row
            else:
                heading = ICON_RX.sub("", str(item.get("heading") or "")).strip()
                text = " | ".join(x for x in (heading, _content_text(content)) if x)
                yield mk("system", "%s: %s" % (kind or "log", text) if text else kind or "log")
