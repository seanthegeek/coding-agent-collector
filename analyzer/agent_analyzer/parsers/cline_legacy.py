"""The per-task layout Cline introduced and Roo Code inherited, shared by the
`cline` and `roo-code` parsers. See `analyzer/research/cline.md` (cline/cline
at 39ff2359) and `analyzer/research/roo-code.md` (RooCodeInc/Roo-Code at
b867ec91).

Files, under a storage root (the editor's `User/globalStorage/<extension id>`
directory, Cline's `~/.cline/data`, Roo's `~/.vscode-mock/global-storage`):

* `tasks/<taskId>/ui_messages.json`: JSON array of `ClineMessage`
  `{ts, type: "ask"|"say", ask, say, text, reasoning, images, partial,
  modelInfo: {modelId, providerId, mode}}`, `ts` in epoch milliseconds.
  `text` is JSON for `tool` (`ClineSayTool {tool, path, diff, content, regex,
  filePattern}`, Roo adds `query`, `mode`, `reason`, `batchFiles[].path`),
  `api_req_started` (`{request, tokensIn, tokensOut, cacheWrites,
  cacheReads, cost, cancelReason}`), `use_mcp_server` (`{serverName, type,
  toolName, arguments, uri}`), `followup` (`{question, options}`; Roo
  `{question, suggest}`), `plan_mode_respond` (`{response, options}`),
  `browser_action` (`{action, coordinate, text}`) and
  `browser_action_result` (`{logs, currentUrl, screenshot}`). Roo's
  `condense_context` carries `contextCondense.summary`. This is the
  preferred transcript because every record has a timestamp.
* `tasks/<taskId>/api_conversation_history.json` (Roo's older name
  `claude_messages.json`): JSON array of Anthropic `MessageParam`
  `{role, content: str | [{type: text|tool_use|tool_result|thinking|image,
  ...}]}`. Roo adds `ts`, `isSummary` and top-level `type: "reasoning"`
  records with `summary`, `text` or `reasoning_content`. It is parsed only
  when no `ui_messages.json` sits beside it, so a task is not counted twice.
  Cline's records have no timestamp, so they inherit the session timestamp:
  the task id when it is a millisecond epoch (Cline's `Date.now()` ids), else
  the earliest `task_metadata.json` timestamp, else the task index `ts`.
* `tasks/<taskId>/task_metadata.json`: `files_in_context[{path,
  record_state, record_source, <agent>_read_date, <agent>_edit_date,
  user_edit_date}]` (Cline prefixes `cline_`, Roo `roo_`), and in Cline
  `model_usage[{ts, model_id, model_provider_id, mode}]` and
  `environment_history[{ts, os_name, os_version, os_arch, host_name,
  host_version, cline_version}]`. One `system` row per dated event.
* The task index, `HistoryItem {id, ts, task, tokensIn, tokensOut,
  cacheWrites, cacheReads, totalCost, size}` plus Cline's
  `cwdOnTaskInitialization`, `modelId`, `apiProvider` or Roo's `workspace`,
  `mode`, `status`, `apiConfigName`, `parentTaskId`, `rootTaskId`. Its
  location differs per agent, so subclasses supply `history_item()`. It
  gives the project path and, for Cline, the fallback model.

Rows from `ui_messages.json`: `task`, `user_feedback`, `user_feedback_diff`
and the first message of a task when it is a `say: "text"` (Roo writes the
prompt that way) are `user`; `text`, `completion_result`, `followup`,
`plan_mode_respond`, `act_mode_respond` are `assistant`; `reasoning` is
`thinking`; `tool`, `command`, `use_mcp_server`, `browser_action*`,
`new_task`, `use_subagents`, `condense`, `summarize_task` are `tool_use` with
the message `ts` as `tool_use_id`; `command_output`, `mcp_server_response`,
`browser_action_result`, `codebase_search_result` and `subtask_result` are
`tool_result` joined to the most recent `tool_use`; everything else
(`api_req_started`, `error`, `checkpoint_created`, `condense_context`,
`resume_task`, ...) is `system`. Records with no text are skipped unless
they are `system`. `source_line` is the record's 1-based position in the
JSON array. No git branch is recorded by either agent.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, text_of
from .claude_code import tool_summary

UI_FILE = "ui_messages.json"
API_FILES = ("api_conversation_history.json", "claude_messages.json")
METADATA_FILE = "task_metadata.json"

USER_KINDS = ("task", "user_feedback", "user_feedback_diff")
ASSISTANT_KINDS = ("text", "completion_result", "plan_completion_result", "followup",
                   "plan_mode_respond", "act_mode_respond")
TOOL_USE_KINDS = ("tool", "command", "use_mcp_server", "browser_action_launch", "browser_action",
                  "new_task", "use_subagents", "condense", "summarize_task")
TOOL_RESULT_KINDS = ("command_output", "mcp_server_response", "browser_action_result",
                     "codebase_search_result", "subtask_result")
TOOL_NAMES = {"command": "execute_command", "browser_action_launch": "browser_action",
              "browser_action": "browser_action"}


# ---- tolerant JSON readers ----------------------------------------------------

_WS = " \t\r\n"


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in _WS:
        i += 1
    return i


def iter_array_at(s: str, i: int, errors: list, end: list | None = None) -> Iterator[tuple[int, object]]:
    """Yield (1-based position, element) from the JSON array starting at
    `s[i]`. A truncated or corrupt element stops the walk and is recorded in
    `errors` as (position, message); the elements before it are kept. When
    `end` is given, the index after the closing bracket is appended to it."""
    dec = json.JSONDecoder()
    i = _skip_ws(s, i)
    if i >= len(s) or s[i] != "[":
        errors.append((1, "not a JSON array"))
        return
    i = _skip_ws(s, i + 1)
    if i < len(s) and s[i] == "]":
        if end is not None:
            end.append(i + 1)
        return
    n = 0
    while True:
        n += 1
        try:
            value, i = dec.raw_decode(s, _skip_ws(s, i))
        except ValueError as e:
            errors.append((n, "record %d unparseable (%s)" % (n, e)))
            return
        yield n, value
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "]":
            if end is not None:
                end.append(i + 1)
            return
        errors.append((n + 1, "array cut off after record %d" % n))
        return


def read_text(path: Path) -> str | None:
    """File contents, or None for a symlink or an unreadable file."""
    p = Path(path)
    try:
        if p.is_symlink() or not p.is_file():
            return None
        with open(p, "rb") as fh:
            s = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    return s[1:] if s.startswith("\ufeff") else s


def iter_json_array(path: Path, errors: list) -> Iterator[tuple[int, object]]:
    """Elements of a file holding one JSON array, tolerant of truncation and
    of data appended after the array, both reported through `errors`."""
    s = read_text(path)
    if s is None:
        errors.append((0, "unreadable"))
        return
    end: list = []
    count = 0
    for n, v in iter_array_at(s, 0, errors, end):
        count = n
        yield n, v
    if end and s[end[0]:].strip(_WS):
        errors.append((count + 1, "unparseable data after the JSON array"))


def load_json(path: Path):
    s = read_text(path)
    if s is None:
        return None
    try:
        return json.loads(s)
    except ValueError:
        return None


def loads_or_none(s) -> dict | None:
    if not isinstance(s, str) or not s.lstrip().startswith("{"):
        return None
    try:
        v = json.loads(s)
    except ValueError:
        return None
    return v if isinstance(v, dict) else None


def error_row(parser: Parser, artifact: Artifact, errors: list, session_id: str = "", project_path: str = "") -> Row:
    row = parser.base_row(artifact)
    row.session_id = session_id
    row.project_path = project_path
    row.turn_type = "system"
    row.source_line = errors[0][0]
    row.text = "parser: %s" % errors[0][1]
    return row


def _join(*parts) -> str:
    return " | ".join(str(p) for p in parts if p not in (None, "", [], {}))


def _fmt_counts(d: dict, keys) -> str:
    return " ".join("%s=%s" % (k, d[k]) for k in keys if d.get(k) not in (None, ""))


# ---- task context ---------------------------------------------------------------

class TaskContext:
    """What one task directory knows about itself: id, project, models and a
    start time for records that carry none."""

    def __init__(self, task_id: str, item: dict | None, metadata: dict | None, project_key: str):
        self.task_id = task_id
        item = item if isinstance(item, dict) else {}
        metadata = metadata if isinstance(metadata, dict) else {}
        self.project_path = str(item.get(project_key) or "")
        self.default_model = str(item.get("modelId") or "")
        usage = metadata.get("model_usage")
        self.model_usage: list[tuple[float, str]] = sorted(
            (float(u.get("ts") or 0), str(u.get("model_id") or ""))
            for u in (usage if isinstance(usage, list) else []) if isinstance(u, dict) and u.get("model_id"))
        self.start = self._start(task_id, item, metadata)

    @staticmethod
    def _start(task_id: str, item: dict, metadata: dict) -> str:
        if re.match(r"^\d{12,14}$", task_id):
            return to_utc(int(task_id))
        stamps = []
        for key in ("model_usage", "environment_history"):
            for e in metadata.get(key) or []:
                if isinstance(e, dict) and isinstance(e.get("ts"), (int, float)):
                    stamps.append(e["ts"])
        if stamps:
            return to_utc(min(stamps))
        return to_utc(item.get("ts"))

    def model_at(self, ts) -> str:
        if self.model_usage:
            chosen = self.model_usage[0][1]
            if isinstance(ts, (int, float)):
                for t, m in self.model_usage:
                    if t <= ts:
                        chosen = m
            return chosen
        return self.default_model


# ---- parser -----------------------------------------------------------------------

class LegacyTaskParser(Parser):
    """Subclasses set ROOT (a regex for the storage root, home-relative) and
    PROJECT_KEY, and implement history_item()."""

    ROOT = ""
    PROJECT_KEY = ""

    def __init__(self) -> None:
        self._task_rx = re.compile(
            r"^%s/tasks/([^/]+)/(ui_messages|api_conversation_history|claude_messages|task_metadata)\.json$" % self.ROOT,
            re.I)
        self._cache: dict[tuple, object] = {}

    # Subclass hook: the HistoryItem for a task, or None.
    def history_item(self, task_dir: Path, root: Path, task_id: str) -> dict | None:
        raise NotImplementedError

    def cached_json(self, path: Path):
        try:
            st = Path(path).lstat()
        except OSError:
            return None
        key = (str(path), st.st_mtime_ns, st.st_size)
        if key not in self._cache:
            self._cache[key] = load_json(path)
        return self._cache[key]

    # Subclass hook: rows for one API history message. The default reads
    # native content blocks; PearAI's Roo fork overrides it for XML tool calls.
    def api_content_rows(self, msg: dict, n: int, base_turn: str,
                         include_thinking: bool) -> Iterator[tuple[str, str, str, str]]:
        return content_rows(msg.get("content"), base_turn, include_thinking)

    def task_match(self, artifact: Artifact):
        return self._task_rx.match(artifact.rel)

    def context(self, artifact: Artifact) -> TaskContext:
        task_dir = artifact.disk_path.parent
        root = task_dir.parent.parent
        task_id = task_dir.name
        item = self.history_item(task_dir, root, task_id)
        metadata = load_json(task_dir / METADATA_FILE)
        return TaskContext(task_id, item, metadata, self.PROJECT_KEY)

    def parse_task_file(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        name = artifact.disk_path.name.lower()
        ctx = self.context(artifact)
        if name == UI_FILE:
            yield from self._parse_ui(artifact, ctx, opts)
        elif name in API_FILES:
            if (artifact.disk_path.parent / UI_FILE).is_file():
                return
            yield from self._parse_api(artifact, ctx, opts)
        elif name == METADATA_FILE:
            yield from self._parse_metadata(artifact, ctx, opts)

    def _row(self, artifact: Artifact, ctx: TaskContext, n: int, ts: str, model: str = "") -> Row:
        row = self.base_row(artifact)
        row.source_line = n
        row.timestamp_utc = ts
        row.session_id = ctx.task_id
        row.project_path = ctx.project_path
        row.model = model
        return row

    # -- ui_messages.json

    def _parse_ui(self, artifact: Artifact, ctx: TaskContext, opts: Options) -> Iterator[Row]:
        errors: list = []
        model = ""
        last_tool_id = ""
        for n, msg in iter_json_array(artifact.disk_path, errors):
            if not isinstance(msg, dict):
                continue
            info = msg.get("modelInfo")
            if isinstance(info, dict) and info.get("modelId"):
                model = str(info["modelId"])
            ts = msg.get("ts")
            row_model = model or ctx.model_at(ts)
            kind = msg.get("say") if msg.get("type") == "say" else msg.get("ask")
            kind = str(kind or msg.get("say") or msg.get("ask") or msg.get("type") or "")
            reasoning = msg.get("reasoning")
            if opts.include_thinking and isinstance(reasoning, str) and reasoning and kind != "reasoning":
                row = self._row(artifact, ctx, n, to_utc(ts), row_model)
                row.turn_type = "thinking"
                row.text = compact(reasoning, opts.max_text_length)
                yield row
            mapped = map_ui(kind, msg, n == 1)
            if mapped is None:
                continue
            turn, text, tool_name = mapped
            if turn == "thinking" and not opts.include_thinking:
                continue
            row = self._row(artifact, ctx, n, to_utc(ts), row_model)
            row.turn_type = turn
            if turn == "tool_use":
                last_tool_id = str(ts if ts is not None else n)
                row.tool_use_id = last_tool_id
                row.tool_name = tool_name
            elif turn == "tool_result":
                row.tool_use_id = last_tool_id
                row.tool_name = tool_name
            if msg.get("partial"):
                text = text + " [partial]" if text else "[partial]"
            row.text = compact(text, opts.max_text_length)
            yield row
        if errors:
            yield error_row(self, artifact, errors, ctx.task_id, ctx.project_path)

    # -- api_conversation_history.json

    def _parse_api(self, artifact: Artifact, ctx: TaskContext, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, msg in iter_json_array(artifact.disk_path, errors):
            if not isinstance(msg, dict):
                continue
            ts = to_utc(msg.get("ts")) or ctx.start
            model = ctx.model_at(msg.get("ts"))
            role = msg.get("role")
            base_turn = "user" if role == "user" else "assistant" if role == "assistant" else "system"
            if msg.get("type") == "reasoning":
                if opts.include_thinking:
                    row = self._row(artifact, ctx, n, ts, model)
                    row.turn_type = "thinking"
                    row.text = compact(text_of(msg.get("summary")) or msg.get("text") or msg.get("reasoning_content")
                                       or "[encrypted reasoning]", opts.max_text_length)
                    yield row
                continue
            if msg.get("isSummary") or msg.get("isTruncationMarker"):
                row = self._row(artifact, ctx, n, ts, model)
                row.turn_type = "system"
                label = "summary" if msg.get("isSummary") else "truncation marker"
                row.text = compact("%s: %s" % (label, text_of(msg.get("content"))), opts.max_text_length)
                yield row
                continue
            if opts.include_thinking and isinstance(msg.get("reasoning_content"), str) and msg["reasoning_content"]:
                row = self._row(artifact, ctx, n, ts, model)
                row.turn_type = "thinking"
                row.text = compact(msg["reasoning_content"], opts.max_text_length)
                yield row
            for turn, text, name, tid in self.api_content_rows(msg, n, base_turn, opts.include_thinking):
                row = self._row(artifact, ctx, n, ts, model)
                row.turn_type = turn
                row.tool_name = name
                row.tool_use_id = tid
                row.text = compact(text, opts.max_text_length)
                yield row
        if errors:
            yield error_row(self, artifact, errors, ctx.task_id, ctx.project_path)

    # -- task_metadata.json

    def _parse_metadata(self, artifact: Artifact, ctx: TaskContext, opts: Options) -> Iterator[Row]:
        data = load_json(artifact.disk_path)
        if not isinstance(data, dict):
            yield error_row(self, artifact, [(0, "task_metadata.json is not a JSON object")],
                            ctx.task_id, ctx.project_path)
            return
        events = []
        seen = set()
        for n, e in enumerate(data.get("files_in_context") or [], 1):
            if not isinstance(e, dict):
                continue
            for key in sorted(k for k in e if k.endswith("_date")):
                ts = e.get(key)
                if not isinstance(ts, (int, float)):
                    continue
                sig = (e.get("path"), key, ts)
                if sig in seen:
                    continue
                seen.add(sig)
                events.append((ts, n, "", "file %s: %s (source=%s state=%s)" % (
                    key[:-5], e.get("path") or "", e.get("record_source") or "", e.get("record_state") or "")))
        for n, e in enumerate(data.get("model_usage") or [], 1):
            if isinstance(e, dict):
                events.append((e.get("ts") or 0, n, str(e.get("model_id") or ""), "model_usage: %s" % _fmt_counts(
                    e, ("model_id", "model_provider_id", "mode"))))
        for n, e in enumerate(data.get("environment_history") or [], 1):
            if isinstance(e, dict):
                events.append((e.get("ts") or 0, n, "", "environment: %s" % _fmt_counts(
                    e, ("os_name", "os_version", "os_arch", "host_name", "host_version", "cline_version"))))
        events.sort(key=lambda x: (x[0] if isinstance(x[0], (int, float)) else 0))
        for ts, n, model, text in events:
            row = self._row(artifact, ctx, n, to_utc(ts), model)
            row.turn_type = "system"
            row.text = compact(text, opts.max_text_length)
            yield row

    # -- task index entries

    def history_row(self, artifact: Artifact, item: dict, n: int, opts: Options) -> Row:
        row = self.base_row(artifact)
        row.source_line = n
        row.timestamp_utc = to_utc(item.get("ts"))
        row.session_id = str(item.get("id") or "")
        row.project_path = str(item.get(self.PROJECT_KEY) or "")
        row.model = str(item.get("modelId") or "")
        row.turn_type = "system"
        extra = _fmt_counts(item, ("tokensIn", "tokensOut", "cacheWrites", "cacheReads", "totalCost", "size",
                                   "apiProvider", "mode", "status", "apiConfigName", "parentTaskId", "rootTaskId"))
        row.text = compact("task: %s | %s" % (item.get("task") or "", extra), opts.max_text_length)
        return row


def map_ui(kind: str, msg: dict, first: bool) -> tuple[str, str, str] | None:
    """(turn_type, text, tool_name) for one ClineMessage, or None to skip."""
    text = msg.get("text")
    text = text if isinstance(text, str) else ("" if text is None else compact_json(text))
    images = msg.get("images")
    nimg = len(images) if isinstance(images, list) else 0
    if kind in USER_KINDS or (kind == "text" and first):
        if nimg:
            text = _join(text, "[%d image(s)]" % nimg)
        return ("user", text, "") if text else None
    if kind == "reasoning":
        return ("thinking", text, "") if text else None
    if kind in ASSISTANT_KINDS:
        j = loads_or_none(text)
        if j is not None:
            opts = j.get("options") or j.get("suggest")
            if isinstance(opts, list):
                opts = "; ".join(o if isinstance(o, str) else str(o.get("answer") or compact_json(o))
                                 if isinstance(o, dict) else str(o) for o in opts)
            text = _join(j.get("question") or j.get("response") or "", opts or "")
        return ("assistant", text, "") if text else None
    if kind in TOOL_USE_KINDS:
        name, body = tool_use_text(kind, text)
        return ("tool_use", body, name) if body or name else None
    if kind in TOOL_RESULT_KINDS:
        if kind == "browser_action_result":
            j = loads_or_none(text) or {}
            text = _join(j.get("currentUrl"), j.get("logs"), "[screenshot]" if j.get("screenshot") else "")
        name = {"command_output": "execute_command", "browser_action_result": "browser_action",
                "codebase_search_result": "codebaseSearch", "subtask_result": "new_task"}.get(kind, "")
        return ("tool_result", text, name) if text else None
    if kind in ("api_req_started", "api_req_finished", "api_req_deleted"):
        j = loads_or_none(text) or {}
        detail = _fmt_counts(j, ("tokensIn", "tokensOut", "cacheWrites", "cacheReads", "cost", "apiProtocol",
                                 "cancelReason", "streamingFailedMessage"))
        return ("system", "%s: %s" % (kind, detail) if detail else kind, "")
    if kind == "condense_context":
        cc = msg.get("contextCondense") or {}
        if isinstance(cc, dict) and cc:
            detail = _fmt_counts(cc, ("prevContextTokens", "newContextTokens", "cost"))
            return ("system", "condense_context: %s | %s" % (detail, cc.get("summary") or ""), "")
    if kind == "checkpoint_created" and msg.get("lastCheckpointHash"):
        return ("system", "checkpoint_created: %s" % msg["lastCheckpointHash"], "")
    return ("system", "%s: %s" % (kind, text) if text else kind, "")


def tool_use_text(kind: str, text: str) -> tuple[str, str]:
    if kind == "tool":
        j = loads_or_none(text)
        if j is None:
            return "tool", text
        batch = j.get("batchFiles")
        paths = "; ".join(str(b.get("path")) for b in batch if isinstance(b, dict)) if isinstance(batch, list) else ""
        body = _join(j.get("path"), paths, j.get("regex"), j.get("filePattern"), j.get("query"), j.get("mode"),
                     j.get("reason"), j.get("diff") or j.get("content"))
        return str(j.get("tool") or "tool"), body
    if kind == "use_mcp_server":
        j = loads_or_none(text)
        if j is None:
            return "use_mcp_server", text
        name = j.get("toolName") or j.get("type") or "use_mcp_server"
        return str(name), _join(j.get("serverName"), j.get("uri"), j.get("arguments"))
    if kind == "browser_action":
        j = loads_or_none(text)
        if j is not None:
            return "browser_action", _join(j.get("action"), j.get("coordinate"), j.get("text"))
    if kind == "use_subagents":
        j = loads_or_none(text)
        if j is not None and isinstance(j.get("prompts"), list):
            return "use_subagents", " ; ".join(str(p) for p in j["prompts"])
    return TOOL_NAMES.get(kind, kind), text


def content_rows(content, base_turn: str, include_thinking: bool) -> Iterator[tuple[str, str, str, str]]:
    """(turn_type, text, tool_name, tool_use_id) per content block of an
    Anthropic-style message, shared by the legacy API history and Cline's SDK
    messages."""
    if isinstance(content, str):
        if content:
            yield base_turn, content, "", ""
        return
    if not isinstance(content, list):
        if content not in (None, ""):
            yield base_turn, compact_json(content), "", ""
        return
    for b in content:
        if isinstance(b, str):
            if b:
                yield base_turn, b, "", ""
            continue
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            if b.get("text"):
                yield base_turn, str(b["text"]), "", ""
        elif t == "tool_use":
            name = str(b.get("name") or "")
            yield "tool_use", tool_summary(name, b.get("input")), name, str(b.get("id") or b.get("call_id") or "")
        elif t == "tool_result":
            c = b.get("content")
            body = text_of(c) if isinstance(c, (str, list)) or c is None else compact_json(c)
            if b.get("is_error"):
                body = "[error] " + body
            yield "tool_result", body, str(b.get("name") or ""), str(b.get("tool_use_id") or "")
        elif t in ("thinking", "reasoning"):
            if include_thinking:
                yield "thinking", str(b.get("thinking") or b.get("text") or ""), "", ""
        elif t == "redacted_thinking":
            if include_thinking:
                yield "thinking", "[redacted thinking]", "", ""
        elif t == "image":
            yield base_turn, "[image]", "", ""
        elif t == "file":
            yield base_turn, _join("[file]", b.get("path")), "", ""
        elif t:
            yield base_turn, "[%s]" % t, "", ""
