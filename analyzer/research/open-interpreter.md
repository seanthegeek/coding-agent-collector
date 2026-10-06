# Open Interpreter transcript schema

Catalog agent: `open-interpreter`. The current Open Interpreter is a Rust
fork of OpenAI Codex CLI that keeps Codex's protocol and file formats and
moves the home to `~/.openinterpreter` (see
[../../collectors/research/open-interpreter.md](../../collectors/research/open-interpreter.md)).
Transcripts are Codex rollouts, byte for byte, so the existing Codex parser
(`doubleagent/parsers/codex.py`) is the reference and this document
records only what was checked in the fork and what differs. Paths cited are
relative to `codex-rs/` in the clone.

## 1. Source

openinterpreter/openinterpreter at
[`2767e5f20d6927500b8f1938c773c61afb823245`](https://github.com/openinterpreter/openinterpreter/commit/2767e5f20d6927500b8f1938c773c61afb823245),
Apache-2.0, open source.

## 2. Transcript files

- `.openinterpreter/sessions/YYYY/MM/DD/rollout-<YYYY-MM-DDThh-mm-ss>-<thread uuid>.jsonl`,
  one file per thread, and the same under `.openinterpreter/archived_sessions/`
  ([`rollout/src/lib.rs:84-85`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/lib.rs#L84-L85),
  [`rollout/src/rollout_file_name.rs:64-67`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/rollout_file_name.rs#L64-L67)). The directory date and
  the file name time are local time
  ([`rollout/src/recorder.rs:1700-1712`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/recorder.rs#L1700-L1712)); record timestamps are UTC.
  A rollout may be stored as `.jsonl.zst`
  ([`rollout/src/compression.rs:25`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/compression.rs#L25),[`94`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/compression.rs#L94)).
- `.openinterpreter/history.jsonl`: one line per submitted prompt, all
  sessions ([`message-history/src/lib.rs:52`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L52),[`86`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L86)).
- `.openinterpreter/session_index.jsonl`: `{id, thread_name, updated_at}`
  per rename ([`rollout/src/session_index.rs:21-29`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/session_index.rs#L21-L29)).
- `.openinterpreter/external_agent_session_imports.json`: which rollouts
  were imported from Claude Code or Cursor (section 4).
- `.openinterpreter/.zcode/cli/artifacts/sess_<session id>/<call id>-tool-result-<uuid>.json`:
  full output of a tool call that was too long to inline under the zcode
  harness ([`core/src/tools/handlers/harness_aliases.rs:887-902`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L887-L902)).

## 3. Record schema

Each line is `RolloutLine`: `timestamp`, optional `ordinal`, and the
flattened item ([`history/src/lib.rs:277-284`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/history/src/lib.rs#L277-L284)), serialised as
`{"type": <snake_case variant>, "payload": {...}}` with an optional
`metadata` on `response_item`
([`history/src/rollout_payload.rs:22-62`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/history/src/rollout_payload.rs#L22-L62)). `timestamp` is UTC,
`YYYY-MM-DDThh:mm:ss.mmmZ` ([`rollout/src/recorder.rs:2054-2059`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/recorder.rs#L2054-L2059)).
Types: `session_meta`, `response_item`, `inter_agent_communication`,
`inter_agent_communication_metadata`, `compacted`, `turn_context`,
`token_usage_record`, `world_state`, `retained_context`,
`security_risk_score`, `event_msg`, `realtime_item`.

- `session_meta` payload ([`protocol/src/protocol.rs:3117-3154`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/protocol.rs#L3117-L3154)):
  `session_id`, `id` (thread), `forked_from_id?`, `parent_thread_id?`,
  `timestamp`, `cwd`, `runtime_workspace_roots?`, `originator`,
  `cli_version`, `source`, `agent_nickname?`, `agent_role?`, `agent_path?`,
  `model_provider`, `base_instructions`; plus `git` with `commit_hash`,
  `branch`, `repository_url` ([`protocol.rs:3222-3228`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/protocol.rs#L3222-L3228),
  [`3423-3437`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/protocol.rs#L3423-L3437)). `originator` defaults to `codex_cli_rs` in the
  fork too ([`login/src/auth/default_client.rs:42`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/auth/default_client.rs#L42),[`64-68`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/auth/default_client.rs#L64-L68)), so
  only the file's location tells Open Interpreter from Codex.
- `turn_context`: `turn_id`, `cwd`, `model`, `approval_policy`,
  `sandbox_policy`, `timezone`, `effort` and more
  ([`protocol.rs:3287-3343`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/protocol.rs#L3287-L3343)). The emulated harness
  (`claude-code`, `kimi-code`, `zcode` and others) is a `config.toml` key
  ([`config/src/config_toml.rs:166-170`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/config/src/config_toml.rs#L166-L170)) and is not recorded per turn.
- `response_item` payload, tagged by `type`
  ([`protocol/src/models.rs:1009-1011`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1009-L1011)): `message` (`role`, `content`
  blocks, `phase?`; [`1020-1035`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1020-L1035)), `reasoning` (`summary`,
  `content?`, `encrypted_content`; [`1047-1059`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1047-L1059)), `local_shell_call`
  (`call_id`, `status`, `action`; [`1060-1072`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1060-L1072)), `function_call`
  (`name`, `namespace?`, `arguments` JSON string, `call_id`;
  [`1073-1092`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1073-L1092)), `function_call_output` (`call_id`, `name?`, `output`;
  [`1113-1132`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L1113-L1132)), `custom_tool_call`, `custom_tool_call_output`,
  `tool_search_call`, `tool_search_output`, `web_search_call`. The harness
  emulation renames tools (`Bash`, `Read`, `Grep` and so on in the
  claude-code harness, [`core/src/harness/claude_code.rs:1287`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/harness/claude_code.rs#L1287)), so `name` values are not the Codex set.
- `event_msg`: UI events (`task_started`, `task_complete`, `token_count`,
  ...), as in Codex.

`history.jsonl`: `{session_id, ts, text}`, `ts` epoch seconds
([`message-history/src/lib.rs:62-66`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L62-L66),[`128-131`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L128-L131)).

## 4. Joins

Session to project: `session_meta.payload.cwd`, updated per turn by
`turn_context.payload.cwd`. Tool call to result: `call_id`. Subagent to
parent: `session_meta.payload.parent_thread_id` and `forked_from_id`.
Imported chats: `external_agent_session_imports.json` `records[]` with
`source_path` (the original `~/.claude/projects/...` or `~/.cursor/...`
file), `content_sha256`, `imported_thread_id` (the rollout's thread id) and
`imported_at`, `source_modified_at` (epoch)
([`external-agent-sessions/src/ledger.rs:18-30`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/ledger.rs#L18-L30)). A rollout whose thread id
is in that ledger was written by `/import`
([`external-agent-sessions/src/export.rs:58-73`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/export.rs#L58-L73)), so its turns were
authored in another agent and their record timestamps are import time.

## 5. SQLite or binary stores

Same SQLite set as Codex (`state_5.sqlite`, `logs_2.sqlite`,
`thread_history_1.sqlite` and others;
[`state/src/sqlite.rs:29-34`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/state/src/sqlite.rs#L29-L34)); the rollouts are the primary record. zstd
for `.jsonl.zst` rollouts.

## 6. Format versions

Tracks upstream Codex; no fork-specific version marker in the records.
`cli_version` in `session_meta` is the fork's version.

## 7. Secrets

Not in rollouts by design, but tool arguments and outputs can carry pasted
keys. `reasoning.encrypted_content` is an opaque provider blob. The
credential files (`auth.json`, `credentials/kimi-code.json`, `.env`) are
listed in the collector document.

## 8. Parser plan

Reuse `CodexParser`, matching `.openinterpreter/sessions/` and
`.openinterpreter/archived_sessions/` rollouts and
`.openinterpreter/history.jsonl` with agent `open-interpreter`. The current
parser matches only `^\.codex/sessions/` and plain `.jsonl`; extending it to
`archived_sessions/` and `.jsonl.zst` would fix Codex as well. Mark rollouts
listed in the import ledger with a `system` row naming `source_path`.

| Column | Source |
| --- | --- |
| timestamp_utc | line `timestamp`; history `ts` (s) |
| session_id | `session_meta.payload.id` |
| project_path | `turn_context.payload.cwd`, else `session_meta.payload.cwd` |
| git_branch | `session_meta.payload.git.branch` |
| turn_type | `message` by role; `function_call`, `custom_tool_call`, `local_shell_call`, `web_search_call` → tool_use; `*_output` → tool_result; `reasoning` → thinking; `task_started`/`task_complete` → system |
| model | `turn_context.payload.model` |
| tool_name, tool_use_id | `name`, `call_id` |
| text | message text, `arguments`/`input`/`action.command`, `output` |

Fixture (`.openinterpreter/sessions/2026/10/01/rollout-2026-10-01T12-00-00-0199a1b2-0000-7000-8000-000000000001.jsonl`):

```json
{"timestamp":"2026-10-01T10:00:00.000Z","type":"session_meta","payload":{"session_id":"0199a1b2-0000-7000-8000-000000000001","id":"0199a1b2-0000-7000-8000-000000000001","timestamp":"2026-10-01T10:00:00.000Z","cwd":"/home/alice/proj","originator":"codex_cli_rs","cli_version":"0.9.0","source":"cli","model_provider":"kimi-for-coding","git":{"branch":"main"}}}
{"timestamp":"2026-10-01T10:00:01.000Z","type":"turn_context","payload":{"turn_id":"t1","cwd":"/home/alice/proj","approval_policy":"on-request","sandbox_policy":{"type":"workspace-write"},"model":"kimi-k3"}}
{"timestamp":"2026-10-01T10:00:01.100Z","type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"list the files"}]}}
{"timestamp":"2026-10-01T10:00:03.000Z","type":"response_item","payload":{"type":"function_call","name":"Bash","arguments":"{\"command\":\"ls\"}","call_id":"call_1"}}
{"timestamp":"2026-10-01T10:00:04.000Z","type":"response_item","payload":{"type":"function_call_output","call_id":"call_1","output":"README.md"}}
```

`external_agent_session_imports.json`:
`{"records":[{"source_path":"/home/alice/.claude/projects/-home-alice-proj/5b1c.jsonl","content_sha256":"ab12...","imported_thread_id":"0199a1b2-0000-7000-8000-000000000002","imported_at":1759312800}]}`

Confidence. High: file locations, line envelope, timestamp format, payload
field names (shared structs), the ledger's `records` key (no serde
rename on the struct), `input_text` content blocks ([`protocol/src/models.rs:876-880`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/models.rs#L876-L880)). Not determined: the exact tool names each emulated harness emits, which
vary by harness module.
