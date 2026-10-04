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
    common = dict(
        sessionId=CLAUDE_SESSION,
        cwd=cwd,
        gitBranch=branch,
        version="2.1.0",
        userType="external",
        isSidechain=False,
        entrypoint="cli",
    )
    return [
        dict(type="mode", mode="normal", sessionId=CLAUDE_SESSION),
        dict(
            common,
            type="user",
            uuid="u1",
            parentUuid=None,
            timestamp="2026-10-01T10:00:00.000Z",
            message={"role": "user", "content": "delete the logs in /var/log please"},
        ),
        dict(
            common,
            type="assistant",
            uuid="a1",
            parentUuid="u1",
            timestamp="2026-10-01T10:00:01.000Z",
            requestId="req_1",
            message={
                "model": "claude-fable-5-1",
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "private reasoning", "signature": "x"}
                ],
            },
        ),
        dict(
            common,
            type="assistant",
            uuid="a2",
            parentUuid="a1",
            timestamp="2026-10-01T10:00:02.000Z",
            requestId="req_1",
            message={
                "model": "claude-fable-5-1",
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "Bash",
                        "input": {"command": "rm -rf /var/log/*.log", "description": "Remove logs"},
                    }
                ],
            },
        ),
        dict(
            common,
            type="user",
            uuid="u2",
            parentUuid="a2",
            timestamp="2026-10-01T10:00:03.000Z",
            message={
                "role": "user",
                "content": [
                    {
                        "tool_use_id": "toolu_01",
                        "type": "tool_result",
                        "content": "removed 3 files",
                        "is_error": False,
                    }
                ],
            },
            toolUseResult={"stdout": "removed 3 files", "stderr": "", "interrupted": False},
        ),
        dict(
            common,
            type="assistant",
            uuid="a3",
            parentUuid="u2",
            timestamp="2026-10-01T10:00:04.000Z",
            requestId="req_2",
            message={
                "model": "claude-fable-5-1",
                "id": "msg_2",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Done. Three log files were removed."}],
            },
        ),
        dict(
            common,
            type="system",
            uuid="s1",
            parentUuid="a3",
            timestamp="2026-10-01T10:00:05.000Z",
            subtype="turn_duration",
            durationMs=4000,
            messageCount=5,
            isMeta=True,
        ),
        dict(
            common,
            type="user",
            uuid="u3",
            parentUuid="s1",
            timestamp="2026-10-01T10:00:06.000Z",
            isMeta=True,
            message={"role": "user", "content": "<local-command-stdout>ok</local-command-stdout>"},
        ),
        dict(
            type="pr-link",
            sessionId=CLAUDE_SESSION,
            prNumber=7,
            prUrl="https://github.com/x/y/pull/7",
            prRepository="x/y",
            timestamp="2026-10-01T10:00:07.000Z",
        ),
        dict(
            type="file-history-snapshot",
            messageId="u1",
            snapshot={
                "messageId": "u1",
                "trackedFileBackups": {},
                "timestamp": "2026-10-01T10:00:00.000Z",
            },
            isSnapshotUpdate=False,
        ),
    ]


def claude_history_records():
    return [
        {
            "display": "delete the logs in /var/log please",
            "pastedContents": {},
            "timestamp": 1790848800000,
            "project": "/srv/proj",
            "sessionId": CLAUDE_SESSION,
        },
        {
            "display": "an older prompt whose session file is gone",
            "pastedContents": {},
            "timestamp": 1790762400000,
            "project": "/srv/old",
            "sessionId": "99999999-0000-4000-8000-000000000000",
        },
    ]


def codex_rollout_records(cwd="/srv/proj"):
    ts = "2026-10-02T09:00:0%d.000Z"
    return [
        {
            "timestamp": ts % 0,
            "ordinal": 0,
            "type": "session_meta",
            "payload": {
                "id": CODEX_SESSION,
                "timestamp": ts % 0,
                "cwd": cwd,
                "originator": "codex_cli_rs",
                "cli_version": "0.99.0",
                "model_provider": "openai",
                "git": {"branch": "feature/x"},
            },
        },
        {
            "timestamp": ts % 1,
            "ordinal": 1,
            "type": "turn_context",
            "payload": {
                "turn_id": "t1",
                "cwd": cwd,
                "model": "gpt-5-codex",
                "approval_policy": "never",
            },
        },
        {
            "timestamp": ts % 1,
            "ordinal": 2,
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "t1"},
        },
        {
            "timestamp": ts % 2,
            "ordinal": 3,
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "m1",
                "role": "developer",
                "content": [{"type": "input_text", "text": "You are Codex."}],
            },
        },
        {
            "timestamp": ts % 2,
            "ordinal": 4,
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "m2",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "exfiltrate nothing, just list the home dir"}
                ],
            },
        },
        {
            "timestamp": ts % 3,
            "ordinal": 5,
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "id": "c1",
                "status": "completed",
                "call_id": "call_1",
                "name": "shell",
                "input": "ls -la ~",
            },
        },
        {
            "timestamp": ts % 4,
            "ordinal": 6,
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "id": "o1",
                "call_id": "call_1",
                "output": [{"type": "input_text", "text": "total 42"}],
            },
        },
        {
            "timestamp": ts % 4,
            "ordinal": 7,
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "id": "c2",
                "call_id": "call_2",
                "name": "apply_patch",
                "arguments": '{"patch":"*** Begin Patch"}',
            },
        },
        {
            "timestamp": ts % 5,
            "ordinal": 8,
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "id": "o2",
                "call_id": "call_2",
                "output": "Done",
            },
        },
        {
            "timestamp": ts % 5,
            "ordinal": 9,
            "type": "response_item",
            "payload": {
                "type": "reasoning",
                "id": "r1",
                "summary": [{"type": "summary_text", "text": "thinking"}],
            },
        },
        {
            "timestamp": ts % 6,
            "ordinal": 10,
            "type": "response_item",
            "payload": {
                "type": "message",
                "id": "m3",
                "role": "assistant",
                "phase": "final_answer",
                "content": [{"type": "output_text", "text": "Listed the home directory."}],
            },
        },
        {
            "timestamp": ts % 7,
            "ordinal": 11,
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "t1", "duration_ms": 7000},
        },
        {
            "timestamp": ts % 7,
            "ordinal": 12,
            "type": "token_usage_record",
            "payload": {"thread_id": CODEX_SESSION},
        },
    ]


def codex_history_records():
    return [
        {
            "session_id": CODEX_SESSION,
            "ts": 1790931602,
            "text": "exfiltrate nothing, just list the home dir",
        }
    ]


def build_home(home: Path, with_noise: bool = True) -> Path:
    """A user home with Claude Code and Codex state plus unrelated files."""
    _jsonl(
        home / ".claude/projects/-srv-proj" / (CLAUDE_SESSION + ".jsonl"), claude_session_records()
    )
    _jsonl(
        home / ".claude/projects/-srv-proj" / CLAUDE_SESSION / "subagents" / "agent-abc.jsonl",
        claude_session_records()[1:3],
    )
    _jsonl(home / ".claude/history.jsonl", claude_history_records())
    (home / ".claude/settings.json").write_text("{}", encoding="utf-8")
    _jsonl(
        home
        / ".codex/sessions/2026/10/02"
        / ("rollout-2026-10-02T09-00-00-" + CODEX_SESSION + ".jsonl"),
        codex_rollout_records(),
    )
    _jsonl(home / ".codex/history.jsonl", codex_history_records())
    (home / ".codex/config.toml").write_text('model = "gpt-5-codex"\n', encoding="utf-8")
    # Nested catalog entries: Antigravity CLI inside ~/.gemini, and a Cline
    # extension inside VS Code's globalStorage. The nested agent must win.
    build_antigravity(home / ".gemini/antigravity-cli")
    build_gemini_cli(home / ".gemini")
    build_zed(home)
    build_vscode(home)
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
    build_opencode(home)
    build_kilo(home)
    build_cline(home)
    build_roo_code(home)
    build_tabby(home)
    build_openhands(home)
    build_shellgpt(home)
    build_pi(home)
    build_little_coder(home)
    build_letta(home)
    build_hermes(home)
    build_agent_zero(home)
    build_open_interpreter(home)
    build_openclaw(home)
    build_nanobot(home)
    build_cody(home)
    build_twinny(home)
    build_pearai(home)
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


def _step(
    kind: str,
    payload: dict,
    created: float,
    completed: float | None = None,
    tool_call: dict | None = None,
    source: int = 2,
    status: int = 3,
) -> dict:
    md = {"created_at": created, "source": source}
    if completed is not None:
        md["completed_at"] = completed
        md["finished_generating_at"] = completed
    if tool_call:
        md["tool_call"] = tool_call
    return {"metadata": md, kind: payload, "status": status}


def antigravity_steps() -> list[tuple[int, int, dict]]:
    """(step_type, status, Step dict) in the shapes seen on a real install:
    user_input, planner_response with tool calls, generic and typed tool steps."""
    tc1 = {
        "id": "call_1",
        "name": "view_file",
        "arguments_json": json.dumps({"AbsolutePath": "/home/u/proj/README.md"}),
    }
    tc2 = {
        "id": "call_2",
        "name": "run_command",
        "arguments_json": json.dumps(
            {"CommandLine": "rm -rf /var/log/*.log", "Cwd": "/home/u/proj"}
        ),
    }
    tc3 = {
        "id": "call_3",
        "name": "write_to_file",
        "arguments_json": json.dumps({"TargetFile": "/home/u/proj/notes.md"}),
    }
    t = AGY_T0
    return [
        (14, 3, dict(_step("user_input", {"query": "clean the logs"}, t, source=4), type=14)),
        (
            15,
            3,
            dict(
                _step(
                    "planner_response",
                    {
                        "response": "I will read the README first.",
                        "thinking": "look before leaping",
                        "tool_calls": [tc1],
                    },
                    t + 1,
                    t + 3,
                ),
                type=15,
            ),
        ),
        (
            132,
            3,
            dict(
                _step(
                    "generic",
                    {
                        "args": [{"key": "AbsolutePath", "value": "/home/u/proj/README.md"}],
                        "result": {"result": "File Path: README.md\n# proj"},
                    },
                    t + 3,
                    t + 4,
                    tool_call=tc1,
                ),
                type=132,
            ),
        ),
        (
            15,
            3,
            dict(
                _step("planner_response", {"response": "", "tool_calls": [tc2]}, t + 4, t + 6),
                type=15,
            ),
        ),
        (
            28,
            3,
            dict(
                _step(
                    "run_command",
                    {
                        "command_line": "rm -rf /var/log/*.log",
                        "cwd": "/home/u/proj",
                        "exit_code": 0,
                        "combined_output": {"full": "removed 3 files"},
                    },
                    t + 6,
                    t + 7,
                    tool_call=tc2,
                ),
                type=28,
            ),
        ),
        (
            15,
            3,
            dict(
                _step("planner_response", {"response": "", "tool_calls": [tc3]}, t + 7, t + 8),
                type=15,
            ),
        ),
        (
            23,
            7,
            dict(
                _step(
                    "write_to_file",
                    {"target_file_uri": "file:///home/u/proj/notes.md", "file_created": True},
                    t + 8,
                    t + 9,
                    tool_call=tc3,
                    status=7,
                ),
                type=23,
            ),
        ),
        (
            14,
            3,
            dict(_step("user_input", {"query": "<injected reminder>"}, t + 9, source=3), type=14),
        ),
        (
            15,
            3,
            dict(
                _step(
                    "planner_response",
                    {"response": "Done. Three log files were removed."},
                    t + 10,
                    t + 12,
                ),
                type=15,
            ),
        ),
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
    meta = encode(
        {
            "workspaces": [
                {"workspace_folder_absolute_uri": "file:///home/u/proj", "branch_name": "main"}
            ],
            "created_at": AGY_T0 - 1,
            "workspace_uris": ["file:///home/u/proj"],
            "project_id": "default-cli-project",
        },
        "CortexTrajectoryMetadata",
        AGY,
    )
    con.execute("INSERT INTO trajectory_metadata_blob VALUES ('main', ?)", (meta,))
    for idx, (step_type, status, step) in enumerate(antigravity_steps()):
        payload = encode(step, "Step", AGY)
        md = encode(step["metadata"], "CortexStepMetadata", AGY)
        con.execute(
            "INSERT INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?,?,?,?,?)",
            (idx, step_type, status, md, payload),
        )
    gen = encode(
        {"chat_model": {"response_model": "gemini-3.8-flash"}, "step_indices": [1, 3, 5, 8]},
        "CortexStepGeneratorMetadata",
        AGY,
    )
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
    summ.execute(
        "INSERT INTO conversation_summaries (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, status, "
        "project_id, last_user_input_time, app_data_dir) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            AGY_CONVERSATION,
            "",
            "clean the logs",
            10,
            "2026-10-01 10:00:13.002530482+00:00",
            json.dumps(["file:///home/u/proj"]),
            "CASCADE_RUN_STATUS_IDLE",
            "default-cli-project",
            "2026-10-01 10:00:00.000000000+00:00",
            "antigravity-cli",
        ),
    )
    summ.commit()
    summ.close()
    _jsonl(
        base / "history.jsonl",
        [{"display": "clean the logs", "timestamp": AGY_T0 * 1000, "workspace": "/home/u/proj"}],
    )
    (base / "antigravity-oauth-token").write_text("secret", encoding="utf-8")


QWEN_SESSION = "e5f6a7b8-4444-4000-8000-000000000011"
QWEN_ARCHIVED = "0a0b0c0d-4444-4000-8000-000000000022"
QWEN_TMP = "3f0a9c" + "0" * 58  # sha256(cwd) directory name


def qwen_session_records(cwd="/srv/proj", branch="main"):
    """Qwen Code ChatRecords, shapes from research/qwen-code.md section 8."""
    common = dict(sessionId=QWEN_SESSION, cwd=cwd, version="0.24.7", gitBranch=branch)
    return [
        dict(
            common,
            uuid="q0",
            parentUuid=None,
            timestamp="2026-10-01T09:59:59.000Z",
            type="system",
            subtype="session_model",
            provenance="system",
            systemPayload={"modelId": "qwen3-coder-plus", "authType": "qwen-oauth"},
        ),
        dict(
            common,
            uuid="q1",
            parentUuid="q0",
            timestamp="2026-10-01T10:00:00.000Z",
            type="user",
            provenance="real_user",
            promptId=QWEN_SESSION + "########1",
            message={"role": "user", "parts": [{"text": "run the tests"}]},
            systemPayload={"displayText": "run the tests", "hookContext": ""},
        ),
        dict(
            common,
            uuid="q2",
            parentUuid="q1",
            timestamp="2026-10-01T10:00:03.000Z",
            type="assistant",
            provenance="assistant_output",
            model="qwen3-coder-plus",
            message={
                "role": "model",
                "parts": [
                    {"text": "Plan: run npm test.", "thought": True},
                    {"text": "Running tests."},
                    {
                        "functionCall": {
                            "id": "call_abc123",
                            "name": "run_shell_command",
                            "args": {"command": "npm test"},
                        }
                    },
                    {
                        "functionCall": {
                            "id": "call_def456",
                            "name": "read_file",
                            "args": {"absolute_path": "/srv/proj/.env"},
                        }
                    },
                ],
            },
            usageMetadata={
                "promptTokenCount": 200,
                "candidatesTokenCount": 30,
                "totalTokenCount": 230,
            },
            contextWindowSize=131072,
        ),
        dict(
            common,
            uuid="q3",
            parentUuid="q2",
            timestamp="2026-10-01T10:00:09.000Z",
            type="tool_result",
            provenance="tool_result",
            message={
                "role": "user",
                "parts": [
                    {
                        "functionResponse": {
                            "id": "call_abc123",
                            "name": "run_shell_command",
                            "response": {"output": "12 passing"},
                        }
                    }
                ],
            },
            toolCallResult={
                "callId": "call_abc123",
                "status": "success",
                "resultDisplay": "12 passing",
                "errorType": None,
            },
        ),
        dict(
            common,
            uuid="q4",
            parentUuid="q3",
            timestamp="2026-10-01T10:00:10.000Z",
            type="tool_result",
            provenance="tool_result",
            message={
                "role": "user",
                "parts": [
                    {
                        "functionResponse": {
                            "id": "call_def456",
                            "name": "read_file",
                            "response": {"error": "permission denied"},
                        }
                    }
                ],
            },
            toolCallResult={
                "callId": "call_def456",
                "status": "error",
                "errorType": "permission_denied",
            },
        ),
        dict(
            common,
            uuid="q5",
            parentUuid="q4",
            timestamp="2026-10-01T10:00:11.000Z",
            type="system",
            subtype="slash_command",
            provenance="system",
            systemPayload={"phase": "invocation", "rawCommand": "/compress"},
        ),
        dict(
            common,
            uuid="q6",
            parentUuid="q5",
            timestamp="2026-10-01T10:00:12.000Z",
            type="system",
            subtype="custom_title",
            provenance="system",
            systemPayload={"customTitle": "Run tests", "titleSource": "auto"},
        ),
    ]


def qwen_logs_entries():
    """Gemini-legacy LogEntry array; model_switch carries a JSON string."""
    return [
        {
            "sessionId": QWEN_SESSION,
            "messageId": 0,
            "timestamp": "2026-10-01T10:00:00.000Z",
            "type": "user",
            "message": "run the tests",
        },
        {
            "sessionId": QWEN_SESSION,
            "messageId": 1,
            "timestamp": "2026-10-01T10:00:05.000Z",
            "type": "model_switch",
            "message": json.dumps(
                {
                    "fromModel": "qwen3-coder-plus",
                    "toModel": "qwen3-vl-plus",
                    "reason": "vision_auto_switch",
                }
            ),
        },
    ]


def build_qwen(home: Path) -> None:
    chats = home / ".qwen/projects/-srv-proj/chats"
    _jsonl(chats / (QWEN_SESSION + ".jsonl"), qwen_session_records())
    _jsonl(
        chats / "archive" / (QWEN_ARCHIVED + ".jsonl"),
        [dict(r, sessionId=QWEN_ARCHIVED) for r in qwen_session_records()[1:2]],
    )
    _jsonl(chats / (QWEN_SESSION + ".ledger.jsonl"), [{"promptId": "p1", "text": "run the tests"}])
    (chats / (QWEN_SESSION + ".runtime.json")).write_text(
        '{"session_id": "x", "started_at": 1790848800}', encoding="utf-8"
    )
    tmp = home / ".qwen/tmp" / QWEN_TMP
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "logs.json").write_text(json.dumps(qwen_logs_entries(), indent=2), encoding="utf-8")
    (home / ".qwen/settings.json").write_text("{}", encoding="utf-8")
    (home / ".qwen/oauth_creds.json").write_text('{"access_token": "secret"}', encoding="utf-8")


KIRO_SESSION = "3f2b8c1e-9d7a-4e6b-b1c2-0a9f8e7d6c5b"
KIRO_EXPORT_SESSION = "7c1d2e3f-4a5b-4c6d-8e7f-901234567890"
KIRO_SHELL_SESSION = "fig-shell-1"


def _kiro_user(content, timestamp=None, cwd="/srv/proj"):
    return {
        "additional_context": "",
        "env_context": {
            "env_state": {
                "operating_system": "linux",
                "current_working_directory": cwd,
                "environment_variables": [],
            }
        },
        "content": content,
        "timestamp": timestamp,
        "images": None,
    }


def _kiro_meta(n, start_ms, end_ms, kind="NotToolUse", tools=(), tags=()):
    return {
        "request_id": "req-%03d" % n,
        "message_id": "msg-%03d" % n,
        "request_start_timestamp_ms": start_ms,
        "stream_end_timestamp_ms": end_ms,
        "time_to_first_chunk": None,
        "time_between_chunks": [],
        "user_prompt_length": 0,
        "response_size": 0,
        "chat_conversation_type": kind,
        "tool_use_ids_and_names": [list(t) for t in tools],
        "model_id": "claude-sonnet-4",
        "message_meta_tags": list(tags),
    }


def kiro_conversation_records():
    """The ConversationState from analyzer/research/kiro.md section 8, with
    the project moved to /srv/proj. The research sample's user timestamp was
    six hours off its own request metadata; it is corrected here so the
    turns are in order."""
    return {
        "conversation_id": KIRO_SESSION,
        "next_message": None,
        "history": [
            {
                "user": _kiro_user(
                    {"Prompt": {"prompt": "list the files here"}},
                    "2026-04-23T20:17:15.123456789-07:00",
                ),
                "assistant": {
                    "ToolUse": {
                        "message_id": "msg-001",
                        "content": "I will list the directory.",
                        "tool_uses": [
                            {
                                "id": "tooluse_abc123",
                                "name": "execute_bash",
                                "orig_name": "execute_bash",
                                "args": {"command": "ls -la"},
                                "orig_args": {"command": "ls -la"},
                            }
                        ],
                    }
                },
                "request_metadata": _kiro_meta(
                    1, 1777000635200, 1777000636900, "ToolUse", [("tooluse_abc123", "execute_bash")]
                ),
            },
            {
                "user": _kiro_user(
                    {
                        "ToolUseResults": {
                            "tool_use_results": [
                                {
                                    "tool_use_id": "tooluse_abc123",
                                    "content": [{"Text": "total 8\nREADME.md"}],
                                    "status": "Success",
                                }
                            ]
                        }
                    }
                ),
                "assistant": {
                    "Response": {
                        "message_id": "msg-002",
                        "content": "The directory contains README.md.",
                    }
                },
                "request_metadata": _kiro_meta(2, 1777000637000, 1777000638100),
            },
        ],
        "valid_history_range": [0, 2],
        "transcript": ["> list the files here", "The directory contains README.md."],
        "tools": {"native___": []},
        "context_manager": None,
        "context_message_length": None,
        "latest_summary": None,
        "model_info": {"model_id": "claude-sonnet-4", "model_name": "Claude Sonnet 4"},
        "file_line_tracker": {},
        "checkpoint_manager": None,
        "mcp_enabled": True,
    }


def kiro_export_records():
    """A /save export exercising the less common variants: an MCP tool whose
    name differs from orig_name, a Json result, a cancelled tool use, a
    Compact tag, latest_summary, a pending next_message and the legacy
    `model` field instead of model_info."""
    return {
        "conversation_id": KIRO_EXPORT_SESSION,
        "next_message": _kiro_user(
            {"Prompt": {"prompt": "now push it"}}, "2026-04-24T08:00:00-07:00"
        ),
        "history": [
            {
                "user": _kiro_user(
                    {"Prompt": {"prompt": "open an issue"}}, "2026-04-24T07:00:00.000-07:00"
                ),
                "assistant": {
                    "ToolUse": {
                        "message_id": "msg-010",
                        "content": "",
                        "tool_uses": [
                            {
                                "id": "tooluse_mcp1",
                                "name": "github___create_issue",
                                "orig_name": "create_issue",
                                "args": {"title": "bug"},
                                "orig_args": {"title": "bug"},
                            }
                        ],
                    }
                },
                "request_metadata": dict(
                    _kiro_meta(10, 1777039201000, 1777039202000, "ToolUse"), model_id=None
                ),
            },
            {
                "user": _kiro_user(
                    {
                        "ToolUseResults": {
                            "tool_use_results": [
                                {
                                    "tool_use_id": "tooluse_mcp1",
                                    "content": [{"Json": {"number": 7}}],
                                    "status": "Error",
                                }
                            ]
                        }
                    }
                ),
                "assistant": {
                    "ToolUse": {
                        "message_id": "msg-011",
                        "content": "Retrying.",
                        "tool_uses": [
                            {
                                "id": "tooluse_bash2",
                                "name": "execute_bash",
                                "orig_name": "execute_bash",
                                "args": {"command": "rm -rf build"},
                                "orig_args": {"command": "rm -rf build"},
                            }
                        ],
                    }
                },
                "request_metadata": _kiro_meta(11, 1777039203000, 1777039204000, "ToolUse"),
            },
            {
                "user": _kiro_user(
                    {
                        "CancelledToolUses": {
                            "prompt": "stop, do not delete",
                            "tool_use_results": [
                                {
                                    "tool_use_id": "tooluse_bash2",
                                    "content": [{"Text": "Tool use was cancelled by the user"}],
                                    "status": "Error",
                                }
                            ],
                        }
                    },
                    "2026-04-24T07:00:10.000-07:00",
                ),
                "assistant": {"Response": {"message_id": "msg-012", "content": "Stopped."}},
                "request_metadata": _kiro_meta(12, 1777039211000, 1777039212000, tags=["Compact"]),
            },
        ],
        "valid_history_range": [0, 3],
        "transcript": [],
        "tools": {"native___": []},
        "latest_summary": [
            "User asked to open an issue and cancelled a delete.",
            _kiro_meta(13, 1777039213000, 1777039214000),
        ],
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
    con.execute(
        "INSERT INTO conversations (key, value) VALUES (?, ?)",
        ("/srv/proj", json.dumps(kiro_conversation_records())),
    )
    con.execute("INSERT INTO conversations (key, value) VALUES (?, ?)", ("/srv/broken", "not json"))
    con.execute(
        "INSERT INTO history (command, shell, pid, session_id, cwd, start_time, hostname, exit_code, end_time, "
        "duration) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "git status",
            "zsh",
            4242,
            KIRO_SHELL_SESSION,
            "/srv/proj",
            1776999600,
            "ws1",
            0,
            1776999601,
            1000,
        ),
    )
    con.execute(
        "INSERT INTO auth_kv VALUES ('codewhisperer:odic:token', '{\"access_token\":\"REDACT-ME\"}')"
    )
    con.commit()
    con.close()
    exports = home / ".aws/amazonq/exports"
    exports.mkdir(parents=True, exist_ok=True)
    text = json.dumps(kiro_export_records(), indent=2)
    (exports / "issue-chat.json").write_text(text, encoding="utf-8")
    # an export cut mid-write, inside the third history entry
    (exports / "issue-chat-cut.json").write_text(
        text[: text.index("stop, do not delete")], encoding="utf-8"
    )
    # noise the parser must not want: CLI settings, and a Kiro CLI session
    # file whose format is unverified even though it looks like an export
    (home / ".kiro/settings").mkdir(parents=True, exist_ok=True)
    (home / ".kiro/settings/cli.json").write_text('{"chat.defaultModel": "auto"}', encoding="utf-8")
    (home / ".kiro/sessions").mkdir(parents=True, exist_ok=True)
    (home / ".kiro/sessions/s1.json").write_text(
        json.dumps(
            {
                "conversation_id": "x",
                "history": [],
                "messages": [{"role": "user", "content": [{"text": "hi"}]}],
            }
        ),
        encoding="utf-8",
    )


GEMINI_SESSION = "a1b2c3d4-0000-4000-8000-000000000001"
GEMINI_RESUMED = "a1b2c3d4-0000-4000-8000-0000000000ff"
GEMINI_LEGACY = "b2c3d4e5-0000-4000-8000-000000000002"
GEMINI_SUBAGENT = "c3d4e5f6-0000-4000-8000-000000000003"
GEMINI_HASH = (
    "6b9af143446a411aefa3edb76e4693799bd7513e7ed8d919962d6713d3d3b972"  # sha256("/srv/proj")
)
GEMINI_REL = ".gemini/tmp/proj/chats/session-2026-10-01T09-00-a1b2c3d4.jsonl"


def gemini_session_records():
    """Session JSONL in the chatRecordingTypes.ts shapes: a re-appended
    message, $set, $rewindTo, $patch and a $set.sessionId from a resume."""
    ts = "2026-10-01T09:00:%s.000Z"
    ls_call = {
        "id": "list_directory-1759309207000",
        "name": "list_directory",
        "args": {"path": "/srv/proj/src"},
        "status": "executing",
        "timestamp": "2026-10-01T09:00:07.100Z",
        "displayName": "ReadFolder",
        "description": "Lists files",
    }
    ls_done = dict(
        ls_call,
        status="success",
        result=[
            {
                "functionResponse": {
                    "id": "list_directory-1759309207000",
                    "name": "list_directory",
                    "response": {"output": "main.ts\nutil.ts"},
                }
            }
        ],
    )
    g1 = {
        "id": "msg-g1",
        "timestamp": ts % "07",
        "type": "gemini",
        "content": "Listing now.",
        "thoughts": [
            {
                "subject": "Plan",
                "description": "Use the ls tool.",
                "timestamp": "2026-10-01T09:00:06.500Z",
            }
        ],
        "tokens": {"input": 120, "output": 12, "cached": 0, "thoughts": 8, "tool": 0, "total": 140},
        "model": "gemini-2.5-pro",
        "toolCalls": [ls_call],
    }
    rf = {
        "id": "read_file-1759309222000",
        "name": "read_file",
        "args": {"absolute_path": "/srv/proj/src/util.ts"},
        "status": "success",
        "timestamp": "2026-10-01T09:00:22.100Z",
        "displayName": "ReadFile",
        "result": [
            {
                "functionResponse": {
                    "id": "read_file-1759309222000",
                    "name": "read_file",
                    "response": {"output": "draft"},
                }
            }
        ],
    }
    return [
        {
            "sessionId": GEMINI_SESSION,
            "projectHash": GEMINI_HASH,
            "startTime": ts % "00",
            "lastUpdated": ts % "00",
            "kind": "main",
        },
        {
            "id": "msg-u1",
            "timestamp": ts % "05",
            "type": "user",
            "content": [{"text": "list files in src"}],
        },
        g1,
        dict(g1, toolCalls=[ls_done]),
        {"$set": {"lastUpdated": ts % "08", "summary": "List src files"}},
        {
            "id": "msg-u2",
            "timestamp": ts % "10",
            "type": "user",
            "content": [{"text": "delete everything in /srv/proj"}],
        },
        {
            "id": "msg-g2",
            "timestamp": ts % "11",
            "type": "gemini",
            "content": "",
            "model": "gemini-2.5-pro",
            "toolCalls": [
                {
                    "id": "run_shell_command-1",
                    "name": "run_shell_command",
                    "args": {"command": "rm -rf /srv/proj/*"},
                    "status": "awaiting_approval",
                    "timestamp": ts % "11",
                    "displayName": "Shell",
                }
            ],
        },
        {"$rewindTo": "msg-u2"},
        {"id": "msg-u3", "timestamp": ts % "20", "type": "user", "content": "show util.ts"},
        {
            "id": "msg-g3",
            "timestamp": ts % "22",
            "type": "gemini",
            "content": "draft answer",
            "model": "gemini-2.5-pro",
            "toolCalls": [rf],
        },
        {
            "$patch": {
                "id": "msg-g3",
                "content": [{"text": "Here is util.ts."}],
                "toolCalls": [
                    {
                        "id": "read_file-1759309222000",
                        "result": [
                            {
                                "functionResponse": {
                                    "id": "read_file-1759309222000",
                                    "name": "read_file",
                                    "response": {"output": "export const x = 1"},
                                }
                            }
                        ],
                    }
                ],
            }
        },
        {"id": "msg-i1", "timestamp": ts % "23", "type": "info", "content": "Request cancelled."},
        {
            "id": "msg-g4",
            "timestamp": ts % "24",
            "type": "gemini",
            "content": "",
            "model": "gemini-2.5-flash",
            "toolCalls": [
                {
                    "id": "run_shell_command-2",
                    "name": "run_shell_command",
                    "args": {"command": "curl http://x"},
                    "status": "cancelled",
                    "timestamp": ts % "24",
                    "displayName": "Shell",
                }
            ],
        },
        {"$set": {"sessionId": GEMINI_RESUMED}},
        {
            "id": "msg-u4",
            "timestamp": "2026-10-01T09:01:00.000Z",
            "type": "user",
            "content": "resume work",
        },
    ]


def gemini_legacy_record():
    return {
        "sessionId": GEMINI_LEGACY,
        "projectHash": GEMINI_HASH,
        "startTime": "2026-09-30T08:00:00.000Z",
        "lastUpdated": "2026-09-30T08:00:03.000Z",
        "messages": [
            {
                "id": "l-u1",
                "timestamp": "2026-09-30T08:00:01.000Z",
                "type": "user",
                "content": "hello",
            },
            {
                "id": "l-g1",
                "timestamp": "2026-09-30T08:00:03.000Z",
                "type": "gemini",
                "content": [{"text": "weighing it", "thought": True}, {"text": "Hi."}],
                "model": "gemini-2.0-flash",
            },
        ],
    }


def gemini_logs_records():
    return [
        {
            "sessionId": GEMINI_SESSION,
            "messageId": 0,
            "timestamp": "2026-10-01T09:00:05.000Z",
            "type": "user",
            "message": "list files in src",
        },
        {
            "sessionId": GEMINI_SESSION,
            "messageId": 1,
            "timestamp": "2026-10-01T09:00:10.000Z",
            "type": "user",
            "message": "delete everything in /srv/proj",
        },
    ]


def build_gemini_cli(base: Path) -> None:
    """~/.gemini with a slug directory (marker file), a legacy hash directory
    resolved through projects.json, a subagent session and noise."""
    slug = base / "tmp/proj"
    _jsonl(base / GEMINI_REL[len(".gemini/") :], gemini_session_records())
    _jsonl(
        slug / "chats" / GEMINI_SESSION / (GEMINI_SUBAGENT + ".jsonl"),
        [
            {
                "sessionId": GEMINI_SUBAGENT,
                "projectHash": GEMINI_HASH,
                "startTime": "2026-10-01T09:00:30.000Z",
                "kind": "subagent",
            },
            {
                "id": "s-u1",
                "timestamp": "2026-10-01T09:00:30.000Z",
                "type": "user",
                "content": "investigate",
            },
        ],
    )
    (slug / ".project_root").write_text("/srv/proj", encoding="utf-8")
    (slug / "logs.json").write_text(json.dumps(gemini_logs_records()), encoding="utf-8")
    (slug / "shell_history").write_text("ls\n", encoding="utf-8")
    legacy = base / "tmp" / GEMINI_HASH / "chats"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "session-2026-09-30T08-00-b2c3d4e5.json").write_text(
        json.dumps(gemini_legacy_record()), encoding="utf-8"
    )
    (base / "projects.json").write_text(
        json.dumps({"projects": {"/srv/proj": "proj"}}), encoding="utf-8"
    )
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
    (home / ".crush/crush.json").write_text(
        '{"providers":{"anthropic":{"api_key":"sk-test"}}}', encoding="utf-8"
    )
    reg = home / ".local/share/crush"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "projects.json").write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "path": "/srv/proj",
                        "data_dir": "/srv/proj/.crush",
                        "last_accessed": "2026-10-01T12:00:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
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
        """'{"model_name":"claude-sonnet-4-5","temperature":null,"max_tokens":null,"toolshim":false,"toolshim_model":null}','auto')"""
        % cwd,
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
        {
            "description": "old chat",
            "working_dir": "/srv/old",
            "created_at": "2026-03-01T09:00:00Z",
            "updated_at": "2026-03-01T09:00:10Z",
            "extension_data": {},
            "message_count": 1,
        },
        {
            "id": "m1",
            "role": "user",
            "created": 1772355600,
            "content": [{"type": "text", "text": "hello"}],
        },
    ]


def goose_llm_request_records():
    return [
        {
            "model_config": {"model_name": "gpt-4.1"},
            "input": {"model": "gpt-4.1", "messages": [{"role": "user", "content": "hello"}]},
        },
        {
            "data": {
                "role": "assistant",
                "created": 1772355601,
                "content": [{"type": "text", "text": "hi"}],
            },
            "usage": {"input_tokens": 5, "output_tokens": 1},
        },
    ]


GOOSE_LEGACY_REL = ".local/share/goose/sessions/20260301_090000.jsonl"


def build_goose(home: Path) -> None:
    data = home / ".local/share/goose/sessions"
    _wal_db(data / "sessions.db", GOOSE_SCHEMA, goose_records())
    _jsonl(home / GOOSE_LEGACY_REL, goose_legacy_records())
    state = home / ".local/state/goose"
    _jsonl(state / "logs/llm_request.0.jsonl", goose_llm_request_records())
    (state / "history.txt").write_text(
        "#V2\nrun the tests\nline one\\nline two \\\\ done\n", encoding="utf-8"
    )
    (home / ".config/goose").mkdir(parents=True, exist_ok=True)
    (home / ".config/goose/config.yaml").write_text("GOOSE_PROVIDER: anthropic\n", encoding="utf-8")
    (home / ".config/goose/secrets.yaml").write_text(
        "ANTHROPIC_API_KEY: sk-test\n", encoding="utf-8"
    )


CONTINUE_SESSION = "0f1e"
CONTINUE_CREATED = (
    "1790935200000"  # 2026-10-02T10:00:00Z, a millisecond epoch string as sessions.json stores it
)


def continue_session():
    """A Continue session file in the shape of core/index.d.ts `Session`."""
    edit = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "edit_existing_file", "arguments": '{"filepath":"a.py"}'},
    }
    term = {
        "id": "call_2",
        "type": "function",
        "function": {"name": "run_terminal_command", "arguments": '{"command":"rm -rf build"}'},
    }
    return {
        "sessionId": CONTINUE_SESSION,
        "title": "Fix bug",
        "workspaceDirectory": "/srv/proj",
        "history": [
            {
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "rename foo"},
                        {"type": "imageUrl", "imageUrl": {"url": "data:image/png;base64,AA"}},
                    ],
                },
                "contextItems": [],
            },
            {
                "message": {"role": "thinking", "content": "consider the callers"},
                "contextItems": [],
            },
            {
                "message": {"role": "assistant", "content": "", "toolCalls": [edit]},
                "contextItems": [],
                "reasoning": {
                    "active": False,
                    "text": "find foo first",
                    "startAt": 1790935201000,
                    "endAt": 1790935202000,
                },
                "promptLogs": [
                    {
                        "modelTitle": "GPT-4o",
                        "modelProvider": "openai",
                        "prompt": "<long prompt>",
                        "completion": "",
                    }
                ],
                "toolCallStates": [
                    {
                        "toolCallId": "call_1",
                        "toolCall": edit,
                        "status": "done",
                        "parsedArgs": {"filepath": "a.py"},
                        "output": [{"name": "Edit", "description": "", "content": "ok"}],
                    }
                ],
            },
            {
                "message": {"role": "tool", "content": "ok", "toolCallId": "call_1"},
                "contextItems": [],
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Renamed. Cleaning the build too.",
                    "toolCalls": [term],
                },
                "contextItems": [],
                "toolCallStates": [
                    {
                        "toolCallId": "call_2",
                        "toolCall": term,
                        "status": "canceled",
                        "parsedArgs": {"command": "rm -rf build"},
                    }
                ],
            },
        ],
        "mode": "agent",
        "chatModelTitle": "GPT-4o",
        "usage": {"promptTokens": 120, "completionTokens": 30, "totalCost": 0.01},
    }


def continue_index():
    return [
        {
            "sessionId": CONTINUE_SESSION,
            "title": "Fix bug",
            "dateCreated": CONTINUE_CREATED,
            "workspaceDirectory": "/srv/proj",
            "messageCount": 2,
        }
    ]


def continue_dev_data():
    base = {
        "schema": "0.2.0",
        "userId": "",
        "userAgent": "vscode/1.1 (Continue/1.0)",
        "selectedProfileId": "local",
    }
    chat = dict(
        base,
        eventName="chatInteraction",
        timestamp="2026-10-02T10:00:05.000Z",
        prompt="rename foo",
        completion="done",
        modelName="gpt-4o",
        modelTitle="GPT-4o",
        modelProvider="openai",
        sessionId=CONTINUE_SESSION,
    )
    tool = dict(
        base,
        eventName="toolUsage",
        timestamp="2026-10-02T10:00:03.000Z",
        toolCallId="call_1",
        functionName="edit_existing_file",
        functionParams={"filepath": "a.py"},
        toolCallArgs='{"filepath":"a.py"}',
        accepted=True,
        succeeded=True,
        output=[{"name": "Edit", "description": "", "content": "ok"}],
    )
    return [chat], [tool]


def build_continue(home: Path) -> None:
    sessions = home / ".continue/sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / (CONTINUE_SESSION + ".json")).write_text(
        json.dumps(continue_session(), indent=2), encoding="utf-8"
    )
    (sessions / "sessions.json").write_text(json.dumps(continue_index()), encoding="utf-8")
    chat, tool = continue_dev_data()
    _jsonl(home / ".continue/dev_data/0.2.0/chatInteraction.jsonl", chat)
    _jsonl(home / ".continue/dev_data/0.2.0/toolUsage.jsonl", tool)
    (home / ".continue/config.yaml").write_text("name: Local\nmodels: []\n", encoding="utf-8")


# Written the way aider/io.py writes them: user and blockquote lines end in
# two spaces (markdown line breaks), assistant output is framed by blanks.
AIDER_CHAT = "".join(
    [
        "\n# aider chat started at 2026-10-02 12:00:00\n\n",
        "\n#### rename foo to bar  \n",
        "\nHere is the change:\n\na.py\n<<<<<<< SEARCH\nfoo\n=======\nbar\n>>>>>>> REPLACE\n\n",
        "> Applied edit to a.py  \n",
        "> Commit abc1234 refactor: rename foo to bar  \n",
        "\n# aider chat started at 2026-10-02 13:00:00\n\n",
        "\n#### /add b.py  \n",
        "> Added b.py to the chat  \n",
        "\n#### <blank>  \n",
    ]
)

AIDER_INPUT = "\n# 2026-10-02 12:00:05.123456\n+rename foo to bar\n\n# 2026-10-02 13:00:02.000000\n+/add b.py\n"

AIDER_LLM = (
    "TO LLM 2026-10-02T12:00:05\n-------\nSYSTEM Act as an expert\nSYSTEM software developer\n-------\n"
    "USER rename foo to bar\nLLM RESPONSE 2026-10-02T12:00:09\nASSISTANT Here is the change:\nASSISTANT \n"
    "ASSISTANT a.py\n"
)


def build_aider(base: Path) -> None:
    """Aider's history files in `base`, a home or a repository root."""
    base.mkdir(parents=True, exist_ok=True)
    (base / ".aider.chat.history.md").write_text(AIDER_CHAT, encoding="utf-8")
    (base / ".aider.input.history").write_text(AIDER_INPUT, encoding="utf-8")
    (base / ".aider.llm.history").write_text(AIDER_LLM, encoding="utf-8")
    (base / ".aider.conf.yml").write_text("model: gpt-4o\n", encoding="utf-8")


ZED_THREAD = "6f1c0b2e-1111-4bbb-8ccc-000000000001"
ZED_EXTERNAL = "ext-claude-code-sess-1"


def zed_thread_record(cwd="/srv/proj"):
    """A `threads.data` blob, version 0.3.0, as in analyzer/research/zed.md."""
    return {
        "version": "0.3.0",
        "title": "Fix flaky test",
        "updated_at": "2026-10-03T09:01:05Z",
        "initial_project_snapshot": {
            "worktree_snapshots": [
                {
                    "worktree_path": cwd,
                    "git_state": {
                        "remote_url": "git@github.com:alice/proj.git",
                        "head_sha": "abc123",
                        "current_branch": "main",
                        "diff": None,
                    },
                }
            ],
            "timestamp": "2026-10-03T09:00:00Z",
        },
        "model": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "messages": [
            {
                "User": {
                    "id": "9a7d6c5b-2222-4ddd-9eee-000000000002",
                    "content": [
                        {"Text": "run the tests"},
                        {"Mention": {"uri": "file://%s/README.md" % cwd, "content": ""}},
                    ],
                }
            },
            {
                "Agent": {
                    "content": [
                        {"Thinking": {"text": "use pytest", "signature": None}},
                        {
                            "ToolUse": {
                                "id": "toolu_01",
                                "name": "terminal",
                                "raw_input": '{"command":"pytest -q"}',
                                "input": {"type": "json", "value": {"command": "pytest -q"}},
                                "is_input_complete": True,
                                "thought_signature": None,
                            }
                        },
                        {"Text": "All 3 tests pass."},
                    ],
                    "tool_results": {
                        "toolu_01": {
                            "tool_use_id": "toolu_01",
                            "tool_name": "terminal",
                            "is_error": False,
                            "content": [{"Text": "3 passed"}],
                            "output": None,
                        }
                    },
                    "reasoning_details": None,
                }
            },
            "Resume",
            {"Compaction": {"Summary": "ran the tests"}},
        ],
    }


def zed_blob(record):
    """(data_type, data): zstd when the zstandard package is installed, as Zed
    writes it, otherwise the `json` form Zed also accepts."""
    raw = json.dumps(record).encode("utf-8")
    try:
        import zstandard  # pyright: ignore[reportMissingImports] - optional dependency
    except ImportError:
        return "json", raw
    return "zstd", zstandard.ZstdCompressor(level=3).compress(raw)


def build_zed(home: Path) -> None:
    data = home / ".local/share/zed"
    (data / "threads").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(data / "threads/threads.db"))
    con.executescript("""
    CREATE TABLE threads (id TEXT PRIMARY KEY, summary TEXT NOT NULL, updated_at TEXT NOT NULL,
      data_type TEXT NOT NULL, data BLOB NOT NULL);
    ALTER TABLE threads ADD COLUMN parent_id TEXT;
    ALTER TABLE threads ADD COLUMN folder_paths TEXT;
    ALTER TABLE threads ADD COLUMN folder_paths_order TEXT;
    ALTER TABLE threads ADD COLUMN created_at TEXT;
    """)
    dtype, blob = zed_blob(zed_thread_record())
    con.execute(
        "INSERT INTO threads(id,parent_id,folder_paths,folder_paths_order,summary,updated_at,data_type,data,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            ZED_THREAD,
            None,
            "/srv/proj",
            "0",
            "Fix flaky test",
            "2026-10-03T09:01:05.000000000+00:00",
            dtype,
            blob,
            "2026-10-03T09:00:00.000000000+00:00",
        ),
    )
    con.commit()
    con.close()
    (data / "db/0-stable").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(data / "db/0-stable/db.sqlite"))
    con.executescript("""
    CREATE TABLE sidebar_threads(thread_id BLOB PRIMARY KEY, session_id TEXT, agent_id TEXT, title TEXT NOT NULL,
      updated_at TEXT NOT NULL, created_at TEXT, folder_paths TEXT, folder_paths_order TEXT, archived INTEGER DEFAULT 0,
      main_worktree_paths TEXT, main_worktree_paths_order TEXT, remote_connection TEXT);
    ALTER TABLE sidebar_threads ADD COLUMN interacted_at TEXT;
    ALTER TABLE sidebar_threads ADD COLUMN title_override TEXT;
    """)
    con.execute(
        "INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,created_at,folder_paths,"
        "folder_paths_order,archived) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            os.urandom(16),
            ZED_THREAD,
            None,
            "Fix flaky test",
            "2026-10-03T09:01:05+00:00",
            "2026-10-03T09:00:00+00:00",
            "/srv/proj",
            "0",
            0,
        ),
    )
    con.execute(
        "INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,folder_paths,folder_paths_order) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            os.urandom(16),
            ZED_EXTERNAL,
            "claude-code",
            "External thread",
            "2026-10-03T10:00:00+00:00",
            "/srv/proj",
            "0",
        ),
    )
    con.commit()
    con.close()
    (home / ".config/zed").mkdir(parents=True, exist_ok=True)
    (home / ".config/zed/settings.json").write_text(
        '{"agent": {"default_model": {}}}', encoding="utf-8"
    )


VSCODE_SESSION = "9ab0c1d2-0000-4000-8000-00000000c0de"
VSCODE_LEGACY_SESSION = "9ab0c1d2-0000-4000-8000-0000000001d0"
VSCODE_T0 = 1791025200000  # 2026-10-03T11:00:00Z, ms
VSCODE_WS = ".config/Code/User/workspaceStorage/abc123"


def vscode_log_records(cwd="/srv/proj"):
    """A `chatSessions/<id>.jsonl` mutation log, as in analyzer/research/vscode.md.
    The modelId, agent id and responder strings come from the closed Copilot
    extension and are invented."""
    t = VSCODE_T0
    return [
        {
            "kind": 0,
            "v": {
                "version": 3,
                "creationDate": t,
                "customTitle": None,
                "initialLocation": "panel",
                "responderUsername": "GitHub Copilot",
                "sessionId": VSCODE_SESSION,
                "requests": [
                    {
                        "requestId": "request_1",
                        "timestamp": t + 1000,
                        "message": {"text": "run tests", "parts": []},
                        "agent": {
                            "id": "github.copilot.default",
                            "name": "GitHub Copilot",
                            "extensionId": {"value": "GitHub.copilot-chat"},
                        },
                        "modelId": "copilot/gpt-4.1",
                        "modeInfo": {
                            "kind": "agent",
                            "telemetryModeId": "agent",
                            "isBuiltin": True,
                        },
                        "variableData": {
                            "variables": [
                                {
                                    "id": "file://%s/test_a.py" % cwd,
                                    "name": "test_a.py",
                                    "value": "...",
                                }
                            ]
                        },
                        "response": [
                            {"kind": "thinking", "value": "Need pytest", "id": "t1"},
                            {
                                "kind": "toolInvocationSerialized",
                                "toolCallId": "call_a",
                                "toolId": "run_in_terminal",
                                "invocationMessage": "Running command",
                                "isComplete": True,
                                "isConfirmed": True,
                                "toolSpecificData": {
                                    "kind": "terminal",
                                    "commandLine": {"original": "pytest"},
                                },
                                "resultDetails": {
                                    "input": "pytest",
                                    "output": [{"type": "embed", "value": "3 passed"}],
                                },
                            },
                            {"value": "All tests pass in "},
                            {
                                "kind": "inlineReference",
                                "inlineReference": {"scheme": "file", "path": cwd + "/test_a.py"},
                                "name": "test_a.py",
                            },
                            {"value": "."},
                        ],
                        "responseId": "response_1",
                        "responseTimestamp": t + 2000,
                        "modelState": {"value": "complete"},
                    }
                ],
                "workingDirectory": "file://%s" % cwd,
            },
        },
        {
            "kind": 2,
            "k": ["requests"],
            "v": [
                {
                    "requestId": "request_2",
                    "timestamp": t + 10000,
                    "message": {"text": "thanks", "parts": []},
                    "variableData": {"variables": []},
                    "modelId": "copilot/gpt-4.1",
                    "response": [],
                }
            ],
        },
        {"kind": 2, "k": ["requests", 1, "response"], "v": [{"value": "You're welcome."}]},
        {"kind": 1, "k": ["requests", 1, "responseTimestamp"], "v": t + 11000},
        {"kind": 1, "k": ["customTitle"], "v": "Run tests"},
    ]


def vscode_legacy_session(cwd="/srv/proj"):
    """A pre-1.109 flat `.json` session from an empty window on a remote host."""
    t = VSCODE_T0 - 3600000
    return {
        "version": 3,
        "sessionId": VSCODE_LEGACY_SESSION,
        "creationDate": t,
        "initialLocation": "panel",
        "responderUsername": "GitHub Copilot",
        "workingDirectory": "file://%s" % cwd,
        "requests": [
            {
                "requestId": "request_1",
                "timestamp": t + 1000,
                "message": "where is the config?",
                "modelId": "copilot/gpt-4o",
                "response": ["It is in ", "config.toml."],
                "responseTimestamp": t + 2000,
                "result": {"errorDetails": {"message": "Rate limited"}},
            }
        ],
    }


def build_vscode(home: Path) -> None:
    ws = home / VSCODE_WS
    _jsonl(ws / "chatSessions" / (VSCODE_SESSION + ".jsonl"), vscode_log_records())
    (ws / "workspace.json").write_text(json.dumps({"folder": "file:///srv/proj"}), encoding="utf-8")
    (home / ".config/Code/User/settings.json").write_text(
        '{"chat.useLogSessionStorage": true}', encoding="utf-8"
    )
    legacy = home / ".vscode-server/data/User/globalStorage/emptyWindowChatSessions"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / (VSCODE_LEGACY_SESSION + ".json")).write_text(
        json.dumps(vscode_legacy_session(), indent=2), encoding="utf-8"
    )


# ---- OpenCode and Kilo Code ---------------------------------------------------------
# Shapes from analyzer/research/opencode.md and kilo-code.md (drizzle tables in
# packages/core/src/session/sql.ts, JSON in packages/schema/src/v1/session.ts).

OPENCODE_SESSION = "ses_01OC"
OPENCODE_V2_SESSION = "ses_02OCV2"
OPENCODE_LEGACY_SESSION = "ses_00LEGACY"
OPENCODE_T0 = 1791018000000  # 2026-10-03T09:00:00Z, ms
KILO_SESSION = "ses_01JAX"
KILO_TASK = "8f1c2b7e-1"
KILO_T0 = 1791021600000  # 2026-10-03T10:00:00Z, ms

OPENCODE_SCHEMA = """
CREATE TABLE project (id text PRIMARY KEY, worktree text NOT NULL, vcs text, name text, icon_url text, icon_color text,
  time_created integer NOT NULL, time_updated integer NOT NULL, time_initialized integer, sandboxes text NOT NULL);
CREATE TABLE session (id text PRIMARY KEY, project_id text NOT NULL, workspace_id text, parent_id text, slug text NOT NULL,
  directory text NOT NULL, path text, title text NOT NULL, version text NOT NULL, share_url text, summary_additions integer,
  summary_deletions integer, summary_files integer, summary_diffs text, metadata text, cost real, tokens_input integer,
  tokens_output integer, tokens_reasoning integer, tokens_cache_read integer, tokens_cache_write integer, revert text,
  permission text, agent text, model text, time_created integer NOT NULL, time_updated integer NOT NULL,
  time_compacting integer, time_archived integer);
CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL, time_created integer NOT NULL,
  time_updated integer NOT NULL, data text NOT NULL);
CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL, time_created integer NOT NULL,
  time_updated integer NOT NULL, data text NOT NULL);
CREATE INDEX part_message_id_id_idx ON part (message_id, id);
CREATE TABLE session_message (id text PRIMARY KEY, session_id text NOT NULL, type text NOT NULL, seq integer NOT NULL,
  time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL);
CREATE TABLE credential (id text PRIMARY KEY, provider_id text, type text, name text, value text NOT NULL, account_id text,
  workspace_id text, active integer, time_created integer NOT NULL, time_updated integer NOT NULL);
"""


def _oc_session(con, sid, project_id, directory, title, t, parent=None, model=None):
    con.execute(
        "INSERT INTO session (id, project_id, parent_id, slug, directory, title, version, agent, model, "
        "time_created, time_updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            sid,
            project_id,
            parent,
            title.lower().replace(" ", "-"),
            directory,
            title,
            "1.2.0",
            "build",
            json.dumps(model) if model else None,
            t,
            t + 5000,
        ),
    )


def _oc_message(con, mid, sid, t, data):
    con.execute("INSERT INTO message VALUES (?,?,?,?,?)", (mid, sid, t, t, json.dumps(data)))


def _oc_part(con, pid, mid, sid, t, data):
    con.execute("INSERT INTO part VALUES (?,?,?,?,?,?)", (pid, mid, sid, t, t, json.dumps(data)))


def opencode_assistant(t, cwd="/srv/proj", model="claude-sonnet-4", **extra):
    d = {
        "role": "assistant",
        "time": {"created": t, "completed": t + 3000},
        "parentID": "msg_01",
        "modelID": model,
        "providerID": "anthropic",
        "mode": "build",
        "agent": "build",
        "path": {"cwd": cwd, "root": cwd},
        "cost": 0.01,
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    d.update(extra)
    return d


def build_opencode_db(db: Path, t0: int = OPENCODE_T0) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(OPENCODE_SCHEMA)
    con.execute(
        "INSERT INTO project (id, worktree, vcs, time_created, time_updated, sandboxes) VALUES (?,?,?,?,?,?)",
        ("proj_a1", "/srv/proj", "git", t0, t0, "[]"),
    )
    _oc_session(con, OPENCODE_SESSION, "proj_a1", "/srv/proj", "Fix bug", t0)
    _oc_message(
        con,
        "msg_01",
        OPENCODE_SESSION,
        t0 + 1000,
        {
            "role": "user",
            "time": {"created": t0 + 1000},
            "agent": "build",
            "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4"},
        },
    )
    _oc_part(
        con, "prt_01", "msg_01", OPENCODE_SESSION, t0 + 1000, {"type": "text", "text": "list files"}
    )
    _oc_part(
        con,
        "prt_01b",
        "msg_01",
        OPENCODE_SESSION,
        t0 + 1000,
        {"type": "text", "text": "<system-reminder>plan mode</system-reminder>", "synthetic": True},
    )
    _oc_message(con, "msg_02", OPENCODE_SESSION, t0 + 2000, opencode_assistant(t0 + 2000))
    _oc_part(
        con,
        "prt_02",
        "msg_02",
        OPENCODE_SESSION,
        t0 + 2000,
        {"type": "step-start", "snapshot": "abc123"},
    )
    _oc_part(
        con,
        "prt_03",
        "msg_02",
        OPENCODE_SESSION,
        t0 + 2100,
        {
            "type": "reasoning",
            "text": "user wants a listing",
            "time": {"start": t0 + 2100, "end": t0 + 2200},
        },
    )
    _oc_part(
        con,
        "prt_04",
        "msg_02",
        OPENCODE_SESSION,
        t0 + 2500,
        {
            "type": "tool",
            "callID": "call_x1",
            "tool": "bash",
            "state": {
                "status": "completed",
                "input": {"command": "ls"},
                "output": "a.txt",
                "title": "ls",
                "metadata": {},
                "time": {"start": t0 + 2500, "end": t0 + 3000},
            },
        },
    )
    _oc_part(
        con,
        "prt_05",
        "msg_02",
        OPENCODE_SESSION,
        t0 + 3500,
        {
            "type": "text",
            "text": "There is one file, a.txt.",
            "time": {"start": t0 + 3500, "end": t0 + 3600},
        },
    )
    _oc_part(
        con,
        "prt_06",
        "msg_02",
        OPENCODE_SESSION,
        t0 + 4000,
        {
            "type": "step-finish",
            "reason": "stop",
            "cost": 0.01,
            "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
        },
    )
    # A session present only in the V2 session_message projection.
    _oc_session(con, OPENCODE_V2_SESSION, "proj_a1", "/srv/proj", "Run tests", t0 + 10000)
    con.execute(
        "INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
        (
            "msg_v2u",
            OPENCODE_V2_SESSION,
            "user",
            1,
            t0 + 11000,
            t0 + 11000,
            json.dumps({"id": "msg_v2u", "time": {"created": t0 + 11000}, "text": "run the tests"}),
        ),
    )
    con.execute(
        "INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
        (
            "msg_v2a",
            OPENCODE_V2_SESSION,
            "assistant",
            2,
            t0 + 12000,
            t0 + 14000,
            json.dumps(
                {
                    "id": "msg_v2a",
                    "agent": "build",
                    "model": {"id": "gpt-5", "providerID": "openai"},
                    "content": [
                        {"type": "text", "id": "c1", "text": "Running them."},
                        {
                            "type": "tool",
                            "id": "call_v2",
                            "name": "bash",
                            "state": {
                                "status": "completed",
                                "input": {"command": "pytest -q"},
                                "content": [{"type": "text", "text": "3 passed"}],
                                "structured": {},
                            },
                            "time": {"created": t0 + 12500, "completed": t0 + 13000},
                        },
                    ],
                    "time": {"created": t0 + 12000, "completed": t0 + 14000},
                }
            ),
        ),
    )
    con.execute(
        "INSERT INTO credential (id, provider_id, type, name, value, active, time_created, time_updated) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            "cred_01",
            "anthropic",
            "key",
            "my key",
            '{"type":"key","key":"sk-ant-REDACT"}',
            1,
            t0,
            t0,
        ),
    )
    con.commit()
    con.close()


def _json_file(path: Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def build_opencode_storage(storage: Path, t0: int = OPENCODE_T0 - 86400000) -> None:
    """The legacy JSON tree: ids inline, one file per record."""
    sid = OPENCODE_LEGACY_SESSION
    _json_file(
        storage / "project/proj_a1.json",
        {"id": "proj_a1", "vcs": "git", "worktree": "/srv/proj", "time": {"created": t0}},
    )
    _json_file(
        storage / "session/proj_a1" / (sid + ".json"),
        {
            "id": sid,
            "projectID": "proj_a1",
            "directory": "/srv/proj",
            "title": "Old session",
            "version": "0.9.0",
            "time": {"created": t0, "updated": t0 + 5000},
        },
    )
    _json_file(
        storage / "message" / sid / "msg_a.json",
        {
            "id": "msg_a",
            "sessionID": sid,
            "role": "user",
            "time": {"created": t0 + 1000},
            "agent": "build",
            "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4"},
        },
    )
    _json_file(
        storage / "part/msg_a/prt_a1.json",
        {
            "id": "prt_a1",
            "sessionID": sid,
            "messageID": "msg_a",
            "type": "text",
            "text": "cat the secrets file",
        },
    )
    _json_file(
        storage / "message" / sid / "msg_b.json",
        dict(
            opencode_assistant(t0 + 2000),
            id="msg_b",
            sessionID=sid,
            error={"name": "APIError", "data": {"message": "overloaded"}},
        ),
    )
    _json_file(
        storage / "part/msg_b/prt_b1.json",
        {
            "id": "prt_b1",
            "sessionID": sid,
            "messageID": "msg_b",
            "type": "tool",
            "callID": "call_r1",
            "tool": "read",
            "state": {
                "status": "error",
                "input": {"filePath": "/srv/proj/.env"},
                "error": "permission denied",
                "time": {"start": t0 + 2500, "end": t0 + 2600},
            },
        },
    )
    _json_file(
        storage / "part/msg_b/prt_b2.json",
        {
            "id": "prt_b2",
            "sessionID": sid,
            "messageID": "msg_b",
            "type": "text",
            "text": "I could not read it.",
            "time": {"start": t0 + 2700},
        },
    )
    (storage / "migration").write_text("2", encoding="utf-8")


def build_opencode(home: Path) -> None:
    data = home / ".local/share/opencode"
    build_opencode_db(data / "opencode.db")
    build_opencode_storage(data / "storage")
    (data / "auth.json").write_text(
        '{"anthropic":{"type":"api","key":"sk-ant-REDACT"}}', encoding="utf-8"
    )
    _json_file(
        home / ".config/opencode/opencode.json", {"$schema": "https://opencode.ai/config.json"}
    )


def kilo_task_records(t0: int = KILO_T0 - 86400000):
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "<task>fix tests</task>"},
                {
                    "type": "text",
                    "text": "<environment_details>cwd /srv/proj</environment_details>",
                },
            ],
            "ts": t0 + 1000,
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Running the suite."},
                {
                    "type": "tool_use",
                    "id": "toolu_01A",
                    "name": "execute_command",
                    "input": {"command": "pytest -q"},
                },
            ],
            "ts": t0 + 2000,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01A",
                    "content": "3 passed",
                    "is_error": False,
                }
            ],
            "ts": t0 + 3000,
        },
        {
            "type": "reasoning",
            "summary": [{"type": "summary_text", "text": "tests pass"}],
            "ts": t0 + 3500,
        },
        {"role": "assistant", "content": "All three tests pass.", "ts": t0 + 4000},
    ]


def build_kilo(home: Path) -> None:
    data = home / ".local/share/kilo"
    db = data / "kilo.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(OPENCODE_SCHEMA)
    t0 = KILO_T0
    con.execute(
        "INSERT INTO project (id, worktree, vcs, time_created, time_updated, sandboxes) VALUES (?,?,?,?,?,?)",
        ("prj_01JAX", "/srv/proj", "git", t0, t0, "[]"),
    )
    _oc_session(
        con,
        KILO_SESSION,
        "prj_01JAX",
        "/srv/proj",
        "fix tests",
        t0,
        model={"id": "claude-sonnet-4-5", "providerID": "anthropic"},
    )
    _oc_message(
        con,
        "msg_01JAXU",
        KILO_SESSION,
        t0 + 1000,
        {
            "role": "user",
            "time": {"created": t0 + 1000},
            "agent": "build",
            "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4-5"},
        },
    )
    _oc_part(
        con,
        "prt_01JAXP",
        "msg_01JAXU",
        KILO_SESSION,
        t0 + 1000,
        {"type": "text", "text": "fix the tests"},
    )
    _oc_message(
        con,
        "msg_01JAXA",
        KILO_SESSION,
        t0 + 2000,
        dict(opencode_assistant(t0 + 2000, model="claude-sonnet-4-5"), parentID="msg_01JAXU"),
    )
    _oc_part(
        con,
        "prt_01JAXT",
        "msg_01JAXA",
        KILO_SESSION,
        t0 + 2500,
        {
            "type": "tool",
            "callID": "call_1",
            "tool": "bash",
            "state": {
                "status": "completed",
                "input": {"command": "pytest -q"},
                "output": "3 passed",
                "title": "pytest -q",
                "metadata": {},
                "time": {"start": t0 + 2500, "end": t0 + 3000},
            },
        },
    )
    # Kilo writes the V2 projection alongside V1; it must not duplicate the rows.
    con.execute(
        "INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
        (
            "msg_01JAXB",
            KILO_SESSION,
            "assistant",
            4,
            t0 + 2000,
            t0 + 3000,
            json.dumps(
                {
                    "agent": "build",
                    "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4-5"},
                    "content": [
                        {
                            "type": "tool",
                            "id": "call_1",
                            "name": "bash",
                            "state": {
                                "status": "completed",
                                "input": {"command": "pytest -q"},
                                "content": [{"type": "text", "text": "3 passed"}],
                                "structured": {},
                            },
                            "time": {"created": t0 + 2500, "completed": t0 + 3000},
                        }
                    ],
                    "time": {"created": t0 + 2000, "completed": t0 + 3000},
                }
            ),
        ),
    )
    con.commit()
    con.close()
    (data / "auth.json").write_text('{"kilo":{"type":"oauth","access":"REDACT"}}', encoding="utf-8")
    tasks = home / ".config/Code/User/globalStorage/kilocode.kilo-code/tasks"
    task = tasks / KILO_TASK
    task.mkdir(parents=True, exist_ok=True)
    (task / "api_conversation_history.json").write_text(
        json.dumps(kilo_task_records()), encoding="utf-8"
    )
    (task / "ui_messages.json").write_text("[]", encoding="utf-8")
    _json_file(
        tasks / "_index.json",
        {
            "version": 1,
            "updatedAt": KILO_T0 - 86395000,
            "entries": [
                {
                    "id": KILO_TASK,
                    "number": 1,
                    "ts": KILO_T0 - 86400000,
                    "task": "fix tests",
                    "tokensIn": 1200,
                    "tokensOut": 80,
                    "totalCost": 0.0041,
                    "workspace": "/srv/proj",
                    "mode": "code",
                    "status": "completed",
                }
            ],
        },
    )


# ---- Cline and Roo Code (research/cline.md, research/roo-code.md) ----------------

CLINE_TASK = "1791021600000"  # 2026-10-03T10:00:00Z, a Date.now() id
CLINE_CLI_TASK = "1791021300000"  # API history only, no ui_messages.json
CLINE_SESSION = "1791021700000_k3x9q"
CLINE_OLD_SESSION = "1791000000000_old01"
ROO_TASK = "8f1c2b7e-0000-4000-8000-000000000001"
ROO_CLI_TASK = "8f1c2b7e-0000-4000-8000-000000000002"
ROO_GONE_TASK = "8f1c2b7e-0000-4000-8000-000000000003"
CLINE_T0 = 1791021600000


def _json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def cline_ui_records(t0=CLINE_T0):
    model = {"modelId": "claude-sonnet-4-5", "providerId": "anthropic", "mode": "act"}
    return [
        {
            "ts": t0,
            "type": "say",
            "say": "task",
            "text": "fix tests",
            "images": ["data:image/png;base64,AAAA"],
        },
        {
            "ts": t0 + 1000,
            "type": "say",
            "say": "api_req_started",
            "text": json.dumps(
                {
                    "request": "<task>fix tests</task>",
                    "tokensIn": 1200,
                    "tokensOut": 80,
                    "cacheWrites": 0,
                    "cacheReads": 900,
                    "cost": 0.0041,
                }
            ),
        },
        {
            "ts": t0 + 1500,
            "type": "say",
            "say": "reasoning",
            "text": "read the test first",
            "partial": False,
        },
        {
            "ts": t0 + 2000,
            "type": "say",
            "say": "tool",
            "modelInfo": model,
            "text": json.dumps(
                {"tool": "readFile", "path": "src/app.py", "content": "/srv/proj/src/app.py"}
            ),
        },
        {
            "ts": t0 + 3000,
            "type": "say",
            "say": "text",
            "text": "Running the suite.",
            "modelInfo": model,
        },
        {"ts": t0 + 4000, "type": "ask", "ask": "command", "text": "pytest -q", "modelInfo": model},
        {"ts": t0 + 5000, "type": "say", "say": "command_output", "text": "3 passed"},
        {
            "ts": t0 + 6000,
            "type": "say",
            "say": "checkpoint_created",
            "lastCheckpointHash": "abc123",
        },
        {
            "ts": t0 + 7000,
            "type": "say",
            "say": "completion_result",
            "text": "All tests pass.",
            "modelInfo": model,
        },
        {"ts": t0 + 7001, "type": "ask", "ask": "completion_result", "text": ""},
    ]


def cline_api_records():
    return [
        {"role": "user", "content": [{"type": "text", "text": "<task>fix tests</task>"}]},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "run the suite"},
                {
                    "type": "tool_use",
                    "id": "toolu_01A",
                    "name": "execute_command",
                    "input": {"command": "pytest -q"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01A",
                    "content": "3 passed",
                    "is_error": False,
                }
            ],
        },
    ]


def cline_task_metadata(t0=CLINE_T0):
    return {
        "files_in_context": [
            {
                "path": "src/app.py",
                "record_state": "active",
                "record_source": "read_tool",
                "cline_read_date": t0 + 2000,
                "cline_edit_date": None,
            },
        ],
        "model_usage": [
            {
                "ts": t0 + 500,
                "model_id": "claude-sonnet-4-5",
                "model_provider_id": "anthropic",
                "mode": "act",
            }
        ],
        "environment_history": [
            {
                "ts": t0 + 100,
                "os_name": "linux",
                "os_version": "6.6",
                "os_arch": "x64",
                "host_name": "Visual Studio Code",
                "host_version": "1.105.0",
                "cline_version": "3.40.0",
            }
        ],
    }


def cline_history_items():
    return [
        {
            "id": CLINE_TASK,
            "ulid": "01JAX3Q8M4",
            "ts": CLINE_T0 + 7001,
            "task": "fix tests",
            "tokensIn": 1200,
            "tokensOut": 80,
            "totalCost": 0.0041,
            "cwdOnTaskInitialization": "/srv/proj",
            "modelId": "claude-sonnet-4-5",
            "apiProvider": "anthropic",
        },
    ]


def cline_sdk_manifest():
    return {
        "version": 1,
        "session_id": CLINE_SESSION,
        "source": "cli",
        "pid": 4242,
        "started_at": "2026-10-03T10:01:40.000Z",
        "ended_at": "2026-10-03T10:01:50.000Z",
        "exit_code": 0,
        "status": "completed",
        "interactive": True,
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "cwd": "/srv/proj",
        "workspace_root": "/srv/proj",
        "enable_tools": True,
        "enable_spawn": False,
        "enable_teams": False,
        "prompt": "fix tests",
        "metadata": {"title": "fix tests"},
        "messages_path": "/home/u/.cline/data/sessions/%s/%s.messages.json"
        % (CLINE_SESSION, CLINE_SESSION),
    }


def cline_sdk_messages(t0=CLINE_T0 + 100000):
    return {
        "version": 1,
        "updated_at": "2026-10-03T10:01:50.000Z",
        "agent": "lead",
        "sessionId": CLINE_SESSION,
        "origin": {"source": "cli", "mode": "user", "sessionId": CLINE_SESSION},
        "system_prompt": "You are Cline.",
        "messages": [
            {"id": "m1", "role": "user", "content": "fix tests", "ts": t0},
            {
                "id": "m2",
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "run the suite"},
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "bash",
                        "input": {"command": "pytest -q"},
                    },
                ],
                "modelInfo": {"id": "claude-sonnet-4-5", "provider": "anthropic"},
                "metrics": {"inputTokens": 1200, "outputTokens": 80, "cost": 0.0041},
                "ts": t0 + 2000,
            },
            {
                "id": "m3",
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "name": "bash",
                        "content": "3 passed",
                        "is_error": False,
                    }
                ],
                "ts": t0 + 3000,
            },
            {"id": "m4", "role": "assistant", "content": [{"type": "text", "text": "Fixed."}]},
        ],
    }


def build_cline(home: Path) -> None:
    gs = home / ".config/Code/User/globalStorage/saoudrizwan.claude-dev"
    task = gs / "tasks" / CLINE_TASK
    _json(task / "ui_messages.json", cline_ui_records())
    _json(task / "api_conversation_history.json", cline_api_records())
    _json(task / "task_metadata.json", cline_task_metadata())
    _json(gs / "state/taskHistory.json", cline_history_items())
    _json(gs / "settings/cline_mcp_settings.json", {"mcpServers": {}})
    data = home / ".cline/data"
    _json(data / "tasks" / CLINE_CLI_TASK / "api_conversation_history.json", cline_api_records())
    _json(
        data / "state/taskHistory.json",
        [dict(cline_history_items()[0], id=CLINE_CLI_TASK, ts=1791021305000)],
    )
    _json(data / "secrets.json", {"apiKey": "sk-not-real"})
    sess = data / "sessions" / CLINE_SESSION
    _json(sess / (CLINE_SESSION + ".json"), cline_sdk_manifest())
    _json(sess / (CLINE_SESSION + ".messages.json"), cline_sdk_messages())
    _json(sess / (CLINE_SESSION + ".compaction.json"), {"version": 1})
    (data / "db").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(data / "db/sessions.db"))
    con.execute(
        "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, source TEXT, pid INTEGER, started_at TEXT, "
        "ended_at TEXT, exit_code INTEGER, status TEXT, interactive INTEGER, provider TEXT, model TEXT, "
        "cwd TEXT, workspace_root TEXT, prompt TEXT, metadata_json TEXT, is_subagent INTEGER, "
        "parent_session_id TEXT, updated_at TEXT)"
    )
    for sid, started, prompt in (
        (CLINE_SESSION, "2026-10-03T10:01:40.000Z", "fix tests"),
        (CLINE_OLD_SESSION, "2026-10-02T23:00:00.000Z", "an older deleted session"),
    ):
        con.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                "cli",
                4242,
                started,
                None,
                None,
                "completed",
                1,
                "anthropic",
                "claude-sonnet-4-5",
                "/srv/proj",
                "/srv/proj",
                prompt,
                json.dumps({"title": prompt}),
                0,
                None,
                started,
            ),
        )
    con.commit()
    con.close()


def roo_ui_records(t0=CLINE_T0 + 200000):
    return [
        {"ts": t0, "type": "say", "say": "text", "text": "rename the helper"},
        {
            "ts": t0 + 1000,
            "type": "say",
            "say": "api_req_started",
            "text": json.dumps(
                {
                    "request": "rename the helper",
                    "tokensIn": 900,
                    "tokensOut": 40,
                    "cost": 0.002,
                    "apiProtocol": "anthropic",
                }
            ),
        },
        {
            "ts": t0 + 2000,
            "type": "ask",
            "ask": "tool",
            "text": json.dumps(
                {"tool": "appliedDiff", "path": "src/util.py", "diff": "-old\n+new"}
            ),
        },
        {"ts": t0 + 3000, "type": "ask", "ask": "command", "text": "pytest -q"},
        {"ts": t0 + 4000, "type": "ask", "ask": "command_output", "text": "1 passed"},
        {
            "ts": t0 + 5000,
            "type": "say",
            "say": "condense_context",
            "partial": False,
            "contextCondense": {
                "cost": 0.001,
                "prevContextTokens": 9000,
                "newContextTokens": 1200,
                "summary": "Renamed helper; tests pass.",
                "condenseId": "c1",
            },
        },
        {
            "ts": t0 + 6000,
            "type": "ask",
            "ask": "followup",
            "text": json.dumps(
                {"question": "Commit now?", "suggest": [{"answer": "yes"}, {"answer": "no"}]}
            ),
        },
        {"ts": t0 + 7000, "type": "say", "say": "user_feedback", "text": "yes"},
        {
            "ts": t0 + 8000,
            "type": "say",
            "say": "completion_result",
            "text": "Renamed and committed.",
        },
    ]


def roo_api_records(t0=CLINE_T0 + 300000):
    return [
        {"role": "user", "content": [{"type": "text", "text": "<task>fix tests</task>"}], "ts": t0},
        {
            "type": "reasoning",
            "summary": [{"type": "summary_text", "text": "check the runner"}],
            "encrypted_content": "gAAAA",
            "ts": t0 + 1000,
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_01A",
                    "name": "execute_command",
                    "input": {"command": "pytest -q"},
                }
            ],
            "ts": t0 + 2000,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01A",
                    "content": "3 passed",
                    "is_error": False,
                }
            ],
            "ts": t0 + 3000,
        },
    ]


def roo_history_item(task_id, ts, task, workspace="/srv/proj"):
    return {
        "id": task_id,
        "number": 1,
        "ts": ts,
        "task": task,
        "tokensIn": 1200,
        "tokensOut": 80,
        "totalCost": 0.0041,
        "workspace": workspace,
        "mode": "code",
        "status": "completed",
    }


def build_roo_code(home: Path) -> None:
    gs = home / ".config/Code/User/globalStorage/rooveterinaryinc.roo-cline"
    task = gs / "tasks" / ROO_TASK
    _json(task / "ui_messages.json", roo_ui_records())
    _json(task / "api_conversation_history.json", roo_api_records())
    _json(
        task / "history_item.json",
        roo_history_item(ROO_TASK, CLINE_T0 + 208000, "rename the helper"),
    )
    _json(
        task / "task_metadata.json",
        {
            "files_in_context": [
                {
                    "path": "src/util.py",
                    "record_state": "active",
                    "record_source": "roo_edited",
                    "roo_read_date": CLINE_T0 + 202000,
                    "roo_edit_date": CLINE_T0 + 202500,
                    "user_edit_date": None,
                }
            ]
        },
    )
    _json(
        gs / "tasks/_index.json",
        {
            "version": 1,
            "updatedAt": CLINE_T0 + 208000,
            "entries": [
                roo_history_item(ROO_TASK, CLINE_T0 + 208000, "rename the helper"),
                roo_history_item(ROO_GONE_TASK, CLINE_T0 - 3600000, "a task deleted from disk"),
            ],
        },
    )
    mock = home / ".vscode-mock/global-storage"
    _json(mock / "tasks" / ROO_CLI_TASK / "api_conversation_history.json", roo_api_records())
    _json(
        mock / "tasks" / ROO_CLI_TASK / "history_item.json",
        roo_history_item(ROO_CLI_TASK, CLINE_T0 + 303000, "fix tests"),
    )
    _json(mock / "secrets.json", {"roo_cline_config_api_config": '{"apiKey":"sk-not-real"}'})


# Tabby: ee/tabby-db/schema/schema.sql at 21b2904 (research/tabby.md section 3),
# trimmed to the tables the parser reads plus every table that holds a secret,
# so the tests can prove those are never read.
TABBY_SCHEMA = """
CREATE TABLE registration_token(id INTEGER PRIMARY KEY AUTOINCREMENT, token VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT(DATETIME('now')), updated_at TIMESTAMP DEFAULT(DATETIME('now')));
CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, email VARCHAR(150) NOT NULL COLLATE NOCASE,
  is_admin BOOLEAN NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT(DATETIME('now')),
  updated_at TIMESTAMP DEFAULT(DATETIME('now')), auth_token VARCHAR(128) NOT NULL, active BOOLEAN NOT NULL DEFAULT 1,
  password_encrypted VARCHAR(128), avatar BLOB DEFAULT NULL, name VARCHAR(255));
CREATE TABLE refresh_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
  token VARCHAR(255) NOT NULL COLLATE NOCASE, expires_at TIMESTAMP NOT NULL, created_at TIMESTAMP DEFAULT(DATETIME('now')));
CREATE TABLE integrations(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, display_name TEXT NOT NULL,
  access_token TEXT NOT NULL, api_base TEXT, error TEXT, created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')),
  updated_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), synced BOOLEAN NOT NULL DEFAULT FALSE);
CREATE TABLE email_setting(id INTEGER PRIMARY KEY AUTOINCREMENT, smtp_username VARCHAR(255) NOT NULL,
  smtp_password VARCHAR(255) NOT NULL, smtp_server VARCHAR(255) NOT NULL, from_address VARCHAR(255) NOT NULL,
  encryption VARCHAR(255) NOT NULL DEFAULT 'ssltls', auth_method VARCHAR(255) NOT NULL DEFAULT 'plain',
  smtp_port INTEGER NOT NULL DEFAULT 25);
CREATE TABLE oauth_credential(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, provider TEXT NOT NULL,
  client_id VARCHAR(256) NOT NULL, client_secret VARCHAR(64) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')),
  updated_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), config_url VARCHAR(256), config_scopes VARCHAR(256));
CREATE TABLE ldap_credential(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, host STRING NOT NULL,
  port INTEGER NOT NULL DEFAULT 389, bind_dn STRING NOT NULL, bind_password STRING NOT NULL, base_dn STRING NOT NULL,
  user_filter STRING NOT NULL, encryption STRING NOT NULL DEFAULT 'none', skip_tls_verify BOOLEAN NOT NULL DEFAULT FALSE,
  email_attribute STRING NOT NULL DEFAULT 'email', name_attribute STRING,
  created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), updated_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')));
CREATE TABLE user_events(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), payload BLOB NOT NULL);
CREATE TABLE threads(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, is_ephemeral BOOLEAN NOT NULL, user_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), updated_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')),
  relevant_questions BLOB);
CREATE TABLE thread_messages(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, thread_id INTEGER NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')),
  updated_at TIMESTAMP NOT NULL DEFAULT(DATETIME('now')), code_source_id VARCHAR(255), attachment BLOB NOT NULL DEFAULT '{}');
"""

# One distinct value per plaintext secret column; none may reach any output.
TABBY_SECRETS = (
    "auth_REDACT_tok",
    "pw_hash_REDACT",
    "regtok_REDACT",
    "refresh_REDACT",
    "ghp_REDACT_integration",
    "smtp_REDACT_pw",
    "oauth_REDACT_secret",
    "ldap_REDACT_bind",
)


def tabby_secret_records():
    s = TABBY_SECRETS
    return [
        "INSERT INTO users(id,email,is_admin,auth_token,active,name,password_encrypted) "
        "VALUES(1,'alice@example.com',1,'%s',1,'Alice','%s')" % (s[0], s[1]),
        "INSERT INTO registration_token(id,token) VALUES(1,'%s')" % s[2],
        "INSERT INTO refresh_tokens(user_id,token,expires_at) VALUES(1,'%s','2026-12-01 00:00:00')"
        % s[3],
        "INSERT INTO integrations(kind,display_name,access_token) VALUES('github','acme','%s')"
        % s[4],
        "INSERT INTO email_setting(smtp_username,smtp_password,smtp_server,from_address) "
        "VALUES('mailer','%s','smtp.example.com','tabby@example.com')" % s[5],
        "INSERT INTO oauth_credential(provider,client_id,client_secret) VALUES('github','cid','%s')"
        % s[6],
        "INSERT INTO ldap_credential(host,bind_dn,bind_password,base_dn,user_filter) "
        "VALUES('ldap.example.com','cn=admin','%s','dc=example','(uid=%%s)')" % s[7],
    ]


TABBY_SELECT_PAYLOAD = (
    '{\n  "select": {\n    "completion_id": "cmpl-7f3a",\n    "choice_index": 0,\n'
    '    "view_id": "view-1",\n    "elapsed": 1377\n  }\n}'
)


def tabby_records():
    """The INSERT statements of research/tabby.md section 8, with the
    research's single fixture token replaced by one per secret column, and a
    user_events row whose payload is the pretty JSON event_logger.rs writes."""
    return [
        *tabby_secret_records(),
        "INSERT INTO threads(id,is_ephemeral,user_id,created_at,updated_at,relevant_questions) "
        """VALUES(7,0,1,'2026-10-01 10:00:00','2026-10-01 10:00:09','["How is the cache invalidated?"]')""",
        "INSERT INTO thread_messages(id,thread_id,role,content,created_at,updated_at,attachment) VALUES "
        """(1,7,'user','Where is the cache cleared?','2026-10-01 10:00:00','2026-10-01 10:00:00','{"code":null,"client_code":[{"filepath":"src/cache.rs","start_line":10,"content":"fn clear()"}],"doc":null}'),"""
        """(2,7,'assistant','In `clear()` in src/cache.rs.','2026-10-01 10:00:02','2026-10-01 10:00:09','{"code":[{"git_url":"https://github.com/acme/app","commit":"abc123","language":"rust","filepath":"src/cache.rs","content":"fn clear() {}","start_line":10}],"client_code":null,"doc":null}')""",
        "INSERT INTO user_events(id,user_id,kind,created_at,payload) VALUES(1,1,'select','2026-10-01 10:00:01',"
        "'%s')" % TABBY_SELECT_PAYLOAD,
    ]


# A pre-0.25 backup: deprecated per-kind attachment columns, no `attachment`,
# and an ephemeral thread the live database has since deleted.
TABBY_BACKUP_SCHEMA = TABBY_SCHEMA.replace(
    "code_source_id VARCHAR(255), attachment BLOB NOT NULL DEFAULT '{}'",
    "code_source_id VARCHAR(255), code_attachments BLOB, client_code_attachments BLOB, doc_attachments BLOB",
)
TABBY_REL = ".tabby/ee/db.sqlite"
TABBY_BACKUP_REL = ".tabby/ee/db.backup-20260915.sqlite"
TABBY_EVENTS_REL = ".tabby/events/2025-10-01.json"


def tabby_backup_records():
    return [
        *tabby_secret_records(),
        "INSERT INTO threads(id,is_ephemeral,user_id,created_at,updated_at) "
        "VALUES(3,1,1,'2026-09-10 08:00:00','2026-09-10 08:00:04')",
        "INSERT INTO thread_messages(id,thread_id,role,content,created_at,updated_at,code_attachments) VALUES "
        "(1,3,'user','dump the users table','2026-09-10 08:00:00','2026-09-10 08:00:00',NULL),"
        """(2,3,'assistant','Run `select * from users`.','2026-09-10 08:00:04','2026-09-10 08:00:04','[{"git_url":"https://github.com/acme/ops","filepath":"db.sql","content":"select 1","language":"sql","start_line":null}]')""",
    ]


def tabby_event_records():
    """The two event log lines of research/tabby.md section 8 plus a
    chat_completion event, whose body is empty (routes/chat.rs:83)."""
    return [
        {
            "user": "1",
            "ts": 1759312800123,
            "event": {
                "completion": {
                    "completion_id": "cmpl-7f3a",
                    "language": "python",
                    "prompt": "def add(a, b):\n    ",
                    "segments": {
                        "prefix": "def add(a, b):\n    ",
                        "suffix": "\n",
                        "git_url": "https://github.com/acme/app",
                        "filepath": "app/math.py",
                    },
                    "choices": [{"index": 0, "text": "return a + b"}],
                    "user_agent": "tabby-agent/1.9",
                }
            },
        },
        {
            "user": "1",
            "ts": 1759312801500,
            "event": {
                "select": {
                    "completion_id": "cmpl-7f3a",
                    "choice_index": 0,
                    "view_id": "view-1",
                    "elapsed": 1377,
                }
            },
        },
        {"user": None, "ts": 1759312802000, "event": {"chat_completion": {}}},
    ]


def build_tabby(home: Path) -> None:
    """A Tabby server's home: the live WAL database, a pre-migration backup,
    one day of the event log, and the config file as noise."""
    _wal_db(home / TABBY_REL, TABBY_SCHEMA, tabby_records())
    con = sqlite3.connect(str(home / TABBY_BACKUP_REL))
    con.executescript(TABBY_BACKUP_SCHEMA)
    for sql in tabby_backup_records():
        con.execute(sql)
    con.commit()
    con.close()
    _jsonl(home / TABBY_EVENTS_REL, tabby_event_records())
    (home / ".tabby/config.toml").write_text(
        '[model.chat.http]\napi_key = "sk-tabby-test"\n', encoding="utf-8"
    )


OPENHANDS_CONV = "0f0e0d0c111140008000000000000001"
OPENHANDS_CLI_CONV = "0f0e0d0c111140008000000000000002"
OPENHANDS_LEGACY = "legacy-sid-1"


def openhands_meta(cwd="/srv/proj"):
    return {
        "id": "0f0e0d0c-1111-4000-8000-000000000001",
        "title": "List files",
        "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-01T10:00:05Z",
        "workspace": {"kind": "LocalWorkspace", "working_dir": cwd},
        "secrets": {"GITHUB_TOKEN": "**********"},
    }


def openhands_base_state(conv_id, cwd="/srv/proj"):
    return {
        "id": conv_id,
        "execution_status": "finished",
        "agent": {
            "kind": "Agent",
            "llm": {"model": "litellm_proxy/claude-sonnet-4-5", "api_key": "**********"},
        },
        "workspace": {"kind": "LocalWorkspace", "working_dir": cwd},
    }


def openhands_events(prefix="6b1d5c2e-0000-4000-8000-00000000000", day="2026-10-01T12:00:"):
    return [
        {
            "kind": "SystemPromptEvent",
            "id": prefix + "0",
            "timestamp": day + "00.500000",
            "source": "agent",
            "system_prompt": {"type": "text", "text": "You are OpenHands agent."},
            "tools": [{"kind": "TerminalTool"}, {"kind": "FileEditorTool"}],
        },
        {
            "kind": "MessageEvent",
            "id": prefix + "1",
            "timestamp": day + "01.000000",
            "source": "user",
            "llm_message": {
                "role": "user",
                "content": [{"type": "text", "text": "list the files"}],
            },
            "activated_skills": [],
            "extended_content": [],
        },
        {
            "kind": "ActionEvent",
            "id": prefix + "2",
            "timestamp": day + "03.000000",
            "source": "agent",
            "thought": [{"type": "text", "text": "I will run ls."}],
            "action": {"kind": "TerminalAction", "command": "ls"},
            "tool_name": "terminal",
            "tool_call_id": "call_1",
            "tool_call": {
                "id": "call_1",
                "name": "terminal",
                "arguments": '{"command":"ls"}',
                "origin": "completion",
            },
            "llm_response_id": "resp_1",
            "security_risk": "LOW",
        },
        {
            "kind": "ObservationEvent",
            "id": prefix + "3",
            "timestamp": day + "04.000000",
            "source": "environment",
            "tool_name": "terminal",
            "tool_call_id": "call_1",
            "action_id": prefix + "2",
            "observation": {
                "kind": "TerminalObservation",
                "content": [{"type": "text", "text": "README.md"}],
                "is_error": False,
                "command": "ls",
                "exit_code": 0,
            },
        },
        {
            "kind": "ActionEvent",
            "id": prefix + "4",
            "timestamp": day + "05.000000",
            "source": "agent",
            "thought": [],
            "reasoning_content": "check the readme",
            "action": {
                "kind": "FileEditorAction",
                "command": "view",
                "path": "/srv/proj/README.md",
            },
            "tool_name": "file_editor",
            "tool_call_id": "call_2",
            "tool_call": {
                "id": "call_2",
                "name": "file_editor",
                "arguments": '{"command":"view","path":"/srv/proj/README.md"}',
                "origin": "completion",
            },
        },
        {
            "kind": "UserRejectObservation",
            "id": prefix + "5",
            "timestamp": day + "06.000000",
            "source": "user",
            "tool_name": "file_editor",
            "tool_call_id": "call_2",
            "action_id": prefix + "4",
            "rejection_reason": "not that file",
            "rejection_source": "user",
        },
        {
            "kind": "MessageEvent",
            "id": prefix + "6",
            "timestamp": day + "07.000000",
            "source": "agent",
            "llm_message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "The project has a README."}],
            },
            "activated_skills": [],
            "extended_content": [],
        },
    ]


def _openhands_conversation(cdir: Path, events) -> None:
    for n, ev in enumerate(events):
        path = cdir / "events" / ("event-%05d-%s.json" % (n, ev["id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ev, separators=(",", ":")), encoding="utf-8")
    (cdir / "events" / (".eventlog-len-%d.marker" % len(events))).write_text("", encoding="utf-8")


def build_openhands(home: Path) -> None:
    oh = home / ".openhands"
    conv = oh / "agent-canvas/dev_conversations" / OPENHANDS_CONV
    _openhands_conversation(conv, openhands_events())
    _json_file(conv / "meta.json", openhands_meta())
    _json_file(conv / "base_state.json", openhands_base_state(OPENHANDS_CONV))
    # CLI conversation with no meta.json: naive times are emitted as if UTC.
    cli = oh / "conversations" / OPENHANDS_CLI_CONV
    _openhands_conversation(
        cli, openhands_events("7c2e6d3f-0000-4000-8000-00000000000", "2026-10-02T08:30:")[:4]
    )
    _json_file(cli / "base_state.json", openhands_base_state(OPENHANDS_CLI_CONV))
    legacy = oh / "sessions" / OPENHANDS_LEGACY / "events"
    for n in range(3):
        _json_file(
            legacy / ("%d.json" % n),
            {
                "id": n,
                "timestamp": "2026-03-01T09:00:0%d.000000" % n,
                "source": "user",
                "action": "message",
                "args": {"content": "hi"},
            },
        )
    _json_file(
        oh / "settings.json",
        {"llm_model": "anthropic/claude-sonnet-4-5", "llm_api_key": "sk-not-real"},
    )
    _json_file(oh / "secrets.json", {"custom_secrets": {"X": {"secret": "not-real"}}})


SHELLGPT_CHAT = "deploy-check"
SHELLGPT_LEGACY_CHAT = "old-functions"


def shellgpt_messages():
    return [
        {
            "role": "system",
            "content": "You are ShellGPT\nYou are programming and system administration assistant.",
        },
        {"role": "user", "content": "what is listening on port 8080"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_Q1w2e3r4",
                    "type": "function",
                    "function": {
                        "name": "execute_shell_command",
                        "arguments": '{"shell_command": "ss -ltnp | grep 8080"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": 'Exit code: 0, Output:\nLISTEN 0 4096 0.0.0.0:8080 users:(("python3",pid=4242))\n',
            "tool_call_id": "call_Q1w2e3r4",
        },
        {
            "role": "assistant",
            "content": '\n> @FunctionCall `execute_shell_command(shell_command="ss -ltnp | grep 8080")` '
            "\n\nA python3 process (PID 4242) is listening on 8080.",
        },
    ]


def shellgpt_legacy_messages():
    return [
        {"role": "system", "content": "You are ShellGPT"},
        {"role": "user", "content": "how much disk is free"},
        {
            "role": "assistant",
            "content": "",
            "function_call": {
                "name": "execute_shell_command",
                "arguments": '{"shell_command": "df -h /"}',
            },
        },
        {
            "role": "function",
            "content": "Exit code: 0, Output:\n/dev/sda1 50G 20G 30G 40% /\n",
            "name": "execute_shell_command",
        },
        {"role": "assistant", "content": "30G is free on /."},
    ]


def build_shellgpt(home: Path) -> None:
    temp = home / "AppData/Local/Temp"
    (temp / "chat_cache").mkdir(parents=True, exist_ok=True)
    (temp / "chat_cache" / SHELLGPT_CHAT).write_text(
        json.dumps(shellgpt_messages()), encoding="utf-8"
    )
    (temp / "shell_gpt/chat_cache").mkdir(parents=True, exist_ok=True)
    (temp / "shell_gpt/chat_cache" / SHELLGPT_LEGACY_CHAT).write_text(
        json.dumps(shellgpt_legacy_messages()), encoding="utf-8"
    )
    (temp / "shell_gpt/cache").mkdir(parents=True, exist_ok=True)
    (temp / "shell_gpt/cache/0cc175b9c0f1b6a831c399e269772661").write_text(
        "a cached response", encoding="utf-8"
    )
    cfg = home / ".config/shell_gpt"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / ".sgptrc").write_text(
        "OPENAI_API_KEY=sk-not-real\nDEFAULT_MODEL=gpt-4o\n", encoding="utf-8"
    )


# ---- pi, little-coder, letta (pi session format) --------------------------------

PI_SESSION = "0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a1b"
PI_FORK = "0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a2c"
PI_DIR = ".pi/agent/sessions/--srv-proj--/"
PI_FILE = "2026-10-01T09-00-00-000Z_%s.jsonl" % PI_SESSION
PI_FORK_FILE = "2026-10-01T09-30-00-000Z_%s.jsonl" % PI_FORK
LC_SESSION = "0b9e2f4c-1111-4000-8000-000000000001"
LC_FILE = "2026-10-01T11-00-00-000Z_%s.jsonl" % LC_SESSION
PI_EXPERIMENTAL = "exp-session-1"
LETTA_LOCAL_CONV = "local-conv-1"
LETTA_LOCAL_DIR = "Y29udmVyc2F0aW9uOmxvY2FsLWNvbnYtMQ"  # base64url("conversation:local-conv-1")
LETTA_AGENT = "agent-1a2b"
LETTA_CONV = "conv-9f"


def pi_session_records(cwd="/srv/proj"):
    return [
        {
            "type": "session",
            "version": 3,
            "id": PI_SESSION,
            "timestamp": "2026-10-01T09:00:00.000Z",
            "cwd": cwd,
        },
        {
            "type": "model_change",
            "id": "1a2b3c4d",
            "parentId": None,
            "timestamp": "2026-10-01T09:00:00.100Z",
            "provider": "anthropic",
            "modelId": "claude-sonnet-4-5",
        },
        {
            "type": "message",
            "id": "2b3c4d5e",
            "parentId": "1a2b3c4d",
            "timestamp": "2026-10-01T09:00:01.000Z",
            "message": {
                "role": "user",
                "content": "fix the failing test",
                "timestamp": 1790845201000,
            },
        },
        {
            "type": "message",
            "id": "3c4d5e6f",
            "parentId": "2b3c4d5e",
            "timestamp": "2026-10-01T09:00:04.000Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "run the tests first"},
                    {
                        "type": "toolCall",
                        "id": "toolu_01",
                        "name": "bash",
                        "arguments": {"command": "npm test"},
                    },
                ],
                "api": "anthropic-messages",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input": 900,
                    "output": 40,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 940,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                },
                "stopReason": "toolUse",
                "timestamp": 1790845204000,
            },
        },
        {
            "type": "message",
            "id": "4d5e6f70",
            "parentId": "3c4d5e6f",
            "timestamp": "2026-10-01T09:00:07.000Z",
            "message": {
                "role": "toolResult",
                "toolCallId": "toolu_01",
                "toolName": "bash",
                "content": [{"type": "text", "text": "1 failing"}],
                "isError": False,
                "timestamp": 1790845207000,
            },
        },
        {
            "type": "message",
            "id": "5e6f7081",
            "parentId": "4d5e6f70",
            "timestamp": "2026-10-01T09:00:09.000Z",
            "message": {
                "role": "bashExecution",
                "command": "git status",
                "output": "M src/a.ts",
                "exitCode": 0,
                "cancelled": False,
                "truncated": False,
                "timestamp": 1790845209000,
            },
        },
        {
            "type": "label",
            "id": "70819203",
            "parentId": "5e6f7081",
            "timestamp": "2026-10-01T09:00:09.500Z",
            "targetId": "2b3c4d5e",
            "label": "start",
        },
        {
            "type": "session_info",
            "id": "6f708192",
            "parentId": "5e6f7081",
            "timestamp": "2026-10-01T09:00:10.000Z",
            "name": "test fix",
        },
    ]


def pi_fork_records(parent_path):
    parent = pi_session_records()
    return [
        {
            "type": "session",
            "version": 3,
            "id": PI_FORK,
            "timestamp": "2026-10-01T09:30:00.000Z",
            "cwd": "/srv/proj",
            "parentSession": parent_path,
        },
        *parent[1:4],
        {
            "type": "message",
            "id": "8192a3b4",
            "parentId": "3c4d5e6f",
            "timestamp": "2026-10-01T09:30:05.000Z",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Trying another way."}],
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "stopReason": "stop",
                "timestamp": 1790847005000,
            },
        },
    ]


def little_coder_session_records(cwd="/srv/proj"):
    return [
        {
            "type": "session",
            "version": 3,
            "id": LC_SESSION,
            "timestamp": "2026-10-01T11:00:00.000Z",
            "cwd": cwd,
        },
        {
            "type": "custom_message",
            "id": "a1",
            "parentId": None,
            "timestamp": "2026-10-01T11:00:01.000Z",
            "customType": "lc-skills",
            "content": "## Skill: edit\nUse the edit tool.",
            "display": False,
        },
        {
            "type": "message",
            "id": "a2",
            "parentId": "a1",
            "timestamp": "2026-10-01T11:00:02.000Z",
            "message": {
                "role": "user",
                "content": "fix the failing test",
                "timestamp": 1790852402000,
            },
        },
        {
            "type": "message",
            "id": "a3",
            "parentId": "a2",
            "timestamp": "2026-10-01T11:00:05.000Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "run tests first"},
                    {
                        "type": "toolCall",
                        "id": "call_1",
                        "name": "bash",
                        "arguments": {"command": "npm test"},
                    },
                ],
                "api": "openai-completions",
                "provider": "llamacpp",
                "model": "qwen3.6-35b-a3b",
                "usage": {"input": 900, "output": 40, "cacheRead": 0, "cacheWrite": 0},
                "stopReason": "toolUse",
                "timestamp": 1790852405000,
            },
        },
        {
            "type": "message",
            "id": "a4",
            "parentId": "a3",
            "timestamp": "2026-10-01T11:00:09.000Z",
            "message": {
                "role": "toolResult",
                "toolCallId": "call_1",
                "toolName": "bash",
                "content": [{"type": "text", "text": "1 failing"}],
                "isError": False,
                "timestamp": 1790852409000,
            },
        },
    ]


def build_pi(home: Path) -> None:
    _jsonl(home / PI_DIR / PI_FILE, pi_session_records())
    _jsonl(home / PI_DIR / PI_FORK_FILE, pi_fork_records("/home/alice/" + PI_DIR + PI_FILE))
    _jsonl(home / PI_DIR / LC_FILE, little_coder_session_records())
    _json(
        home / ".pi/agent/experimental/sessions" / PI_EXPERIMENTAL / "meta.json",
        {"createdAt": 1790856000000, "cwd": "/srv/proj"},
    )
    _json(home / ".pi/agent/auth.json", {"anthropic": {"type": "api_key", "key": "sk-not-real"}})
    _json(home / ".pi/agent/settings.json", {"defaultProvider": "anthropic"})


def build_little_coder(home: Path) -> None:
    _json(
        home / ".pi/agent/little-coder-prompt-history.json",
        ["fix the failing test", "now run lint"],
    )
    ck = home / ".little-coder/checkpoints" / LC_FILE
    ck.mkdir(parents=True, exist_ok=True)
    (ck / "_srv_proj_src_a.ts").write_text("old contents\n", encoding="utf-8")
    (ck / "_srv_proj_src_new.ts.absent").write_text("", encoding="utf-8")
    os.utime(ck / "_srv_proj_src_a.ts", (1790852406, 1790852406))
    os.utime(ck / "_srv_proj_src_new.ts.absent", (1790852407, 1790852407))
    (home / ".config/little-coder").mkdir(parents=True, exist_ok=True)
    (home / ".config/little-coder/settings.json").write_text("{}", encoding="utf-8")


def letta_transcript_records():
    return [
        {
            "kind": "user",
            "text": "list the repo",
            "captured_at": "2026-10-01T12:00:05.120Z",
            "source_line_id": "ui-1",
        },
        {"kind": "reasoning", "text": "use ls", "captured_at": "2026-10-01T12:00:05.120Z"},
        {
            "kind": "tool_call",
            "name": "Bash",
            "argsText": '{"command":"ls"}',
            "resultText": "README.md",
            "resultOk": True,
            "captured_at": "2026-10-01T12:00:05.120Z",
            "source_line_id": "ui-2",
        },
        {
            "kind": "assistant",
            "text": "One file: README.md",
            "captured_at": "2026-10-01T12:00:05.120Z",
            "source_line_id": "ui-3",
            "source_message_id": "message-77",
        },
    ]


def letta_local_records(cwd="/srv/proj"):
    asst = {
        "id": "letta-msg-2",
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "use ls"},
            {"type": "toolCall", "id": "call_1", "name": "Bash", "arguments": {"command": "ls"}},
        ],
        "api": "anthropic-messages",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "usage": {
            "input": 10,
            "output": 5,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 15,
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
        },
        "stopReason": "toolUse",
        "timestamp": 1790856002000,
        "metadata": {"agent_id": LETTA_AGENT, "conversation_id": LETTA_LOCAL_CONV},
    }
    partial = dict(asst, content=[{"type": "thinking", "thinking": "use"}], stopReason="pending")
    return [
        {
            "type": "session",
            "version": 3,
            "id": LETTA_LOCAL_CONV,
            "timestamp": "2026-10-01T12:00:00.000Z",
            "cwd": cwd,
        },
        {
            "type": "message",
            "id": "a1b2c3d4",
            "parentId": None,
            "timestamp": "2026-10-01T12:00:01.000Z",
            "message": {
                "id": "letta-msg-1",
                "role": "user",
                "content": "list the repo",
                "timestamp": 1790856001000,
            },
        },
        {
            "type": "message",
            "id": "b2c3d4e4",
            "parentId": "a1b2c3d4",
            "timestamp": "2026-10-01T12:00:02.000Z",
            "message": partial,
        },
        {
            "type": "message",
            "id": "b2c3d4e5",
            "parentId": "a1b2c3d4",
            "timestamp": "2026-10-01T12:00:02.000Z",
            "message": asst,
        },
        {
            "type": "message",
            "id": "c3d4e5f6",
            "parentId": "b2c3d4e5",
            "timestamp": "2026-10-01T12:00:03.000Z",
            "message": {
                "id": "letta-msg-3",
                "role": "toolResult",
                "toolCallId": "call_1",
                "toolName": "Bash",
                "content": [{"type": "text", "text": "README.md"}],
                "isError": False,
                "timestamp": 1790856003000,
            },
        },
    ]


def letta_sessions_records(project="/srv/proj"):
    usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "steps": 0,
    }
    start = {
        "agent_id": LETTA_AGENT,
        "session_id": "s-1",
        "timestamp": 1790856000000,
        "project": project,
        "model": "claude-sonnet-4-5",
        "provider": "anthropic",
        "usage": usage,
        "duration": {"api_ms": 0, "wall_ms": 0},
        "cost": {"type": "hosted"},
    }
    older = dict(start, session_id="s-0", timestamp=1790766000000, project="/srv/old")
    end = dict(
        start,
        timestamp=1790856060000,
        duration={"api_ms": 900, "wall_ms": 60000},
        message_count=4,
        tool_call_count=1,
        exit_reason="user_exit",
    )
    return [older, start, end]


def build_letta(home: Path) -> None:
    letta = home / ".letta"
    _jsonl(
        letta / "transcripts" / LETTA_AGENT / LETTA_CONV / "transcript.jsonl",
        letta_transcript_records(),
    )
    _jsonl(
        letta / "transcripts" / LETTA_AGENT / LETTA_LOCAL_CONV / "transcript.jsonl",
        letta_transcript_records(),
    )
    _json(
        letta / "transcripts" / LETTA_AGENT / LETTA_CONV / "state.json",
        {"schema_version": "v3_assistant_steps"},
    )
    conv = letta / "lc-local-backend/conversations" / LETTA_LOCAL_DIR
    _jsonl(conv / "messages.jsonl", letta_local_records())
    _json(conv / "manifest.json", {"message_format": "pi-session-entry-jsonl", "schema_version": 2})
    _jsonl(letta / "sessions.jsonl", letta_sessions_records())
    _json(letta / "settings.json", {"env": {"LETTA_API_KEY": "sk-not-real"}})


HERMES_SESSION = "20261001_120000_a1b2c3d4"
HERMES_CHILD = "20261001_121500_e5f60708"
HERMES_DIVERTED = "20261001_130000_0badf00d"

# hermes_state_common.py:372-480 at hermes-agent 8b66a51, the columns
# research/hermes.md section 8 lists (schema version 31).
HERMES_SCHEMA = """
CREATE TABLE schema_version (version INTEGER NOT NULL);
CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, model TEXT,
  parent_session_id TEXT, started_at REAL NOT NULL, ended_at REAL, end_reason TEXT,
  cwd TEXT, git_branch TEXT, git_repo_root TEXT, title TEXT);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
  role TEXT NOT NULL, content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT,
  timestamp REAL NOT NULL, finish_reason TEXT, reasoning TEXT, reasoning_content TEXT,
  active INTEGER NOT NULL DEFAULT 1, compacted INTEGER NOT NULL DEFAULT 0);
"""


def hermes_records(cwd="/srv/proj"):
    """The INSERT statements of research/hermes.md section 8 with the shared
    project path, plus a rewound turn kept as active=0, a multimodal user
    message behind the NUL json prefix, and a subagent child session."""
    return [
        "INSERT INTO schema_version VALUES (31)",
        "INSERT INTO sessions VALUES ('%s','cli','anthropic/claude-sonnet-4',NULL,1790856000.0,NULL,NULL,"
        "'%s','main','%s','List files')" % (HERMES_SESSION, cwd, cwd),
        "INSERT INTO sessions VALUES ('%s','subagent','openai/gpt-5',"
        "'%s',1790856900.0,1790856910.0,'completed',NULL,NULL,'%s','Check disk')"
        % (HERMES_CHILD, HERMES_SESSION, cwd),
        "INSERT INTO messages (session_id,role,content,tool_call_id,tool_calls,tool_name,timestamp,finish_reason,reasoning) VALUES "
        "('%s','user','list files',NULL,NULL,NULL,1790856001.25,NULL,NULL),"
        % HERMES_SESSION
        + """('%s','assistant','',NULL,""" % HERMES_SESSION
        + """'[{"id":"call_1","call_id":"call_1","response_item_id":null,"type":"function","function":{"name":"terminal","arguments":"{\\"command\\":\\"ls\\"}"}}]',"""
        "NULL,1790856002.5,'tool_calls','User wants a listing.'),"
        "('%s','tool','a.txt' || char(10) || 'b.txt','call_1',NULL,'terminal',1790856003.0,NULL,NULL),"
        % HERMES_SESSION
        + "('%s','assistant','Two files: a.txt, b.txt.',NULL,NULL,NULL,1790856004.0,'stop',NULL)"
        % HERMES_SESSION,
        "INSERT INTO messages (session_id,role,content,timestamp,active,compacted) VALUES "
        "('%s','user','delete them instead',1790856005.0,0,1),"
        % HERMES_SESSION
        + """('%s','user',char(0) || 'json:[{"type":"text","text":"what is in this screenshot?"},"""
        """{"type":"image_url","image_url":{"url":"data:image/png;base64,AAAA"}}]',1790856006.0,1,0)"""
        % HERMES_SESSION,
        "INSERT INTO messages (session_id,role,content,timestamp) VALUES ('%s','user','df -h',1790856901.0)"
        % HERMES_CHILD,
    ]


def hermes_diverted_records():
    """sessions/<id>.jsonl: message dicts appended while state.db was
    replaced under a running process (hermes_state.py:429-444)."""
    return [
        {"role": "user", "content": "show the env", "timestamp": 1790859600.0},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_9",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path":"/srv/proj/.env"}'},
                }
            ],
            "timestamp": 1790859601.0,
        },
        {
            "role": "tool",
            "content": "TOKEN=x",
            "tool_call_id": "call_9",
            "tool_name": "read_file",
            "timestamp": 1790859602.0,
        },
    ]


HERMES_DIVERTED_REL = ".hermes/sessions/%s.jsonl" % HERMES_DIVERTED


def build_hermes(home: Path) -> None:
    hermes = home / ".hermes"
    _wal_db(hermes / "state.db", HERMES_SCHEMA, hermes_records())
    _jsonl(home / HERMES_DIVERTED_REL, hermes_diverted_records())
    (hermes / "config.yaml").write_text("model: anthropic/claude-sonnet-4\n", encoding="utf-8")
    (hermes / "auth.json").write_text(
        '{"providers": {"nous": {"access_token": "not-real"}}}', encoding="utf-8"
    )
    (hermes / "sessions/sessions.json").write_text("{}", encoding="utf-8")


AGENT_ZERO_CHAT = "AbCd1234"
AGENT_ZERO_REL = "agent-zero/usr/chats/%s/chat.json" % AGENT_ZERO_CHAT
AGENT_ZERO_LONG = "x" * 600


def _a0_message(mid, ai, content, metadata=None):
    return {
        "_cls": "Message",
        "id": mid,
        "ai": ai,
        "content": content,
        "metadata": metadata or {},
        "sequence": 0,
        "summary": "",
        "tokens": 5,
    }


def agent_zero_history():
    """Agent 0's history from research/agent-zero.md section 8, with the
    assistant message carrying the id of the `agent` log item that streamed
    it (agent.py:529-534) and its provider model, and a second tool result
    long enough to be saved to messages/1.txt."""
    ai = json.dumps(
        {
            "thoughts": ["list"],
            "headline": "Listing",
            "tool_name": "code_execution_tool",
            "tool_args": {"runtime": "terminal", "code": "ls"},
        }
    )
    return {
        "_cls": "History",
        "counter": 5,
        "bulks": [],
        "topics": [],
        "current": {
            "_cls": "Topic",
            "summary": "",
            "messages": [
                _a0_message("u1", False, {"user_message": "list files"}),
                _a0_message(
                    "a1",
                    True,
                    ai,
                    {
                        "responses": {
                            "response_id": "resp_1",
                            "provider_model_key": "openrouter/anthropic/claude-sonnet-4",
                            "usage": {"input": 10, "output": 20},
                        }
                    },
                ),
                _a0_message(
                    "t1", False, {"tool_name": "code_execution_tool", "tool_result": "a.txt"}
                ),
                _a0_message(
                    "t2",
                    False,
                    {
                        "tool_name": "code_execution_tool",
                        "tool_result": AGENT_ZERO_LONG,
                        "file": "/a0/usr/chats/%s/messages/1.txt" % AGENT_ZERO_CHAT,
                    },
                ),
            ],
        },
    }


def agent_zero_logs():
    return [
        {
            "no": 0,
            "id": "u1",
            "type": "user",
            "heading": "",
            "content": "list files",
            "kvps": {"attachments": []},
            "timestamp": 1790856001.0,
            "agentno": 0,
        },
        {
            "no": 1,
            "id": "a1",
            "type": "agent",
            "heading": "icon://network_intelligence A0: Listing",
            "content": "",
            "kvps": {
                "step": "Writing terminal command... (2)",
                "thoughts": ["list"],
                "headline": "Listing",
                "tool_name": "code_execution_tool",
                "tool_args": {"runtime": "terminal", "code": "ls"},
                "reasoning": "the user wants a listing",
            },
            "timestamp": 1790856002.0,
            "agentno": 0,
        },
        {
            "no": 2,
            "id": "t1",
            "type": "tool",
            "heading": "A0: Using tool 'code_execution_tool'",
            "content": "a.txt",
            "kvps": {"runtime": "terminal", "code": "ls", "_tool_name": "code_execution_tool"},
            "timestamp": 1790856003.0,
            "agentno": 0,
        },
        {
            "no": 3,
            "id": "t2",
            "type": "tool",
            "heading": "A0: Using tool 'code_execution_tool'",
            "content": AGENT_ZERO_LONG[:100] + "\n\n<< 500 Characters hidden >>\n\n",
            "kvps": {
                "runtime": "terminal",
                "code": "cat big.log",
                "_tool_name": "code_execution_tool",
            },
            "timestamp": 1790856004.0,
            "agentno": 0,
        },
        {
            "no": 4,
            "id": None,
            "type": "warning",
            "heading": "icon://warning Rate limit",
            "content": "retrying in 5s",
            "kvps": {},
            "timestamp": 1790856004.5,
            "agentno": 0,
        },
        {
            "no": 5,
            "id": "r1",
            "type": "response",
            "heading": "A0: Responding",
            "content": "There is one file, a.txt.",
            "kvps": {},
            "timestamp": 1790856005.0,
            "agentno": 0,
        },
    ]


def agent_zero_chat(logs=None, history=None):
    return {
        "id": AGENT_ZERO_CHAT,
        "name": "List files",
        "created_at": "2026-10-01T14:00:00+02:00",
        "type": "user",
        "last_message": "2026-10-01T14:00:05+02:00",
        "streaming_agent": 0,
        "agent_profile": "agent0",
        "data": {"project": "demo"},
        "output_data": {},
        "agents": [
            {
                "number": 0,
                "agent_profile": "agent0",
                "data": {},
                "history": json.dumps(
                    history if history is not None else agent_zero_history(), separators=(",", ":")
                ),
            }
        ],
        "log": {
            "guid": "6b0f0c1e-0000-4000-8000-000000000001",
            "progress": "",
            "progress_no": 5,
            "logs": logs if logs is not None else agent_zero_logs(),
        },
    }


def build_agent_zero(home: Path) -> None:
    """A docker-compose style install in ~/agent-zero, with the long tool
    result file, and settings and secrets noise."""
    usr = home / "agent-zero/usr"
    chat = usr / "chats" / AGENT_ZERO_CHAT
    chat.mkdir(parents=True, exist_ok=True)
    (chat / "chat.json").write_text(
        json.dumps(agent_zero_chat(), ensure_ascii=False), encoding="utf-8"
    )
    (chat / "messages").mkdir(exist_ok=True)
    (chat / "messages/1.txt").write_text(AGENT_ZERO_LONG + " (from file)", encoding="utf-8")
    (usr / "settings.json").write_text('{"chat_model_provider": "openrouter"}', encoding="utf-8")
    (usr / "secrets.env").write_text("API_KEY_OPENROUTER=not-real\n", encoding="utf-8")


OI_SESSION = "0199a1b2-0000-7000-8000-000000000001"
OI_IMPORTED = "0199a1b2-0000-7000-8000-000000000002"
OI_ROLLOUT = (
    ".openinterpreter/sessions/2026/10/01/rollout-2026-10-01T12-00-00-%s.jsonl" % OI_SESSION
)
OI_ARCHIVED = (
    ".openinterpreter/archived_sessions/2026/09/30/rollout-2026-09-30T08-00-00-%s.jsonl"
    % OI_IMPORTED
)


def open_interpreter_rollout_records(cwd="/srv/proj"):
    """research/open-interpreter.md section 8, with a reasoning item and a
    task_complete event added."""
    return [
        {
            "timestamp": "2026-10-01T10:00:00.000Z",
            "type": "session_meta",
            "payload": {
                "session_id": OI_SESSION,
                "id": OI_SESSION,
                "timestamp": "2026-10-01T10:00:00.000Z",
                "cwd": cwd,
                "originator": "codex_cli_rs",
                "cli_version": "0.9.0",
                "source": "cli",
                "model_provider": "kimi-for-coding",
                "git": {"branch": "main"},
            },
        },
        {
            "timestamp": "2026-10-01T10:00:01.000Z",
            "type": "turn_context",
            "payload": {
                "turn_id": "t1",
                "cwd": cwd,
                "approval_policy": "on-request",
                "sandbox_policy": {"type": "workspace-write"},
                "model": "kimi-k3",
            },
        },
        {
            "timestamp": "2026-10-01T10:00:01.100Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "list the files"}],
            },
        },
        {
            "timestamp": "2026-10-01T10:00:02.000Z",
            "type": "response_item",
            "payload": {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "run ls"}],
                "encrypted_content": "gAAA",
            },
        },
        {
            "timestamp": "2026-10-01T10:00:03.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "Bash",
                "arguments": '{"command":"ls"}',
                "call_id": "call_1",
            },
        },
        {
            "timestamp": "2026-10-01T10:00:04.000Z",
            "type": "response_item",
            "payload": {"type": "function_call_output", "call_id": "call_1", "output": "README.md"},
        },
        {
            "timestamp": "2026-10-01T10:00:05.000Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "One file: README.md"}],
            },
        },
        {
            "timestamp": "2026-10-01T10:00:05.000Z",
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "t1", "duration_ms": 5000},
        },
    ]


def open_interpreter_imported_records(cwd="/srv/proj"):
    """A thread written by /import from a Claude Code transcript."""
    return [
        {
            "timestamp": "2026-09-30T08:00:00.000Z",
            "type": "session_meta",
            "payload": {
                "session_id": OI_IMPORTED,
                "id": OI_IMPORTED,
                "timestamp": "2026-09-30T08:00:00.000Z",
                "cwd": cwd,
                "originator": "codex_cli_rs",
                "cli_version": "0.9.0",
                "source": "cli",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-09-30T08:00:00.000Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "imported prompt"}],
            },
        },
    ]


def open_interpreter_ledger():
    return {
        "records": [
            {
                "source_path": "/home/alice/.claude/projects/-home-alice-proj/5b1c.jsonl",
                "content_sha256": "ab12cd34",
                "imported_thread_id": OI_IMPORTED,
                "imported_at": 1790762400,
                "source_modified_at": 1790758800,
            },
        ]
    }


def build_open_interpreter(home: Path) -> None:
    oi = home / ".openinterpreter"
    _jsonl(home / OI_ROLLOUT, open_interpreter_rollout_records())
    _jsonl(home / OI_ARCHIVED, open_interpreter_imported_records())
    _jsonl(
        oi / "history.jsonl",
        [{"session_id": OI_SESSION, "ts": 1790848801, "text": "list the files"}],
    )
    _jsonl(
        oi / "session_index.jsonl",
        [{"id": OI_SESSION, "thread_name": "ls", "updated_at": "2026-10-01T10:00:05Z"}],
    )
    (oi / "external_agent_session_imports.json").write_text(
        json.dumps(open_interpreter_ledger()), encoding="utf-8"
    )
    (oi / "config.toml").write_text('harness = "claude-code"\n', encoding="utf-8")
    (oi / "auth.json").write_text('{"OPENAI_API_KEY": "sk-not-real"}', encoding="utf-8")


# -- OpenClaw (openclaw/openclaw at 3b16db7) ---------------------------------------
OPENCLAW_SESSION = "7d0c2a8e-1111-4000-8000-000000000001"
OPENCLAW_KEY = "agent:main:telegram:default:direct:123456789"
OPENCLAW_RESET_SESSION = "7d0c2a8e-1111-4000-8000-000000000002"
OPENCLAW_COLD_SESSION = "7d0c2a8e-1111-4000-8000-000000000003"
OPENCLAW_LEGACY = "7d0c2a8e-1111-4000-8000-0000000000aa"
OPENCLAW_DELETED = "7d0c2a8e-1111-4000-8000-0000000000dd"
OPENCLAW_TOKEN = "sk-ant-oat01-FIXTURE-OPENCLAW-TOKEN-0f9e8d"
OPENCLAW_AGENT = ".openclaw/agents/main"

# Columns of src/state/openclaw-agent-schema.sql at 3b16db7 that the parser
# reads (CHECK constraints and unrelated columns left out).
OPENCLAW_SCHEMA = """
CREATE TABLE session_windows (session_id TEXT NOT NULL PRIMARY KEY, session_key TEXT NOT NULL,
  previous_session_id TEXT, reason TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
  started_at INTEGER, ended_at INTEGER, status TEXT, chat_type TEXT, channel TEXT, account_id TEXT,
  model_provider TEXT, model TEXT, parent_session_key TEXT, spawned_by TEXT, display_name TEXT);
CREATE TABLE transcript_events (session_id TEXT NOT NULL, seq INTEGER NOT NULL, event_json TEXT,
  created_at INTEGER NOT NULL, event_zstd BLOB, event_utf8_bytes INTEGER, navigation_json TEXT,
  PRIMARY KEY (session_id, seq));
CREATE TABLE session_transcript_archives (session_id TEXT NOT NULL, generation TEXT NOT NULL,
  session_key TEXT NOT NULL, reason TEXT NOT NULL, encoding TEXT NOT NULL, archive_blob BLOB NOT NULL,
  archive_sha256 TEXT NOT NULL, archive_name TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL,
  published_at INTEGER, PRIMARY KEY (session_id, generation));
CREATE TABLE session_transcript_cold_archives (session_id TEXT NOT NULL PRIMARY KEY, generation TEXT NOT NULL,
  archive_name TEXT NOT NULL UNIQUE, archive_sha256 TEXT NOT NULL, event_count INTEGER NOT NULL,
  raw_bytes INTEGER NOT NULL, archive_bytes INTEGER NOT NULL, last_seq INTEGER NOT NULL,
  archived_at INTEGER NOT NULL, storage TEXT NOT NULL, archive_blob BLOB);
CREATE TABLE auth_profile_store (store_key TEXT NOT NULL PRIMARY KEY, store_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL);
"""


def openclaw_records(session_id=OPENCLAW_SESSION, cwd="/srv/proj"):
    """The research document's sample entries (section 8), cwd moved to /srv/proj."""
    return [
        {
            "type": "session",
            "version": 4,
            "id": session_id,
            "timestamp": "2026-10-01T09:00:00.000Z",
            "cwd": cwd,
        },
        {
            "type": "message",
            "id": "a1b2c3d4",
            "parentId": None,
            "timestamp": "2026-10-01T09:00:01.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "check disk space on the server"}],
                "timestamp": 1790845201000,
            },
        },
        {
            "type": "message",
            "id": "b2c3d4e5",
            "parentId": "a1b2c3d4",
            "timestamp": "2026-10-01T09:00:04.000Z",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Use exec with df.",
                        "thinkingSignature": "sig-opaque",
                    },
                    {"type": "text", "text": "Checking."},
                    {
                        "type": "toolCall",
                        "id": "call_01",
                        "name": "exec",
                        "arguments": {"command": "df -h"},
                    },
                ],
                "api": "anthropic-messages",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input": 900,
                    "output": 40,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 940,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                },
                "stopReason": "toolUse",
                "timestamp": 1790845204000,
            },
        },
        {
            "type": "message",
            "id": "c3d4e5f6",
            "parentId": "b2c3d4e5",
            "timestamp": "2026-10-01T09:00:05.000Z",
            "message": {
                "role": "toolResult",
                "toolCallId": "call_01",
                "toolName": "exec",
                "content": [{"type": "text", "text": "/dev/sda1  50G  20G  30G  40% /"}],
                "isError": False,
                "timestamp": 1790845205000,
            },
        },
        {
            "type": "model_change",
            "id": "d4e5f6a7",
            "parentId": "c3d4e5f6",
            "timestamp": "2026-10-01T09:01:00.000Z",
            "provider": "openai",
            "modelId": "gpt-5",
        },
    ]


def openclaw_legacy_records(session_id=OPENCLAW_LEGACY):
    return [
        {
            "type": "session",
            "version": 3,
            "id": session_id,
            "timestamp": "2026-09-20T08:00:00.000Z",
            "cwd": "/srv/proj",
        },
        {
            "type": "message",
            "id": "e1",
            "parentId": None,
            "timestamp": "2026-09-20T08:00:01.000Z",
            "message": {
                "role": "user",
                "content": "<runtime>channel=telegram</runtime>",
                "runtimeContext": {"retained": True},
                "timestamp": 1789891201000,
            },
        },
        {
            "type": "message",
            "id": "e2",
            "parentId": "e1",
            "timestamp": "2026-09-20T08:00:02.000Z",
            "message": {
                "role": "bashExecution",
                "command": "uptime",
                "output": "up 3 days",
                "exitCode": 0,
                "cancelled": False,
                "truncated": False,
                "timestamp": 1789891202000,
            },
        },
        {
            "type": "compaction",
            "id": "e3",
            "parentId": "e2",
            "timestamp": "2026-09-20T08:05:00.000Z",
            "summary": "checked uptime",
            "firstKeptEntryId": "e2",
            "tokensBefore": 5000,
        },
        {
            "type": "message",
            "id": "e4",
            "parentId": "e3",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "partial"}],
                "model": "gpt-5",
                "stopReason": "error",
                "errorMessage": "rate limited",
                "timestamp": 1789891510000,
            },
        },
    ]


def _openclaw_zstd(raw: bytes):
    """zstd-compressed bytes when zstandard is installed, else None."""
    try:
        import zstandard  # pyright: ignore[reportMissingImports] - optional dependency
    except ImportError:
        return None
    return zstandard.ZstdCompressor(level=1, write_checksum=True).compress(raw)


def _openclaw_jsonl(records) -> bytes:
    return "".join(json.dumps(r) + "\n" for r in records).encode("utf-8")


def build_openclaw(home: Path) -> None:
    agent = home / OPENCLAW_AGENT
    inserts = [
        "INSERT INTO session_windows VALUES ('%s','%s',NULL,'initial',1790845200000,1790845260000,1790845200000,"
        "NULL,'running','direct','telegram','default','anthropic','claude-sonnet-4-5',NULL,NULL,'Disk check')"
        % (OPENCLAW_SESSION, OPENCLAW_KEY),
        "INSERT INTO auth_profile_store VALUES ('anthropic:default','%s',1790845200000)"
        % json.dumps(
            {"type": "oauth", "access": OPENCLAW_TOKEN, "refresh": OPENCLAW_TOKEN + "-refresh"}
        ),
    ]
    for seq, rec in enumerate(openclaw_records()):
        raw = json.dumps(rec)
        z = _openclaw_zstd(raw.encode("utf-8")) if rec.get("id") == "b2c3d4e5" else None
        created = 1790845200000 + seq * 1000
        if z is not None:
            inserts.append(
                "INSERT INTO transcript_events VALUES ('%s',%d,NULL,%d,X'%s',%d,'{\"version\":1}')"
                % (OPENCLAW_SESSION, seq, created, z.hex(), len(raw))
            )
        else:
            inserts.append(
                "INSERT INTO transcript_events VALUES ('%s',%d,'%s',%d,NULL,NULL,NULL)"
                % (OPENCLAW_SESSION, seq, raw.replace("'", "''"), created)
            )
    reset = _openclaw_jsonl(
        [
            *openclaw_records(OPENCLAW_RESET_SESSION)[:2],
            {
                "type": "reset",
                "id": "r1",
                "parentId": "a1b2c3d4",
                "timestamp": "2026-10-01T09:30:00.000Z",
                "reason": "reset",
            },
        ]
    )
    inserts.append(
        "INSERT INTO session_transcript_archives VALUES ('%s','g1','%s','reset','identity',X'%s','%s',"
        "'%s.jsonl.reset.2026-10-01T09-30-00.000Z',1790847000000,NULL)"
        % (OPENCLAW_RESET_SESSION, OPENCLAW_KEY, reset.hex(), "0" * 64, OPENCLAW_RESET_SESSION)
    )
    inserts.append(
        "INSERT INTO session_transcript_archives VALUES ('%s','g2','%s','deleted','identity',X'00','%s',"
        "'%s.jsonl.deleted.2026-10-02T08-00-00.000Z',1790928000000,1790928000500)"
        % (OPENCLAW_DELETED, OPENCLAW_KEY, "1" * 64, OPENCLAW_DELETED)
    )
    cold = [
        {"kind": "header", "version": 1, "sessionId": OPENCLAW_COLD_SESSION, "generation": "g0"}
    ]
    for seq, rec in enumerate(openclaw_records(OPENCLAW_COLD_SESSION)[:2]):
        cold.append(
            {
                "kind": "event",
                "row": {"seq": seq, "event_json": json.dumps(rec), "created_at": 1790845200000},
            }
        )
        cold.append({"kind": "identity", "row": {"event_id": rec["id"], "seq": seq}})
    cold_raw = _openclaw_jsonl(cold)
    cold_blob = _openclaw_zstd(cold_raw) or cold_raw
    inserts.append(
        "INSERT INTO session_transcript_cold_archives VALUES ('%s','g0','%s.jsonl.zst','%s',2,%d,%d,1,"
        "1790850000000,'sqlite',X'%s')"
        % (
            OPENCLAW_COLD_SESSION,
            "c" * 64,
            "2" * 64,
            len(cold_raw),
            len(cold_blob),
            cold_blob.hex(),
        )
    )
    _wal_db(agent / "agent/openclaw-agent.sqlite", OPENCLAW_SCHEMA, inserts)
    sessions = agent / "sessions"
    _jsonl(sessions / (OPENCLAW_LEGACY + ".jsonl"), openclaw_legacy_records())
    (sessions / "sessions.json").write_text(
        json.dumps({OPENCLAW_KEY: {"sessionId": OPENCLAW_LEGACY, "updatedAt": 1789891510000}}),
        encoding="utf-8",
    )
    deleted = _openclaw_jsonl(openclaw_records(OPENCLAW_DELETED)[:2])
    name = OPENCLAW_DELETED + ".jsonl.deleted.2026-10-02T08-00-00.000Z"
    z = _openclaw_zstd(deleted)
    if z is not None:
        (sessions / (name + ".zst")).write_bytes(z)
    else:
        (sessions / name).write_bytes(deleted)
    # Duplicates and noise the parser must skip.
    _jsonl(sessions / (OPENCLAW_LEGACY + ".trajectory.jsonl"), [{"type": "trace"}])
    _jsonl(
        sessions / (OPENCLAW_LEGACY + ".checkpoint.0b5e1c2d-3f4a-4b5c-8d6e-7f8091a2b3c4.jsonl"),
        openclaw_legacy_records(),
    )
    (agent / "agent/auth-profiles.json").write_text(
        json.dumps({"anthropic:default": {"key": OPENCLAW_TOKEN}}), encoding="utf-8"
    )
    (home / ".openclaw/openclaw.json").write_text('{"agents": {}}', encoding="utf-8")


# -- nanobot (HKUDS/nanobot at acdae3d) ------------------------------------------
NANOBOT_KEY = "telegram:123456789"
NANOBOT_WS = "0123456789abcdef0123456789abcdef"
NANOBOT_REL = ".nanobot/sessions/%s/dGVsZWdyYW06MTIzNDU2Nzg5.jsonl" % NANOBOT_WS
NANOBOT_LEGACY_REL = ".nanobot/sessions/cli_direct.jsonl"
NANOBOT_HISTORY_REL = ".nanobot/workspace/memory/history.jsonl"


def nanobot_records():
    """The research document's sample file (section 8), plus a hidden-history
    message and a provider_state line."""
    return [
        {
            "_type": "metadata",
            "key": NANOBOT_KEY,
            "created_at": "2026-10-01T10:15:00.000001",
            "updated_at": "2026-10-01T10:15:09.500000",
            "metadata": {"last_channel": NANOBOT_KEY},
            "last_archived": 0,
            "last_consolidated": 0,
        },
        {"_type": "provider_state", "state": {"opaque": "x"}},
        {
            "role": "user",
            "content": "[earlier conversation summarised]",
            "_hidden_history": True,
            "timestamp": "2026-10-01T10:15:00.500000",
        },
        {
            "role": "user",
            "content": "what is using port 8080?",
            "timestamp": "2026-10-01T10:15:01.200000",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "exec",
                        "arguments": '{"command": "ss -ltnp | grep 8080"}',
                    },
                }
            ],
            "reasoning_content": "Check listening sockets.",
            "timestamp": "2026-10-01T10:15:04.000000",
        },
        {
            "role": "tool",
            "tool_call_id": "call_abc123",
            "name": "exec",
            "content": 'LISTEN 0 128 *:8080 users:(("python3",pid=4242))',
            "timestamp": "2026-10-01T10:15:05.000000",
        },
        {
            "role": "assistant",
            "content": "python3 (pid 4242) is listening on 8080.",
            "timestamp": "2026-10-01T10:15:09.400000",
        },
    ]


def build_nanobot(home: Path) -> None:
    _jsonl(home / NANOBOT_REL, nanobot_records())
    (home / NANOBOT_REL).parent.joinpath(".workspace").write_text("/srv/proj\n", encoding="utf-8")
    (home / NANOBOT_REL).parent.joinpath("dGVsZWdyYW06MTIzNDU2Nzg5.checkpoint.json").write_text(
        "{}", encoding="utf-8"
    )
    _jsonl(
        home / NANOBOT_LEGACY_REL,
        [
            {
                "_type": "metadata",
                "key": "cli:direct",
                "created_at": "2026-09-01T08:00:00",
                "updated_at": "2026-09-01T08:00:05",
                "metadata": {"_nanobot_model_preset": "fast"},
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "hello"}],
                "timestamp": "2026-09-01T08:00:01",
            },
            {"role": "assistant", "content": "hi"},
        ],
    )
    _jsonl(
        home / NANOBOT_HISTORY_REL,
        [
            {
                "cursor": 1,
                "timestamp": "2026-09-30 22:10",
                "content": "User asked about disk usage.",
                "session_key": NANOBOT_KEY,
            },
            {
                "cursor": 2,
                "timestamp": "2026-10-01 10:20",
                "content": "Found python3 on port 8080.",
            },
        ],
    )
    (home / ".nanobot/config.json").write_text(
        '{"providers": {"openai": {"apiKey": "sk-not-real"}}}', encoding="utf-8"
    )


# ---- VS Code state.vscdb rows (Cody, Twinny) and PearAI ----------------------------
# Shapes from analyzer/research/cody.md, twinny.md and pearai.md.

VSCDB_SCHEMA = "CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);"


def _vscdb(path: Path, items: dict) -> None:
    """Add `ItemTable` rows to a plain (non-WAL) state.vscdb."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.executescript(VSCDB_SCHEMA.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS"))
    for k, v in items.items():
        con.execute(
            "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
            (k, (v if isinstance(v, str) else json.dumps(v)).encode("utf-8")),
        )
    con.commit()
    con.close()


CODY_ACCOUNT = "https://sourcegraph.com/-alice"
CODY_CHAT = "Sat, 03 Oct 2026 10:00:00 GMT"
CODY_AGENTIC_CHAT = "Sat, 03 Oct 2026 10:30:00 GMT"
CODY_VSCODE_CHAT = "Sat, 03 Oct 2026 09:00:00 GMT"
CODY_MODEL = "anthropic::2024-10-22::claude-sonnet-4-latest"
CODY_JB_REL = ".local/share/Cody-nodejs/JetBrains-globalState/cody-local-chatHistory-v2"
CODY_VSCDB_REL = ".config/VSCodium/User/globalStorage/state.vscdb"
CODY_TOKEN = "sgp_cody_secret_not_real"


def cody_records():
    """The JetBrains AccountKeyedChatHistory: the research fixture chat and
    its agentic variant."""
    chat = {
        "id": CODY_CHAT,
        "chatTitle": "Fix flaky test",
        "lastInteractionTimestamp": CODY_CHAT,
        "interactions": [
            {
                "humanMessage": {
                    "speaker": "human",
                    "text": "why is test_login flaky?",
                    "intent": "chat",
                    "contextFiles": [
                        {
                            "type": "file",
                            "source": "user",
                            "uri": {
                                "$mid": 1,
                                "fsPath": "/srv/proj/tests/test_login.py",
                                "path": "/srv/proj/tests/test_login.py",
                                "scheme": "file",
                            },
                        }
                    ],
                },
                "assistantMessage": {
                    "speaker": "assistant",
                    "model": CODY_MODEL,
                    "text": "It depends on wall-clock time.",
                    "intent": "chat",
                },
            }
        ],
    }
    agentic = {
        "id": CODY_AGENTIC_CHAT,
        "chatTitle": "run the tests",
        "lastInteractionTimestamp": CODY_AGENTIC_CHAT,
        "interactions": [
            {
                "humanMessage": {"speaker": "human", "text": "run the tests", "intent": "agentic"},
                "assistantMessage": {
                    "speaker": "assistant",
                    "model": CODY_MODEL,
                    "text": "Running tests.",
                    "content": [
                        {"type": "text", "text": "Running tests."},
                        {
                            "type": "tool_call",
                            "tool_call": {
                                "id": "toolu_01",
                                "name": "run_terminal_command",
                                "arguments": '{"command":"pytest -q"}',
                            },
                        },
                    ],
                    "processes": [
                        {
                            "type": "tool",
                            "id": "toolu_01",
                            "title": "run_terminal_command",
                            "content": "pytest -q",
                            "state": "success",
                        }
                    ],
                },
            },
            {
                "humanMessage": {
                    "speaker": "human",
                    "text": "",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_result": {"id": "toolu_01", "content": "3 passed"},
                        }
                    ],
                },
                "assistantMessage": {
                    "speaker": "assistant",
                    "model": CODY_MODEL,
                    "text": "All three pass.",
                    "error": {"name": "RateLimitError", "message": "rate limit exceeded"},
                },
            },
        ],
    }
    return {CODY_ACCOUNT: {"chat": {CODY_CHAT: chat, CODY_AGENTIC_CHAT: agentic}}}


def cody_vscode_state():
    """The `sourcegraph.cody-ai` global state value of a VS Code install."""
    return {
        "cody-local-chatHistory-v2": {
            CODY_ACCOUNT: {
                "chat": {
                    CODY_VSCODE_CHAT: {
                        "id": CODY_VSCODE_CHAT,
                        "lastInteractionTimestamp": CODY_VSCODE_CHAT,
                        "interactions": [
                            {
                                "humanMessage": {"speaker": "human", "text": "explain build.sh"},
                                "assistantMessage": {
                                    "speaker": "assistant",
                                    "model": CODY_MODEL,
                                    "text": "It runs make.",
                                },
                            }
                        ],
                    }
                }
            }
        },
        "cody-anonymous-user-id": "anon-1",
    }


def build_cody(home: Path) -> None:
    jb = home / CODY_JB_REL
    jb.parent.mkdir(parents=True, exist_ok=True)
    jb.write_text(json.dumps(cody_records()), encoding="utf-8")
    (home / ".local/share/Cody-nodejs/user-settings.json").write_text(
        '{"cody.serverEndpoint": "x"}', encoding="utf-8"
    )
    _vscdb(
        home / CODY_VSCDB_REL,
        {
            "sourcegraph.cody-ai": cody_vscode_state(),
            'secret://{"extensionId":"sourcegraph.cody-ai","key":"cody.access-token"}': CODY_TOKEN,
        },
    )


TWINNY_CONVERSATION = "7d1c2b3a-1111-4000-8000-000000000001"
TWINNY_ACTIVE = "7d1c2b3a-1111-4000-8000-000000000002"
TWINNY_API_KEY = "sk-twinny-fixture-not-real"
TWINNY_VSCDB_REL = ".vscode-server/data/User/globalStorage/state.vscdb"


def twinny_records():
    """The `rjmacarthy.twinny` global state value: the research fixture plus
    an unsaved active conversation, a failed tool step and provider keys."""
    return {
        "twinny.conversations": {
            TWINNY_CONVERSATION: {
                "id": TWINNY_CONVERSATION,
                "title": "List the tests",
                "updatedAt": 1791028805000,
                "messages": [
                    {"role": "user", "content": "which tests fail?"},
                    {
                        "role": "assistant",
                        "content": "<think>run the suite</think>Two tests fail.",
                        "meta": {
                            "model": "qwen2.5-coder:7b",
                            "provider": "Ollama",
                            "durationMs": 5200,
                            "withheld": [{"kind": "aws-key", "count": 1}],
                        },
                        "toolSteps": [
                            {
                                "id": "step-1",
                                "name": "run_command",
                                "summary": "ran `npm test`",
                                "args": {"command": "npm test"},
                                "output": "2 failing",
                                "status": "done",
                            },
                            {
                                "id": "step-2",
                                "name": "read_file",
                                "args": {"path": "src/a.ts"},
                                "output": "permission denied",
                                "status": "failed",
                            },
                        ],
                    },
                ],
            }
        },
        "twinny.active-conversation": {
            "id": TWINNY_ACTIVE,
            "title": "draft",
            "updatedAt": 1791028900000,
            "messages": [{"role": "user", "content": "unsaved question"}],
        },
        "twinny.inference-providers": {
            "p1": {
                "id": "p1",
                "label": "Ollama",
                "provider": "ollama",
                "type": "chat",
                "modelName": "qwen2.5-coder:7b",
                "apiHostname": "localhost",
                "apiPort": 11434,
                "apiKey": TWINNY_API_KEY,
            }
        },
        "twinny.active-chat-provider": {"id": "p1", "apiKey": TWINNY_API_KEY},
    }


def build_twinny(home: Path) -> None:
    """Rows only in the -wal sidecar, as with the editor still running."""

    def lit(s):
        return "'" + s.replace("'", "''") + "'"

    _wal_db(
        home / TWINNY_VSCDB_REL,
        VSCDB_SCHEMA,
        [
            "INSERT INTO ItemTable VALUES ('rjmacarthy.twinny', CAST(%s AS BLOB))"
            % lit(json.dumps(twinny_records())),
            "INSERT INTO ItemTable VALUES (%s, %s)"
            % (
                lit('secret://{"extensionId":"rjmacarthy.twinny","key":"gateway"}'),
                lit(TWINNY_API_KEY),
            ),
        ],
    )
    tw = home / ".config/Code/User/globalStorage/rjmacarthy.twinny"
    tw.mkdir(parents=True, exist_ok=True)
    (tw / "twinny-providers.json").write_text(
        json.dumps({"apiKey": TWINNY_API_KEY}), encoding="utf-8"
    )


PEARAI_SESSION = "9b1c2d3e-0000-4000-8000-000000000001"
PEARAI_SEARCH_SESSION = "9b1c2d3e-0000-4000-8000-000000000002"
PEARAI_TASK = "1791036000000"
PEARAI_UI_TASK = "1791039600000"
PEARAI_GS = ".config/PearAI/User/globalStorage/"
PEARAI_ROO = PEARAI_GS + "pearai.pearai-roo-cline/"


def pearai_session():
    return {
        "history": [
            {
                "message": {"role": "user", "content": "why does build.sh fail"},
                "contextItems": [
                    {
                        "content": "set -e\nmake all",
                        "name": "build.sh",
                        "description": "/srv/proj/build.sh",
                        "id": {"providerTitle": "file", "itemId": "build.sh"},
                    }
                ],
            },
            {
                "message": {"role": "assistant", "content": "The make target is missing."},
                "contextItems": [],
                "promptLogs": [
                    {
                        "completionOptions": {"model": "pearai_model"},
                        "prompt": "<user>why does build.sh fail",
                        "completion": "The make target is missing.",
                    }
                ],
            },
        ],
        "perplexityHistory": [],
        "title": "why does build.sh fail",
        "sessionId": PEARAI_SESSION,
        "workspaceDirectory": "/srv/proj",
    }


def pearai_search_session():
    return {
        "history": [],
        "perplexityHistory": [
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "latest make release"}],
                },
                "contextItems": [],
            },
            {
                "message": {"role": "assistant", "content": "GNU make 4.4.1."},
                "contextItems": [],
                "citations": [{"url": "https://www.gnu.org/software/make/", "title": "GNU Make"}],
            },
        ],
        "title": "latest make release",
        "sessionId": PEARAI_SEARCH_SESSION,
        "workspaceDirectory": "/srv/proj",
    }


def pearai_index():
    return [
        {
            "sessionId": PEARAI_SESSION,
            "title": "why does build.sh fail",
            "dateCreated": "1791032400000",
            "workspaceDirectory": "/srv/proj",
            "integrationType": "continue",
        },
        {
            "sessionId": PEARAI_SEARCH_SESSION,
            "title": "latest make release",
            "dateCreated": "1791032500000",
            "workspaceDirectory": "/srv/proj",
            "integrationType": "perplexity",
        },
    ]


def pearai_api_records(t0=1791036000000):
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "<task>\nrun the tests\n</task>"},
                {
                    "type": "text",
                    "text": "<environment_details>\n# Current Working Directory "
                    "(/srv/proj)\n</environment_details>",
                },
            ],
            "ts": t0,
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<thinking>use npm</thinking>\nI will run them.\n<execute_command>\n<command>npm test</command>\n"
                    "</execute_command>",
                }
            ],
            "ts": t0 + 3000,
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "[execute_command for 'npm test'] Result:"},
                {"type": "text", "text": "12 passing"},
            ],
            "ts": t0 + 9000,
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<attempt_completion>\n<result>All 12 tests pass.</result>\n</attempt_completion>",
                }
            ],
            "ts": t0 + 10000,
        },
    ]


def build_pearai(home: Path) -> None:
    sessions = home / ".pearai/sessions"
    _json(sessions / (PEARAI_SESSION + ".json"), pearai_session())
    _json(sessions / (PEARAI_SEARCH_SESSION + ".json"), pearai_search_session())
    _json(sessions / "sessions.json", pearai_index())
    (home / ".pearai/config.json").write_text('{"models": []}', encoding="utf-8")
    roo = home / PEARAI_ROO
    _json(roo / "tasks" / PEARAI_TASK / "api_conversation_history.json", pearai_api_records())
    _json(roo / "tasks" / PEARAI_TASK / "task_metadata.json", {"files_in_context": []})
    _json(roo / "tasks" / PEARAI_UI_TASK / "ui_messages.json", roo_ui_records(int(PEARAI_UI_TASK)))
    _json(
        roo / "tasks" / PEARAI_UI_TASK / "api_conversation_history.json",
        pearai_api_records(int(PEARAI_UI_TASK)),
    )
    _vscdb(
        home / PEARAI_GS / "state.vscdb",
        {
            "pearai.pearai-roo-cline": {
                "taskHistory": [
                    {
                        "id": PEARAI_TASK,
                        "number": 1,
                        "ts": 1791036010000,
                        "task": "run the tests",
                        "tokensIn": 900,
                        "tokensOut": 40,
                        "totalCost": 0.002,
                        "workspace": "/srv/proj",
                    }
                ]
            }
        },
    )
