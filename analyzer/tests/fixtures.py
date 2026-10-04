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
    build_zed(home)
    build_vscode(home)
    (home / ".gemini/settings.json").write_text("{}", encoding="utf-8")
    gs = home / ".config/Code/User/globalStorage"
    gs.mkdir(parents=True, exist_ok=True)
    (gs / "state.vscdb").write_text("sqlite", encoding="utf-8")
    (gs / "saoudrizwan.claude-dev/state").mkdir(parents=True, exist_ok=True)
    (gs / "saoudrizwan.claude-dev/state/taskHistory.json").write_text("[]", encoding="utf-8")
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


ZED_THREAD = "6f1c0b2e-1111-4bbb-8ccc-000000000001"
ZED_EXTERNAL = "ext-claude-code-sess-1"


def zed_thread_record(cwd="/srv/proj"):
    """A `threads.data` blob, version 0.3.0, as in analyzer/research/zed.md."""
    return {
        "version": "0.3.0", "title": "Fix flaky test", "updated_at": "2026-10-03T09:01:05Z",
        "initial_project_snapshot": {"worktree_snapshots": [{"worktree_path": cwd, "git_state": {
            "remote_url": "git@github.com:alice/proj.git", "head_sha": "abc123", "current_branch": "main", "diff": None}}],
            "timestamp": "2026-10-03T09:00:00Z"},
        "model": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "messages": [
            {"User": {"id": "9a7d6c5b-2222-4ddd-9eee-000000000002", "content": [
                {"Text": "run the tests"}, {"Mention": {"uri": "file://%s/README.md" % cwd, "content": ""}}]}},
            {"Agent": {"content": [
                {"Thinking": {"text": "use pytest", "signature": None}},
                {"ToolUse": {"id": "toolu_01", "name": "terminal", "raw_input": "{\"command\":\"pytest -q\"}",
                             "input": {"type": "json", "value": {"command": "pytest -q"}},
                             "is_input_complete": True, "thought_signature": None}},
                {"Text": "All 3 tests pass."}],
                "tool_results": {"toolu_01": {"tool_use_id": "toolu_01", "tool_name": "terminal", "is_error": False,
                                              "content": [{"Text": "3 passed"}], "output": None}},
                "reasoning_details": None}},
            "Resume",
            {"Compaction": {"Summary": "ran the tests"}},
        ],
    }


def zed_blob(record):
    """(data_type, data): zstd when the zstandard package is installed, as Zed
    writes it, otherwise the `json` form Zed also accepts."""
    raw = json.dumps(record).encode("utf-8")
    try:
        import zstandard
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
    con.execute("INSERT INTO threads(id,parent_id,folder_paths,folder_paths_order,summary,updated_at,data_type,data,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (ZED_THREAD, None, "/srv/proj", "0", "Fix flaky test", "2026-10-03T09:01:05.000000000+00:00", dtype, blob,
                 "2026-10-03T09:00:00.000000000+00:00"))
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
    con.execute("INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,created_at,folder_paths,"
                "folder_paths_order,archived) VALUES (?,?,?,?,?,?,?,?,?)",
                (os.urandom(16), ZED_THREAD, None, "Fix flaky test", "2026-10-03T09:01:05+00:00",
                 "2026-10-03T09:00:00+00:00", "/srv/proj", "0", 0))
    con.execute("INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,folder_paths,folder_paths_order) "
                "VALUES (?,?,?,?,?,?,?)",
                (os.urandom(16), ZED_EXTERNAL, "claude-code", "External thread", "2026-10-03T10:00:00+00:00", "/srv/proj", "0"))
    con.commit()
    con.close()
    (home / ".config/zed").mkdir(parents=True, exist_ok=True)
    (home / ".config/zed/settings.json").write_text('{"agent": {"default_model": {}}}', encoding="utf-8")


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
        {"kind": 0, "v": {"version": 3, "creationDate": t, "customTitle": None, "initialLocation": "panel",
                          "responderUsername": "GitHub Copilot", "sessionId": VSCODE_SESSION, "requests": [
            {"requestId": "request_1", "timestamp": t + 1000, "message": {"text": "run tests", "parts": []},
             "agent": {"id": "github.copilot.default", "name": "GitHub Copilot", "extensionId": {"value": "GitHub.copilot-chat"}},
             "modelId": "copilot/gpt-4.1", "modeInfo": {"kind": "agent", "telemetryModeId": "agent", "isBuiltin": True},
             "variableData": {"variables": [{"id": "file://%s/test_a.py" % cwd, "name": "test_a.py", "value": "..."}]},
             "response": [
                 {"kind": "thinking", "value": "Need pytest", "id": "t1"},
                 {"kind": "toolInvocationSerialized", "toolCallId": "call_a", "toolId": "run_in_terminal",
                  "invocationMessage": "Running command", "isComplete": True, "isConfirmed": True,
                  "toolSpecificData": {"kind": "terminal", "commandLine": {"original": "pytest"}},
                  "resultDetails": {"input": "pytest", "output": [{"type": "embed", "value": "3 passed"}]}},
                 {"value": "All tests pass in "},
                 {"kind": "inlineReference", "inlineReference": {"scheme": "file", "path": cwd + "/test_a.py"},
                  "name": "test_a.py"},
                 {"value": "."}],
             "responseId": "response_1", "responseTimestamp": t + 2000, "modelState": {"value": "complete"}}],
            "workingDirectory": "file://%s" % cwd}},
        {"kind": 2, "k": ["requests"], "v": [
            {"requestId": "request_2", "timestamp": t + 10000, "message": {"text": "thanks", "parts": []},
             "variableData": {"variables": []}, "modelId": "copilot/gpt-4.1", "response": []}]},
        {"kind": 2, "k": ["requests", 1, "response"], "v": [{"value": "You're welcome."}]},
        {"kind": 1, "k": ["requests", 1, "responseTimestamp"], "v": t + 11000},
        {"kind": 1, "k": ["customTitle"], "v": "Run tests"},
    ]


def vscode_legacy_session(cwd="/srv/proj"):
    """A pre-1.109 flat `.json` session from an empty window on a remote host."""
    t = VSCODE_T0 - 3600000
    return {"version": 3, "sessionId": VSCODE_LEGACY_SESSION, "creationDate": t, "initialLocation": "panel",
            "responderUsername": "GitHub Copilot", "workingDirectory": "file://%s" % cwd, "requests": [
                {"requestId": "request_1", "timestamp": t + 1000, "message": "where is the config?",
                 "modelId": "copilot/gpt-4o", "response": ["It is in ", "config.toml."],
                 "responseTimestamp": t + 2000, "result": {"errorDetails": {"message": "Rate limited"}}}]}


def build_vscode(home: Path) -> None:
    ws = home / VSCODE_WS
    _jsonl(ws / "chatSessions" / (VSCODE_SESSION + ".jsonl"), vscode_log_records())
    (ws / "workspace.json").write_text(json.dumps({"folder": "file:///srv/proj"}), encoding="utf-8")
    (home / ".config/Code/User/settings.json").write_text('{"chat.useLogSessionStorage": true}', encoding="utf-8")
    legacy = home / ".vscode-server/data/User/globalStorage/emptyWindowChatSessions"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / (VSCODE_LEGACY_SESSION + ".json")).write_text(json.dumps(vscode_legacy_session(), indent=2),
                                                            encoding="utf-8")
