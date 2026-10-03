# Gemini CLI and Qwen Code transcript schemas

Paths below are relative to the repo clones under `scratchpad/repos/`. `G:` = gemini-cli, `Q:` = qwen-code.

## 1. Repos, commits, licenses

| Tool | Repo | Commit | Version | License |
|---|---|---|---|---|
| Gemini CLI | google-gemini/gemini-cli | `fb972b2f87fe7d5b06d37eac711490162d98de2c` (2026-10-02) | 0.64.0-nightly.20260929 | Apache-2.0 |
| Qwen Code | QwenLM/qwen-code | `2c591ecc08a6fa080342f9b1b9f7f43215178cbb` (2026-10-03) | 0.24.7 | Apache-2.0 |

Qwen Code forked Gemini CLI but its transcript format has fully diverged: Gemini writes a session-metadata-plus-messages log with `$set`/`$patch`/`$rewindTo` operations; Qwen writes a flat, Claude-Code-style record stream with `uuid`/`parentUuid`/`cwd`/`gitBranch`. Only `logs.json`, `checkpoint-*.json`, `shell_history` and the `tmp/<sha256>` layout are still shared. Each finding is tagged G or Q.

## 2. Transcript files

**Gemini (G).** Base dir `~/.gemini` (`packages/core/src/config/storage.ts:54-60`); under macOS `SANDBOX=sandbox-exec` it is `~/.cache/.gemini` (storage.ts:97-101). Project identifier is now a *slug*, not a hash: `~/.gemini/projects.json` maps `{ "projects": { "<abs path>": "<slug>" } }` (storage.ts:289-299; `projectRegistry.ts:16-18,304-316,414-421`, slug = lowercased basename with non-alnum runs replaced by `-`, suffixed `-1`, `-2` on collision). Each slug dir carries a marker `~/.gemini/tmp/<slug>/.project_root` whose content is the absolute project path (projectRegistry.ts:24,372-412). Legacy `tmp/<sha256(projectRoot)>` dirs are *copied* to the slug dir on first run and left in place (storage.ts:310-324; `storageMigration.ts:20-52`; `utils/paths.ts:318-320`), so both may exist.

- Session: `~/.gemini/tmp/<slug>/chats/session-<YYYY-MM-DDTHH-MM>-<shortId8>.jsonl`, one file per session, JSONL (`services/chatRecordingService.ts:757-799`; prefix `chatRecordingTypes.ts:12`). Collisions insert `-1-`, `-2-` before the shortId (795-797). Subagent sessions: `chats/<parentSessionId>/<sessionId>.jsonl` (763-791).
- Legacy session: same name with `.json`, one JSON object (`ConversationRecord`) (1566-1616); on resume it is re-emitted into a sibling `.jsonl` (708-735).
- Prompt history: `~/.gemini/tmp/<slug>/logs.json`, JSON array of `LogEntry` (`core/logger.ts:15,21-27,148-149,229-233`).
- `/chat save` checkpoints: `tmp/<slug>/checkpoint-<encodeURIComponent(tag)>.json` (logger.ts:285-295,329-343; `cli/.../chatCommand.ts:142`).
- Tool checkpoints: `tmp/<slug>/checkpoints/<ISO ts with : and . replaced>-<basename>-<tool>.json` (`utils/checkpointUtils.ts:59-66,130-141`; storage.ts:364-366) backed by a shadow git repo at `~/.gemini/history/<slug>` (storage.ts:326-330; `gitService.ts:74-75`).
- Activity log (optional): `tmp/<slug>/logs/session-<sessionId>.jsonl` (`cli/src/utils/activityLogger.ts:693-699`). Schema not examined.
- Externalised large tool output: `tmp/<slug>/tool-outputs/` (`utils/fileUtils.ts:799,814`); shell history `tmp/<slug>/shell_history` (storage.ts:480-482).

**Qwen (Q).** Base dir `~/.qwen`, overridable by `$QWEN_HOME` (`core/src/config/storage.ts:193-202`) or the `runtimeOutputDir` setting (128-130).

- Session: `~/.qwen/projects/<sanitizeCwd(cwd)>/chats/<sessionId>.jsonl`, one file per session, JSONL (storage.ts:619-623; `utils/paths.ts:388-392`: every non-`[a-zA-Z0-9]` char becomes `-`, Windows lowercased; `services/chatRecordingService.ts:1305,1318-1321`). `sessionId` is a UUID; listing accepts `/^[0-9a-fA-F-]{32,36}\.jsonl$/` (`services/sessionService.ts:459`). Archived sessions move to `chats/archive/` (sessionService.ts:949-951).
- Sidecars in the same dir: `<sessionId>.runtime.json` (storage.ts:733-740; snake_case keys, `startedAt` epoch *seconds*, `utils/runtimeStatus.ts:46-60`), `<sessionId>.worktree.json` (`worktreeSessionService.ts:38`), `<sessionId>.ledger.jsonl` prompt ledger (sessionService.ts:1043-1046).
- `~/.qwen/tmp/<sha256(cwd)>/`: `logs.json`, `checkpoint-<tag>.json`, `checkpoints/`, `shell_history`, `tool-results/` (storage.ts:625-633,742-744,772-774; `core/logger.ts:14,203-204,693`; `paths.ts:368-373`).
- Managed-engine sessions: same `.jsonl` location plus `~/.qwen/resources/<sessionId>/` (`utils/sessionStorageUtils.ts:806-816`).

## 3. Record schemas

**G session JSONL** (`services/chatRecordingTypes.ts`). Line 1 is `PartialMetadataRecord` (156-165): `sessionId`, `projectHash` (sha256 of project path, string), `startTime`, `lastUpdated` (ISO 8601), `summary?`, `directories?: string[]`, `kind?: 'main'|'subagent'`. Subsequent lines are one of (discriminated at `chatRecordingService.ts:79-95`):

- `MessageRecord` = `BaseMessageRecord & ConversationRecordExtra` (44-87): `id` (UUID), `timestamp` (ISO 8601, `toISOString`, chatRecordingService.ts:1022), `content: PartListUnion` (string | Part | Part[]), `displayContent?`, `type: 'user'|'info'|'error'|'warning'|'gemini'`. For `type:'gemini'` also `toolCalls?: ToolCallRecord[]`, `thoughts?: {subject, description, timestamp}[]` (`utils/thoughtUtils.ts:7-10`), `tokens?: {input, output, cached, thoughts?, tool?, total}` (19-26), `model?: string`.
- `ToolCallRecord` (54-67): `id`, `name`, `args: object`, `result?: PartListUnion|null`, `status` from `CoreToolCallStatus` = `validating|scheduled|error|success|executing|cancelled|awaiting_approval` (`scheduler/types.ts:26-34`), `timestamp`, `agentId?`, `displayName?`, `description?`, `resultDisplay?` (string | `FileDiff{fileDiff,fileName,filePath,originalContent,newContent}` | ... `tools/tools.ts:935-966`), `renderOutputAsMarkdown?`.
- `{ "$set": {...metadata fields..., "memoryScratchpad"?, legacy "messages"?} }` (149-154); `{ "$patch": { id?, content?, toolCalls?:[{id,result}], updates?, removeIds?, orderIds? } }` (138-147); `{ "$rewindTo": "<message id>" }` (123-125) drops that message and all later ones (chatRecordingService.ts:305-335).

Current code records model text only as `content` (geminiChat.ts:1652-1656) with tool calls in `toolCalls`; the reader also accepts `functionCall`/`thought: true` parts inside `content` ("modern session", `utils/sessionUtils.ts:138-144`). **No cwd and no git branch** are stored in the session file.

**G logs.json** `LogEntry`: `sessionId`, `messageId` (int, per-session counter), `timestamp` (ISO), `type: 'user'`, `message` (logger.ts:17-27). User prompts only.

**G checkpoint-<tag>.json**: `{ "history": Content[], "authType"?: string }` (logger.ts:29-32). **G checkpoints/*.json** `ToolCallData`: `history?`, `clientHistory?: Content[]`, `commitHash?`, `toolCall: {name, args}`, `messageId?` (= `prompt_id`) (checkpointUtils.ts:15-24,130-139).

**Q session JSONL** — every line is a `ChatRecord` (`services/chatRecordingService.ts:336-521`): `uuid`, `parentUuid: string|null`, `sessionId`, `timestamp` (ISO 8601, 1490), `type: 'user'|'assistant'|'tool_result'|'system'`, `subtype?` (36 values, 354-389, incl. `chat_compression`, `slash_command`, `custom_title`, `session_model`, `rewind`, `turn_result`, `branch_checkpoint`, `managed_session_header_v1`), `provenance?` (270-276), `cwd` (string), `version` (CLI version, 1501), `gitBranch?` (1502-1510 via `getGitBranch(cwd)`), `promptId?`, `daemonPromptId?`, `message?: Content` (`{role, parts}`), `usageMetadata?` (genai `GenerateContentResponseUsageMetadata`), `model?`, `contextWindowSize?`, `toolCallResult?: Partial<ToolCallResponseInfo> & {status?}`, `systemPayload?`, `agentId?`, `agentName?`, `isSidechain?`, `agentRunId?`, `agentRound?`, `forkedFrom?: {sessionId, messageUuid}`. Base fields set at 1474-1504 (`parentUuid` = previous record's uuid).

- user: `message = {role:'user', parts:[{text}]}`, optional `systemPayload: UserPromptRecordPayload {displayText, hookContext, attachmentReferences?, resourceLinks?}` (542-557), `promptId` (2281-2304).
- assistant: `model`, `message = {role:'model', parts}` where parts carry `text`, `thought: true` text, and `functionCall {id, name, args}`; `usageMetadata`, `contextWindowSize` (2575-2611).
- tool_result: `message = {role:'user', parts:[{functionResponse:{id, name, response}}]}` plus `toolCallResult {callId, responseParts, resultDisplay, error, errorType, executionStatus, contentLength, status}` (`core/turn.ts:219-246`; status values `core/coreToolScheduler.ts:710`, same seven strings as Gemini) (2741-2840).
- system payloads of interest: `ChatCompressionRecordPayload {info, compressedHistory: Content[], promptIds?}` (610-621), `SlashCommandRecordPayload {phase, rawCommand, sentToModel?}` (628-644), `SessionModelRecordPayload {modelId, authType, baseUrl?}` (703-708), `TurnResultRecordPayload {promptId, state, startedAt?, endedAt (numbers), promptText?, resultText?}` (949-965), `RewindRecordPayload {truncatedCount}` (837-839).

**Q logs.json** adds `type: 'model_switch'` with `message` = JSON `ModelSwitchEvent {fromModel, toModel, reason, context?}` (logger.ts:16-33). **Q checkpoint-<tag>.json** is a raw `Content[]` array (logger.ts:726), i.e. Gemini's *legacy* shape.

## 4. Joins

- G: session = file; `sessionId` from line 1 (and any later `$set.sessionId`, which is rewritten on resume, chatRecordingService.ts:739). Messages join by file. A tool call and its result are the same `toolCalls[]` element (`id`, `result`, `status`); the whole gemini message is re-appended each time its toolCalls change (1125-1200, 989-1005), so parsers must keep the *last* record per `id` and apply `$patch`/`$rewindTo`. Project path: `tmp/<slug>/.project_root` content, or `projects.json` reverse lookup; legacy hash dirs have no reverse map (sha256 of the path, compare against known cwds). `kind` + directory nesting link subagent to parent.
- Q: session = file = `sessionId` on every record; `cwd` and `gitBranch` on every record (first record is what the lister reads, sessionService.ts:1184-1197). Tool call `message.parts[].functionCall.id` joins `tool_result.toolCallResult.callId` / `message.parts[].functionResponse.id`. Turn grouping via `promptId`; tree via `parentUuid`; subagent via `isSidechain`/`agentId`; forks via `forkedFrom`.

## 5. SQLite or binary stores

None in either tool. All stores are JSON/JSONL text. Gemini's `~/.gemini/history/<slug>` is a bare-ish git repository (shadow checkpoints); treat as binary.

## 6. Format versions

- G: hash dirs → slug dirs (copied, both remain); `session-*.json` single object → `.jsonl`; `$set.messages` full-history checkpoints deprecated (chatRecordingTypes.ts:150-153); checkpoint-<tag> raw array → `{history, authType}` (logger.ts:359-372); legacy un-encoded `checkpoint-<tag>.json` names (logger.ts:312-313). No explicit version field.
- Q: `version` on every record is the CLI version; Managed-engine transcripts begin with `subtype:'managed_session_header_v1'` (`{formatVersion, minimumReader, sessionKey, engine:'managed', ...}`, `managed-runtime/managed-session-records.ts:220-229`) followed by `managed_session_event_v1`/`commit_v1` records (209-241); detector `sessionStorageUtils.ts:827,920-958`. `logs.json` and `checkpoint-*.json` are the inherited Gemini legacy formats.

## 7. Secrets to redact

- G: `~/.gemini/oauth_creds.json` (storage.ts:22,255-257), `mcp-oauth-tokens.json`, `a2a-oauth-tokens.json` (70-76), `gemini-credentials.json` (`services/fileKeychain.ts:20`), `google_accounts.json`. Checkpoints (`clientHistory`) and `toolCalls[].result` embed full tool output (env dumps, `.env` reads).
- Q: `~/.qwen/oauth_creds.json` (storage.ts:16; `qwen/qwenOAuth2.ts:41`), `mcp-oauth-tokens.json` (206), `.qwen-extension-git-credentials.json` (`extension/extension-git-credentials.ts:20`); `session_model.systemPayload.baseUrl` (endpoint, not a key); `tool_result.toolCallResult.responseParts` and `message.parts[].functionResponse.response` hold raw tool output; `UserPromptRecordPayload.hookContext` is hook stdout. Session registry records contain `ipcToken` (`services/session-registry.ts:235`); location not traced.

## 8. Parser plan

Globs (relative to home): G `.gemini/tmp/*/chats/**/*.jsonl`, `.gemini/tmp/*/chats/**/*.json`, `.gemini/tmp/*/logs.json`, `.gemini/tmp/*/checkpoints/*.json`, `.cache/.gemini/tmp/*/chats/**/*.jsonl`; Q `.qwen/projects/*/chats/*.jsonl`, `.qwen/projects/*/chats/archive/*.jsonl`, `.qwen/tmp/*/logs.json`. Exclude `*.runtime.json`, `*.worktree.json`, `*.ledger.jsonl` from transcript parsing but keep as metadata.

One row per: G user/info/error/warning message; one `assistant` row per gemini message plus one `thinking` row per `thoughts[]` entry, one `tool_use` per `toolCalls[]` element (and one `tool_result` when `result` is non-null, same `tool_use_id`); `logs.json` entries as `user` rows when no session file covers that sessionId. Q: one row per record; an assistant record additionally yields a `tool_use` row per `functionCall` part and a `thinking` row per `thought:true` part.

Column mapping:

| CSV | Gemini | Qwen |
|---|---|---|
| timestamp_utc | `timestamp` (ISO; `toolCalls[].timestamp`, `thoughts[].timestamp`) | `timestamp` |
| session_id | line-1 `sessionId` (override by later `$set.sessionId`) | `sessionId` |
| project_path | `.project_root` / `projects.json`; else `projectHash` | `cwd` |
| git_branch | empty | `gitBranch` |
| turn_type | user→user; gemini→assistant; info/error/warning→system; toolCalls→tool_use/tool_result; thoughts→thinking | user/assistant/tool_result as-is; system→system; functionCall→tool_use; thought part→thinking |
| model | `model` | `model` |
| tool_name | `toolCalls[].name` | `functionCall.name` / `functionResponse.name` |
| tool_use_id | `toolCalls[].id` | `functionCall.id` / `toolCallResult.callId` |
| summary | `content` text (first 200 chars); for tool_use `displayName`+args; `summary` on `$set` | text parts / `systemPayload.displayText` / `rawCommand` / `toolCallResult.status`+`errorType` |

Synthetic fixtures (one line each):

```json
{"sessionId":"a1b2c3d4-0000-4000-8000-000000000001","projectHash":"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08","startTime":"2026-10-01T09:00:00.000Z","lastUpdated":"2026-10-01T09:00:00.000Z","kind":"main"}
{"id":"6a0e3e5a-1111-4000-8000-000000000002","timestamp":"2026-10-01T09:00:05.000Z","type":"user","content":[{"text":"list files in src"}]}
{"id":"7b1f4f6b-2222-4000-8000-000000000003","timestamp":"2026-10-01T09:00:07.000Z","type":"gemini","content":"Listing now.","thoughts":[{"subject":"Plan","description":"Use the ls tool.","timestamp":"2026-10-01T09:00:06.500Z"}],"tokens":{"input":120,"output":12,"cached":0,"thoughts":8,"tool":0,"total":140},"model":"gemini-2.5-pro","toolCalls":[{"id":"list_directory-1759309207000","name":"list_directory","args":{"path":"/home/alice/proj/src"},"status":"success","timestamp":"2026-10-01T09:00:07.100Z","result":[{"functionResponse":{"id":"list_directory-1759309207000","name":"list_directory","response":{"output":"main.ts\nutil.ts"}}}],"displayName":"ReadFolder","description":"Lists files"}]}
{"$set":{"lastUpdated":"2026-10-01T09:00:08.000Z","summary":"List src files"}}
{"$patch":{"id":"7b1f4f6b-2222-4000-8000-000000000003","toolCalls":[{"id":"list_directory-1759309207000","result":null}]}}
{"$rewindTo":"7b1f4f6b-2222-4000-8000-000000000003"}
```
G `logs.json`: `[{"sessionId":"a1b2c3d4-0000-4000-8000-000000000001","messageId":0,"timestamp":"2026-10-01T09:00:05.000Z","type":"user","message":"list files in src"}]`

```json
{"uuid":"0f0e0d0c-3333-4000-8000-000000000010","parentUuid":null,"sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:00.000Z","type":"user","provenance":"real_user","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","promptId":"e5f6a7b8-4444-4000-8000-000000000011########1","message":{"role":"user","parts":[{"text":"run the tests"}]},"systemPayload":{"displayText":"run the tests","hookContext":""}}
{"uuid":"1a1b1c1d-5555-4000-8000-000000000012","parentUuid":"0f0e0d0c-3333-4000-8000-000000000010","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:03.000Z","type":"assistant","provenance":"assistant_output","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","model":"qwen3-coder-plus","message":{"role":"model","parts":[{"text":"Plan: run npm test.","thought":true},{"text":"Running tests."},{"functionCall":{"id":"call_abc123","name":"run_shell_command","args":{"command":"npm test"}}}]},"usageMetadata":{"promptTokenCount":200,"candidatesTokenCount":30,"totalTokenCount":230},"contextWindowSize":131072}
{"uuid":"2b2c2d2e-6666-4000-8000-000000000013","parentUuid":"1a1b1c1d-5555-4000-8000-000000000012","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:09.000Z","type":"tool_result","provenance":"tool_result","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","message":{"role":"user","parts":[{"functionResponse":{"id":"call_abc123","name":"run_shell_command","response":{"output":"12 passing"}}}]},"toolCallResult":{"callId":"call_abc123","status":"success","resultDisplay":"12 passing","errorType":null}}
{"uuid":"3c3d3e3f-7777-4000-8000-000000000014","parentUuid":"2b2c2d2e-6666-4000-8000-000000000013","sessionId":"e5f6a7b8-4444-4000-8000-000000000011","timestamp":"2026-10-01T10:00:10.000Z","type":"system","subtype":"custom_title","provenance":"system","cwd":"/home/alice/proj","version":"0.24.7","gitBranch":"main","systemPayload":{"customTitle":"Run tests","titleSource":"auto"}}
```

**Confidence.** High (read from type definitions and writers): all G/Q record field names, file paths, status values, ISO timestamps, slug registry and `.project_root`, Q sidecar names. Medium: Q `turn_result.startedAt/endedAt` unit (numbers; inferred ms, not confirmed); Q `errorType` serialised value; whether current Gemini ever writes `functionCall` parts into `content` (reader supports it, the examined writer does not). Not determined: G `activityLogger` JSONL schema and whether it is on by default; Q `logs.json` `model_switch` exact serialisation; Q session-registry file location holding `ipcToken`; exact `UserPromptRecordPayload.hookContext` content; `a2a-server` and `sdk` packages' separate storage.
