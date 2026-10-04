"""Codex CLI transcripts, and the rollout format shared with its forks.

Validated against a real install (Codex CLI, October 2026) and codex source
at 3e23877 (see `research/codex-cli.md`). Files, under `~/.codex` for Codex
(`RolloutParser.home_prefix` for a fork):

* `sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`, older releases
  wrote `sessions/rollout-*.jsonl`; `archived_sessions/` holds archived
  threads in the same layout (codex `rollout/src/lib.rs:87` at 3e23877).
  A reverted thread is `rollout-<timestamp>-<thread id>_<rollout id>.jsonl`
  (`rollout/src/rollout_file_name.rs:40-47`). Cold rollouts may be
  zstd-compressed to `.jsonl.zst` (`rollout/src/compression.rs:29`); those
  need the `zstandard` package, imported lazily, and without it each becomes
  one `system` row. A truncated zstd frame yields the lines decoded before
  the cut. Each line is `{timestamp, ordinal, type, payload}` with
  `timestamp` ISO 8601 Z, and a `response_item` line may carry a sibling
  `metadata` object. Types:
  - `session_meta`: payload `id` (thread id), `session_id` (root thread),
    `timestamp`, `cwd`, `originator`, `cli_version`, `model_provider`,
    optional `git` (`branch`), and for spawned threads `parent_thread_id`,
    `thread_source`, `source.subagent.thread_spawn.parent_thread_id`,
    `agent_path`, `agent_role`, `agent_nickname`; `forked_from_id` on a fork.
    Only the file's first `session_meta` sets the session id, project and
    branch. A subagent (a parent in `parent_thread_id`, else in
    `source.subagent.thread_spawn`, else a `session_id` other than `id` on
    a thread that is not a fork) gets a `subagent <id> of <parent>` row, a
    fork a `forked from <id>` row. A later `session_meta` with another id is
    an ancestor's, copied into a fork, and becomes a `copied from ancestor:`
    row; one with the same id is skipped.
  - `turn_context`: payload `turn_id`, `cwd`, `model`; updates the current
    project path and model.
  - `response_item`: payload `type` is `message` (`role` user, assistant or
    developer; `content` blocks with `text`;
    `internal_chat_message_metadata_passthrough.content_item_kinds`, one
    kind per block), `function_call` or `custom_tool_call` (`name`,
    `call_id`, `arguments` or `input`), `function_call_output` or
    `custom_tool_call_output` (`call_id`, `output`), `local_shell_call`
    (`action.command`), `web_search_call` (`action.query`),
    `tool_search_call` (`call_id`, `arguments`), `tool_search_output`
    (`call_id`, `tools[].name`), `agent_message` (`author`, `recipient`,
    `content`), `image_generation_call` (`revised_prompt`, `status`; the
    image in `result` is not copied), `reasoning` (`summary`, `content`).
    A user-role block whose kind starts `user.` (or is `unknown` or empty,
    which Codex itself treats as possibly the user's) is a `user` row; any
    other kind (`environments.environment_context`, AGENTS.md and skill
    instructions, subagent notifications, `shell.user_command`,
    `generic.turn_aborted`) is a `system` row `context: <kind>: <text>`.
    Without a kinds list as long as `content` (older rollouts) a block
    that is wholly one of the harness's own wrappers (`CONTEXT_MARKERS`:
    open marker at its start, close marker at its end, as Codex's
    `matches_marked_text` checks) is `context: <marker name>: <text>`, and
    any other block a `user` row, so a tag typed mid-message stays `user`.
    A line whose `metadata` has `inherited_user_message` was copied from
    the parent thread, which records it itself, and is skipped. In a
    subagent's file the first prompt, a user message or an agent message,
    is the parent's task: `system` `subagent task: <text>`. Later user
    messages in a subagent's file stay `user`: the parent's v1
    `send_input` tool writes plain user input into the child
    (`core/src/agent/control.rs:134-143`), but a person can also type into
    a subagent thread, since the TUI's `/subagents` picker makes it the
    active thread and composer input goes to the active thread
    (`tui/src/multi_agents.rs:1-5`, `tui/src/app/thread_routing.rs:475-497`),
    and the two are recorded alike. Other agent messages are `system`
    `agent message <author> -> <recipients>: <text>`. Reasoning with no
    text is skipped.
  - `event_msg`: payload `type` task_started and task_complete
    (`turn_id`, `duration_ms`), turn_aborted (`reason`, `error.message`),
    thread_rolled_back (`num_turns`) become system rows. item_completed
    (`item`, `started_at_ms`, `completed_at_ms`) carries a turn item; a
    `UserMessage`, `AgentMessage`, `Reasoning`, `HookPrompt` or
    `ContextCompaction` item only repeats a response_item or `compacted`
    line under an id of its own and is skipped, and any other item whose
    `id` equals a response_item's `id` or `call_id` in the same file is
    skipped too: the response_item wins. A `CommandExecution` item's
    non-zero `exit_code` is still added to its call's `tool_result` as
    `[exit N]`. The rest become rows: `CommandExecution` (`command`,
    `aggregated_output`), `McpToolCall` (`server`, `tool`, `arguments`,
    `result.content`, `error`), `DynamicToolCall` (`tool`, `arguments`,
    `content_items`), `FileChange` (`changes`, `stdout`, `stderr`) and web
    search (`WebSearch`, or `Extension` kind `web.search`: `query`,
    `results`) as a tool_use at `started_at_ms` and a tool_result at
    `completed_at_ms` joined on the item `id`; `FunctionCallOutput` as a
    tool_result; `Plan` (`text`), `SubAgentActivity`, image generation
    (`revised_prompt` or `revisedPrompt`) and `clock.sleep` (`durationMs`)
    as system rows; anything else as `item <type>: <JSON>`. Legacy events
    that repeat response items (`user_message`, `agent_message`,
    `agent_reasoning`) and the rest are skipped.
  - `compacted`: `message` becomes `compaction summary: <text>`, or
    `compaction: replacement history of N items` when empty.
  - `inter_agent_communication` (`author`, `recipient`,
    `other_recipients`, `content`, `encrypted_content`, `id`): as an agent
    message, skipped when an `agent_message` response_item has its id.
  - `realtime_item`: `type` `transcript_segment` with `role` user or
    assistant becomes that row type with `text`; other types a
    `realtime: <type> <JSON>` system row.
  - `world_state`, `token_usage_record`, `inter_agent_communication_metadata`,
    `retained_context`, `security_risk_score`: skipped.
  Until `session_meta` is read, the session id is the thread id in the file
  name, so a rollout cut before its first line is still attributed.
  Copied forks re-append the parent's records with no marker other than the
  ancestor's `session_meta` and the per-message `inherited_user_message`,
  so the rest of a copied prefix is not separated out; it carries the
  fork's session id. Referenced forks keep the prefix in the parent's file.
* `history.jsonl`: `{session_id, text, ts}` per prompt, `ts` epoch seconds.
* Forks only, when `ledger_name` is set: an import ledger
  `{"records": [{source_path, content_sha256, imported_thread_id,
  imported_at, source_modified_at?}]}` (times epoch seconds), one `system`
  row per record. See `open_interpreter.py`.

Not read: `session_index.jsonl` (thread names), `state_5.sqlite` and
`thread_history_1.sqlite` (projections of the rollouts).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import cast

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

ROLLOUT_TMPL = r"^%s/(?:archived_)?sessions/(?:.*/)?rollout-[^/]*\.jsonl(?:\.zst)?$"
ROLLOUT_RX = re.compile(ROLLOUT_TMPL % re.escape(".codex"))
HISTORY_REL = ".codex/history.jsonl"
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# `rollout-<time>-<thread id>.jsonl`, or `...-<thread id>_<rollout id>.jsonl`
# for a reverted thread; group 1 is the thread id either way.
UUID_TAIL_RX = re.compile(r"(%s)(?:_%s)?\.jsonl(?:\.zst)?$" % (UUID, UUID))

CALL_TYPES = ("function_call", "custom_tool_call", "local_shell_call", "web_search_call")
OUTPUT_TYPES = ("function_call_output", "custom_tool_call_output", "local_shell_call_output")


def call_summary(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        action = payload.get("action") or {}
        cmd = action.get("command")
        if isinstance(cmd, list):
            return " ".join(str(c) for c in cmd)
        return str(cmd or compact_json(action))
    if ptype == "web_search_call":
        action = payload.get("action") or {}
        return str(action.get("query") or compact_json(action))
    for key in ("arguments", "input"):
        v = payload.get(key)
        if v not in (None, ""):
            return v if isinstance(v, str) else compact_json(v)
    return compact_json(
        {k: v for k, v in payload.items() if k not in ("type", "id", "call_id", "name", "status")}
    )


def call_name(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        return "shell"
    if ptype == "web_search_call":
        return "web_search"
    return str(payload.get("name") or ptype or "")


def _zstd_module():
    """The `zstandard` module, or None when it is not installed."""
    try:
        import zstandard  # pyright: ignore[reportMissingImports] - optional dependency
    except ImportError:
        return None
    return zstandard


def _decode_line(n: int, raw: bytes, errors: list) -> dict | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        rec = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError as e:
        errors.append((n, str(e)))
        return None
    return rec if isinstance(rec, dict) else None


class TruncatedFrame(Exception):
    pass


def iter_zst_chunks(fh, zstd) -> Iterator[bytes]:
    """Decompressed bytes of every zstd frame in `fh`, streamed. Raises
    `zstd.ZstdError` on corrupt input and `TruncatedFrame` when the file ends
    inside a frame (the stream reader would end silently instead)."""
    dctx = zstd.ZstdDecompressor()
    dobj = dctx.decompressobj()
    open_frame = False
    while True:
        data = fh.read(1 << 16)
        if not data:
            break
        while data:
            out = dobj.decompress(data)
            open_frame = True
            if out:
                yield out
            if getattr(dobj, "eof", False):
                data = dobj.unused_data
                dobj = dctx.decompressobj()
                open_frame = False
            else:
                data = b""
    if open_frame and hasattr(dobj, "eof"):
        raise TruncatedFrame("file ends inside a zstd frame")


def iter_zst_jsonl(path, errors: list, zstd) -> Iterator[tuple[int, dict]]:
    """`iter_jsonl` over a zstd-compressed file, streamed. A corrupt or
    truncated frame becomes one entry in `errors`; the lines decoded before
    it are still yielded, and a line cut by the damage is a bad line."""
    n = 0
    buf = b""
    with open(path, "rb") as fh:
        try:
            for chunk in iter_zst_chunks(fh, zstd):
                buf += chunk
                lines = buf.split(b"\n")
                buf = lines.pop()
                for raw in lines:
                    n += 1
                    rec = _decode_line(n, raw, errors)
                    if rec is not None:
                        yield n, rec
        except (zstd.ZstdError, TruncatedFrame) as e:
            errors.append((n + 1, "zstd: %s" % e))
    if buf.strip():
        n += 1
        rec = _decode_line(n, buf, errors)
        if rec is not None:
            yield n, rec


# Turn items that only repeat a response_item message, reasoning or the
# `compacted` line, under an id of their own (`items.rs` `new_item_id`).
RESPONSE_CARRIED_ITEMS = (
    "UserMessage",
    "AgentMessage",
    "Reasoning",
    "HookPrompt",
    "ContextCompaction",
)
# Content kinds of a user-role message block that the person supplied.
USER_KINDS = ("", "unknown")
# Wrappers the harness puts around the user-role context it injects, as
# (name, start, end); Codex recognises the same blocks with
# CONTEXTUAL_USER_FRAGMENT_MATCHERS (`core/src/context/contextual_user_message.rs`
# at 3e23877; citations in research/codex-cli.md section 8). Used only for
# rollouts without content kinds.
CONTEXT_MARKERS = (
    ("agents_md_instructions", "# AGENTS.md instructions", "</INSTRUCTIONS>"),
    ("environment_context", "<environment_context>", "</environment_context>"),
    (
        "agent_message_board_notification",
        "<agent_message_board_notification>",
        "</agent_message_board_notification>",
    ),
    ("skill", "<skill>", "</skill>"),
    ("user_shell_command", "<user_shell_command>", "</user_shell_command>"),
    ("turn_aborted", "<turn_aborted>", "</turn_aborted>"),
    ("subagent_notification", "<subagent_notification>", "</subagent_notification>"),
    ("recommended_plugins", "<recommended_plugins>", "</recommended_plugins>"),
)


def context_marker(text: str) -> str:
    """The name of the harness wrapper `text` is, or "". Like Codex's own
    `matches_marked_text`, the block must start with the open marker after
    leading whitespace and end with the close marker before trailing
    whitespace, ignoring ASCII case; a tag typed mid-message does not count."""
    body = text.strip().lower()
    for name, start, end in CONTEXT_MARKERS:
        if body.startswith(start.lower()) and body.endswith(end.lower()):
            return name
    return ""


def user_parts(payload: dict) -> list[tuple[str, str]]:
    """(kind, text) runs of a `role: "user"` message. kind is "" for input the
    person supplied (`user.*`, or `unknown`, which Codex itself treats as
    possibly the user's) and the content kind for harness context. Without a
    `content_item_kinds` list as long as `content`, each block is classified
    by `context_marker` instead, and kind is the marker name."""
    content = payload.get("content")
    if isinstance(content, str):
        content = [{"type": "input_text", "text": content}]
    if not isinstance(content, list):
        text = text_of(content)
        return [("", text)] if text else []
    meta = payload.get("internal_chat_message_metadata_passthrough")
    kinds = meta.get("content_item_kinds") if isinstance(meta, dict) else None
    use_kinds = isinstance(kinds, list) and len(kinds) == len(content)
    parts: list[tuple[str, str]] = []
    for i, block in enumerate(content):
        text = text_of([block])
        if not text:
            continue
        if use_kinds:
            kind = str(cast(list, kinds)[i] or "")
            key = "" if kind.startswith("user.") or kind in USER_KINDS else kind
        else:
            key = context_marker(text)
        if parts and parts[-1][0] == key:
            parts[-1] = (key, parts[-1][1] + "\n" + text)
        else:
            parts.append((key, text))
    return parts


def _parent_of(meta: dict) -> str:
    """The parent thread of a subagent's `session_meta`: `parent_thread_id`,
    else `source.subagent.thread_spawn.parent_thread_id`, else a root
    `session_id` that differs from `id` when the thread is not a fork."""
    parent = meta.get("parent_thread_id")
    if parent:
        return str(parent)
    source = meta.get("source")
    sub = source.get("subagent") if isinstance(source, dict) else None
    spawn = sub.get("thread_spawn") if isinstance(sub, dict) else None
    if isinstance(spawn, dict) and spawn.get("parent_thread_id"):
        return str(spawn["parent_thread_id"])
    root = meta.get("session_id")
    if root and meta.get("id") and root != meta.get("id") and not meta.get("forked_from_id"):
        return str(root)
    return ""


def _is_subagent(meta: dict) -> bool:
    source = meta.get("source")
    return meta.get("thread_source") == "subagent" or (
        isinstance(source, dict) and "subagent" in source
    )


def _prescan(records: list) -> tuple[set, dict]:
    """Ids and call ids every response_item carries, and the exit code of each
    `CommandExecution` turn item by its id (which is the call's `call_id`)."""
    carried: set = set()
    exit_codes: dict = {}
    for _n, rec in records:
        payload = rec.get("payload")
        if not isinstance(payload, dict):
            continue
        if rec.get("type") == "response_item":
            for key in ("id", "call_id"):
                if payload.get(key):
                    carried.add(str(payload[key]))
        elif rec.get("type") == "event_msg" and payload.get("type") == "item_completed":
            item = payload.get("item")
            if (
                isinstance(item, dict)
                and item.get("type") == "CommandExecution"
                and item.get("exit_code") is not None
            ):
                exit_codes[str(item.get("id") or "")] = item["exit_code"]
    carried.discard("")
    return carried, exit_codes


def _with_exit(text: str, code) -> str:
    if code in (None, 0):
        return text
    return "[exit %s] %s" % (code, text)


def _tool_names(tools) -> str:
    if not isinstance(tools, list):
        return compact_json(tools)
    names = [
        str(t.get("name")) if isinstance(t, dict) and t.get("name") else compact_json(t)
        for t in tools
    ]
    return ", ".join(names)


def _agent_label(payload: dict) -> str:
    to = [str(payload.get("recipient") or "")]
    others = payload.get("other_recipients")
    if isinstance(others, list):
        to += [str(o) for o in others]
    return "agent message %s -> %s: " % (payload.get("author") or "", ", ".join(to))


def _agent_text(payload: dict) -> str:
    content = payload.get("content")
    text = text_of(content)
    if isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "encrypted_content" for b in content
    ):
        text = (text + " [encrypted]").strip()
    return text


def _result_text(value) -> str:
    """Text of an MCP `CallToolResult` or dynamic tool output."""
    if isinstance(value, dict):
        if "content" in value:
            return text_of(value.get("content"))
        return compact_json(value)
    return text_of(value)


def item_rows(item: dict, payload: dict) -> list[tuple[str, object, dict, str]]:
    """Rows for an `item_completed` turn item that no response_item carries,
    as (turn_type, timestamp, {tool_name, tool_use_id}, text). A tool item
    becomes a tool_use at `started_at_ms` and a tool_result at
    `completed_at_ms`; anything else one system row."""
    itype = str(item.get("type") or "")
    iid = str(item.get("id") or "")
    t0 = payload.get("started_at_ms")
    t1 = payload.get("completed_at_ms")

    def pair(name: str, call: str, result: str) -> list:
        ids = {"tool_name": name, "tool_use_id": iid}
        return [("tool_use", t0, ids, call), ("tool_result", t1, {"tool_use_id": iid}, result)]

    def failure() -> str:
        err = item.get("error")
        if isinstance(err, dict):
            return "[error] %s" % (err.get("message") or compact_json(err))
        return "[error] %s" % err if err else ""

    if itype == "CommandExecution":
        cmd = item.get("command")
        call = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd or "")
        out = _with_exit(str(item.get("aggregated_output") or ""), item.get("exit_code"))
        return pair("shell", call, out)
    if itype == "McpToolCall":
        name = "%s.%s" % (item.get("server") or "", item.get("tool") or "")
        result = _result_text(item.get("result")) if item.get("result") else failure()
        return pair(name, compact_json(item.get("arguments")), result)
    if itype == "DynamicToolCall":
        result = _result_text(item.get("content_items")) or failure()
        return pair(str(item.get("tool") or ""), compact_json(item.get("arguments")), result)
    if itype == "FileChange":
        changes = item.get("changes")
        paths = ", ".join(sorted(changes)) if isinstance(changes, dict) else ""
        out = "\n".join(str(item.get(k)) for k in ("stdout", "stderr") if item.get(k))
        return pair("apply_patch", paths, out or str(item.get("status") or ""))
    if itype == "FunctionCallOutput":
        ids = {"tool_name": str(item.get("name") or ""), "tool_use_id": iid}
        return [("tool_result", t1, ids, text_of(item.get("output")))]
    if itype == "WebSearch" or (itype == "Extension" and item.get("kind") == "web.search"):
        results = item.get("results")
        return pair("web_search", str(item.get("query") or ""), compact_json(results or []))
    if itype == "Extension" and item.get("kind") == "clock.sleep":
        return [("system", t1, {}, "sleep: %s ms" % item.get("durationMs", ""))]
    if itype in ("ImageGeneration", "Extension"):
        prompt = item.get("revised_prompt") or item.get("revisedPrompt") or ""
        saved = item.get("saved_path") or item.get("savedPath") or ""
        text = "image generation: %s status=%s" % (prompt, item.get("status") or "")
        if itype == "Extension" and item.get("kind") != "image_gen.generation":
            rest = {k: v for k, v in item.items() if k not in ("type", "id")}
            text = "item Extension: " + compact_json(rest)
        elif saved:
            text += " saved=%s" % saved
        return [("system", t1, {}, text)]
    if itype == "Plan":
        return [("system", t1, {}, "plan: %s" % (item.get("text") or ""))]
    if itype == "SubAgentActivity":
        return [
            (
                "system",
                t1,
                {},
                "subagent activity: %s %s %s"
                % (
                    item.get("kind") or "",
                    item.get("agent_path") or "",
                    item.get("agent_thread_id") or "",
                ),
            )
        ]
    rest = {k: v for k, v in item.items() if k not in ("type", "id", "result")}
    return [("system", t1, {}, "item %s: %s" % (itype, compact_json(rest)))]


class RolloutParser(Parser):
    """Codex rollouts and prompt history under `home_prefix`. Codex forks
    that keep the format subclass this with their own agent and home."""

    home_prefix = ".codex"
    ledger_name = ""  # import ledger file under home_prefix; empty when the agent has none

    def __init__(self) -> None:
        self.rollout_rx = re.compile(ROLLOUT_TMPL % re.escape(self.home_prefix))
        self.history_rel = self.home_prefix + "/history.jsonl"
        self.ledger_rel = self.home_prefix + "/" + self.ledger_name if self.ledger_name else ""

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        return (
            rel == self.history_rel
            or bool(self.rollout_rx.match(rel))
            or bool(self.ledger_rel and rel == self.ledger_rel)
        )

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == self.history_rel:
            yield from self._parse_history(artifact, opts)
        elif self.ledger_rel and artifact.rel == self.ledger_rel:
            yield from self._parse_ledger(artifact, opts)
        else:
            yield from self._parse_rollout(artifact, opts)

    def _system(self, artifact: Artifact, text: str, session_id: str = "", line: int = 0) -> Row:
        row = self.base_row(artifact)
        row.turn_type = "system"
        row.session_id = session_id
        row.source_line = line
        row.text = text
        return row

    def _parse_ledger(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        try:
            with open(artifact.disk_path, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", errors="replace"))
        except (OSError, ValueError) as e:
            yield self._system(artifact, "parser: unreadable import ledger: %s" % e)
            return
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            yield self._system(artifact, "parser: import ledger has no records list")
            return
        for i, rec in enumerate(records, 1):
            if not isinstance(rec, dict):
                continue
            # source_line is the record's position in `records`, not a file line.
            row = self._system(artifact, "", str(rec.get("imported_thread_id") or ""), i)
            row.timestamp_utc = to_utc(rec.get("imported_at"))
            text = "imported session from %s sha256=%s" % (
                rec.get("source_path") or "",
                rec.get("content_sha256") or "",
            )
            modified = to_utc(rec.get("source_modified_at"))
            if modified:
                text += " source_modified=%s" % modified
            row.text = compact(text, opts.max_text_length)
            yield row

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("ts"))
            row.session_id = str(rec.get("session_id") or "")
            row.turn_type = "user"
            row.text = compact(rec.get("text"), opts.max_text_length)
            yield row

    def _parse_rollout(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        m = UUID_TAIL_RX.search(artifact.rel)
        session_id = m.group(1) if m else ""  # until session_meta says otherwise
        if artifact.rel.endswith(".zst"):
            zstd = _zstd_module()
            if zstd is None:
                yield self._system(
                    artifact,
                    "parser: compressed rollout not read: zstandard package not installed",
                    session_id,
                )
                return
            records = list(iter_zst_jsonl(artifact.disk_path, errors, zstd))
        else:
            records = list(iter_jsonl(artifact.disk_path, errors))
        carried, exit_codes = _prescan(records)
        cwd = ""
        model = ""
        branch = ""
        meta_seen = False
        task_pending = False  # a subagent file whose first prompt is still to come
        for n, rec in records:
            rtype = rec.get("type")
            payload = rec.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            def base(turn_type: str = "system", ts=None) -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(ts) or to_utc(rec.get("timestamp"))
                row.session_id = session_id
                row.project_path = cwd
                row.git_branch = branch
                row.model = model
                row.turn_type = turn_type
                return row

            def prompt(text: str) -> Row:
                """A prompt that is not context: the person's, or a subagent's task."""
                nonlocal task_pending
                if task_pending:
                    task_pending = False
                    return self._fill(base(), "subagent task: " + text, opts)
                return self._fill(base("user"), text, opts)

            if rtype == "session_meta":
                sid = str(payload.get("id") or payload.get("session_id") or "")
                if meta_seen:
                    if sid and sid != session_id:
                        yield self._fill(
                            base(ts=payload.get("timestamp")),
                            "copied from ancestor: session start %s %s id=%s cwd=%s"
                            % (
                                payload.get("originator") or "codex",
                                payload.get("cli_version") or "",
                                sid,
                                payload.get("cwd") or "",
                            ),
                            opts,
                        )
                    continue
                meta_seen = True
                session_id = sid or session_id
                cwd = str(payload.get("cwd") or cwd)
                git = payload.get("git") or {}
                if isinstance(git, dict):
                    branch = str(git.get("branch") or branch)
                yield self._fill(
                    base(ts=payload.get("timestamp")),
                    "session start: %s %s provider=%s cwd=%s"
                    % (
                        payload.get("originator") or "codex",
                        payload.get("cli_version") or "",
                        payload.get("model_provider") or "",
                        cwd,
                    ),
                    opts,
                )
                parent = _parent_of(payload)
                if parent:
                    extra = " ".join(
                        "%s=%s" % (k, payload.get(k))
                        for k in ("agent_path", "agent_role", "agent_nickname")
                        if payload.get(k)
                    )
                    yield self._fill(
                        base(ts=payload.get("timestamp")),
                        ("subagent %s of %s %s" % (session_id, parent, extra)).strip(),
                        opts,
                    )
                if payload.get("forked_from_id"):
                    yield self._fill(
                        base(ts=payload.get("timestamp")),
                        "forked from %s" % payload.get("forked_from_id"),
                        opts,
                    )
                task_pending = bool(parent) or _is_subagent(payload)
            elif rtype == "turn_context":
                cwd = str(payload.get("cwd") or cwd)
                model = str(payload.get("model") or model)
            elif rtype == "response_item":
                meta = rec.get("metadata")
                if isinstance(meta, dict) and meta.get("inherited_user_message"):
                    continue  # copied from the parent thread, which records it itself
                ptype = payload.get("type")
                if ptype == "message":
                    role = payload.get("role")
                    if role == "user":
                        for kind, text in user_parts(payload):
                            if not kind:
                                yield prompt(text)
                            else:
                                yield self._fill(base(), "context: %s: %s" % (kind, text), opts)
                        continue
                    text = text_of(payload.get("content"))
                    if not text:
                        continue
                    if role == "assistant":
                        yield self._fill(base("assistant"), text, opts)
                    else:
                        yield self._fill(base(), "%s: %s" % (role, text), opts)
                elif ptype in CALL_TYPES:
                    row = base("tool_use")
                    row.tool_name = call_name(payload)
                    row.tool_use_id = str(payload.get("call_id") or payload.get("id") or "")
                    yield self._fill(row, call_summary(payload), opts)
                elif ptype in OUTPUT_TYPES:
                    row = base("tool_result")
                    row.tool_use_id = str(payload.get("call_id") or "")
                    text = text_of(payload.get("output"))
                    yield self._fill(row, _with_exit(text, exit_codes.get(row.tool_use_id)), opts)
                elif ptype == "tool_search_call":
                    row = base("tool_use")
                    row.tool_name = "tool_search"
                    row.tool_use_id = str(payload.get("call_id") or payload.get("id") or "")
                    yield self._fill(row, compact_json(payload.get("arguments")), opts)
                elif ptype == "tool_search_output":
                    row = base("tool_result")
                    row.tool_use_id = str(payload.get("call_id") or "")
                    yield self._fill(row, _tool_names(payload.get("tools")), opts)
                elif ptype == "agent_message":
                    text = _agent_text(payload)
                    if task_pending:
                        yield prompt(text)
                    else:
                        yield self._fill(base(), _agent_label(payload) + text, opts)
                elif ptype == "image_generation_call":
                    yield self._fill(
                        base(),
                        "image generation: %s status=%s"
                        % (payload.get("revised_prompt") or "", payload.get("status") or ""),
                        opts,
                    )
                elif ptype == "reasoning" and opts.include_thinking:
                    text = text_of(payload.get("summary")) or text_of(payload.get("content"))
                    if text:
                        yield self._fill(base("thinking"), text, opts)
            elif rtype == "event_msg":
                ptype = payload.get("type")
                if ptype == "task_started":
                    yield self._fill(
                        base(), "task_started turn=%s" % (payload.get("turn_id") or ""), opts
                    )
                elif ptype == "task_complete":
                    yield self._fill(
                        base(),
                        "task_complete turn=%s duration_ms=%s"
                        % (payload.get("turn_id") or "", payload.get("duration_ms") or ""),
                        opts,
                    )
                elif ptype == "turn_aborted":
                    err = payload.get("error")
                    detail = err.get("message") if isinstance(err, dict) else ""
                    text = "turn aborted: %s" % (payload.get("reason") or "")
                    yield self._fill(base(), ("%s %s" % (text, detail or "")).strip(), opts)
                elif ptype == "thread_rolled_back":
                    yield self._fill(
                        base(), "rolled back %s turns" % payload.get("num_turns", ""), opts
                    )
                elif ptype == "item_completed":
                    item = payload.get("item")
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") in RESPONSE_CARRIED_ITEMS:
                        continue
                    if str(item.get("id") or "") in carried:
                        continue
                    for turn_type, ts, fields, text in item_rows(item, payload):
                        row = base(turn_type, ts)
                        row.tool_name = fields.get("tool_name", "")
                        row.tool_use_id = fields.get("tool_use_id", "")
                        yield self._fill(row, text, opts)
            elif rtype == "compacted":
                msg = payload.get("message")
                if isinstance(msg, str) and msg:
                    yield self._fill(base(), "compaction summary: " + msg, opts)
                else:
                    hist = payload.get("replacement_history")
                    n_items = len(hist) if isinstance(hist, list) else 0
                    yield self._fill(
                        base(), "compaction: replacement history of %d items" % n_items, opts
                    )
            elif rtype == "inter_agent_communication":
                if str(payload.get("id") or "") in carried:
                    continue  # the agent_message response_item with this id wins
                text = payload.get("content")
                if not isinstance(text, str) or not text:
                    text = "[encrypted]" if payload.get("encrypted_content") else ""
                if task_pending:
                    yield prompt(text)
                else:
                    yield self._fill(base(), _agent_label(payload) + text, opts)
            elif rtype == "realtime_item":
                kind = payload.get("type")
                if kind == "transcript_segment" and payload.get("role") in ("user", "assistant"):
                    yield self._fill(
                        base(str(payload["role"])), str(payload.get("text") or ""), opts
                    )
                else:
                    rest = {k: v for k, v in payload.items() if k not in ("type", "id", "text")}
                    text = "realtime: %s %s" % (kind or "", compact_json(rest))
                    if payload.get("text"):
                        text += " " + str(payload["text"])
                    yield self._fill(base(), text, opts)
        if errors:
            yield self._system(
                artifact,
                "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0]),
                session_id,
                errors[0][0],
            )

    @staticmethod
    def _fill(row: Row, text: str, opts: Options) -> Row:
        row.text = compact(text, opts.max_text_length)
        return row


class CodexParser(RolloutParser):
    agent = "codex-cli"
    name = "codex-cli"
    home_prefix = ".codex"
