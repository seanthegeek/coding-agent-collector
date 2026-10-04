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
    build_opencode(home)
    build_kilo(home)
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
    con.execute("INSERT INTO session (id, project_id, parent_id, slug, directory, title, version, agent, model, "
                "time_created, time_updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (sid, project_id, parent, title.lower().replace(" ", "-"), directory, title, "1.2.0", "build",
                 json.dumps(model) if model else None, t, t + 5000))


def _oc_message(con, mid, sid, t, data):
    con.execute("INSERT INTO message VALUES (?,?,?,?,?)", (mid, sid, t, t, json.dumps(data)))


def _oc_part(con, pid, mid, sid, t, data):
    con.execute("INSERT INTO part VALUES (?,?,?,?,?,?)", (pid, mid, sid, t, t, json.dumps(data)))


def opencode_assistant(t, cwd="/srv/proj", model="claude-sonnet-4", **extra):
    d = {"role": "assistant", "time": {"created": t, "completed": t + 3000}, "parentID": "msg_01",
         "modelID": model, "providerID": "anthropic", "mode": "build", "agent": "build",
         "path": {"cwd": cwd, "root": cwd}, "cost": 0.01,
         "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}}}
    d.update(extra)
    return d


def build_opencode_db(db: Path, t0: int = OPENCODE_T0) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(OPENCODE_SCHEMA)
    con.execute("INSERT INTO project (id, worktree, vcs, time_created, time_updated, sandboxes) VALUES (?,?,?,?,?,?)",
                ("proj_a1", "/srv/proj", "git", t0, t0, "[]"))
    _oc_session(con, OPENCODE_SESSION, "proj_a1", "/srv/proj", "Fix bug", t0)
    _oc_message(con, "msg_01", OPENCODE_SESSION, t0 + 1000,
                {"role": "user", "time": {"created": t0 + 1000}, "agent": "build",
                 "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4"}})
    _oc_part(con, "prt_01", "msg_01", OPENCODE_SESSION, t0 + 1000, {"type": "text", "text": "list files"})
    _oc_part(con, "prt_01b", "msg_01", OPENCODE_SESSION, t0 + 1000,
             {"type": "text", "text": "<system-reminder>plan mode</system-reminder>", "synthetic": True})
    _oc_message(con, "msg_02", OPENCODE_SESSION, t0 + 2000, opencode_assistant(t0 + 2000))
    _oc_part(con, "prt_02", "msg_02", OPENCODE_SESSION, t0 + 2000, {"type": "step-start", "snapshot": "abc123"})
    _oc_part(con, "prt_03", "msg_02", OPENCODE_SESSION, t0 + 2100,
             {"type": "reasoning", "text": "user wants a listing", "time": {"start": t0 + 2100, "end": t0 + 2200}})
    _oc_part(con, "prt_04", "msg_02", OPENCODE_SESSION, t0 + 2500,
             {"type": "tool", "callID": "call_x1", "tool": "bash",
              "state": {"status": "completed", "input": {"command": "ls"}, "output": "a.txt", "title": "ls",
                        "metadata": {}, "time": {"start": t0 + 2500, "end": t0 + 3000}}})
    _oc_part(con, "prt_05", "msg_02", OPENCODE_SESSION, t0 + 3500,
             {"type": "text", "text": "There is one file, a.txt.", "time": {"start": t0 + 3500, "end": t0 + 3600}})
    _oc_part(con, "prt_06", "msg_02", OPENCODE_SESSION, t0 + 4000,
             {"type": "step-finish", "reason": "stop", "cost": 0.01,
              "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}}})
    # A session present only in the V2 session_message projection.
    _oc_session(con, OPENCODE_V2_SESSION, "proj_a1", "/srv/proj", "Run tests", t0 + 10000)
    con.execute("INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
                ("msg_v2u", OPENCODE_V2_SESSION, "user", 1, t0 + 11000, t0 + 11000,
                 json.dumps({"id": "msg_v2u", "time": {"created": t0 + 11000}, "text": "run the tests"})))
    con.execute("INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
                ("msg_v2a", OPENCODE_V2_SESSION, "assistant", 2, t0 + 12000, t0 + 14000, json.dumps(
                    {"id": "msg_v2a", "agent": "build", "model": {"id": "gpt-5", "providerID": "openai"},
                     "content": [{"type": "text", "id": "c1", "text": "Running them."},
                                 {"type": "tool", "id": "call_v2", "name": "bash",
                                  "state": {"status": "completed", "input": {"command": "pytest -q"},
                                            "content": [{"type": "text", "text": "3 passed"}], "structured": {}},
                                  "time": {"created": t0 + 12500, "completed": t0 + 13000}}],
                     "time": {"created": t0 + 12000, "completed": t0 + 14000}})))
    con.execute("INSERT INTO credential (id, provider_id, type, name, value, active, time_created, time_updated) "
                "VALUES (?,?,?,?,?,?,?,?)", ("cred_01", "anthropic", "key", "my key",
                                             '{"type":"key","key":"sk-ant-REDACT"}', 1, t0, t0))
    con.commit()
    con.close()


def _json_file(path: Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def build_opencode_storage(storage: Path, t0: int = OPENCODE_T0 - 86400000) -> None:
    """The legacy JSON tree: ids inline, one file per record."""
    sid = OPENCODE_LEGACY_SESSION
    _json_file(storage / "project/proj_a1.json",
               {"id": "proj_a1", "vcs": "git", "worktree": "/srv/proj", "time": {"created": t0}})
    _json_file(storage / "session/proj_a1" / (sid + ".json"),
               {"id": sid, "projectID": "proj_a1", "directory": "/srv/proj", "title": "Old session",
                "version": "0.9.0", "time": {"created": t0, "updated": t0 + 5000}})
    _json_file(storage / "message" / sid / "msg_a.json",
               {"id": "msg_a", "sessionID": sid, "role": "user", "time": {"created": t0 + 1000},
                "agent": "build", "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4"}})
    _json_file(storage / "part/msg_a/prt_a1.json",
               {"id": "prt_a1", "sessionID": sid, "messageID": "msg_a", "type": "text", "text": "cat the secrets file"})
    _json_file(storage / "message" / sid / "msg_b.json",
               dict(opencode_assistant(t0 + 2000), id="msg_b", sessionID=sid,
                    error={"name": "APIError", "data": {"message": "overloaded"}}))
    _json_file(storage / "part/msg_b/prt_b1.json",
               {"id": "prt_b1", "sessionID": sid, "messageID": "msg_b", "type": "tool", "callID": "call_r1",
                "tool": "read", "state": {"status": "error", "input": {"filePath": "/srv/proj/.env"},
                                          "error": "permission denied", "time": {"start": t0 + 2500, "end": t0 + 2600}}})
    _json_file(storage / "part/msg_b/prt_b2.json",
               {"id": "prt_b2", "sessionID": sid, "messageID": "msg_b", "type": "text", "text": "I could not read it.",
                "time": {"start": t0 + 2700}})
    (storage / "migration").write_text("2", encoding="utf-8")


def build_opencode(home: Path) -> None:
    data = home / ".local/share/opencode"
    build_opencode_db(data / "opencode.db")
    build_opencode_storage(data / "storage")
    (data / "auth.json").write_text('{"anthropic":{"type":"api","key":"sk-ant-REDACT"}}', encoding="utf-8")
    _json_file(home / ".config/opencode/opencode.json", {"$schema": "https://opencode.ai/config.json"})


def kilo_task_records(t0: int = KILO_T0 - 86400000):
    return [
        {"role": "user", "content": [{"type": "text", "text": "<task>fix tests</task>"},
                                     {"type": "text", "text": "<environment_details>cwd /srv/proj</environment_details>"}],
         "ts": t0 + 1000},
        {"role": "assistant", "content": [{"type": "text", "text": "Running the suite."},
                                          {"type": "tool_use", "id": "toolu_01A", "name": "execute_command",
                                           "input": {"command": "pytest -q"}}], "ts": t0 + 2000},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01A", "content": "3 passed",
                                      "is_error": False}], "ts": t0 + 3000},
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "tests pass"}], "ts": t0 + 3500},
        {"role": "assistant", "content": "All three tests pass.", "ts": t0 + 4000},
    ]


def build_kilo(home: Path) -> None:
    data = home / ".local/share/kilo"
    db = data / "kilo.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(OPENCODE_SCHEMA)
    t0 = KILO_T0
    con.execute("INSERT INTO project (id, worktree, vcs, time_created, time_updated, sandboxes) VALUES (?,?,?,?,?,?)",
                ("prj_01JAX", "/srv/proj", "git", t0, t0, "[]"))
    _oc_session(con, KILO_SESSION, "prj_01JAX", "/srv/proj", "fix tests", t0,
                model={"id": "claude-sonnet-4-5", "providerID": "anthropic"})
    _oc_message(con, "msg_01JAXU", KILO_SESSION, t0 + 1000,
                {"role": "user", "time": {"created": t0 + 1000}, "agent": "build",
                 "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4-5"}})
    _oc_part(con, "prt_01JAXP", "msg_01JAXU", KILO_SESSION, t0 + 1000, {"type": "text", "text": "fix the tests"})
    _oc_message(con, "msg_01JAXA", KILO_SESSION, t0 + 2000, dict(
        opencode_assistant(t0 + 2000, model="claude-sonnet-4-5"), parentID="msg_01JAXU"))
    _oc_part(con, "prt_01JAXT", "msg_01JAXA", KILO_SESSION, t0 + 2500,
             {"type": "tool", "callID": "call_1", "tool": "bash",
              "state": {"status": "completed", "input": {"command": "pytest -q"}, "output": "3 passed",
                        "title": "pytest -q", "metadata": {}, "time": {"start": t0 + 2500, "end": t0 + 3000}}})
    # Kilo writes the V2 projection alongside V1; it must not duplicate the rows.
    con.execute("INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
                ("msg_01JAXB", KILO_SESSION, "assistant", 4, t0 + 2000, t0 + 3000, json.dumps(
                    {"agent": "build", "model": {"providerID": "anthropic", "modelID": "claude-sonnet-4-5"},
                     "content": [{"type": "tool", "id": "call_1", "name": "bash",
                                  "state": {"status": "completed", "input": {"command": "pytest -q"},
                                            "content": [{"type": "text", "text": "3 passed"}], "structured": {}},
                                  "time": {"created": t0 + 2500, "completed": t0 + 3000}}],
                     "time": {"created": t0 + 2000, "completed": t0 + 3000}})))
    con.commit()
    con.close()
    (data / "auth.json").write_text('{"kilo":{"type":"oauth","access":"REDACT"}}', encoding="utf-8")
    tasks = home / ".config/Code/User/globalStorage/kilocode.kilo-code/tasks"
    task = tasks / KILO_TASK
    task.mkdir(parents=True, exist_ok=True)
    (task / "api_conversation_history.json").write_text(json.dumps(kilo_task_records()), encoding="utf-8")
    (task / "ui_messages.json").write_text("[]", encoding="utf-8")
    _json_file(tasks / "_index.json", {"version": 1, "updatedAt": KILO_T0 - 86395000, "entries": [
        {"id": KILO_TASK, "number": 1, "ts": KILO_T0 - 86400000, "task": "fix tests", "tokensIn": 1200,
         "tokensOut": 80, "totalCost": 0.0041, "workspace": "/srv/proj", "mode": "code", "status": "completed"}]})
