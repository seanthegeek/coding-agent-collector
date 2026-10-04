# Kiro CLI and Amazon Q Developer CLI transcript schema

Catalog agent: `kiro`, which covers the Kiro CLI, its open-source
predecessor the Amazon Q Developer CLI, and the Kiro IDE. This document is
about the CLI store. Paths cited are relative to the clone; `C=` means
`crates/chat-cli/src`.

## 1. Source and applicability

aws/amazon-q-developer-cli at [`15cc8f3cd18c4272925ce1c7053268eedff1ea0a`](https://github.com/aws/amazon-q-developer-cli/commit/15cc8f3cd18c4272925ce1c7053268eedff1ea0a)
(2026-04-23), workspace version 1.19.7 ([`Cargo.toml:11`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/Cargo.toml#L11)), dual licensed
Apache-2.0 and MIT. [`README.md:4`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/README.md#L4) says the project is unmaintained except
for security fixes and that the product continues as the closed-source Kiro
CLI. Two agent cores exist: `chat-cli` is the shipped `q chat` and the only
one that persists conversations; `crates/agent` is a newer loop with its own
camelCase `Message` types that is never written to disk here and is the most
likely shape of what Kiro CLI stores, though that is inference. Nothing in
the repository mentions `.kiro`, `kiro-cli`, `sessions/` or
`workspace-roots`; those catalog paths come from the closed binary and
remain unverified. No Kiro CLI binary or state existed on the research
machine.

## 2. Transcript stores

`dirs::data_local_dir()/amazon-q/data.sqlite3` ([`C/util/paths.rs:327-331`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/util/paths.rs#L327-L331);
[`crates/agent/src/agent/util/directories.rs:16`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/util/directories.rs#L16),[`37-48`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/util/directories.rs#L37-L48), overridable with
`Q_CLI_DATA_DIR`, [`crates/agent/src/agent/util/consts.rs:27`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/util/consts.rs#L27)): that is
`~/.local/share/amazon-q/`, `~/Library/Application Support/amazon-q/` and
`%LOCALAPPDATA%\amazon-q\`. Mode is forced to 0600 on Unix
([`C/database/mod.rs:212-223`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L212-L223)). The `kiro-cli` catalog variants are the
unverified rebrand.

Table `conversations`: one row per working directory. The key is the cwd
string and the value is `serde_json::to_string(&ConversationState)`
([`C/database/mod.rs:385-410`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L385-L410)), written with `INSERT OR REPLACE`
([`mod.rs:470-475`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L470-L475)) after every assistant turn ([`C/cli/chat/conversation.rs:403-422`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L403-L422)),
so only the latest conversation in each directory survives. Resume reads the
same key ([`C/cli/chat/mod.rs:719-724`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/mod.rs#L719-L724)).

`/save <path>` writes `serde_json::to_string_pretty(&session.conversation)`,
the same schema, to any user-chosen path; `/load` appends `.json` if missing
([`C/cli/chat/cli/persist.rs:60`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/cli/persist.rs#L60),[`89-90`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/cli/persist.rs#L89-L90)). `~/.aws/amazonq/.cli_bash_history`
([`paths.rs:63`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/util/paths.rs#L63)) and the shadow checkouts `~/.aws/amazonq/cli-checkouts`
([`paths.rs:62`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/util/paths.rs#L62)) are adjacent evidence, not transcripts.

## 3. Record schema

Migrations ([`C/database/mod.rs:67-76`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L67-L76), SQL in [`C/database/sqlite_migrations/`](https://github.com/aws/amazon-q-developer-cli/tree/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/sqlite_migrations)):

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

`history` has no writer in this repository (legacy shell history from the
Fig lineage); old installs may still hold rows.

Serialised `ConversationState` ([`conversation.rs:106-152`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L106-L152); default serde,
snake_case, externally tagged enums): `conversation_id` (random,
[`conversation.rs:109`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L109)), `next_message: UserMessage|null`, `history:
[HistoryEntry]`, `valid_history_range: [int,int]`, `transcript: [string]`,
`tools: {"native___"|<mcp server>: [...]}` ([`tools/mod.rs:305-315`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/tools/mod.rs#L305-L315)),
`context_manager`, `checkpoint_manager`, `file_line_tracker`,
`context_message_length` (opaque), `latest_summary: [string,
RequestMetadata]|null`, `model` (legacy, 1.13.3 and earlier), `model_info:
{model_id, model_name?, description?}` ([`cli/model.rs:26-35`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/cli/model.rs#L26-L35)),
`mcp_enabled`, `tangent_state` (optional, [`conversation.rs:154-167`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L154-L167)).
`tool_manager` and `agents` are `#[serde(skip)]`.

`HistoryEntry` ([`conversation.rs:91-97`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L91-L97)): `{user: UserMessage, assistant:
AssistantMessage, request_metadata: RequestMetadata|null}`.

`UserMessage` ([`message.rs:53-60`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L53-L60)): `additional_context`, `env_context:
{env_state: {operating_system, current_working_directory (truncated to 256,
consts.rs:3), environment_variables: [{key,value}]}}`
([`message.rs:422-425`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L422-L425),[`542-559`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L542-L559); [`api_client/model.rs:724-728`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/api_client/model.rs#L724-L728),[`761-764`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/api_client/model.rs#L761-L764)),
`content`, `timestamp: string|null`, `images`. `content` ([`message.rs:62-76`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L62-L76))
is one of `{"Prompt":{"prompt":s}}`, `{"CancelledToolUses":{"prompt":s|null,
"tool_use_results":[...]}}`, `{"ToolUseResults":{"tool_use_results":[...]}}`.
`timestamp` is `chrono::DateTime<FixedOffset>` from
`Local::now().fixed_offset()` ([`conversation.rs:398`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L398)), serialised RFC 3339
with the local offset, for example `2026-04-23T14:17:15.123456789-07:00`
(`chrono/src/datetime/serde.rs:32-46`, v0.4.42 per [`Cargo.lock:1575-1576`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/Cargo.lock#L1575-L1576)).
Tool-result user messages may carry `null`.

`ToolUseResult` ([`message.rs:332-340`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L332-L340)): `{tool_use_id, content: [{"Text":
string} | {"Json": any}], status: "Success"|"Error"}` ([`message.rs:387-391`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L387-L391);
[`api_client/model.rs:491-495`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/api_client/model.rs#L491-L495)).

`AssistantMessage` ([`message.rs:435-448`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L435-L448)): `{"Response":{"message_id":s|null,
"content":s}}` or `{"ToolUse":{"message_id":s|null,"content":s,"tool_uses":
[AssistantToolUse]}}`. `AssistantToolUse` ([`message.rs:507-519`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L507-L519)): `{id, name,
orig_name, args, orig_args}`; `id` is the backend `tool_use_id`
([`message.rs:531-539`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/message.rs#L531-L539)).

`RequestMetadata` ([`C/cli/chat/parser.rs:687-715`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/parser.rs#L687-L715)): `request_id`,
`message_id`, `request_start_timestamp_ms`, `stream_end_timestamp_ms` (unix
ms, [`parser.rs:693-696`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/parser.rs#L693-L696)), `time_to_first_chunk: {secs,nanos}|null`,
`time_between_chunks`, `user_prompt_length`, `response_size`,
`chat_conversation_type: "NotToolUse"|"ToolUse"|null`
([`telemetry/core.rs:534-539`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/telemetry/core.rs#L534-L539)), `tool_use_ids_and_names: [[id,name]]`,
`model_id`, `message_meta_tags: ["Compact"|"GenerateAgent"|"TangentMode"]`
([`core.rs:551-558`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/telemetry/core.rs#L551-L558)).

The newer `crates/agent` shape (not persisted here, [`agent_loop/types.rs`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs)):
`ConversationState {id: uuid, messages: [Message]}` ([`types.rs:147-150`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/types.rs#L147-L150));
`Message {id, role: "user"|"assistant", content: [{"text": s} | {"toolUse":
{toolUseId, name, input}} | {"toolResult": {toolUseId, content:
[{"text"}|{"json"}|{"image"}], status: "success"|"error"}} | {"image":
...}], timestamp: unix seconds|null}` ([`types.rs:161-170`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L161-L170),[`310-316`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L310-L316),[`383-400`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L383-L400),
[`402-407`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L402-L407),[`426-431`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L426-L431),[`445-451`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/agent/src/agent/agent_loop/types.rs#L445-L451)). Note camelCase and lower-case status.

## 4. Joins

All messages are embedded in the one JSON blob; `history[i]` is one
user/assistant pair in turn order, and `next_message` is a pending user
message. `history[i].assistant.ToolUse.tool_uses[].id` matches
`history[i+1].user.content.ToolUseResults.tool_use_results[].tool_use_id`
(or `CancelledToolUses`). `request_metadata.tool_use_ids_and_names`
duplicates the id to name map and `request_metadata.message_id` matches
`assistant.*.message_id`. cwd is the row `key` and, per message,
`user.env_context.env_state.current_working_directory`. No git branch is
recorded. Session id is `conversation_id`.

## 5. SQLite specifics

rusqlite 0.32 `bundled` via r2d2 ([`Cargo.toml:82-89`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/Cargo.toml#L82-L89)); no `PRAGMA` anywhere,
so the default rollback journal: no `-wal` or `-shm`, only a transient
`data.sqlite3-journal` during a write. A copied `data.sqlite3` alone is
complete unless Kiro CLI enabled WAL (unverified). Each write replaces the
whole blob, so a mid-write copy is the old or the new conversation, never a
partial row. No encryption.

## 6. Format versions

Migrations 000 to 007; `migrations.version` is the 0-based index,
`migration_time` unix seconds ([`mod.rs:448-451`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L448-L451)). `has_migration` re-checks
versions up to 7 because of an off-by-one in early builds ([`mod.rs:532-556`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L532-L556)).
No schema version inside the JSON; `request_metadata` is `#[serde(default)]`
([`conversation.rs:95`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L95)), `model` is kept only for 1.13.3 and earlier
([`conversation.rs:133-136`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/cli/chat/conversation.rs#L133-L136)), and `model_info`, `file_line_tracker`,
`mcp_enabled` and `tangent_state` are defaulted, so a parser must treat them
as optional. Legacy JSON exists only as `/save` exports. Paths still say
`amazon-q`, `.aws/amazonq` and `.amazonq` at this commit; expect the
`crates/agent` camelCase schema and per-session files if Kiro CLI stores
`~/.kiro/sessions/`.

## 7. Secrets

`auth_kv` keys `codewhisperer:odic:token` ([`C/auth/builder_id.rs:304`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/auth/builder_id.rs#L304)) and
`codewhisperer:odic:device-registration` ([`builder_id.rs:119`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/auth/builder_id.rs#L119)); values are
JSON with access and refresh tokens and a client secret. `state` key
`telemetry-cognito-credentials` holds `{access_key_id, secret_key,
session_token, expiration}` ([`mod.rs:57`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L57),[`78-84`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L78-L84)); also
`api.codewhisperer.profile`, `auth.idc.start-url`, `auth.idc.region`,
`telemetryClientId` ([`mod.rs:57-61`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/database/mod.rs#L57-L61)). Inside conversations, `tool_uses[].args`
and tool result `content` hold command lines and output, and
`env_state.environment_variables` can carry environment values.
`~/.aws/sso/cache` holds MCP OAuth tokens ([`paths.rs:314-316`](https://github.com/aws/amazon-q-developer-cli/blob/15cc8f3cd18c4272925ce1c7053268eedff1ea0a/crates/chat-cli/src/util/paths.rs#L314-L316)). The
collector flags `data.sqlite3` as secret.

## 8. Parser plan

Globs: `.local/share/amazon-q/data.sqlite3*`, `Library/Application Support/amazon-q/data.sqlite3*`,
`AppData/Local/amazon-q/data.sqlite3*`, the same three under `kiro-cli/`,
plus `**/*.json` whose top level has `conversation_id` and `history` (saved
exports), plus `.kiro/sessions/**` (format unknown; detect by
`messages[].role`).

Rows: one per user prompt, assistant message, `tool_uses[]` entry and
`tool_use_results[]` entry, and one `system` row per `latest_summary` or
`Compact` tag. The legacy `history` table yields optional rows
(`start_time`, `session_id`, `cwd`, `command`).

| Column | Source |
| --- | --- |
| timestamp_utc | `user.timestamp` converted to UTC for user and tool_result rows; `request_metadata.stream_end_timestamp_ms` for assistant and tool_use rows, falling back to `request_start_timestamp_ms` |
| session_id | `conversation_id` |
| project_path | row `key`, fallback `env_state.current_working_directory` |
| git_branch | empty |
| turn_type | `Prompt` → user; `Response`/`ToolUse` content → assistant; `tool_uses[]` → tool_use; `tool_use_results[]` → tool_result; `CancelledToolUses` → tool_result with summary "cancelled" |
| model | `request_metadata.model_id`, else `model_info.model_id`, else `model` |
| tool_name | `tool_uses[].name` (keep `orig_name` for MCP); result rows look the name up by id |
| tool_use_id | `id` / `tool_use_id` |
| text | prompt, content, `json.dumps(args)` or result text, with status appended for results |

Fixture:

```sql
CREATE TABLE conversations (key TEXT PRIMARY KEY, value TEXT);
INSERT INTO conversations (key, value) VALUES ('/home/alice/proj', '{"conversation_id":"3f2b8c1e-9d7a-4e6b-b1c2-0a9f8e7d6c5b","next_message":null,"history":[{"user":{"additional_context":"","env_context":{"env_state":{"operating_system":"linux","current_working_directory":"/home/alice/proj","environment_variables":[]}},"content":{"Prompt":{"prompt":"list the files here"}},"timestamp":"2026-04-23T14:17:15.123456789-07:00","images":null},"assistant":{"ToolUse":{"message_id":"msg-001","content":"I will list the directory.","tool_uses":[{"id":"tooluse_abc123","name":"execute_bash","orig_name":"execute_bash","args":{"command":"ls -la"},"orig_args":{"command":"ls -la"}}]}},"request_metadata":{"request_id":"req-001","message_id":"msg-001","request_start_timestamp_ms":1777000635200,"stream_end_timestamp_ms":1777000636900,"time_to_first_chunk":{"secs":0,"nanos":400000000},"time_between_chunks":[],"user_prompt_length":19,"response_size":26,"chat_conversation_type":"ToolUse","tool_use_ids_and_names":[["tooluse_abc123","execute_bash"]],"model_id":"claude-sonnet-4","message_meta_tags":[]}},{"user":{"additional_context":"","env_context":{"env_state":{"operating_system":"linux","current_working_directory":"/home/alice/proj","environment_variables":[]}},"content":{"ToolUseResults":{"tool_use_results":[{"tool_use_id":"tooluse_abc123","content":[{"Text":"total 8\nREADME.md"}],"status":"Success"}]}},"timestamp":null,"images":null},"assistant":{"Response":{"message_id":"msg-002","content":"The directory contains README.md."}},"request_metadata":{"request_id":"req-002","message_id":"msg-002","request_start_timestamp_ms":1777000637000,"stream_end_timestamp_ms":1777000638100,"time_to_first_chunk":null,"time_between_chunks":[],"user_prompt_length":0,"response_size":34,"chat_conversation_type":"NotToolUse","tool_use_ids_and_names":[],"model_id":"claude-sonnet-4","message_meta_tags":[]}}],"valid_history_range":[0,2],"transcript":["> list the files here","The directory contains README.md."],"tools":{"native___":[]},"context_manager":null,"context_message_length":null,"latest_summary":null,"model_info":{"model_id":"claude-sonnet-4","model_name":"Claude Sonnet 4"},"file_line_tracker":{},"checkpoint_manager":null,"mcp_enabled":true}');
CREATE TABLE auth_kv (key TEXT PRIMARY KEY, value TEXT);
INSERT INTO auth_kv VALUES ('codewhisperer:odic:token', '{"access_token":"REDACT-ME"}');
```

Confidence. High: path, tables, migrations, key = cwd, JSON field names and
enum tags, chrono RFC 3339 and unix-ms timestamp formats. Medium: the `dirs`
platform mapping (crate docs, not read); `tangent_start_time` serialisation.
Unverified: everything specific to Kiro CLI (`kiro-cli` directories,
`.kiro/sessions`, `workspace-roots`, WAL use, the camelCase `agent` schema
on disk, token key names after the rebrand); it needs strings from a shipped
binary.
