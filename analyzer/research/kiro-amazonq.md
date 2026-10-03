# Amazon Q Developer CLI / Kiro CLI transcript schema

All paths are in the clone at `scratchpad/repos/amazon-q-developer-cli`; `C=` means `crates/chat-cli/src`.

## 1. Repo, commit, license, applicability

- `https://github.com/aws/amazon-q-developer-cli`, commit `15cc8f3cd18c4272925ce1c7053268eedff1ea0a` (2026-04-23), workspace version `1.19.7` (`Cargo.toml:11`). Dual licensed Apache-2.0 / MIT (`LICENSE.APACHE`, `LICENSE.MIT`).
- `README.md:4`: the project is unmaintained except for security fixes; "Amazon Q Developer CLI is now available as Kiro CLI, a closed-source product".
- Two agent cores exist in the repo. `chat-cli` is the shipped `q chat` and is the only one that persists conversations. `crates/agent` is a newer loop with its own camelCase `Message` types that is never written to disk here (no writer found by grep); it is the most likely shape of what Kiro CLI stores but that is inference, not evidence.
- Nothing in this repo mentions `.kiro`, `kiro-cli`, `sessions/` or `workspace-roots` (grep returned zero hits). Those catalog paths come from the closed binary and remain unverified. No Kiro CLI binary or state exists on this workstation, so no strings check was possible. The only "kiro" tokens are in generated API clients: subscription names `KIRO_FREE`/`KIRO_PRO`/... (`crates/amzn-codewhisperer-client/src/types/_subscription_name.rs:53-59`) and an `x-amzn-kiro-agent-mode` header (`.../shape_generate_assistant_response.rs:200`).

## 2. Transcript stores

- `dirs::data_local_dir()/amazon-q/data.sqlite3` (`C/util/paths.rs:327-331`; `crates/agent/src/agent/util/directories.rs:16,37-48`, overridable with `Q_CLI_DATA_DIR`, `crates/agent/src/agent/util/consts.rs:27`). Per the `dirs` crate that is `~/.local/share/amazon-q/`, `~/Library/Application Support/amazon-q/`, `%LOCALAPPDATA%\amazon-q\`. Mode forced to 0600 on Unix (`C/database/mod.rs:212-223`). Catalog entries `.local/share/amazon-q`, `Library/Application Support/amazon-q`, `AppData/Local/amazon-q` are confirmed; the `kiro-cli` variants are the unverified rebrand.
- Table `conversations`: one row per working directory. Key is the cwd string; value is `serde_json::to_string(&ConversationState)` (`C/database/mod.rs:385-410`). Written with `INSERT OR REPLACE` (`mod.rs:470-475`) after every assistant turn (`C/cli/chat/conversation.rs:403-422`), so only the latest conversation in each directory survives; earlier ones in the same directory are overwritten. Resume reads the same key (`C/cli/chat/mod.rs:719-724`).
- `/save <path>` writes `serde_json::to_string_pretty(&session.conversation)`, identical schema, to any user-chosen path; `/load` appends `.json` if missing (`C/cli/chat/cli/persist.rs:60,89-90`). These stray JSON files are the only other transcript store.
- `~/.aws/amazonq/.cli_bash_history` (`paths.rs:63`) and shadow checkouts `~/.aws/amazonq/cli-checkouts` (`paths.rs:62`) are adjacent evidence, not transcripts.

## 3. Record schema

Migrations (`C/database/mod.rs:63-72`, SQL in `C/database/sqlite_migrations/`):

```
000 CREATE TABLE migrations (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, migration_time INTEGER NOT NULL);
001 CREATE TABLE history (id INTEGER PRIMARY KEY, command TEXT, shell TEXT, pid INTEGER, session_id TEXT, cwd TEXT, time INTEGER, in_ssh INTEGER, in_docker INTEGER, hostname TEXT, exit_code INTEGER);
002 ALTER TABLE history DROP COLUMN in_ssh; DROP COLUMN in_docker;
003 ALTER TABLE history RENAME COLUMN time TO start_time; ADD COLUMN end_time INTEGER; ADD COLUMN duration INTEGER;
004 CREATE TABLE state (key TEXT PRIMARY KEY, value TEXT);
005 CREATE TABLE auth_kv (key TEXT PRIMARY KEY, value TEXT);
006 state recreated with value BLOB
007 CREATE TABLE conversations (key TEXT PRIMARY KEY, value TEXT);
```

`history` has no writer in this repo (legacy shell history from the Fig lineage); old installs may still hold rows.

Serialised `ConversationState` (`conversation.rs:106-152`; all structs use default serde, snake_case, externally tagged enums):

```
conversation_id: string (random, conversation.rs:109)
next_message: UserMessage|null
history: [HistoryEntry]              valid_history_range: [int,int]
transcript: [string]                 tools: {"native___"|<mcp server>: [...]}   (tools/mod.rs:305-315)
context_manager, checkpoint_manager, file_line_tracker, context_message_length: opaque
latest_summary: [string, RequestMetadata]|null
model: string (optional, legacy <=1.13.3)   model_info: {model_id: string, model_name?, description?}  (cli/model.rs:26-35)
mcp_enabled: bool                    tangent_state: optional (holds main_history etc., conversation.rs:154-167)
```
`tool_manager` and `agents` are `#[serde(skip)]`.

`HistoryEntry` (`conversation.rs:91-97`): `{user: UserMessage, assistant: AssistantMessage, request_metadata: RequestMetadata|null}`.

`UserMessage` (`message.rs:53-60`): `additional_context: string`, `env_context: {env_state: {operating_system, current_working_directory (truncated to 256, consts.rs:3), environment_variables: [{key,value}]}}` (`message.rs:422-425,542-559`; `api_client/model.rs:724-728,761-764`), `content`, `timestamp: string|null`, `images: [...]|null`.
`content` (`message.rs:62-76`) is one of `{"Prompt":{"prompt":s}}`, `{"CancelledToolUses":{"prompt":s|null,"tool_use_results":[...]}}`, `{"ToolUseResults":{"tool_use_results":[...]}}`.
`timestamp` is `chrono::DateTime<FixedOffset>` from `Local::now().fixed_offset()` (`conversation.rs:398`), serialised RFC 3339 with local offset, e.g. `2026-04-23T14:17:15.123456789-07:00` (`chrono/src/datetime/serde.rs:32-46`, v0.4.42 per `Cargo.lock:1575`). Tool-result user messages may carry `null`.

`ToolUseResult` (`message.rs:332-340`): `{tool_use_id: string, content: [{"Text": string} | {"Json": any}], status: "Success"|"Error"}` (`message.rs:387-391`; `api_client/model.rs:491-495`).

`AssistantMessage` (`message.rs:435-448`): `{"Response":{"message_id":s|null,"content":s}}` or `{"ToolUse":{"message_id":s|null,"content":s,"tool_uses":[AssistantToolUse]}}`.
`AssistantToolUse` (`message.rs:507-519`): `{id, name, orig_name, args: any, orig_args: any}`; `id` is the backend `tool_use_id` (`message.rs:531-539`).

`RequestMetadata` (`C/cli/chat/parser.rs:685-699`): `request_id: s|null`, `message_id: s`, `request_start_timestamp_ms: int`, `stream_end_timestamp_ms: int` (unix ms, `parser.rs:701-707`), `time_to_first_chunk: {secs,nanos}|null`, `time_between_chunks: [{secs,nanos}]` (serde Duration, `serde-1.0.219/src/ser/impls.rs:736-746`), `user_prompt_length`, `response_size`, `chat_conversation_type: "NotToolUse"|"ToolUse"|null` (`telemetry/core.rs:534-539`), `tool_use_ids_and_names: [[id,name]]`, `model_id: s|null`, `message_meta_tags: ["Compact"|"GenerateAgent"|"TangentMode"]` (`core.rs:551-558`).

Newer `crates/agent` shape (not persisted here, `agent_loop/types.rs`): `ConversationState {id: uuid, messages: [Message]}` (`types.rs:147-150`); `Message {id, role: "user"|"assistant", content: [ {"text": s} | {"toolUse": {toolUseId, name, input}} | {"toolResult": {toolUseId, content: [{"text"}|{"json"}|{"image"}], status: "success"|"error"}} | {"image": ...} ], timestamp: unix seconds int|null}` (`agent_loop/types.rs:161-170,310-316,383-400,402-407,426-431,445-451`). Note camelCase and lowercase status versus the chat-cli schema.

## 4. Joins

- Conversation ↔ messages: all messages are embedded in the one JSON blob; `history[i]` is one user/assistant pair, so `history` order is the turn order. `next_message` is a pending, unanswered user message.
- Tool pairing: `history[i].assistant.ToolUse.tool_uses[].id` matches `history[i+1].user.content.ToolUseResults.tool_use_results[].tool_use_id` (or `CancelledToolUses`). `request_metadata.tool_use_ids_and_names` duplicates the id→name map and `request_metadata.message_id` matches `assistant.*.message_id`.
- cwd: the row `key` (`mod.rs:385-410`) and, per message, `user.env_context.env_state.current_working_directory`. No git branch is recorded anywhere.
- Session id: `conversation_id`; the per-request `request_id`/`message_id` are secondary.

## 5. SQLite specifics

- rusqlite 0.32 `bundled` via r2d2 (`Cargo.toml:82-89`); no `PRAGMA` anywhere (grep), so default rollback-journal mode: no `-wal`/`-shm` sidecars, only a transient `data.sqlite3-journal` during a write. A copied `data.sqlite3` alone is complete unless Kiro CLI enabled WAL (unverified; collect `-wal`/`-shm`/`-journal` if present). No encryption.
- Each write is a whole-blob replace, so a mid-write copy is either the old or the new conversation, never a partial row.

## 6. Format versions

- Migrations `000`-`007` above; `migrations.version` is the 0-based index, `migration_time` unix seconds (`mod.rs:448-451`). `has_migration` re-checks versions <= 7 because of an off-by-one in early builds (`mod.rs:532-556`).
- No schema version inside the JSON. Compatibility shims: `request_metadata` `#[serde(default)]` (`conversation.rs:95`), `model` kept only for <=1.13.3 (`conversation.rs:133-136`), `model_info`, `file_line_tracker`, `mcp_enabled`, `tangent_state` all defaulted; a parser must treat them as optional.
- Legacy JSON: only `/save` exports (same schema).
- Rebrand: paths still say `amazon-q`/`.aws/amazonq`/`.amazonq` in this commit; the catalog's `kiro-cli` and `.kiro` entries are unverified Kiro additions. Expect the `crates/agent` camelCase schema and per-session files rather than one row per cwd if Kiro CLI stores `~/.kiro/sessions/`.

## 7. Secrets to redact

- `auth_kv` keys `codewhisperer:odic:token` (`C/auth/builder_id.rs:304`) and `codewhisperer:odic:device-registration` (`builder_id.rs:119`); values are JSON with access/refresh tokens and client secret.
- `state` key `telemetry-cognito-credentials` → `{access_key_id, secret_key, session_token, expiration}` (`mod.rs:55,78-84`); also `api.codewhisperer.profile` (ARN), `auth.idc.start-url`, `auth.idc.region`, `telemetryClientId` (`mod.rs:55-62`).
- Inside conversations: `tool_uses[].args`/`orig_args` and tool result `content` hold command lines and output (e.g. `execute_bash`), and `env_state.environment_variables` can carry env values. `~/.aws/sso/cache` holds MCP OAuth tokens (`paths.rs:314-316`).

## 8. Parser plan

Globs relative to home: `.local/share/amazon-q/data.sqlite3*`, `Library/Application Support/amazon-q/data.sqlite3*`, `AppData/Local/amazon-q/data.sqlite3*`, same three with `kiro-cli/`; plus `**/*.json` whose top level has `conversation_id` and `history` (saved exports); plus `.kiro/sessions/**` (format unknown, detect by `messages[].role`).

One CSV row per: user prompt, assistant message, each `tool_uses[]` entry, each `tool_use_results[]` entry, and one `system` row per `latest_summary`/`Compact` tag. The legacy `history` table yields optional rows (`start_time`, `session_id`, `cwd`, `command`).

Mapping: `timestamp_utc` = `user.timestamp` converted to UTC for user and tool_result rows; `request_metadata.stream_end_timestamp_ms` for assistant and tool_use rows (fallback `request_start_timestamp_ms`, else previous row). `session_id` = `conversation_id`. `project_path` = row `key` (fallback `env_state.current_working_directory`). `git_branch` = empty. `turn_type`: `Prompt` → user; `Response`/`ToolUse` content → assistant; `tool_uses[]` → tool_use; `tool_use_results[]` → tool_result; `CancelledToolUses` → tool_result with summary "cancelled". `model` = `request_metadata.model_id`, else `model_info.model_id`, else `model`. `tool_name` = `tool_uses[].name` (keep `orig_name` for MCP), result rows look up the name via the matching id. `tool_use_id` = `id` / `tool_use_id`. `summary` = first 200 chars of prompt, content, `json.dumps(args)`, or result text; status appended for results.

Fixture:

```sql
CREATE TABLE conversations (key TEXT PRIMARY KEY, value TEXT);
INSERT INTO conversations (key, value) VALUES ('/home/alice/proj', '{"conversation_id":"3f2b8c1e-9d7a-4e6b-b1c2-0a9f8e7d6c5b","next_message":null,"history":[{"user":{"additional_context":"","env_context":{"env_state":{"operating_system":"linux","current_working_directory":"/home/alice/proj","environment_variables":[]}},"content":{"Prompt":{"prompt":"list the files here"}},"timestamp":"2026-04-23T14:17:15.123456789-07:00","images":null},"assistant":{"ToolUse":{"message_id":"msg-001","content":"I will list the directory.","tool_uses":[{"id":"tooluse_abc123","name":"execute_bash","orig_name":"execute_bash","args":{"command":"ls -la"},"orig_args":{"command":"ls -la"}}]}},"request_metadata":{"request_id":"req-001","message_id":"msg-001","request_start_timestamp_ms":1777000635200,"stream_end_timestamp_ms":1777000636900,"time_to_first_chunk":{"secs":0,"nanos":400000000},"time_between_chunks":[],"user_prompt_length":19,"response_size":26,"chat_conversation_type":"ToolUse","tool_use_ids_and_names":[["tooluse_abc123","execute_bash"]],"model_id":"claude-sonnet-4","message_meta_tags":[]}},{"user":{"additional_context":"","env_context":{"env_state":{"operating_system":"linux","current_working_directory":"/home/alice/proj","environment_variables":[]}},"content":{"ToolUseResults":{"tool_use_results":[{"tool_use_id":"tooluse_abc123","content":[{"Text":"total 8\nREADME.md"}],"status":"Success"}]}},"timestamp":null,"images":null},"assistant":{"Response":{"message_id":"msg-002","content":"The directory contains README.md."}},"request_metadata":{"request_id":"req-002","message_id":"msg-002","request_start_timestamp_ms":1777000637000,"stream_end_timestamp_ms":1777000638100,"time_to_first_chunk":null,"time_between_chunks":[],"user_prompt_length":0,"response_size":34,"chat_conversation_type":"NotToolUse","tool_use_ids_and_names":[],"model_id":"claude-sonnet-4","message_meta_tags":[]}}],"valid_history_range":[0,2],"transcript":["> list the files here","The directory contains README.md."],"tools":{"native___":[]},"context_manager":null,"context_message_length":null,"latest_summary":null,"model_info":{"model_id":"claude-sonnet-4","model_name":"Claude Sonnet 4"},"file_line_tracker":{},"checkpoint_manager":null,"mcp_enabled":true}');
CREATE TABLE auth_kv (key TEXT PRIMARY KEY, value TEXT);
INSERT INTO auth_kv VALUES ('codewhisperer:odic:token', '{"access_token":"REDACT-ME"}');
```

Confidence: path, tables, migrations, key = cwd, JSON field names and enum tags: high (read directly from source). Timestamp formats: high for chrono RFC 3339 and unix-ms fields; `tangent_start_time` uses the `time` crate's default serde, not checked. `dirs` platform mapping: medium (crate docs, not read). Everything about Kiro CLI (`kiro-cli` dirs, `.kiro/sessions`, `workspace-roots`, WAL use, camelCase `agent` schema on disk, token key names after rebrand): unverified; needs strings from a shipped binary.
