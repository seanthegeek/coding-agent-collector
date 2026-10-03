# Qwen Code transcript schema

Catalog agent: `qwen-code`. Qwen Code forked Gemini CLI, but its transcript
format has fully diverged: Gemini writes a metadata line plus message records
with `$set`/`$patch`/`$rewindTo` operations, Qwen writes a flat,
Claude-Code-style record stream with `uuid`, `parentUuid`, `cwd` and
`gitBranch` on every line. Only `logs.json`, `checkpoint-*.json`,
`shell_history` and the `tmp/<sha256>` layout are still shared with
[gemini-cli.md](gemini-cli.md). Paths cited are relative to the clone.

## 1. Source

QwenLM/qwen-code at `2c591ecc08a6fa080342f9b1b9f7f43215178cbb` (2026-10-03),
version 0.24.7, Apache-2.0. Open source.

## 2. Transcript files

Base directory `~/.qwen`, overridable by `$QWEN_HOME`
(`core/src/config/storage.ts:193-202`) or the `runtimeOutputDir` setting
(128-130).

- Session: `~/.qwen/projects/<sanitizeCwd(cwd)>/chats/<sessionId>.jsonl`,
  one file per session (storage.ts:619-623; `utils/paths.ts:388-392`: every
  character outside `[a-zA-Z0-9]` becomes `-`, Windows lower-cased;
  `services/chatRecordingService.ts:1305,1318-1321`). `sessionId` is a UUID;
  listing accepts `/^[0-9a-fA-F-]{32,36}\.jsonl$/`
  (`services/sessionService.ts:459`). Archived sessions move to
  `chats/archive/` (sessionService.ts:949-951).
- Sidecars in the same directory: `<sessionId>.runtime.json`
  (storage.ts:733-740; snake_case keys, `startedAt` epoch seconds,
  `utils/runtimeStatus.ts:46-60`), `<sessionId>.worktree.json`
  (`worktreeSessionService.ts:38`), `<sessionId>.ledger.jsonl` prompt ledger
  (sessionService.ts:1043-1046).
- `~/.qwen/tmp/<sha256(cwd)>/`: `logs.json`, `checkpoint-<tag>.json`,
  `checkpoints/`, `shell_history`, `tool-results/`
  (storage.ts:625-633,742-744,772-774; `core/logger.ts:14,203-204,693`;
  `paths.ts:368-373`).
- Managed-engine sessions: same `.jsonl` location plus
  `~/.qwen/resources/<sessionId>/` (`utils/sessionStorageUtils.ts:806-816`).

## 3. Record schema

Every line is a `ChatRecord` (`services/chatRecordingService.ts:336-521`):
`uuid`, `parentUuid: string|null`, `sessionId`, `timestamp` (ISO 8601, 1490),
`type: 'user'|'assistant'|'tool_result'|'system'`, `subtype?` (36 values,
354-389, including `chat_compression`, `slash_command`, `custom_title`,
`session_model`, `rewind`, `turn_result`, `branch_checkpoint`,
`managed_session_header_v1`), `provenance?` (270-276), `cwd`, `version` (CLI
version, 1501), `gitBranch?` (1502-1510 via `getGitBranch(cwd)`),
`promptId?`, `daemonPromptId?`, `message?: Content` (`{role, parts}`),
`usageMetadata?`, `model?`, `contextWindowSize?`, `toolCallResult?:
Partial<ToolCallResponseInfo> & {status?}`, `systemPayload?`, `agentId?`,
`agentName?`, `isSidechain?`, `agentRunId?`, `agentRound?`, `forkedFrom?:
{sessionId, messageUuid}`. Base fields are set at 1474-1504; `parentUuid`
is the previous record's uuid.

- user: `message = {role:'user', parts:[{text}]}`, optional `systemPayload:
  UserPromptRecordPayload {displayText, hookContext, attachmentReferences?,
  resourceLinks?}` (542-557), `promptId` (2281-2304).
- assistant: `model`, `message = {role:'model', parts}` whose parts carry
  `text`, `thought: true` text, and `functionCall {id, name, args}`;
  `usageMetadata`, `contextWindowSize` (2575-2611).
- tool_result: `message = {role:'user', parts:[{functionResponse:{id, name,
  response}}]}` plus `toolCallResult {callId, responseParts, resultDisplay,
  error, errorType, executionStatus, contentLength, status}`
  (`core/turn.ts:219-246`; status values `core/coreToolScheduler.ts:710`,
  the same seven strings as Gemini) (2741-2840).
- system payloads of interest: `ChatCompressionRecordPayload {info,
  compressedHistory: Content[], promptIds?}` (610-621),
  `SlashCommandRecordPayload {phase, rawCommand, sentToModel?}` (628-644),
  `SessionModelRecordPayload {modelId, authType, baseUrl?}` (703-708),
  `TurnResultRecordPayload {promptId, state, startedAt?, endedAt, promptText?,
  resultText?}` (949-965), `RewindRecordPayload {truncatedCount}` (837-839).

`logs.json` adds `type: 'model_switch'` with `message` = JSON
`ModelSwitchEvent {fromModel, toModel, reason, context?}` (logger.ts:16-33).
`checkpoint-<tag>.json` is a raw `Content[]` array (logger.ts:726), Gemini's
legacy shape.

## 4. Joins

Session = file = `sessionId` on every record; `cwd` and `gitBranch` on every
record (the lister reads the first record, sessionService.ts:1184-1197). Tool
call `message.parts[].functionCall.id` joins `tool_result.toolCallResult.callId`
and `message.parts[].functionResponse.id`. Turns group by `promptId`, the
tree by `parentUuid`, subagents by `isSidechain` and `agentId`, forks by
`forkedFrom`.

## 5. SQLite or binary stores

None; all stores are JSON or JSONL text.

## 6. Format versions

`version` on every record is the CLI version. Managed-engine transcripts
begin with `subtype:'managed_session_header_v1'` (`{formatVersion,
minimumReader, sessionKey, engine:'managed', ...}`,
`managed-runtime/managed-session-records.ts:220-229`) followed by
`managed_session_event_v1` and `commit_v1` records (209-241); detector
`sessionStorageUtils.ts:827,920-958`. `logs.json` and `checkpoint-*.json`
are the inherited Gemini legacy formats.

## 7. Secrets

`~/.qwen/oauth_creds.json` (storage.ts:16; `qwen/qwenOAuth2.ts:41`),
`mcp-oauth-tokens.json` (206), `.qwen-extension-git-credentials.json`
(`extension/extension-git-credentials.ts:20`). `session_model.systemPayload.baseUrl`
is an endpoint, not a key. `tool_result.toolCallResult.responseParts` and
`message.parts[].functionResponse.response` hold raw tool output;
`UserPromptRecordPayload.hookContext` is hook stdout. Session registry
records contain an `ipcToken` (`services/session-registry.ts:235`); location
not traced.

## 8. Parser plan

Globs (home-relative): `.qwen/projects/*/chats/*.jsonl`,
`.qwen/projects/*/chats/archive/*.jsonl`, `.qwen/tmp/*/logs.json`. Exclude
`*.runtime.json`, `*.worktree.json` and `*.ledger.jsonl` from transcript
parsing.

Rows: one per record; an assistant record additionally yields a `tool_use`
row per `functionCall` part and a `thinking` row per `thought:true` part.

| Column | Source |
| --- | --- |
| timestamp_utc | `timestamp` |
| session_id | `sessionId` |
| project_path | `cwd` |
| git_branch | `gitBranch` |
| turn_type | user/assistant/tool_result as-is; system → system; functionCall → tool_use; thought part → thinking |
| model | `model` |
| tool_name | `functionCall.name` / `functionResponse.name` |
| tool_use_id | `functionCall.id` / `toolCallResult.callId` |
| summary | text parts, `systemPayload.displayText`, `rawCommand`, `toolCallResult.status` plus `errorType` |

Fixture:

```json
{"uuid":"0f0e0d0c-3333-4000-8000-000000000010","parentUuid":null,"sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:00.000Z","type":"user","provenance":"real_user","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","promptId":"e5f6a7b8-4444-4000-8000-000000000011########1","message":{"role":"user","parts":[{"text":"run the tests"}]},"systemPayload":{"displayText":"run the tests","hookContext":""}}
{"uuid":"1a1b1c1d-5555-4000-8000-000000000012","parentUuid":"0f0e0d0c-3333-4000-8000-000000000010","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:03.000Z","type":"assistant","provenance":"assistant_output","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","model":"qwen3-coder-plus","message":{"role":"model","parts":[{"text":"Plan: run npm test.","thought":true},{"text":"Running tests."},{"functionCall":{"id":"call_abc123","name":"run_shell_command","args":{"command":"npm test"}}}]},"usageMetadata":{"promptTokenCount":200,"candidatesTokenCount":30,"totalTokenCount":230},"contextWindowSize":131072}
{"uuid":"2b2c2d2e-6666-4000-8000-000000000013","parentUuid":"1a1b1c1d-5555-4000-8000-000000000012","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:09.000Z","type":"tool_result","provenance":"tool_result","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","message":{"role":"user","parts":[{"functionResponse":{"id":"call_abc123","name":"run_shell_command","response":{"output":"12 passing"}}}]},"toolCallResult":{"callId":"call_abc123","status":"success","resultDisplay":"12 passing","errorType":null}}
{"uuid":"3c3d3e3f-7777-4000-8000-000000000014","parentUuid":"2b2c2d2e-6666-4000-8000-000000000013","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:10.000Z","type":"system","subtype":"custom_title","provenance":"system","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","systemPayload":{"customTitle":"Run tests","titleSource":"auto"}}
```

Confidence. High: record field names, file paths, status values, ISO
timestamps, sidecar names. Medium: `turn_result.startedAt/endedAt` unit
(numbers; inferred milliseconds); `errorType` serialised value. Not
determined: exact `logs.json` `model_switch` serialisation; the session
registry file location holding `ipcToken`; `hookContext` content.
