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
    (home / ".gemini/settings.json").write_text("{}", encoding="utf-8")
    gs = home / ".config/Code/User/globalStorage"
    gs.mkdir(parents=True, exist_ok=True)
    (gs / "state.vscdb").write_text("sqlite", encoding="utf-8")
    (gs / "saoudrizwan.claude-dev/state").mkdir(parents=True, exist_ok=True)
    (gs / "saoudrizwan.claude-dev/state/taskHistory.json").write_text("[]", encoding="utf-8")
    build_cline(home)
    build_roo_code(home)
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


# ---- Cline and Roo Code (research/cline.md, research/roo-code.md) ----------------

CLINE_TASK = "1791021600000"            # 2026-10-03T10:00:00Z, a Date.now() id
CLINE_CLI_TASK = "1791021300000"        # API history only, no ui_messages.json
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
        {"ts": t0, "type": "say", "say": "task", "text": "fix tests", "images": ["data:image/png;base64,AAAA"]},
        {"ts": t0 + 1000, "type": "say", "say": "api_req_started",
         "text": json.dumps({"request": "<task>fix tests</task>", "tokensIn": 1200, "tokensOut": 80,
                             "cacheWrites": 0, "cacheReads": 900, "cost": 0.0041})},
        {"ts": t0 + 1500, "type": "say", "say": "reasoning", "text": "read the test first", "partial": False},
        {"ts": t0 + 2000, "type": "say", "say": "tool", "modelInfo": model,
         "text": json.dumps({"tool": "readFile", "path": "src/app.py", "content": "/srv/proj/src/app.py"})},
        {"ts": t0 + 3000, "type": "say", "say": "text", "text": "Running the suite.", "modelInfo": model},
        {"ts": t0 + 4000, "type": "ask", "ask": "command", "text": "pytest -q", "modelInfo": model},
        {"ts": t0 + 5000, "type": "say", "say": "command_output", "text": "3 passed"},
        {"ts": t0 + 6000, "type": "say", "say": "checkpoint_created", "lastCheckpointHash": "abc123"},
        {"ts": t0 + 7000, "type": "say", "say": "completion_result", "text": "All tests pass.", "modelInfo": model},
        {"ts": t0 + 7001, "type": "ask", "ask": "completion_result", "text": ""},
    ]


def cline_api_records():
    return [
        {"role": "user", "content": [{"type": "text", "text": "<task>fix tests</task>"}]},
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "run the suite"},
                                          {"type": "tool_use", "id": "toolu_01A", "name": "execute_command",
                                           "input": {"command": "pytest -q"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01A", "content": "3 passed",
                                      "is_error": False}]},
    ]


def cline_task_metadata(t0=CLINE_T0):
    return {
        "files_in_context": [
            {"path": "src/app.py", "record_state": "active", "record_source": "read_tool",
             "cline_read_date": t0 + 2000, "cline_edit_date": None},
        ],
        "model_usage": [{"ts": t0 + 500, "model_id": "claude-sonnet-4-5", "model_provider_id": "anthropic",
                         "mode": "act"}],
        "environment_history": [{"ts": t0 + 100, "os_name": "linux", "os_version": "6.6", "os_arch": "x64",
                                 "host_name": "Visual Studio Code", "host_version": "1.105.0",
                                 "cline_version": "3.40.0"}],
    }


def cline_history_items():
    return [
        {"id": CLINE_TASK, "ulid": "01JAX3Q8M4", "ts": CLINE_T0 + 7001, "task": "fix tests", "tokensIn": 1200,
         "tokensOut": 80, "totalCost": 0.0041, "cwdOnTaskInitialization": "/srv/proj",
         "modelId": "claude-sonnet-4-5", "apiProvider": "anthropic"},
    ]


def cline_sdk_manifest():
    return {"version": 1, "session_id": CLINE_SESSION, "source": "cli", "pid": 4242,
            "started_at": "2026-10-03T10:01:40.000Z", "ended_at": "2026-10-03T10:01:50.000Z", "exit_code": 0,
            "status": "completed", "interactive": True, "provider": "anthropic", "model": "claude-sonnet-4-5",
            "cwd": "/srv/proj", "workspace_root": "/srv/proj", "enable_tools": True, "enable_spawn": False,
            "enable_teams": False, "prompt": "fix tests", "metadata": {"title": "fix tests"},
            "messages_path": "/home/u/.cline/data/sessions/%s/%s.messages.json" % (CLINE_SESSION, CLINE_SESSION)}


def cline_sdk_messages(t0=CLINE_T0 + 100000):
    return {"version": 1, "updated_at": "2026-10-03T10:01:50.000Z", "agent": "lead", "sessionId": CLINE_SESSION,
            "origin": {"source": "cli", "mode": "user", "sessionId": CLINE_SESSION},
            "system_prompt": "You are Cline.",
            "messages": [
                {"id": "m1", "role": "user", "content": "fix tests", "ts": t0},
                {"id": "m2", "role": "assistant",
                 "content": [{"type": "thinking", "thinking": "run the suite"},
                             {"type": "tool_use", "id": "call_1", "name": "bash", "input": {"command": "pytest -q"}}],
                 "modelInfo": {"id": "claude-sonnet-4-5", "provider": "anthropic"},
                 "metrics": {"inputTokens": 1200, "outputTokens": 80, "cost": 0.0041}, "ts": t0 + 2000},
                {"id": "m3", "role": "user",
                 "content": [{"type": "tool_result", "tool_use_id": "call_1", "name": "bash", "content": "3 passed",
                              "is_error": False}], "ts": t0 + 3000},
                {"id": "m4", "role": "assistant", "content": [{"type": "text", "text": "Fixed."}]},
            ]}


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
    _json(data / "state/taskHistory.json", [dict(cline_history_items()[0], id=CLINE_CLI_TASK, ts=1791021305000)])
    _json(data / "secrets.json", {"apiKey": "sk-not-real"})
    sess = data / "sessions" / CLINE_SESSION
    _json(sess / (CLINE_SESSION + ".json"), cline_sdk_manifest())
    _json(sess / (CLINE_SESSION + ".messages.json"), cline_sdk_messages())
    _json(sess / (CLINE_SESSION + ".compaction.json"), {"version": 1})
    (data / "db").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(data / "db/sessions.db"))
    con.execute("CREATE TABLE sessions (session_id TEXT PRIMARY KEY, source TEXT, pid INTEGER, started_at TEXT, "
                "ended_at TEXT, exit_code INTEGER, status TEXT, interactive INTEGER, provider TEXT, model TEXT, "
                "cwd TEXT, workspace_root TEXT, prompt TEXT, metadata_json TEXT, is_subagent INTEGER, "
                "parent_session_id TEXT, updated_at TEXT)")
    for sid, started, prompt in ((CLINE_SESSION, "2026-10-03T10:01:40.000Z", "fix tests"),
                                 (CLINE_OLD_SESSION, "2026-10-02T23:00:00.000Z", "an older deleted session")):
        con.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, "cli", 4242, started, None, None, "completed", 1, "anthropic", "claude-sonnet-4-5",
                     "/srv/proj", "/srv/proj", prompt, json.dumps({"title": prompt}), 0, None, started))
    con.commit()
    con.close()


def roo_ui_records(t0=CLINE_T0 + 200000):
    return [
        {"ts": t0, "type": "say", "say": "text", "text": "rename the helper"},
        {"ts": t0 + 1000, "type": "say", "say": "api_req_started",
         "text": json.dumps({"request": "rename the helper", "tokensIn": 900, "tokensOut": 40, "cost": 0.002,
                             "apiProtocol": "anthropic"})},
        {"ts": t0 + 2000, "type": "ask", "ask": "tool",
         "text": json.dumps({"tool": "appliedDiff", "path": "src/util.py", "diff": "-old\n+new"})},
        {"ts": t0 + 3000, "type": "ask", "ask": "command", "text": "pytest -q"},
        {"ts": t0 + 4000, "type": "ask", "ask": "command_output", "text": "1 passed"},
        {"ts": t0 + 5000, "type": "say", "say": "condense_context", "partial": False,
         "contextCondense": {"cost": 0.001, "prevContextTokens": 9000, "newContextTokens": 1200,
                             "summary": "Renamed helper; tests pass.", "condenseId": "c1"}},
        {"ts": t0 + 6000, "type": "ask", "ask": "followup",
         "text": json.dumps({"question": "Commit now?", "suggest": [{"answer": "yes"}, {"answer": "no"}]})},
        {"ts": t0 + 7000, "type": "say", "say": "user_feedback", "text": "yes"},
        {"ts": t0 + 8000, "type": "say", "say": "completion_result", "text": "Renamed and committed."},
    ]


def roo_api_records(t0=CLINE_T0 + 300000):
    return [
        {"role": "user", "content": [{"type": "text", "text": "<task>fix tests</task>"}], "ts": t0},
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "check the runner"}],
         "encrypted_content": "gAAAA", "ts": t0 + 1000},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_01A", "name": "execute_command",
                                           "input": {"command": "pytest -q"}}], "ts": t0 + 2000},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01A", "content": "3 passed",
                                      "is_error": False}], "ts": t0 + 3000},
    ]


def roo_history_item(task_id, ts, task, workspace="/srv/proj"):
    return {"id": task_id, "number": 1, "ts": ts, "task": task, "tokensIn": 1200, "tokensOut": 80,
            "totalCost": 0.0041, "workspace": workspace, "mode": "code", "status": "completed"}


def build_roo_code(home: Path) -> None:
    gs = home / ".config/Code/User/globalStorage/rooveterinaryinc.roo-cline"
    task = gs / "tasks" / ROO_TASK
    _json(task / "ui_messages.json", roo_ui_records())
    _json(task / "api_conversation_history.json", roo_api_records())
    _json(task / "history_item.json", roo_history_item(ROO_TASK, CLINE_T0 + 208000, "rename the helper"))
    _json(task / "task_metadata.json", {"files_in_context": [
        {"path": "src/util.py", "record_state": "active", "record_source": "roo_edited",
         "roo_read_date": CLINE_T0 + 202000, "roo_edit_date": CLINE_T0 + 202500, "user_edit_date": None}]})
    _json(gs / "tasks/_index.json", {"version": 1, "updatedAt": CLINE_T0 + 208000, "entries": [
        roo_history_item(ROO_TASK, CLINE_T0 + 208000, "rename the helper"),
        roo_history_item(ROO_GONE_TASK, CLINE_T0 - 3600000, "a task deleted from disk"),
    ]})
    mock = home / ".vscode-mock/global-storage"
    _json(mock / "tasks" / ROO_CLI_TASK / "api_conversation_history.json", roo_api_records())
    _json(mock / "tasks" / ROO_CLI_TASK / "history_item.json",
          roo_history_item(ROO_CLI_TASK, CLINE_T0 + 303000, "fix tests"))
    _json(mock / "secrets.json", {"roo_cline_config_api_config": "{\"apiKey\":\"sk-not-real\"}"})
