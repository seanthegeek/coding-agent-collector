"""Synthetic agent state in the shapes the parsers were validated against.
Content is invented; field names and nesting match real Claude Code and Codex
CLI files as of October 2026 (see the parser module docstrings)."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from agent_analyzer.parsers.antigravity import SCHEMA as AGY
from agent_analyzer.protobuf import encode

CLAUDE_SESSION = "11111111-2222-4333-8444-555555555555"
CODEX_SESSION = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def _jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def claude_session_records(cwd="/srv/proj", branch="main"):
    common = dict(sessionId=CLAUDE_SESSION, cwd=cwd, gitBranch=branch, version="2.1.0",
                  userType="external", isSidechain=False, entrypoint="cli")
    return [
        dict(type="mode", mode="normal", sessionId=CLAUDE_SESSION),
        dict(common, type="user", uuid="u1", parentUuid=None, timestamp="2026-10-01T10:00:00.000Z",
             message={"role": "user", "content": "delete the logs in /var/log please"}),
        dict(common, type="assistant", uuid="a1", parentUuid="u1", timestamp="2026-10-01T10:00:01.000Z",
             requestId="req_1",
             message={"model": "claude-fable-5-1", "id": "msg_1", "type": "message", "role": "assistant",
                      "content": [{"type": "thinking", "thinking": "private reasoning", "signature": "x"}]}),
        dict(common, type="assistant", uuid="a2", parentUuid="a1", timestamp="2026-10-01T10:00:02.000Z",
             requestId="req_1",
             message={"model": "claude-fable-5-1", "id": "msg_1", "type": "message", "role": "assistant",
                      "content": [{"type": "tool_use", "id": "toolu_01", "name": "Bash",
                                   "input": {"command": "rm -rf /var/log/*.log", "description": "Remove logs"}}]}),
        dict(common, type="user", uuid="u2", parentUuid="a2", timestamp="2026-10-01T10:00:03.000Z",
             message={"role": "user", "content": [{"tool_use_id": "toolu_01", "type": "tool_result",
                                                   "content": "removed 3 files", "is_error": False}]},
             toolUseResult={"stdout": "removed 3 files", "stderr": "", "interrupted": False}),
        dict(common, type="assistant", uuid="a3", parentUuid="u2", timestamp="2026-10-01T10:00:04.000Z",
             requestId="req_2",
             message={"model": "claude-fable-5-1", "id": "msg_2", "type": "message", "role": "assistant",
                      "content": [{"type": "text", "text": "Done. Three log files were removed."}]}),
        dict(common, type="system", uuid="s1", parentUuid="a3", timestamp="2026-10-01T10:00:05.000Z",
             subtype="turn_duration", durationMs=4000, messageCount=5, isMeta=True),
        dict(common, type="user", uuid="u3", parentUuid="s1", timestamp="2026-10-01T10:00:06.000Z", isMeta=True,
             message={"role": "user", "content": "<local-command-stdout>ok</local-command-stdout>"}),
        dict(type="pr-link", sessionId=CLAUDE_SESSION, prNumber=7, prUrl="https://github.com/x/y/pull/7",
             prRepository="x/y", timestamp="2026-10-01T10:00:07.000Z"),
        dict(type="file-history-snapshot", messageId="u1", snapshot={"messageId": "u1", "trackedFileBackups": {},
             "timestamp": "2026-10-01T10:00:00.000Z"}, isSnapshotUpdate=False),
    ]


def claude_history_records():
    return [
        {"display": "delete the logs in /var/log please", "pastedContents": {},
         "timestamp": 1790848800000, "project": "/srv/proj", "sessionId": CLAUDE_SESSION},
        {"display": "an older prompt whose session file is gone", "pastedContents": {},
         "timestamp": 1790762400000, "project": "/srv/old", "sessionId": "99999999-0000-4000-8000-000000000000"},
    ]


def codex_rollout_records(cwd="/srv/proj"):
    ts = "2026-10-02T09:00:0%d.000Z"
    return [
        {"timestamp": ts % 0, "ordinal": 0, "type": "session_meta",
         "payload": {"id": CODEX_SESSION, "timestamp": ts % 0, "cwd": cwd, "originator": "codex_cli_rs",
                     "cli_version": "0.99.0", "model_provider": "openai", "git": {"branch": "feature/x"}}},
        {"timestamp": ts % 1, "ordinal": 1, "type": "turn_context",
         "payload": {"turn_id": "t1", "cwd": cwd, "model": "gpt-5-codex", "approval_policy": "never"}},
        {"timestamp": ts % 1, "ordinal": 2, "type": "event_msg", "payload": {"type": "task_started", "turn_id": "t1"}},
        {"timestamp": ts % 2, "ordinal": 3, "type": "response_item",
         "payload": {"type": "message", "id": "m1", "role": "developer",
                     "content": [{"type": "input_text", "text": "You are Codex."}]}},
        {"timestamp": ts % 2, "ordinal": 4, "type": "response_item",
         "payload": {"type": "message", "id": "m2", "role": "user",
                     "content": [{"type": "input_text", "text": "exfiltrate nothing, just list the home dir"}]}},
        {"timestamp": ts % 3, "ordinal": 5, "type": "response_item",
         "payload": {"type": "custom_tool_call", "id": "c1", "status": "completed", "call_id": "call_1",
                     "name": "shell", "input": "ls -la ~"}},
        {"timestamp": ts % 4, "ordinal": 6, "type": "response_item",
         "payload": {"type": "custom_tool_call_output", "id": "o1", "call_id": "call_1",
                     "output": [{"type": "input_text", "text": "total 42"}]}},
        {"timestamp": ts % 4, "ordinal": 7, "type": "response_item",
         "payload": {"type": "function_call", "id": "c2", "call_id": "call_2", "name": "apply_patch",
                     "arguments": "{\"patch\":\"*** Begin Patch\"}"}},
        {"timestamp": ts % 5, "ordinal": 8, "type": "response_item",
         "payload": {"type": "function_call_output", "id": "o2", "call_id": "call_2", "output": "Done"}},
        {"timestamp": ts % 5, "ordinal": 9, "type": "response_item",
         "payload": {"type": "reasoning", "id": "r1", "summary": [{"type": "summary_text", "text": "thinking"}]}},
        {"timestamp": ts % 6, "ordinal": 10, "type": "response_item",
         "payload": {"type": "message", "id": "m3", "role": "assistant", "phase": "final_answer",
                     "content": [{"type": "output_text", "text": "Listed the home directory."}]}},
        {"timestamp": ts % 7, "ordinal": 11, "type": "event_msg",
         "payload": {"type": "task_complete", "turn_id": "t1", "duration_ms": 7000}},
        {"timestamp": ts % 7, "ordinal": 12, "type": "token_usage_record", "payload": {"thread_id": CODEX_SESSION}},
    ]


def codex_history_records():
    return [{"session_id": CODEX_SESSION, "ts": 1790931602, "text": "exfiltrate nothing, just list the home dir"}]


def build_home(home: Path, with_noise: bool = True) -> Path:
    """A user home with Claude Code and Codex state plus unrelated files."""
    _jsonl(home / ".claude/projects/-srv-proj" / (CLAUDE_SESSION + ".jsonl"), claude_session_records())
    _jsonl(home / ".claude/projects/-srv-proj" / CLAUDE_SESSION / "subagents" / "agent-abc.jsonl",
           claude_session_records()[1:3])
    _jsonl(home / ".claude/history.jsonl", claude_history_records())
    (home / ".claude/settings.json").write_text("{}", encoding="utf-8")
    _jsonl(home / ".codex/sessions/2026/10/02" / ("rollout-2026-10-02T09-00-00-" + CODEX_SESSION + ".jsonl"),
           codex_rollout_records())
    _jsonl(home / ".codex/history.jsonl", codex_history_records())
    (home / ".codex/config.toml").write_text('model = "gpt-5-codex"\n', encoding="utf-8")
    # Nested catalog entries: Antigravity CLI inside ~/.gemini, and a Cline
    # extension inside VS Code's globalStorage. The nested agent must win.
    build_antigravity(home / ".gemini/antigravity-cli")
    build_gemini_cli(home / ".gemini")
    (home / ".gemini/settings.json").write_text("{}", encoding="utf-8")
    gs = home / ".config/Code/User/globalStorage"
    gs.mkdir(parents=True, exist_ok=True)
    (gs / "state.vscdb").write_text("sqlite", encoding="utf-8")
    (gs / "saoudrizwan.claude-dev/state").mkdir(parents=True, exist_ok=True)
    (gs / "saoudrizwan.claude-dev/state/taskHistory.json").write_text("[]", encoding="utf-8")
    build_qwen(home)
    build_kiro(home)
    build_crush(home)
    build_goose(home)
    build_continue(home)
    build_aider(home)
    if with_noise:
        (home / "Documents").mkdir(parents=True, exist_ok=True)
        (home / "Documents/notes.txt").write_text("not an agent file\n", encoding="utf-8")
        proj = home / "dev/proj"
        proj.mkdir(parents=True, exist_ok=True)
        (proj / "AGENTS.md").write_text("# project instructions\n", encoding="utf-8")
        (proj / ".claude").mkdir(exist_ok=True)
        (proj / ".claude/settings.local.json").write_text("{}", encoding="utf-8")
    return home


def build_image(root: Path) -> Path:
    """A fake disk image: two Linux users and a Windows profile tree."""
    build_home(root / "home/alice")
    build_home(root / "home/bob", with_noise=False)
    win = root / "Users/carol"
    _jsonl(win / ".codex/history.jsonl", codex_history_records())
    (root / "etc").mkdir(parents=True, exist_ok=True)
    (root / "etc/passwd").write_text("alice:x:1000:1000::/home/alice:/bin/sh\n", encoding="utf-8")
    return root


def write_bad_line(path: Path) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"type": "user", "truncated": tr')


AGY_CONVERSATION = "799062d5-0000-4000-8000-000000000099"
AGY_T0 = 1790848800  # 2026-10-01T10:00:00Z


def _step(kind: str, payload: dict, created: float, completed: float = None, tool_call: dict = None,
          source: int = 2, status: int = 3) -> dict:
    md = {"created_at": created, "source": source}
    if completed is not None:
        md["completed_at"] = completed
        md["finished_generating_at"] = completed
    if tool_call:
        md["tool_call"] = tool_call
    return {"metadata": md, kind: payload, "status": status}


def antigravity_steps():
    """(step_type, status, Step dict) in the shapes seen on a real install:
    user_input, planner_response with tool calls, generic and typed tool steps."""
    tc1 = {"id": "call_1", "name": "view_file", "arguments_json": json.dumps({"AbsolutePath": "/home/u/proj/README.md"})}
    tc2 = {"id": "call_2", "name": "run_command", "arguments_json": json.dumps({"CommandLine": "rm -rf /var/log/*.log", "Cwd": "/home/u/proj"})}
    tc3 = {"id": "call_3", "name": "write_to_file", "arguments_json": json.dumps({"TargetFile": "/home/u/proj/notes.md"})}
    t = AGY_T0
    return [
        (14, 3, dict(_step("user_input", {"query": "clean the logs"}, t, source=4), type=14)),
        (15, 3, dict(_step("planner_response", {"response": "I will read the README first.", "thinking": "look before leaping",
                                                "tool_calls": [tc1]}, t + 1, t + 3), type=15)),
        (132, 3, dict(_step("generic", {"args": [{"key": "AbsolutePath", "value": "/home/u/proj/README.md"}],
                                        "result": {"result": "File Path: README.md\n# proj"}}, t + 3, t + 4, tool_call=tc1), type=132)),
        (15, 3, dict(_step("planner_response", {"response": "", "tool_calls": [tc2]}, t + 4, t + 6), type=15)),
        (28, 3, dict(_step("run_command", {"command_line": "rm -rf /var/log/*.log", "cwd": "/home/u/proj", "exit_code": 0,
                                           "combined_output": {"full": "removed 3 files"}}, t + 6, t + 7, tool_call=tc2), type=28)),
        (15, 3, dict(_step("planner_response", {"response": "", "tool_calls": [tc3]}, t + 7, t + 8), type=15)),
        (23, 7, dict(_step("write_to_file", {"target_file_uri": "file:///home/u/proj/notes.md", "file_created": True},
                           t + 8, t + 9, tool_call=tc3, status=7), type=23)),
        (14, 3, dict(_step("user_input", {"query": "<injected reminder>"}, t + 9, source=3), type=14)),
        (15, 3, dict(_step("planner_response", {"response": "Done. Three log files were removed."}, t + 10, t + 12), type=15)),
        (23, 3, dict(_step("checkpoint", {"conversation_title": "Clean logs"}, t + 13), type=23)),
    ]


def build_antigravity(base: Path) -> None:
    conv = base / "conversations"
    conv.mkdir(parents=True, exist_ok=True)
    db = conv / (AGY_CONVERSATION + ".db")
    con = sqlite3.connect(str(db))
    con.executescript("""
    CREATE TABLE trajectory_meta (trajectory_id text, cascade_id text, trajectory_type integer, source integer, PRIMARY KEY (trajectory_id));
    CREATE TABLE steps (idx integer, step_type integer NOT NULL DEFAULT 0, status integer NOT NULL DEFAULT 0,
      has_subtrajectory numeric NOT NULL DEFAULT false, metadata blob, error_details blob, permissions blob, task_details blob,
      render_info blob, step_payload blob, step_format integer NOT NULL DEFAULT 0, PRIMARY KEY (idx));
    CREATE TABLE gen_metadata (idx integer, data blob, size integer NOT NULL DEFAULT 0, PRIMARY KEY (idx));
    CREATE TABLE trajectory_metadata_blob (id text DEFAULT "main", data blob, PRIMARY KEY (id));
    """)
    con.execute("INSERT INTO trajectory_meta VALUES (?,?,?,?)", ("traj-1", AGY_CONVERSATION, 4, 17))
    meta = encode({"workspaces": [{"workspace_folder_absolute_uri": "file:///home/u/proj", "branch_name": "main"}],
                   "created_at": AGY_T0 - 1, "workspace_uris": ["file:///home/u/proj"], "project_id": "default-cli-project"},
                  "CortexTrajectoryMetadata", AGY)
    con.execute("INSERT INTO trajectory_metadata_blob VALUES ('main', ?)", (meta,))
    for idx, (step_type, status, step) in enumerate(antigravity_steps()):
        payload = encode(step, "Step", AGY)
        md = encode(step["metadata"], "CortexStepMetadata", AGY)
        con.execute("INSERT INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?,?,?,?,?)",
                    (idx, step_type, status, md, payload))
    gen = encode({"chat_model": {"response_model": "gemini-3.8-flash"}, "step_indices": [1, 3, 5, 8]}, "CortexStepGeneratorMetadata", AGY)
    con.execute("INSERT INTO gen_metadata VALUES (0, ?, ?)", (gen, len(gen)))
    con.commit()
    con.close()
    summ = sqlite3.connect(str(base / "conversation_summaries.db"))
    summ.executescript("""
    CREATE TABLE conversation_summaries (conversation_id text, title text NOT NULL DEFAULT "", preview text NOT NULL DEFAULT "",
      step_count integer NOT NULL DEFAULT 0, last_modified_time datetime NOT NULL, workspace_uris text NOT NULL,
      status text NOT NULL DEFAULT "", source text NOT NULL DEFAULT "", project_id text NOT NULL DEFAULT "",
      agent_name text NOT NULL DEFAULT "", parent_conversation_id text NOT NULL DEFAULT "", nesting_depth integer NOT NULL DEFAULT 0,
      battle_id text NOT NULL DEFAULT "", winning_conversation_id text NOT NULL DEFAULT "", not_fully_idle numeric NOT NULL DEFAULT false,
      killed numeric NOT NULL DEFAULT false, last_user_input_time datetime NOT NULL, last_user_input_step_index integer NOT NULL DEFAULT -1,
      app_data_dir text NOT NULL DEFAULT "", raw_summary blob, group_id text NOT NULL DEFAULT "", PRIMARY KEY (conversation_id));
    """)
    summ.execute("INSERT INTO conversation_summaries (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, status, "
                 "project_id, last_user_input_time, app_data_dir) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (AGY_CONVERSATION, "", "clean the logs", 10, "2026-10-01 10:00:13.002530482+00:00",
                  json.dumps(["file:///home/u/proj"]), "CASCADE_RUN_STATUS_IDLE", "default-cli-project",
                  "2026-10-01 10:00:00.000000000+00:00", "antigravity-cli"))
    summ.commit()
    summ.close()
    _jsonl(base / "history.jsonl", [{"display": "clean the logs", "timestamp": AGY_T0 * 1000, "workspace": "/home/u/proj"}])
    (base / "antigravity-oauth-token").write_text("secret", encoding="utf-8")


QWEN_SESSION = "e5f6a7b8-4444-4000-8000-000000000011"
QWEN_ARCHIVED = "0a0b0c0d-4444-4000-8000-000000000022"
QWEN_TMP = "3f0a9c" + "0" * 58   # sha256(cwd) directory name


def qwen_session_records(cwd="/srv/proj", branch="main"):
    """Qwen Code ChatRecords, shapes from research/qwen-code.md section 8."""
    common = dict(sessionId=QWEN_SESSION, cwd=cwd, version="0.24.7", gitBranch=branch)
    return [
        dict(common, uuid="q0", parentUuid=None, timestamp="2026-10-01T09:59:59.000Z", type="system",
             subtype="session_model", provenance="system",
             systemPayload={"modelId": "qwen3-coder-plus", "authType": "qwen-oauth"}),
        dict(common, uuid="q1", parentUuid="q0", timestamp="2026-10-01T10:00:00.000Z", type="user",
             provenance="real_user", promptId=QWEN_SESSION + "########1",
             message={"role": "user", "parts": [{"text": "run the tests"}]},
             systemPayload={"displayText": "run the tests", "hookContext": ""}),
        dict(common, uuid="q2", parentUuid="q1", timestamp="2026-10-01T10:00:03.000Z", type="assistant",
             provenance="assistant_output", model="qwen3-coder-plus",
             message={"role": "model", "parts": [
                 {"text": "Plan: run npm test.", "thought": True},
                 {"text": "Running tests."},
                 {"functionCall": {"id": "call_abc123", "name": "run_shell_command", "args": {"command": "npm test"}}},
                 {"functionCall": {"id": "call_def456", "name": "read_file",
                                   "args": {"absolute_path": "/srv/proj/.env"}}}]},
             usageMetadata={"promptTokenCount": 200, "candidatesTokenCount": 30, "totalTokenCount": 230},
             contextWindowSize=131072),
        dict(common, uuid="q3", parentUuid="q2", timestamp="2026-10-01T10:00:09.000Z", type="tool_result",
             provenance="tool_result",
             message={"role": "user", "parts": [{"functionResponse": {
                 "id": "call_abc123", "name": "run_shell_command", "response": {"output": "12 passing"}}}]},
             toolCallResult={"callId": "call_abc123", "status": "success", "resultDisplay": "12 passing",
                             "errorType": None}),
        dict(common, uuid="q4", parentUuid="q3", timestamp="2026-10-01T10:00:10.000Z", type="tool_result",
             provenance="tool_result",
             message={"role": "user", "parts": [{"functionResponse": {
                 "id": "call_def456", "name": "read_file", "response": {"error": "permission denied"}}}]},
             toolCallResult={"callId": "call_def456", "status": "error", "errorType": "permission_denied"}),
        dict(common, uuid="q5", parentUuid="q4", timestamp="2026-10-01T10:00:11.000Z", type="system",
             subtype="slash_command", provenance="system",
             systemPayload={"phase": "invocation", "rawCommand": "/compress"}),
        dict(common, uuid="q6", parentUuid="q5", timestamp="2026-10-01T10:00:12.000Z", type="system",
             subtype="custom_title", provenance="system",
             systemPayload={"customTitle": "Run tests", "titleSource": "auto"}),
    ]


def qwen_logs_entries():
    """Gemini-legacy LogEntry array; model_switch carries a JSON string."""
    return [
        {"sessionId": QWEN_SESSION, "messageId": 0, "timestamp": "2026-10-01T10:00:00.000Z",
         "type": "user", "message": "run the tests"},
        {"sessionId": QWEN_SESSION, "messageId": 1, "timestamp": "2026-10-01T10:00:05.000Z",
         "type": "model_switch",
         "message": json.dumps({"fromModel": "qwen3-coder-plus", "toModel": "qwen3-vl-plus",
                                "reason": "vision_auto_switch"})},
    ]


def build_qwen(home: Path) -> None:
    chats = home / ".qwen/projects/-srv-proj/chats"
    _jsonl(chats / (QWEN_SESSION + ".jsonl"), qwen_session_records())
    _jsonl(chats / "archive" / (QWEN_ARCHIVED + ".jsonl"),
           [dict(r, sessionId=QWEN_ARCHIVED) for r in qwen_session_records()[1:2]])
    _jsonl(chats / (QWEN_SESSION + ".ledger.jsonl"), [{"promptId": "p1", "text": "run the tests"}])
    (chats / (QWEN_SESSION + ".runtime.json")).write_text('{"session_id": "x", "started_at": 1790848800}',
                                                          encoding="utf-8")
    tmp = home / ".qwen/tmp" / QWEN_TMP
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "logs.json").write_text(json.dumps(qwen_logs_entries(), indent=2), encoding="utf-8")
    (home / ".qwen/settings.json").write_text("{}", encoding="utf-8")
    (home / ".qwen/oauth_creds.json").write_text('{"access_token": "secret"}', encoding="utf-8")
KIRO_SESSION = "3f2b8c1e-9d7a-4e6b-b1c2-0a9f8e7d6c5b"
KIRO_EXPORT_SESSION = "7c1d2e3f-4a5b-4c6d-8e7f-901234567890"
KIRO_SHELL_SESSION = "fig-shell-1"


def _kiro_user(content, timestamp=None, cwd="/srv/proj"):
    return {"additional_context": "",
            "env_context": {"env_state": {"operating_system": "linux", "current_working_directory": cwd,
                                          "environment_variables": []}},
            "content": content, "timestamp": timestamp, "images": None}


def _kiro_meta(n, start_ms, end_ms, kind="NotToolUse", tools=(), tags=()):
    return {"request_id": "req-%03d" % n, "message_id": "msg-%03d" % n, "request_start_timestamp_ms": start_ms,
            "stream_end_timestamp_ms": end_ms, "time_to_first_chunk": None, "time_between_chunks": [],
            "user_prompt_length": 0, "response_size": 0, "chat_conversation_type": kind,
            "tool_use_ids_and_names": [list(t) for t in tools], "model_id": "claude-sonnet-4",
            "message_meta_tags": list(tags)}


def kiro_conversation_records():
    """The ConversationState from analyzer/research/kiro.md section 8, with
    the project moved to /srv/proj. The research sample's user timestamp was
    six hours off its own request metadata; it is corrected here so the
    turns are in order."""
    return {
        "conversation_id": KIRO_SESSION, "next_message": None,
        "history": [
            {"user": _kiro_user({"Prompt": {"prompt": "list the files here"}}, "2026-04-23T20:17:15.123456789-07:00"),
             "assistant": {"ToolUse": {"message_id": "msg-001", "content": "I will list the directory.",
                                       "tool_uses": [{"id": "tooluse_abc123", "name": "execute_bash",
                                                      "orig_name": "execute_bash", "args": {"command": "ls -la"},
                                                      "orig_args": {"command": "ls -la"}}]}},
             "request_metadata": _kiro_meta(1, 1777000635200, 1777000636900, "ToolUse",
                                            [("tooluse_abc123", "execute_bash")])},
            {"user": _kiro_user({"ToolUseResults": {"tool_use_results": [
                {"tool_use_id": "tooluse_abc123", "content": [{"Text": "total 8\nREADME.md"}], "status": "Success"}]}}),
             "assistant": {"Response": {"message_id": "msg-002", "content": "The directory contains README.md."}},
             "request_metadata": _kiro_meta(2, 1777000637000, 1777000638100)},
        ],
        "valid_history_range": [0, 2], "transcript": ["> list the files here", "The directory contains README.md."],
        "tools": {"native___": []}, "context_manager": None, "context_message_length": None, "latest_summary": None,
        "model_info": {"model_id": "claude-sonnet-4", "model_name": "Claude Sonnet 4"}, "file_line_tracker": {},
        "checkpoint_manager": None, "mcp_enabled": True,
    }


def kiro_export_records():
    """A /save export exercising the less common variants: an MCP tool whose
    name differs from orig_name, a Json result, a cancelled tool use, a
    Compact tag, latest_summary, a pending next_message and the legacy
    `model` field instead of model_info."""
    return {
        "conversation_id": KIRO_EXPORT_SESSION,
        "next_message": _kiro_user({"Prompt": {"prompt": "now push it"}}, "2026-04-24T08:00:00-07:00"),
        "history": [
            {"user": _kiro_user({"Prompt": {"prompt": "open an issue"}}, "2026-04-24T07:00:00.000-07:00"),
             "assistant": {"ToolUse": {"message_id": "msg-010", "content": "",
                                       "tool_uses": [{"id": "tooluse_mcp1", "name": "github___create_issue",
                                                      "orig_name": "create_issue", "args": {"title": "bug"},
                                                      "orig_args": {"title": "bug"}}]}},
             "request_metadata": dict(_kiro_meta(10, 1777039201000, 1777039202000, "ToolUse"), model_id=None)},
            {"user": _kiro_user({"ToolUseResults": {"tool_use_results": [
                {"tool_use_id": "tooluse_mcp1", "content": [{"Json": {"number": 7}}], "status": "Error"}]}}),
             "assistant": {"ToolUse": {"message_id": "msg-011", "content": "Retrying.",
                                       "tool_uses": [{"id": "tooluse_bash2", "name": "execute_bash",
                                                      "orig_name": "execute_bash", "args": {"command": "rm -rf build"},
                                                      "orig_args": {"command": "rm -rf build"}}]}},
             "request_metadata": _kiro_meta(11, 1777039203000, 1777039204000, "ToolUse")},
            {"user": _kiro_user({"CancelledToolUses": {"prompt": "stop, do not delete", "tool_use_results": [
                {"tool_use_id": "tooluse_bash2", "content": [{"Text": "Tool use was cancelled by the user"}],
                 "status": "Error"}]}}, "2026-04-24T07:00:10.000-07:00"),
             "assistant": {"Response": {"message_id": "msg-012", "content": "Stopped."}},
             "request_metadata": _kiro_meta(12, 1777039211000, 1777039212000, tags=["Compact"])},
        ],
        "valid_history_range": [0, 3], "transcript": [], "tools": {"native___": []},
        "latest_summary": ["User asked to open an issue and cancelled a delete.",
                           _kiro_meta(13, 1777039213000, 1777039214000)],
        "model": "claude-3.7-sonnet",
    }


def build_kiro(home: Path) -> None:
    base = home / ".local/share/amazon-q"
    base.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(base / "data.sqlite3"))
    con.executescript("""
    CREATE TABLE migrations (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, migration_time INTEGER NOT NULL);
    CREATE TABLE history (id INTEGER PRIMARY KEY, command TEXT, shell TEXT, pid INTEGER, session_id TEXT, cwd TEXT,
      start_time INTEGER, hostname TEXT, exit_code INTEGER, end_time INTEGER, duration INTEGER);
    CREATE TABLE state (key TEXT PRIMARY KEY, value BLOB);
    CREATE TABLE auth_kv (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE conversations (key TEXT PRIMARY KEY, value TEXT);
    """)
    con.execute("INSERT INTO conversations (key, value) VALUES (?, ?)",
                ("/srv/proj", json.dumps(kiro_conversation_records())))
    con.execute("INSERT INTO conversations (key, value) VALUES (?, ?)", ("/srv/broken", "not json"))
    con.execute("INSERT INTO history (command, shell, pid, session_id, cwd, start_time, hostname, exit_code, end_time, "
                "duration) VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("git status", "zsh", 4242, KIRO_SHELL_SESSION, "/srv/proj", 1776999600, "ws1", 0, 1776999601, 1000))
    con.execute("INSERT INTO auth_kv VALUES ('codewhisperer:odic:token', '{\"access_token\":\"REDACT-ME\"}')")
    con.commit()
    con.close()
    exports = home / ".aws/amazonq/exports"
    exports.mkdir(parents=True, exist_ok=True)
    text = json.dumps(kiro_export_records(), indent=2)
    (exports / "issue-chat.json").write_text(text, encoding="utf-8")
    # an export cut mid-write, inside the third history entry
    (exports / "issue-chat-cut.json").write_text(text[:text.index("stop, do not delete")], encoding="utf-8")
    # noise the parser must not want: CLI settings, and a Kiro CLI session
    # file whose format is unverified even though it looks like an export
    (home / ".kiro/settings").mkdir(parents=True, exist_ok=True)
    (home / ".kiro/settings/cli.json").write_text('{"chat.defaultModel": "auto"}', encoding="utf-8")
    (home / ".kiro/sessions").mkdir(parents=True, exist_ok=True)
    (home / ".kiro/sessions/s1.json").write_text(json.dumps(
        {"conversation_id": "x", "history": [], "messages": [{"role": "user", "content": [{"text": "hi"}]}]}),
        encoding="utf-8")
GEMINI_SESSION = "a1b2c3d4-0000-4000-8000-000000000001"
GEMINI_RESUMED = "a1b2c3d4-0000-4000-8000-0000000000ff"
GEMINI_LEGACY = "b2c3d4e5-0000-4000-8000-000000000002"
GEMINI_SUBAGENT = "c3d4e5f6-0000-4000-8000-000000000003"
GEMINI_HASH = "6b9af143446a411aefa3edb76e4693799bd7513e7ed8d919962d6713d3d3b972"   # sha256("/srv/proj")
GEMINI_REL = ".gemini/tmp/proj/chats/session-2026-10-01T09-00-a1b2c3d4.jsonl"


def gemini_session_records():
    """Session JSONL in the chatRecordingTypes.ts shapes: a re-appended
    message, $set, $rewindTo, $patch and a $set.sessionId from a resume."""
    ts = "2026-10-01T09:00:%s.000Z"
    ls_call = {"id": "list_directory-1759309207000", "name": "list_directory", "args": {"path": "/srv/proj/src"},
               "status": "executing", "timestamp": "2026-10-01T09:00:07.100Z", "displayName": "ReadFolder",
               "description": "Lists files"}
    ls_done = dict(ls_call, status="success", result=[{"functionResponse": {
        "id": "list_directory-1759309207000", "name": "list_directory", "response": {"output": "main.ts\nutil.ts"}}}])
    g1 = {"id": "msg-g1", "timestamp": ts % "07", "type": "gemini", "content": "Listing now.",
          "thoughts": [{"subject": "Plan", "description": "Use the ls tool.", "timestamp": "2026-10-01T09:00:06.500Z"}],
          "tokens": {"input": 120, "output": 12, "cached": 0, "thoughts": 8, "tool": 0, "total": 140},
          "model": "gemini-2.5-pro", "toolCalls": [ls_call]}
    rf = {"id": "read_file-1759309222000", "name": "read_file", "args": {"absolute_path": "/srv/proj/src/util.ts"},
          "status": "success", "timestamp": "2026-10-01T09:00:22.100Z", "displayName": "ReadFile",
          "result": [{"functionResponse": {"id": "read_file-1759309222000", "name": "read_file",
                                           "response": {"output": "draft"}}}]}
    return [
        {"sessionId": GEMINI_SESSION, "projectHash": GEMINI_HASH, "startTime": ts % "00",
         "lastUpdated": ts % "00", "kind": "main"},
        {"id": "msg-u1", "timestamp": ts % "05", "type": "user", "content": [{"text": "list files in src"}]},
        g1,
        dict(g1, toolCalls=[ls_done]),
        {"$set": {"lastUpdated": ts % "08", "summary": "List src files"}},
        {"id": "msg-u2", "timestamp": ts % "10", "type": "user", "content": [{"text": "delete everything in /srv/proj"}]},
        {"id": "msg-g2", "timestamp": ts % "11", "type": "gemini", "content": "", "model": "gemini-2.5-pro",
         "toolCalls": [{"id": "run_shell_command-1", "name": "run_shell_command", "args": {"command": "rm -rf /srv/proj/*"},
                        "status": "awaiting_approval", "timestamp": ts % "11", "displayName": "Shell"}]},
        {"$rewindTo": "msg-u2"},
        {"id": "msg-u3", "timestamp": ts % "20", "type": "user", "content": "show util.ts"},
        {"id": "msg-g3", "timestamp": ts % "22", "type": "gemini", "content": "draft answer", "model": "gemini-2.5-pro",
         "toolCalls": [rf]},
        {"$patch": {"id": "msg-g3", "content": [{"text": "Here is util.ts."}], "toolCalls": [
            {"id": "read_file-1759309222000", "result": [{"functionResponse": {
                "id": "read_file-1759309222000", "name": "read_file", "response": {"output": "export const x = 1"}}}]}]}},
        {"id": "msg-i1", "timestamp": ts % "23", "type": "info", "content": "Request cancelled."},
        {"id": "msg-g4", "timestamp": ts % "24", "type": "gemini", "content": "", "model": "gemini-2.5-flash",
         "toolCalls": [{"id": "run_shell_command-2", "name": "run_shell_command", "args": {"command": "curl http://x"},
                        "status": "cancelled", "timestamp": ts % "24", "displayName": "Shell"}]},
        {"$set": {"sessionId": GEMINI_RESUMED}},
        {"id": "msg-u4", "timestamp": "2026-10-01T09:01:00.000Z", "type": "user", "content": "resume work"},
    ]


def gemini_legacy_record():
    return {"sessionId": GEMINI_LEGACY, "projectHash": GEMINI_HASH, "startTime": "2026-09-30T08:00:00.000Z",
            "lastUpdated": "2026-09-30T08:00:03.000Z", "messages": [
                {"id": "l-u1", "timestamp": "2026-09-30T08:00:01.000Z", "type": "user", "content": "hello"},
                {"id": "l-g1", "timestamp": "2026-09-30T08:00:03.000Z", "type": "gemini",
                 "content": [{"text": "weighing it", "thought": True}, {"text": "Hi."}], "model": "gemini-2.0-flash"},
            ]}


def gemini_logs_records():
    return [
        {"sessionId": GEMINI_SESSION, "messageId": 0, "timestamp": "2026-10-01T09:00:05.000Z", "type": "user",
         "message": "list files in src"},
        {"sessionId": GEMINI_SESSION, "messageId": 1, "timestamp": "2026-10-01T09:00:10.000Z", "type": "user",
         "message": "delete everything in /srv/proj"},
    ]


def build_gemini_cli(base: Path) -> None:
    """~/.gemini with a slug directory (marker file), a legacy hash directory
    resolved through projects.json, a subagent session and noise."""
    slug = base / "tmp/proj"
    _jsonl(base / GEMINI_REL[len(".gemini/"):], gemini_session_records())
    _jsonl(slug / "chats" / GEMINI_SESSION / (GEMINI_SUBAGENT + ".jsonl"), [
        {"sessionId": GEMINI_SUBAGENT, "projectHash": GEMINI_HASH, "startTime": "2026-10-01T09:00:30.000Z", "kind": "subagent"},
        {"id": "s-u1", "timestamp": "2026-10-01T09:00:30.000Z", "type": "user", "content": "investigate"},
    ])
    (slug / ".project_root").write_text("/srv/proj", encoding="utf-8")
    (slug / "logs.json").write_text(json.dumps(gemini_logs_records()), encoding="utf-8")
    (slug / "shell_history").write_text("ls\n", encoding="utf-8")
    legacy = base / "tmp" / GEMINI_HASH / "chats"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "session-2026-09-30T08-00-b2c3d4e5.json").write_text(json.dumps(gemini_legacy_record()), encoding="utf-8")
    (base / "projects.json").write_text(json.dumps({"projects": {"/srv/proj": "proj"}}), encoding="utf-8")
    (base / "oauth_creds.json").write_text('{"access_token": "secret"}', encoding="utf-8")
def _wal_db(path: Path, script: str, inserts) -> None:
    """Build a WAL-mode SQLite file whose schema is checkpointed into the main
    file and whose rows live only in the -wal sidecar, as on a host where the
    agent is still running. The files are copied out while the writer is
    still open, so closing it cannot checkpoint the copy."""
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="cac-fixture-"))
    try:
        src = tmp / path.name
        con = sqlite3.connect(str(src))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA wal_autocheckpoint=0")
        con.executescript(script)
        con.commit()
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        for sql in inserts:
            con.execute(sql)
        con.commit()
        path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            if Path(str(src) + suffix).exists():
                shutil.copyfile(str(src) + suffix, str(path) + suffix)
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


CRUSH_SESSION = "6f1c0001"

# Columns of internal/db/migrations at crush ca6ae26 that the parser reads.
CRUSH_SCHEMA = """
CREATE TABLE sessions (id TEXT PRIMARY KEY, parent_session_id TEXT, title TEXT NOT NULL,
  message_count INTEGER NOT NULL DEFAULT 0, prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0, cost REAL NOT NULL DEFAULT 0.0,
  updated_at INTEGER NOT NULL, created_at INTEGER NOT NULL, summary_message_id TEXT, todos TEXT, channel TEXT);
CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, parts TEXT NOT NULL DEFAULT '[]',
  model TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, finished_at INTEGER, provider TEXT,
  is_summary_message INTEGER DEFAULT 0 NOT NULL, prism_model_id TEXT, prism_model_name TEXT);
CREATE TABLE files (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, path TEXT NOT NULL, content TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
"""


def crush_records():
    """The INSERT statements of research/crush.md section 8, plus a final
    assistant message with reasoning, text and an abnormal finish."""
    return [
        "INSERT INTO sessions(id,title,message_count,prompt_tokens,completion_tokens,cost,updated_at,created_at) "
        "VALUES('6f1c0001','Fix bug',3,10,5,0.01,1760000005,1760000001)",
        "INSERT INTO messages(id,session_id,role,parts,model,provider,created_at,updated_at,finished_at,is_summary_message) VALUES "
        """('m1','6f1c0001','user','[{"type":"text","data":{"text":"list files"}},{"type":"finish","data":{"reason":"stop","time":0}}]','claude-sonnet-4','anthropic',1760000001,1760000001,NULL,0),"""
        """('m2','6f1c0001','assistant','[{"type":"tool_call","data":{"id":"call_x1","name":"bash","input":"{\\"command\\":\\"ls\\"}","provider_executed":false,"finished":true}},{"type":"finish","data":{"reason":"tool_use","time":1760000003}}]','claude-sonnet-4','anthropic',1760000002,1760000003,1760000003,0),"""
        """('m3','6f1c0001','tool','[{"type":"tool_result","data":{"tool_call_id":"call_x1","name":"bash","content":"a.txt","data":"","mime_type":"","metadata":"","is_error":false}},{"type":"finish","data":{"reason":"stop","time":0}}]','','',1760000003,1760000003,NULL,0)""",
        "INSERT INTO messages(id,session_id,role,parts,model,provider,created_at,updated_at,finished_at,is_summary_message) VALUES "
        """('m4','6f1c0001','assistant','[{"type":"reasoning","data":{"thinking":"one file only","signature":"sig","started_at":1760000004,"finished_at":1760000004}},{"type":"text","data":{"text":"There is one file, a.txt."}},{"type":"finish","data":{"reason":"max_tokens","time":1760000005}}]','claude-sonnet-4','anthropic',1760000004,1760000005,1760000005,0)""",
    ]


def build_crush(home: Path) -> None:
    """Crush run in the home directory, so its per-project store is
    ~/.crush/crush.db, plus the global project registry and config noise."""
    _wal_db(home / ".crush/crush.db", CRUSH_SCHEMA, crush_records())
    (home / ".crush/crush.json").write_text('{"providers":{"anthropic":{"api_key":"sk-test"}}}', encoding="utf-8")
    reg = home / ".local/share/crush"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "projects.json").write_text(json.dumps({"projects": [
        {"path": "/srv/proj", "data_dir": "/srv/proj/.crush", "last_accessed": "2026-10-01T12:00:00Z"}]}), encoding="utf-8")
    (home / ".config/crush").mkdir(parents=True, exist_ok=True)
    (home / ".config/crush/crush.json").write_text("{}", encoding="utf-8")


GOOSE_SESSION = "20260301_1"

# session_manager.rs at goose 591edd4, schema version 16 (research/goose.md section 3).
GOOSE_SCHEMA = """
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE sessions (
  id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
  user_set_name BOOLEAN DEFAULT FALSE, session_type TEXT NOT NULL DEFAULT 'user',
  working_dir TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, extension_data TEXT DEFAULT '{}',
  total_tokens INTEGER, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
  cache_write_tokens INTEGER, accumulated_total_tokens INTEGER, accumulated_input_tokens INTEGER,
  accumulated_output_tokens INTEGER, accumulated_cache_read_tokens INTEGER,
  accumulated_cache_write_tokens INTEGER, accumulated_cost REAL, schedule_id TEXT, recipe_json TEXT,
  user_recipe_values_json TEXT, provider_name TEXT, model_config_json TEXT,
  goose_mode TEXT NOT NULL DEFAULT 'auto', archived_at TIMESTAMP, project_id TEXT, parent_session_id TEXT);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, message_id TEXT, session_id TEXT NOT NULL REFERENCES sessions(id),
  role TEXT NOT NULL, content_json TEXT NOT NULL, created_timestamp INTEGER NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, tokens INTEGER, metadata_json TEXT);
CREATE TABLE usage_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  created_timestamp INTEGER NOT NULL, model TEXT, input_tokens INTEGER, output_tokens INTEGER,
  total_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, cost REAL,
  cost_source TEXT, is_compaction INTEGER DEFAULT 0);
"""


def goose_records(cwd="/srv/proj"):
    """The INSERT statements of research/goose.md section 8, with the
    working directory moved to the shared project path."""
    return [
        "INSERT INTO schema_version(version) VALUES (16)",
        "INSERT INTO sessions(id,name,session_type,working_dir,created_at,updated_at,extension_data,provider_name,model_config_json,goose_mode) "
        "VALUES ('20260301_1','Fix flaky test','user','%s','2026-03-01 09:00:00','2026-03-01 09:01:05','{}','anthropic',"
        """'{"model_name":"claude-sonnet-4-5","temperature":null,"max_tokens":null,"toolshim":false,"toolshim_model":null}','auto')""" % cwd,
        "INSERT INTO messages(message_id,session_id,role,content_json,created_timestamp,metadata_json) VALUES "
        """('msg_20260301_1_a1','20260301_1','user','[{"type":"text","text":"run the tests"}]',1772355600,'{"userVisible":true,"agentVisible":true}'),"""
        """('msg_20260301_1_a2','20260301_1','assistant','[{"type":"toolRequest","id":"call_1","toolCall":{"status":"success","value":{"name":"developer__shell","arguments":{"command":"pytest -q"}}}}]',1772355601,"""
        """ '{"userVisible":true,"agentVisible":true,"inference":{"provider":"anthropic","requestedModel":"claude-sonnet-4-5"}}'),"""
        """('msg_20260301_1_a3','20260301_1','user','[{"type":"toolResponse","id":"call_1","toolResult":{"status":"success","value":{"content":[{"type":"text","text":"3 passed"}]}}}]',1772355603,'{"userVisible":true,"agentVisible":true}'),"""
        """('msg_20260301_1_a4','20260301_1','assistant','[{"type":"thinking","thinking":"all green","signature":"sig"},{"type":"text","text":"All 3 tests pass."}]',1772355605,'{"userVisible":true,"agentVisible":true}')""",
        "INSERT INTO usage_ledger(session_id,created_timestamp,model,input_tokens,output_tokens,total_tokens) "
        "VALUES ('20260301_1',1772355605,'claude-sonnet-4-5',120,30,150)",
    ]


def goose_legacy_records():
    return [
        {"description": "old chat", "working_dir": "/srv/old", "created_at": "2026-03-01T09:00:00Z",
         "updated_at": "2026-03-01T09:00:10Z", "extension_data": {}, "message_count": 1},
        {"id": "m1", "role": "user", "created": 1772355600, "content": [{"type": "text", "text": "hello"}]},
    ]


def goose_llm_request_records():
    return [
        {"model_config": {"model_name": "gpt-4.1"},
         "input": {"model": "gpt-4.1", "messages": [{"role": "user", "content": "hello"}]}},
        {"data": {"role": "assistant", "created": 1772355601, "content": [{"type": "text", "text": "hi"}]},
         "usage": {"input_tokens": 5, "output_tokens": 1}},
    ]


GOOSE_LEGACY_REL = ".local/share/goose/sessions/20260301_090000.jsonl"


def build_goose(home: Path) -> None:
    data = home / ".local/share/goose/sessions"
    _wal_db(data / "sessions.db", GOOSE_SCHEMA, goose_records())
    _jsonl(home / GOOSE_LEGACY_REL, goose_legacy_records())
    state = home / ".local/state/goose"
    _jsonl(state / "logs/llm_request.0.jsonl", goose_llm_request_records())
    (state / "history.txt").write_text("#V2\nrun the tests\nline one\\nline two \\\\ done\n", encoding="utf-8")
    (home / ".config/goose").mkdir(parents=True, exist_ok=True)
    (home / ".config/goose/config.yaml").write_text("GOOSE_PROVIDER: anthropic\n", encoding="utf-8")
    (home / ".config/goose/secrets.yaml").write_text("ANTHROPIC_API_KEY: sk-test\n", encoding="utf-8")
CONTINUE_SESSION = "0f1e"
CONTINUE_CREATED = "1790935200000"  # 2026-10-02T10:00:00Z, a millisecond epoch string as sessions.json stores it


def continue_session():
    """A Continue session file in the shape of core/index.d.ts `Session`."""
    edit = {"id": "call_1", "type": "function",
            "function": {"name": "edit_existing_file", "arguments": "{\"filepath\":\"a.py\"}"}}
    term = {"id": "call_2", "type": "function",
            "function": {"name": "run_terminal_command", "arguments": "{\"command\":\"rm -rf build\"}"}}
    return {
        "sessionId": CONTINUE_SESSION, "title": "Fix bug", "workspaceDirectory": "/srv/proj",
        "history": [
            {"message": {"role": "user", "content": [{"type": "text", "text": "rename foo"},
                                                     {"type": "imageUrl", "imageUrl": {"url": "data:image/png;base64,AA"}}]},
             "contextItems": []},
            {"message": {"role": "thinking", "content": "consider the callers"}, "contextItems": []},
            {"message": {"role": "assistant", "content": "", "toolCalls": [edit]}, "contextItems": [],
             "reasoning": {"active": False, "text": "find foo first", "startAt": 1790935201000, "endAt": 1790935202000},
             "promptLogs": [{"modelTitle": "GPT-4o", "modelProvider": "openai", "prompt": "<long prompt>", "completion": ""}],
             "toolCallStates": [{"toolCallId": "call_1", "toolCall": edit, "status": "done",
                                 "parsedArgs": {"filepath": "a.py"},
                                 "output": [{"name": "Edit", "description": "", "content": "ok"}]}]},
            {"message": {"role": "tool", "content": "ok", "toolCallId": "call_1"}, "contextItems": []},
            {"message": {"role": "assistant", "content": "Renamed. Cleaning the build too.", "toolCalls": [term]},
             "contextItems": [],
             "toolCallStates": [{"toolCallId": "call_2", "toolCall": term, "status": "canceled",
                                 "parsedArgs": {"command": "rm -rf build"}}]},
        ],
        "mode": "agent", "chatModelTitle": "GPT-4o",
        "usage": {"promptTokens": 120, "completionTokens": 30, "totalCost": 0.01},
    }


def continue_index():
    return [{"sessionId": CONTINUE_SESSION, "title": "Fix bug", "dateCreated": CONTINUE_CREATED,
             "workspaceDirectory": "/srv/proj", "messageCount": 2}]


def continue_dev_data():
    base = {"schema": "0.2.0", "userId": "", "userAgent": "vscode/1.1 (Continue/1.0)", "selectedProfileId": "local"}
    chat = dict(base, eventName="chatInteraction", timestamp="2026-10-02T10:00:05.000Z", prompt="rename foo",
                completion="done", modelName="gpt-4o", modelTitle="GPT-4o", modelProvider="openai",
                sessionId=CONTINUE_SESSION)
    tool = dict(base, eventName="toolUsage", timestamp="2026-10-02T10:00:03.000Z", toolCallId="call_1",
                functionName="edit_existing_file", functionParams={"filepath": "a.py"},
                toolCallArgs="{\"filepath\":\"a.py\"}", accepted=True, succeeded=True,
                output=[{"name": "Edit", "description": "", "content": "ok"}])
    return [chat], [tool]


def build_continue(home: Path) -> None:
    sessions = home / ".continue/sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / (CONTINUE_SESSION + ".json")).write_text(json.dumps(continue_session(), indent=2), encoding="utf-8")
    (sessions / "sessions.json").write_text(json.dumps(continue_index()), encoding="utf-8")
    chat, tool = continue_dev_data()
    _jsonl(home / ".continue/dev_data/0.2.0/chatInteraction.jsonl", chat)
    _jsonl(home / ".continue/dev_data/0.2.0/toolUsage.jsonl", tool)
    (home / ".continue/config.yaml").write_text("name: Local\nmodels: []\n", encoding="utf-8")


# Written the way aider/io.py writes them: user and blockquote lines end in
# two spaces (markdown line breaks), assistant output is framed by blanks.
AIDER_CHAT = "".join([
    "\n# aider chat started at 2026-10-02 12:00:00\n\n",
    "\n#### rename foo to bar  \n",
    "\nHere is the change:\n\na.py\n<<<<<<< SEARCH\nfoo\n=======\nbar\n>>>>>>> REPLACE\n\n",
    "> Applied edit to a.py  \n",
    "> Commit abc1234 refactor: rename foo to bar  \n",
    "\n# aider chat started at 2026-10-02 13:00:00\n\n",
    "\n#### /add b.py  \n",
    "> Added b.py to the chat  \n",
    "\n#### <blank>  \n",
])

AIDER_INPUT = "\n# 2026-10-02 12:00:05.123456\n+rename foo to bar\n\n# 2026-10-02 13:00:02.000000\n+/add b.py\n"

AIDER_LLM = ("TO LLM 2026-10-02T12:00:05\n-------\nSYSTEM Act as an expert\nSYSTEM software developer\n-------\n"
             "USER rename foo to bar\nLLM RESPONSE 2026-10-02T12:00:09\nASSISTANT Here is the change:\nASSISTANT \n"
             "ASSISTANT a.py\n")


def build_aider(base: Path) -> None:
    """Aider's history files in `base`, a home or a repository root."""
    base.mkdir(parents=True, exist_ok=True)
    (base / ".aider.chat.history.md").write_text(AIDER_CHAT, encoding="utf-8")
    (base / ".aider.input.history").write_text(AIDER_INPUT, encoding="utf-8")
    (base / ".aider.llm.history").write_text(AIDER_LLM, encoding="utf-8")
    (base / ".aider.conf.yml").write_text("model: gpt-4o\n", encoding="utf-8")
