# Cline transcript schema

Catalog agent: `cline`. Researched together with Roo Code and Kilo Code; Roo
forked Cline and still shares its task layout ([roo-code.md](roo-code.md)),
Kilo has since moved to an OpenCode-derived store
([kilo-code.md](kilo-code.md)). Paths cited are relative to the clone.

## 1. Source

cline/cline at `39ff2359f7e08231281539696e48a166ce49270c`, Apache-2.0. Open
source. Applies to the VS Code extension (`saoudrizwan.claude-dev`), the CLI
and JetBrains, all through the `sdk/` packages.

## 2. Transcript files

Legacy task layout, one directory per task. Root is VS Code
`globalStorage/saoudrizwan.claude-dev/` for the extension
(`apps/vscode/src/core/storage/disk.ts:190-194`) or `~/.cline/data/` for CLI
and JetBrains (`apps/vscode/src/sdk/legacy-state-reader.ts:24-29`); env
`CLINE_DATA_DIR` or `CLINE_DIR` overrides. Files (`disk.ts:17-36`,
`legacy-state-reader.ts:42-72`): `tasks/<taskId>/api_conversation_history.json`
(JSON array), `ui_messages.json` (JSON array), `context_history.json`,
`task_metadata.json`, `settings.json`; index `state/taskHistory.json` (JSON
array of `HistoryItem`); `globalState.json`, `secrets.json`,
`settings/cline_mcp_settings.json`. `taskId` is a `Date.now()` millisecond
string (`HistoryItem.id`).

SDK session layout, current on all hosts: `~/.cline/data/sessions/<sessionId>/`
(`sdk/packages/shared/src/storage/paths.ts:179-192`) holding
`<sessionId>.json` (manifest), `<sessionId>.messages.json`,
`<sessionId>.compaction.json` (`sdk/packages/core/src/services/session-artifacts.ts:75-94`);
subagent transcripts in the same directory as `<agentId>.messages.json` or
`<agentId>__<teamTaskId>.messages.json` (`:34-57,132-144`). `sessionId` is
`${Date.now()}_${nanoid(5)}` (`session/services/persistence-service.ts:109`).
Fallback index `sessions/sessions.index.json`
(`session/services/file-session-service.ts:63`). SQLite in `~/.cline/data/db/`
(section 5). Hook audit `~/.cline/data/logs/hooks.jsonl`
(`hooks/hook-file-hooks.ts:647`).

## 3. Record schema

`api_conversation_history.json` is `Anthropic.MessageParam[]` (`disk.ts:155`):
`{role: "user"|"assistant", content: string | [{type:"text",text} |
{type:"tool_use",id,name,input} | {type:"tool_result",tool_use_id,content,is_error?}
| {type:"thinking",thinking} | {type:"image",source:{type:"base64",media_type,data}}]}`
(block handling `apps/vscode/src/sdk/legacy-task-handling.ts:13-45`). No
timestamps. Legacy tool calls are mostly XML inside text blocks, not
`tool_use`.

`ui_messages.json` is `ClineMessage[]` (`apps/vscode/src/shared/ExtensionMessage.ts:178-208`):
`ts` (ms, also the identity), `type: "ask"|"say"`, `ask?`, `say?`, `text?`,
`reasoning?`, `images?`, `files?`, `partial?`, `conversationHistoryIndex?`,
`lastCheckpointHash?`, `modelInfo?: {modelId, providerId, mode}`
(`shared/messages/metrics.ts`). Asks `:210-228` (followup,
plan_mode_respond, act_mode_respond, command, command_output,
completion_result, tool, api_req_failed, resume_task, use_mcp_server,
new_task, condense, ...); says `:230-266` (task, error, api_req_started,
api_req_finished, text, reasoning, completion_result, user_feedback, command,
command_output, tool, browser_action*, mcp_server_request_started,
mcp_server_response, checkpoint_created, hook_status, subagent, compaction,
...). `text` is JSON for `say`/`ask` `"tool"` (`ClineSayTool {tool, path,
diff, content, regex, filePattern}`, `:269-294`), `"api_req_started"`
(`ClineApiReqInfo {request, tokensIn, tokensOut, cacheWrites, cacheReads,
cost, cancelReason}`, `:370-379`) and `"use_mcp_server"` (`{serverName, type,
toolName, arguments, uri}`, `:346-352`).

`HistoryItem` (`apps/vscode/src/shared/HistoryItem.ts:1-26`): `id, ulid?, ts,
task, tokensIn, tokensOut, cacheWrites?, cacheReads?, totalCost, size?,
cwdOnTaskInitialization?, modelId?, apiProvider?, isLegacy?`.

`task_metadata.json` (`core/context/context-tracking/ContextTrackerTypes.ts:28-32`):
`files_in_context[{path, record_state, record_source, cline_read_date,
cline_edit_date}]`, `model_usage[{ts, model_id, model_provider_id, mode}]`,
`environment_history[{ts, os_name, os_version, host_name, cline_version}]`.

SDK manifest `<id>.json` (`sdk/packages/core/src/session/models/session-manifest.ts:6-28`):
`version:1, session_id, source, pid, started_at (ISO 8601), ended_at?,
exit_code?, status (idle|running|pending|completed|failed|cancelled,
shared/src/session/records.ts:1-15), interactive, provider, model, cwd,
workspace_root, team_name?, enable_tools, enable_spawn, enable_teams,
prompt?, metadata?{title,...}, messages_path?`.

SDK `<id>.messages.json` (`services/session-data.ts:334-359,281-294`):
`{version:1, updated_at (ISO), agent:"lead"|"subagent"|"teammate",
sessionId, taskType?, origin{source, mode, sessionId, parentThreadId?,
subagent?, version?, trigger?}, system_prompt?, messages:
MessageWithMetadata[]}`. Message (`sdk/packages/shared/src/llms/messages.ts:130-165`):
`role: "user"|"assistant"`, `content: string|ContentBlock[]`, `id?`, `agent?`,
`sessionId?`, `metadata?` (keys seen at call sites: `displayOnly`,
`displayRole`, `kind`, `userRunSpan`, `checkpoint`), `modelInfo?{id, provider,
family?}`, `metrics?{inputTokens, outputTokens, cacheReadTokens,
cacheWriteTokens, cost}`, `ts?` (ms epoch, `session-data.ts:196`). Blocks
(`messages.ts:19-125`): `text{text}`, `tool_use{id, call_id?, name, input}`,
`tool_result{tool_use_id, name, content, is_error?}`, `thinking{thinking,
signature?}`, `redacted_thinking{data}`, `image{data, mediaType}`,
`file{content, path}`, `media`.

Timestamps are millisecond epochs except the SDK manifest and payload
(`started_at`, `updated_at` ISO). No git branch is recorded.

## 4. Joins

Legacy: directory name = `HistoryItem.id`; workspace =
`cwdOnTaskInitialization` in `state/taskHistory.json`;
`ClineMessage.conversationHistoryIndex` indexes into
`api_conversation_history.json`; `tool_use.id` pairs with
`tool_result.tool_use_id` within the array (rare, since most tool traffic is
XML text). SDK: `messages.json.sessionId` = manifest `session_id` =
`sessions.session_id`; workspace = manifest `cwd` or `workspace_root`;
`tool_use.id` pairs with `tool_result.tool_use_id`. VS Code merges the legacy
and SDK lists (`apps/vscode/src/sdk/sdk-task-history.ts:413-424`), stamping
`metadata.legacyTask`.

## 5. SQLite stores

`~/.cline/data/db/sessions.db` (`paths.ts:240-249`;
`shared/src/db/sqlite-db.ts:188-273`): `sessions(session_id, source, pid,
started_at, ended_at, exit_code, status, status_lock, interactive, provider,
model, cwd, workspace_root, team_name, enable_*, parent_session_id,
parent_agent_id, agent_id, conversation_id, is_subagent, prompt,
metadata_json, transcript_path, hook_path, messages_path, updated_at)`,
`subagent_spawn_queue`, `schedules(prompt, system_prompt, ...)`,
`schedule_executions`. `db/session-search.db`: `indexed_sessions` plus FTS5
`session_search(session_id, document_id, ordinal, role, started_at,
workspace_root, title, content)` (`session/search/session-history-search.ts:123-153,196`),
a full-text copy of every transcript. `teams/teams.db`
(`services/storage/sqlite-team-store.ts:210-330`): `team_events(payload_json)`,
`team_tasks`, `team_runs`, `team_mailbox(data_json)`,
`team_mission_log(data_json)`.

## 6. Format versions

Three generations coexist on disk: VS Code globalStorage tasks,
`~/.cline/data/tasks` with `state/taskHistory.json`, and
`~/.cline/data/sessions/<id>/`. The VS Code to file migration of state and
secrets uses the sentinel `__migrationVersion`
(`hosts/vscode/vscode-to-file-migration.ts:11-31`); task files are not moved.
SDK files carry `version: 1`. Legacy tasks resumed in the SDK get
`metadata.legacyTask: true`. `sessions.db` has ALTER-based column migrations
(`sqlite-db.ts:275-324`).

## 7. Secrets

`secrets.json` keys (`apps/vscode/src/shared/storage/state-keys.ts`
SECRETS_KEYS): `apiKey, clineApiKey, clineAccountId, openRouterApiKey,
awsAccessKey, awsSecretKey, awsSessionToken, openAiApiKey, geminiApiKey, ...,
mcpOAuthSecrets, openai-codex-oauth-credentials, ocaRefreshToken`. Also
`messages.json.system_prompt`, `manifest.prompt`, `schedules.system_prompt`,
`session-search.db` content, `images[]` base64, and file contents and command
output in every transcript.

## 8. Parser plan

Globs (home-relative; `<GS>` is each VS Code `User/globalStorage`):
`<GS>/saoudrizwan.claude-dev/tasks/*/{api_conversation_history,ui_messages,task_metadata}.json`,
`<GS>/saoudrizwan.claude-dev/state/taskHistory.json`, the same under
`.cline/data/`, `.cline/data/sessions/*/*.json`,
`.cline/data/sessions/*/*.messages.json`, `.cline/data/db/sessions.db`,
`.cline/data/logs/hooks.jsonl`.

Rows: one per `ui_messages` entry for legacy tasks (preferred over the API
history because it has `ts`), one per content block of SDK messages.

| Column | Legacy | SDK |
| --- | --- | --- |
| timestamp_utc | `ClineMessage.ts` ms | `message.ts` ms, else manifest `started_at` |
| session_id | directory name | `sessionId` |
| project_path | `cwdOnTaskInitialization` | manifest `cwd` |
| git_branch | empty | empty |
| turn_type | say `task`/`user_feedback` → user; `text`/`completion_result` → assistant; `reasoning` → thinking; `tool`/`command`/`use_mcp_server` → tool_use; `command_output`/`mcp_server_response` → tool_result; `error`/`api_req_*` → system | text → by role; tool_use; tool_result; thinking |
| model | `modelInfo.modelId` or `task_metadata.model_usage` | `modelInfo.id` or manifest `model` |
| tool_name | `ClineSayTool.tool` / `use_mcp_server.toolName` | `tool_use.name` |
| tool_use_id | `ts` | `tool_use.id` / `tool_use_id` |
| text | `text` | first text or tool input |

Fixtures (invented content, real field names):

```json
{"_file":"ui_messages.json","record":{"ts":1760000000000,"type":"say","say":"tool","text":"{\"tool\":\"readFile\",\"path\":\"src/app.py\",\"content\":\"/home/u/proj/src/app.py\"}","modelInfo":{"modelId":"claude-sonnet-4-5","providerId":"anthropic","mode":"act"}}}
{"_file":"ui_messages.json","record":{"ts":1760000001000,"type":"say","say":"api_req_started","text":"{\"request\":\"<task>fix tests</task>\",\"tokensIn\":1200,\"tokensOut\":80,\"cacheWrites\":0,\"cacheReads\":900,\"cost\":0.0041}"}}
{"_file":"api_conversation_history.json","record":{"role":"assistant","content":[{"type":"tool_use","id":"toolu_01A","name":"execute_command","input":{"command":"pytest -q"}}]}}
{"_file":"api_conversation_history.json","record":{"role":"user","content":[{"type":"tool_result","tool_use_id":"toolu_01A","content":"3 passed","is_error":false}]}}
{"_file":"state/taskHistory.json","record":{"id":"1760000000000","ulid":"01JAX3Q8M4","ts":1760000000000,"task":"fix tests","tokensIn":1200,"tokensOut":80,"totalCost":0.0041,"cwdOnTaskInitialization":"/home/u/proj","modelId":"claude-sonnet-4-5","apiProvider":"anthropic"}}
{"_file":"sessions/<id>/<id>.json","record":{"version":1,"session_id":"1760000000000_k3x9q","source":"cli","pid":4242,"started_at":"2026-10-03T09:00:00.000Z","status":"completed","interactive":true,"provider":"anthropic","model":"claude-sonnet-4-5","cwd":"/home/u/proj","workspace_root":"/home/u/proj","enable_tools":true,"enable_spawn":false,"enable_teams":false,"prompt":"fix tests","metadata":{"title":"fix tests"},"messages_path":"/home/u/.cline/data/sessions/1760000000000_k3x9q/1760000000000_k3x9q.messages.json"}}
{"_file":"sessions/<id>/<id>.messages.json","record":{"version":1,"updated_at":"2026-10-03T09:00:05.000Z","agent":"lead","sessionId":"1760000000000_k3x9q","origin":{"source":"cli","mode":"user","sessionId":"1760000000000_k3x9q"},"messages":[{"id":"m1","role":"user","content":"fix tests","ts":1760000000000},{"id":"m2","role":"assistant","content":[{"type":"thinking","thinking":"run the suite"},{"type":"tool_use","id":"call_1","name":"bash","input":{"command":"pytest -q"}}],"modelInfo":{"id":"claude-sonnet-4-5","provider":"anthropic"},"metrics":{"inputTokens":1200,"outputTokens":80,"cost":0.0041},"ts":1760000002000},{"id":"m3","role":"user","content":[{"type":"tool_result","tool_use_id":"call_1","name":"bash","content":"3 passed","is_error":false}],"ts":1760000003000}]}}
```

Confidence. High: file names, layouts, `ClineMessage`, `HistoryItem`,
manifest and `MessageWithMetadata` fields, `sessions.db` columns. Medium:
exact `metadata` keys in SDK messages (collected from call sites, not a
schema); whether the VS Code extension now writes new tasks to
`~/.cline/data/sessions` rather than globalStorage (code reads both;
`legacyExtensionStorageDir` is the globalStorage path, `SdkController.ts:505`).
