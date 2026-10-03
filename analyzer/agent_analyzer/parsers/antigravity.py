"""Antigravity CLI (`agy`) conversations.

Antigravity stores each conversation as a SQLite database of protobuf blobs.
There is no public schema, so the message definitions below were taken from
the protobuf file descriptors embedded in the shipped `agy` binary (Google
Antigravity CLI, Linux x86-64, October 2026): `third_party/gemini_coder/proto/
trajectory.proto`, `third_party/jetski/cortex_pb/cortex.proto`,
`third_party/jetski/codeium_common_pb/codeium_common.proto` and
`third_party/jetski/jetski_cortex_pb/jetski_cortex.proto`. They were checked
against a real install. `analyzer/tools/proto_descriptors.py` re-extracts them
from a binary when a new release changes the format.

Files, relative to the home directory:

* `.gemini/antigravity-cli/conversations/<conversation id>.db`, with `-wal`
  and `-shm` sidecars (WAL mode, so the sidecars hold the newest steps):
  - `trajectory_meta(trajectory_id, cascade_id, trajectory_type, source)`:
    `cascade_id` is the conversation id; `source` 17 is the CLI.
  - `trajectory_metadata_blob(id, data)`: `exa.cortex_pb.CortexTrajectoryMetadata`
    with `workspaces[].workspace_folder_absolute_uri` and `branch_name`,
    `created_at`, `parent_conversation_id`, `project_id`.
  - `steps(idx, step_type, status, metadata, step_payload, ...)`: one row
    per step. `step_payload` is a `gemini_coder.Step` whose `metadata`
    (`exa.cortex_pb.CortexStepMetadata`) carries `created_at`,
    `completed_at`, `source` and the `tool_call` the step executed
    (`exa.codeium_common_pb.ChatToolCall`: `id`, `name`, `arguments_json`).
    The payload oneof names the step kind: `user_input.query`,
    `planner_response.response` with `thinking` and `tool_calls[]`, and one
    message per tool (`run_command`, `view_file`, `write_to_file`,
    `code_action`, `mcp_tool`, `generic`, ...).
  - `gen_metadata(idx, data)`: `exa.cortex_pb.CortexStepGeneratorMetadata`
    with `step_indices[]` and `chat_model.response_model`, the only place
    the model name is recorded.
* `.gemini/antigravity-cli/conversation_summaries.db`, table
  `conversation_summaries`: one row per conversation with `title`,
  `preview`, `step_count`, `last_modified_time`, `workspace_uris` (JSON
  array), `status`, `agent_name`, `parent_conversation_id`, `project_id`.
* `.gemini/antigravity-cli/history.jsonl`: `{display, timestamp, workspace}`
  per prompt, `timestamp` in epoch milliseconds, no conversation id.

Rows: one `user` row per user_input step (`system` when the source is
USER_IMPLICIT); for each planner_response step an `assistant` row, one
`tool_use` row per proposed tool call, and a `thinking` row with
`--include-thinking`; one `tool_result` row per executed tool step, keyed by
the planner's call id; `system` rows for the session start, checkpoints,
system messages, errors and the conversation summary. Step timestamps come
from the step metadata; tool results use `completed_at`.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Iterator, Optional
from urllib.parse import unquote, urlparse

from ..inputs import Artifact
from ..model import Row, compact
from ..protobuf import Schema, decode
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl

BASE = ".gemini/antigravity-cli/"
CONV_RX = re.compile(r"^\.gemini/antigravity-cli/conversations/[^/]+\.db$")
SUMMARIES_REL = BASE + "conversation_summaries.db"
HISTORY_REL = BASE + "history.jsonl"

# exa.cortex_pb.CortexStepType, lower-cased without the prefix.
STEP_TYPES = {
    0: "unspecified",
    1: "dummy",
    2: "finish",
    3: "plan_input",
    4: "mquery",
    5: "code_action",
    6: "git_commit",
    7: "grep_search",
    8: "view_file",
    9: "list_directory",
    10: "compile",
    13: "view_code_item",
    14: "user_input",
    15: "planner_response",
    17: "error_message",
    21: "run_command",
    23: "checkpoint",
    24: "propose_code",
    25: "find",
    27: "suggested_responses",
    28: "command_status",
    29: "memory",
    31: "read_url_content",
    32: "view_content_chunk",
    33: "search_web",
    34: "retrieve_memory",
    38: "mcp_tool",
    39: "manager_feedback",
    40: "tool_call_proposal",
    41: "tool_call_choice",
    42: "trajectory_choice",
    45: "clipboard",
    47: "view_file_outline",
    49: "post_pr_review",
    51: "list_resources",
    52: "read_resource",
    53: "lint_diff",
    54: "find_all_references",
    55: "brain_update",
    56: "open_browser_url",
    57: "run_extension_code",
    59: "proposal_feedback",
    60: "trajectory_search",
    61: "execute_browser_javascript",
    62: "list_browser_pages",
    63: "capture_browser_screenshot",
    64: "click_browser_pixel",
    65: "read_terminal",
    66: "capture_browser_console_logs",
    67: "read_browser_page",
    68: "browser_get_dom",
    73: "code_search",
    74: "browser_input",
    75: "browser_move_mouse",
    76: "browser_select_option",
    77: "browser_scroll_up",
    78: "browser_scroll_down",
    79: "browser_click_element",
    80: "browser_press_key",
    81: "task_boundary",
    82: "notify_user",
    83: "code_acknowledgement",
    84: "internal_search",
    85: "browser_subagent",
    86: "file_change",
    87: "move",
    88: "browser_scroll",
    89: "knowledge_generation",
    90: "ephemeral_message",
    91: "generate_image",
    92: "delete_directory",
    93: "compile_applet",
    94: "install_applet_dependencies",
    95: "install_applet_package",
    96: "browser_resize_window",
    97: "browser_drag_pixel_to_pixel",
    98: "conversation_history",
    99: "knowledge_artifacts",
    100: "send_command_input",
    101: "system_message",
    102: "wait",
    103: "agency_tool_call",
    104: "cider_agent_dummy",
    105: "build_cleaner",
    106: "blaze_build_targets",
    107: "blaze_test_targets",
    108: "set_up_firebase",
    109: "moma",
    110: "restart_dev_server",
    111: "deploy_firebase",
    112: "shell_exec",
    113: "browser_mouse_wheel",
    114: "lint_applet",
    116: "ki_insertion",
    117: "retrieve_content",
    118: "critique",
    119: "findings",
    120: "browser_mouse_up",
    121: "browser_mouse_down",
    122: "workspace_api",
    123: "browser_list_network_requests",
    124: "browser_get_network_request",
    125: "browser_refresh_page",
    126: "edit_notebook",
    127: "invoke_subagent",
    128: "write_blob",
    129: "read_notebook",
    130: "propose_ai_comments",
    131: "start_code_review",
    132: "generic",
    133: "set_up_cloud_sql",
    134: "execute_notebook",
    135: "cloud_sql_update_schema",
    136: "rpc_action",
    137: "cloud_sql_execute_sql",
    138: "ask_question",
    139: "directory_rules",
    140: "tool_search",
}

# exa.cortex_pb.CortexStepStatus
STEP_STATUS = {
    0: "unspecified",
    1: "pending",
    2: "running",
    3: "done",
    4: "invalid",
    5: "cleared",
    6: "canceled",
    7: "error",
    8: "generating",
    9: "waiting",
    11: "queued",
    12: "interrupted",
}

STEP_SOURCE_USER_IMPLICIT = 3   # exa.cortex_pb.CortexStepSource

# Field numbers from the embedded descriptors; only the fields the parser reads.
SCHEMA: Schema = {
    "Step": {
        1: ("type", "int"), 4: ("status", "int"), 5: ("metadata", "CortexStepMetadata"),
        10: ("code_action", "CortexStepCodeAction"), 12: ("finish", "CortexStepFinish"),
        13: ("grep_search", "CortexStepGrepSearch"), 14: ("view_file", "CortexStepViewFile"),
        15: ("list_directory", "CortexStepListDirectory"), 19: ("user_input", "CortexStepUserInput"),
        20: ("planner_response", "CortexStepPlannerResponse"), 23: ("write_to_file", "CortexStepWriteToFile"),
        24: ("error_message", "CortexStepErrorMessage"), 28: ("run_command", "CortexStepRunCommand"),
        30: ("checkpoint", "CortexStepCheckpoint"), 31: ("error", "CortexErrorDetails"),
        34: ("find", "CortexStepFind"), 37: ("command_status", "CortexStepCommandStatus"),
        38: ("memory", "CortexStepMemory"), 40: ("read_url_content", "CortexStepReadUrlContent"),
        42: ("search_web", "CortexStepSearchWeb"), 47: ("mcp_tool", "CortexStepMcpTool"),
        93: ("task_boundary", "CortexStepTaskBoundary"), 94: ("notify_user", "CortexStepNotifyUser"),
        98: ("file_change", "CortexStepFileChange"), 103: ("ephemeral_message", "CortexStepEphemeralMessage"),
        111: ("conversation_history", "CortexStepConversationHistory"),
        113: ("send_command_input", "CortexStepSendCommandInput"), 114: ("system_message", "CortexStepSystemMessage"),
        116: ("agency_tool_call", "CortexStepAgencyToolCall"), 127: ("shell_exec", "CortexStepShellExec"),
        140: ("generic", "CortexStepGeneric"), 143: ("invoke_subagent", "CortexStepInvokeSubagent"),
        154: ("ask_question", "CortexStepAskQuestion"), 156: ("directory_rules", "CortexStepDirectoryRules"),
    },
    "CortexStepMetadata": {
        1: ("created_at", "ts"), 3: ("source", "int"), 4: ("tool_call", "ChatToolCall"),
        7: ("finished_generating_at", "ts"), 8: ("completed_at", "ts"), 12: ("execution_id", "str"),
        30: ("tool_summary", "str"), 31: ("tool_action", "str"), 32: ("started_at", "ts"),
    },
    "ChatToolCall": {1: ("id", "str"), 2: ("name", "str"), 3: ("arguments_json", "str"), 9: ("original_name", "str")},
    "CortexStepUserInput": {1: ("query", "str"), 2: ("user_response", "str"), 6: ("is_queued_message", "bool")},
    "CortexStepPlannerResponse": {
        1: ("response", "str"), 3: ("thinking", "str"), 6: ("message_id", "str"),
        7: ("+tool_calls", "ChatToolCall"), 8: ("modified_response", "str"), 16: ("raw_thinking", "str"),
    },
    "CortexStepGeneric": {1: ("+args", "KV"), 2: ("result", "GenericStepResult")},
    "KV": {1: ("key", "str"), 2: ("value", "str")},
    "GenericStepResult": {1: ("result", "str"), 7: ("full_output_uri", "str")},
    "CortexStepRunCommand": {
        1: ("command", "str"), 2: ("cwd", "str"), 4: ("stdout", "str"), 5: ("stderr", "str"),
        6: ("exit_code", "int"), 14: ("user_rejected", "bool"), 21: ("combined_output", "RunCommandOutput"),
        23: ("command_line", "str"), 34: ("ran_in_sandbox", "bool"), 37: ("timed_out", "bool"),
    },
    "RunCommandOutput": {1: ("full", "str"), 2: ("truncated", "str")},
    "CortexStepCommandStatus": {1: ("command_id", "str"), 3: ("stdout", "str"), 4: ("stderr", "str"), 5: ("exit_code", "int"), 9: ("combined", "str")},
    "CortexStepShellExec": {1: ("command", "str"), 2: ("exit_code", "int"), 3: ("output", "str"), 4: ("error_message", "str")},
    "CortexStepSendCommandInput": {1: ("command_id", "str"), 2: ("input", "str"), 6: ("terminate", "bool")},
    "CortexStepViewFile": {1: ("absolute_path_uri", "str"), 2: ("start_line", "int"), 3: ("end_line", "int"), 17: ("is_skill_file", "bool")},
    "CortexStepListDirectory": {1: ("directory_path_uri", "str")},
    "CortexStepGrepSearch": {1: ("query", "str"), 10: ("command_run", "str"), 11: ("search_path_uri", "str")},
    "CortexStepFind": {1: ("pattern", "str"), 9: ("command_run", "str"), 10: ("search_directory", "str")},
    "CortexStepWriteToFile": {1: ("target_file_uri", "str"), 4: ("file_created", "bool")},
    "CortexStepFileChange": {1: ("absolute_path_uri", "str"), 2: ("file_change_type", "int"), 5: ("instruction", "str")},
    "CortexStepCodeAction": {1: ("action_spec", "ActionSpec"), 8: ("code_instruction", "str"), 26: ("description", "str")},
    "ActionSpec": {1: ("command", "ActionSpecCommand"), 2: ("create_file", "ActionSpecPath"), 4: ("delete_file", "ActionSpecPath"), 5: ("sed", "ActionSpecSed")},
    "ActionSpecCommand": {1: ("instruction", "str"), 4: ("file", "PathScopeItem")},
    "ActionSpecPath": {1: ("instruction", "str"), 2: ("path", "PathScopeItem")},
    "ActionSpecSed": {3: ("path", "PathScopeItem")},
    "PathScopeItem": {1: ("absolute_path_migrate_me_to_uri", "str"), 5: ("absolute_uri", "str")},
    "CortexStepReadUrlContent": {1: ("url", "str"), 3: ("resolved_url", "str")},
    "CortexStepSearchWeb": {1: ("query", "str"), 5: ("summary", "str")},
    "CortexStepMcpTool": {1: ("server_name", "str"), 2: ("tool_call", "ChatToolCall"), 3: ("result_string", "str"), 7: ("user_rejected", "bool")},
    "CortexStepAgencyToolCall": {1: ("agent_name", "str"), 2: ("function_name", "str")},
    "CortexStepInvokeSubagent": {1: ("subagent_name", "str"), 2: ("prompt", "str"), 5: ("conversation_id", "str"), 10: ("+results", "SubagentResult")},
    "SubagentResult": {1: ("conversation_id", "str")},
    "CortexStepAskQuestion": {1: ("+questions", "AskQuestionEntry")},
    "AskQuestionEntry": {1: ("question", "str"), 4: ("+selected_option_ids", "str"), 5: ("write_in_response", "str"), 6: ("skipped", "bool")},
    "CortexStepCheckpoint": {4: ("user_intent", "str"), 5: ("session_summary", "str"), 10: ("conversation_title", "str")},
    "CortexStepMemory": {1: ("memory_id", "str"), 3: ("action", "int")},
    "CortexStepFinish": {2: ("output_string", "str")},
    "CortexStepErrorMessage": {3: ("error", "CortexErrorDetails")},
    "CortexErrorDetails": {1: ("user_error_message", "str"), 2: ("short_error", "str"), 3: ("full_error", "str")},
    "CortexStepSystemMessage": {1: ("message", "str"), 3: ("event_type", "str")},
    "CortexStepEphemeralMessage": {1: ("content", "str")},
    "CortexStepTaskBoundary": {1: ("task_name", "str"), 2: ("task_status", "str"), 3: ("task_summary", "str")},
    "CortexStepNotifyUser": {2: ("notification_content", "str")},
    "CortexStepDirectoryRules": {2: ("+rule_file_uris", "str")},
    "CortexStepConversationHistory": {1: ("content", "str")},
    "CortexTrajectoryMetadata": {
        1: ("+workspaces", "CortexWorkspaceMetadata"), 2: ("created_at", "ts"), 5: ("parent_conversation_id", "str"),
        6: ("root_conversation_id", "str"), 7: ("+workspace_uris", "str"), 17: ("nesting_depth", "int"), 18: ("project_id", "str"),
    },
    "CortexWorkspaceMetadata": {1: ("workspace_folder_absolute_uri", "str"), 2: ("git_root_absolute_uri", "str"), 4: ("branch_name", "str")},
    "CortexStepGeneratorMetadata": {1: ("chat_model", "ChatModelMetadata"), 2: ("+step_indices", "int")},
    "ChatModelMetadata": {19: ("response_model", "str"), 21: ("model_display_name", "str"), 22: ("response_model_full", "str")},
}

PAYLOAD_KINDS = [name for num, (name, kind) in SCHEMA["Step"].items() if kind not in ("int", "CortexStepMetadata")]

# Which JSON argument best identifies a proposed tool call, tried in order.
ARG_KEYS = ("CommandLine", "Command", "AbsolutePath", "TargetFile", "AbsolutePathUri", "Path", "DirectoryPath",
            "Url", "Query", "SearchPath", "Pattern", "Prompt", "Instruction", "TaskName", "Name")


def uri_to_path(uri: str) -> str:
    if not uri:
        return ""
    if not uri.startswith("file:"):
        return uri
    p = unquote(urlparse(uri).path)
    if re.match(r"^/[A-Za-z]:", p):
        p = p[1:]
    return p


def tool_args_summary(arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except ValueError:
        return arguments_json
    if isinstance(args, dict):
        for k in ARG_KEYS:
            v = args.get(k)
            if v not in (None, "", [], {}):
                return v if isinstance(v, str) else compact_json(v)
    return compact_json(args)


def _path_of(scope: Optional[dict]) -> str:
    if not scope:
        return ""
    return uri_to_path(scope.get("absolute_uri") or scope.get("absolute_path_migrate_me_to_uri") or "")


def _output(p: dict) -> str:
    combined = p.get("combined_output") or {}
    return (combined.get("full") or combined.get("truncated") or p.get("combined")
            or p.get("stdout") or p.get("stderr") or p.get("output") or "")


def _join(*parts: str) -> str:
    return " | ".join(x for x in parts if x)


def describe_payload(kind: str, p: dict) -> str:
    """One line describing a tool step's result or a system event."""
    if kind == "run_command":
        return _join(p.get("command_line") or p.get("command") or "",
                     "[rejected by user]" if p.get("user_rejected") else "",
                     "[timed out]" if p.get("timed_out") else "",
                     "exit=%s" % p["exit_code"] if "exit_code" in p else "", _output(p))
    if kind in ("command_status", "shell_exec"):
        return _join(p.get("command", ""), "exit=%s" % p["exit_code"] if "exit_code" in p else "",
                     _output(p) or p.get("error_message", ""))
    if kind == "send_command_input":
        return "input to %s: %s%s" % (p.get("command_id", ""), p.get("input", ""), " [terminate]" if p.get("terminate") else "")
    if kind == "view_file":
        rng = ""
        if p.get("start_line") or p.get("end_line"):
            rng = ":%s-%s" % (p.get("start_line", ""), p.get("end_line", ""))
        return uri_to_path(p.get("absolute_path_uri", "")) + rng
    if kind == "list_directory":
        return uri_to_path(p.get("directory_path_uri", ""))
    if kind == "grep_search":
        return _join(p.get("query", ""), uri_to_path(p.get("search_path_uri", "")), p.get("command_run", ""))
    if kind == "find":
        return _join(p.get("pattern", ""), p.get("search_directory", ""), p.get("command_run", ""))
    if kind == "write_to_file":
        return uri_to_path(p.get("target_file_uri", "")) + (" [created]" if p.get("file_created") else "")
    if kind == "file_change":
        return _join(uri_to_path(p.get("absolute_path_uri", "")), p.get("instruction", ""))
    if kind == "code_action":
        spec = p.get("action_spec") or {}
        kindname = path = ""
        for key in ("command", "create_file", "delete_file", "sed"):
            sub = spec.get(key)
            if sub:
                kindname, path = key, _path_of(sub.get("file") or sub.get("path"))
                break
        return _join(kindname, path, p.get("description") or p.get("code_instruction", ""))
    if kind == "read_url_content":
        return p.get("resolved_url") or p.get("url", "")
    if kind == "search_web":
        return p.get("query", "")
    if kind == "mcp_tool":
        tc = p.get("tool_call") or {}
        return _join("%s/%s" % (p.get("server_name", ""), tc.get("name", "")),
                     "[rejected by user]" if p.get("user_rejected") else "", p.get("result_string", ""))
    if kind == "agency_tool_call":
        return "%s.%s" % (p.get("agent_name", ""), p.get("function_name", ""))
    if kind == "invoke_subagent":
        children = " ".join(r.get("conversation_id", "") for r in p.get("results", []) if r.get("conversation_id"))
        return _join(p.get("subagent_name", ""), p.get("prompt", ""), "children: " + children if children else "")
    if kind == "ask_question":
        qs = []
        for q in p.get("questions", []):
            ans = q.get("write_in_response") or " ".join(q.get("selected_option_ids", [])) or ("skipped" if q.get("skipped") else "")
            qs.append(q.get("question", "") + (" -> " + ans if ans else ""))
        return "; ".join(qs)
    if kind == "generic":
        return (p.get("result") or {}).get("result", "")
    if kind == "checkpoint":
        return "checkpoint: " + (p.get("conversation_title") or p.get("session_summary") or p.get("user_intent", ""))
    if kind == "system_message":
        return "%s: %s" % (p.get("event_type") or "system_message", p.get("message", ""))
    if kind == "ephemeral_message":
        return "ephemeral: " + p.get("content", "")
    if kind == "task_boundary":
        return "task %s [%s]: %s" % (p.get("task_name", ""), p.get("task_status", ""), p.get("task_summary", ""))
    if kind == "notify_user":
        return "notify user: " + p.get("notification_content", "")
    if kind in ("error", "error_message"):
        e = p.get("error", {}) if kind == "error_message" else p
        return "error: " + (e.get("short_error") or e.get("user_error_message") or e.get("full_error", ""))
    if kind == "finish":
        return "finish: " + p.get("output_string", "")
    if kind == "memory":
        return "memory %s action=%s" % (p.get("memory_id", ""), p.get("action", ""))
    if kind == "directory_rules":
        return "directory rules: " + " ".join(uri_to_path(u) for u in p.get("rule_file_uris", []))
    if kind == "conversation_history":
        return "conversation history injected (%d chars)" % len(p.get("content", ""))
    return compact_json(p)


class AntigravityParser(Parser):
    agent = "antigravity"
    name = "antigravity"

    def wants(self, artifact: Artifact) -> bool:
        return artifact.rel in (SUMMARIES_REL, HISTORY_REL) or bool(CONV_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == HISTORY_REL:
            yield from self._parse_history(artifact, opts)
        elif artifact.rel == SUMMARIES_REL:
            yield from self._parse_summaries(artifact, opts)
        else:
            yield from self._parse_conversation(artifact, opts)

    # -- history.jsonl ------------------------------------------------------------
    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("timestamp"))
            row.project_path = uri_to_path(str(rec.get("workspace") or ""))
            row.turn_type = "user"
            row.summary = compact(rec.get("display"), opts.summary_length)
            yield row

    # -- conversation_summaries.db ----------------------------------------------
    def _parse_summaries(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            return
        with open_copy(artifact.disk_path) as con:
            if "conversation_summaries" not in table_names(con):
                return
            for n, r in enumerate(con.execute("select * from conversation_summaries order by last_modified_time"), 1):
                r = dict(r)
                row = self.base_row(artifact)
                row.source_line = n
                row.session_id = str(r.get("conversation_id") or "")
                row.timestamp_utc = to_utc(r.get("last_modified_time"))
                try:
                    uris = json.loads(r.get("workspace_uris") or "[]")
                except ValueError:
                    uris = []
                row.project_path = uri_to_path(uris[0]) if uris else ""
                row.turn_type = "system"
                row.summary = compact(_join(
                    "conversation summary", r.get("title") or r.get("preview") or "",
                    str(r.get("status") or ""), "%s steps" % r.get("step_count", 0),
                    "agent=%s" % r["agent_name"] if r.get("agent_name") else "",
                    "parent=%s" % r["parent_conversation_id"] if r.get("parent_conversation_id") else "",
                ), opts.summary_length)
                yield row

    # -- conversations/<id>.db -----------------------------------------------------
    def _parse_conversation(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            return
        with open_copy(artifact.disk_path) as con:
            tables = table_names(con)
            if "steps" not in tables:
                return
            session_id = artifact.disk_path.name[:-3]
            project_path = branch = source = ""
            if "trajectory_meta" in tables:
                tm = con.execute("select * from trajectory_meta limit 1").fetchone()
                if tm:
                    session_id = tm["cascade_id"] or session_id
                    source = str(tm["source"])
            if "trajectory_metadata_blob" in tables:
                blob = con.execute("select data from trajectory_metadata_blob limit 1").fetchone()
                if blob and blob[0]:
                    try:
                        meta = decode(blob[0], "CortexTrajectoryMetadata", SCHEMA)
                    except ValueError:
                        meta = {}
                    ws = (meta.get("workspaces") or [{}])[0]
                    project_path = uri_to_path(ws.get("workspace_folder_absolute_uri") or (meta.get("workspace_uris") or [""])[0])
                    branch = ws.get("branch_name", "")
                    if meta.get("created_at"):
                        row = self._row(artifact, 0, session_id, project_path, branch)
                        row.timestamp_utc = meta["created_at"]
                        row.turn_type = "system"
                        row.summary = compact(_join(
                            "session start", "source=%s" % source if source else "",
                            "project_id=%s" % meta["project_id"] if meta.get("project_id") else "",
                            "parent=%s" % meta["parent_conversation_id"] if meta.get("parent_conversation_id") else "",
                        ), opts.summary_length)
                        yield row
            models: Dict[int, str] = {}
            if "gen_metadata" in tables:
                for (data,) in con.execute("select data from gen_metadata"):
                    try:
                        gm = decode(data or b"", "CortexStepGeneratorMetadata", SCHEMA)
                    except ValueError:
                        continue
                    cm = gm.get("chat_model") or {}
                    model = cm.get("response_model") or cm.get("model_display_name") or ""
                    for idx in gm.get("step_indices", []):
                        models[idx] = model
            bad = 0
            for srow in con.execute("select idx, step_type, status, metadata, step_payload from steps order by idx"):
                idx = srow["idx"]
                try:
                    step = decode(srow["step_payload"], "Step", SCHEMA) if srow["step_payload"] else {}
                    if "metadata" not in step and srow["metadata"]:
                        step["metadata"] = decode(srow["metadata"], "CortexStepMetadata", SCHEMA)
                except ValueError:
                    bad += 1
                    continue
                yield from self._step_rows(artifact, idx, srow["step_type"], srow["status"], step,
                                           session_id, project_path, branch, models.get(idx, ""), opts)
            if bad:
                row = self._row(artifact, 0, session_id, project_path, branch)
                row.turn_type = "system"
                row.summary = "parser: %d step(s) could not be decoded" % bad
                yield row

    def _row(self, artifact: Artifact, idx: int, session_id: str, project_path: str, branch: str) -> Row:
        row = self.base_row(artifact)
        row.source_line = idx
        row.session_id = session_id
        row.project_path = project_path
        row.git_branch = branch
        return row

    def _step_rows(self, artifact: Artifact, idx: int, step_type: int, status: int, step: dict,
                   session_id: str, project_path: str, branch: str, model: str, opts: Options) -> Iterator[Row]:
        md = step.get("metadata") or {}
        created = md.get("created_at", "")
        completed = md.get("completed_at") or md.get("finished_generating_at") or created
        kind = next((k for k in PAYLOAD_KINDS if k in step), "")
        payload = step.get(kind) or {}
        status_name = STEP_STATUS.get(status, str(status))
        type_name = STEP_TYPES.get(step_type, str(step_type))

        def base(ts: str) -> Row:
            row = self._row(artifact, idx, session_id, project_path, branch)
            row.timestamp_utc = ts
            row.model = model
            return row

        if kind == "user_input":
            row = base(created)
            row.turn_type = "system" if md.get("source") == STEP_SOURCE_USER_IMPLICIT else "user"
            text = payload.get("query") or payload.get("user_response") or ""
            if payload.get("is_queued_message"):
                text = "[queued] " + text
            row.summary = compact(text, opts.summary_length)
            yield row
            return

        if kind == "planner_response":
            thinking = payload.get("raw_thinking") or payload.get("thinking")
            if thinking and opts.include_thinking:
                row = base(created)
                row.turn_type = "thinking"
                row.summary = compact(thinking, opts.summary_length)
                yield row
            text = payload.get("modified_response") or payload.get("response")
            if text:
                row = base(completed)
                row.turn_type = "assistant"
                row.summary = compact(text, opts.summary_length)
                yield row
            for tc in payload.get("tool_calls", []):
                row = base(completed)
                row.turn_type = "tool_use"
                row.tool_name = tc.get("name") or tc.get("original_name", "")
                row.tool_use_id = tc.get("id", "")
                row.summary = compact(tool_args_summary(tc.get("arguments_json", "")), opts.summary_length)
                yield row
            return

        tc = md.get("tool_call")
        text = describe_payload(kind, payload) if kind else "step %s" % type_name
        if status_name != "done":
            text = "[%s] %s" % (status_name, text)
        if tc:
            row = base(completed)
            row.turn_type = "tool_result"
            row.tool_name = tc.get("name") or tc.get("original_name", "")
            row.tool_use_id = tc.get("id", "")
        else:
            row = base(created)
            row.turn_type = "system"
        row.summary = compact(text, opts.summary_length)
        yield row
