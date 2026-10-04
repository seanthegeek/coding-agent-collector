# Gemini CLI transcript schema

Catalog agent: `gemini-cli`. Researched together with Qwen Code, which forked
Gemini CLI; see [qwen-code.md](qwen-code.md) for how far the fork has drifted.
Paths cited are relative to the repository clone.

## 1. Source

google-gemini/gemini-cli at [`fb972b2f87fe7d5b06d37eac711490162d98de2c`](https://github.com/google-gemini/gemini-cli/commit/fb972b2f87fe7d5b06d37eac711490162d98de2c)
(2026-10-02), version 0.64.0-nightly.20260929, Apache-2.0. Open source.

## 2. Transcript files

Base directory `~/.gemini` ([`packages/core/src/config/storage.ts:54-60`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L54-L60));
under the macOS `SANDBOX=sandbox-exec` sandbox it is `~/.cache/.gemini`
([storage.ts:97-101](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L97-L101)). The project identifier is now a slug, not a hash:
`~/.gemini/projects.json` maps `{ "projects": { "<abs path>": "<slug>" } }`
([storage.ts:289-299](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L289-L299); [`projectRegistry.ts:16-18`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L16-L18),[`304-316`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L304-L316),[`414-421`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L414-L421); slug is the
lower-cased basename with non-alphanumeric runs replaced by `-`, suffixed
`-1`, `-2` on collision). Each slug directory carries a marker
`~/.gemini/tmp/<slug>/.project_root` whose content is the absolute project
path ([projectRegistry.ts:24](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L24),[372-412](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L372-L412)). Legacy `tmp/<sha256(projectRoot)>`
directories are copied to the slug directory on first run and left in place
([storage.ts:310-324](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L310-L324); [`storageMigration.ts:20-52`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storageMigration.ts#L20-L52); [`utils/paths.ts:318-320`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts#L318-L320)),
so both may exist.

- Session: `~/.gemini/tmp/<slug>/chats/session-<YYYY-MM-DDTHH-MM>-<shortId8>.jsonl`,
  one file per session ([`services/chatRecordingService.ts:757-799`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L757-L799); prefix
  [`chatRecordingTypes.ts:12`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L12)). Collisions insert `-1-`, `-2-` before the
  short id ([795-797](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L795-L797)). Subagent sessions: `chats/<parentSessionId>/<sessionId>.jsonl`
  ([763-791](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L763-L791)).
- Legacy session: same name with `.json`, one JSON object
  (`ConversationRecord`) ([1566-1616](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L1566-L1616)); on resume it is re-emitted into a
  sibling `.jsonl` ([708-735](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L708-L735)).
- Prompt history: `~/.gemini/tmp/<slug>/logs.json`, JSON array of `LogEntry`
  ([`core/logger.ts:15`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L15),[`21-27`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L21-L27),[`148-149`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L148-L149),[`229-233`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L229-L233)).
- `/chat save` checkpoints: `tmp/<slug>/checkpoint-<encodeURIComponent(tag)>.json`
  ([logger.ts:285-295](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L285-L295),[329-343](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L329-L343); [`cli/.../chatCommand.ts:142`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/ui/commands/chatCommand.ts#L142)).
- Tool checkpoints: `tmp/<slug>/checkpoints/<ISO ts with : and . replaced>-<basename>-<tool>.json`
  ([`utils/checkpointUtils.ts:59-66`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/checkpointUtils.ts#L59-L66),[`130-141`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/checkpointUtils.ts#L130-L141); [storage.ts:364-366](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L364-L366)), backed by a
  shadow git repository at `~/.gemini/history/<slug>` ([storage.ts:326-330](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L326-L330);
  [`gitService.ts:74-75`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/gitService.ts#L74-L75)).
- Optional activity log: `tmp/<slug>/logs/session-<sessionId>.jsonl`
  ([`cli/src/utils/activityLogger.ts:693-699`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/utils/activityLogger.ts#L693-L699)). Schema not examined.
- Externalised large tool output: `tmp/<slug>/tool-outputs/`
  ([`utils/fileUtils.ts:799`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/fileUtils.ts#L799),[`814`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/fileUtils.ts#L814)); shell history `tmp/<slug>/shell_history`
  ([storage.ts:480-482](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L480-L482)).

## 3. Record schema

Session JSONL ([`services/chatRecordingTypes.ts`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts)). Line 1 is
`PartialMetadataRecord` ([156-165](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L156-L165)): `sessionId`, `projectHash` (sha256 of the
project path), `startTime`, `lastUpdated` (ISO 8601), `summary?`,
`directories?: string[]`, `kind?: 'main'|'subagent'`. Later lines are one of
(discriminated at [`chatRecordingService.ts:79-95`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L79-L95)):

- `MessageRecord` = `BaseMessageRecord & ConversationRecordExtra` ([44-87](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L44-L87)):
  `id` (UUID), `timestamp` (ISO 8601 via `toISOString`,
  [chatRecordingService.ts:1022](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L1022)), `content: PartListUnion` (string, Part or
  Part[]), `displayContent?`, `type: 'user'|'info'|'error'|'warning'|'gemini'`.
  For `type:'gemini'` also `toolCalls?: ToolCallRecord[]`, `thoughts?:
  {subject, description, timestamp}[]` ([`utils/thoughtUtils.ts:7-10`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/thoughtUtils.ts#L7-L10)),
  `tokens?: {input, output, cached, thoughts?, tool?, total}` ([19-26](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L19-L26)),
  `model?: string`.
- `ToolCallRecord` ([54-67](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L54-L67)): `id`, `name`, `args: object`, `result?:
  PartListUnion|null`, `status` from `CoreToolCallStatus` =
  `validating|scheduled|error|success|executing|cancelled|awaiting_approval`
  ([`scheduler/types.ts:26-34`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/scheduler/types.ts#L26-L34)), `timestamp`, `agentId?`, `displayName?`,
  `description?`, `resultDisplay?` (string or `FileDiff{fileDiff, fileName,
  filePath, originalContent, newContent}`, [`tools/tools.ts:935-966`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/tools/tools.ts#L935-L966)),
  `renderOutputAsMarkdown?`.
- `{ "$set": {...metadata fields..., "memoryScratchpad"?, legacy "messages"?} }`
  ([149-154](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L149-L154)); `{ "$patch": { id?, content?, toolCalls?:[{id,result}], updates?,
  removeIds?, orderIds? } }` ([138-147](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L138-L147)); `{ "$rewindTo": "<message id>" }`
  ([123-125](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L123-L125)) drops that message and everything after it
  ([chatRecordingService.ts:305-335](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L305-L335)).

Current code records model text only as `content` ([geminiChat.ts:1652-1656](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/geminiChat.ts#L1652-L1656))
with tool calls in `toolCalls`; the reader also accepts `functionCall` and
`thought: true` parts inside `content` ("modern session",
[`utils/sessionUtils.ts:138-144`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/sessionUtils.ts#L138-L144)). No cwd and no git branch are stored in the
session file.

`logs.json` `LogEntry`: `sessionId`, `messageId` (per-session counter),
`timestamp` (ISO), `type: 'user'`, `message` ([logger.ts:17-27](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L17-L27)). User prompts
only.

`checkpoint-<tag>.json`: `{ "history": Content[], "authType"?: string }`
([logger.ts:29-32](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L29-L32)). `checkpoints/*.json` `ToolCallData`: `history?`,
`clientHistory?: Content[]`, `commitHash?`, `toolCall: {name, args}`,
`messageId?` (equals `prompt_id`) ([checkpointUtils.ts:15-24](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/checkpointUtils.ts#L15-L24),[130-139](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/checkpointUtils.ts#L130-L139)).

## 4. Joins

Session = file; `sessionId` from line 1, overridden by any later
`$set.sessionId`, which is rewritten on resume ([chatRecordingService.ts:737](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L737)).
A tool call and its result are the same `toolCalls[]` element (`id`,
`result`, `status`); the whole gemini message is re-appended whenever its
tool calls change ([1118-1187](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L1118-L1187), [989-1005](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L989-L1005)), so a parser must keep the last
record per `id` and apply `$patch` and `$rewindTo`. Project path: the
`tmp/<slug>/.project_root` content or a `projects.json` reverse lookup;
legacy hash directories have no reverse map (compare sha256 of known cwds).
`kind` plus directory nesting links a subagent session to its parent.

## 5. SQLite or binary stores

None. `~/.gemini/history/<slug>` is a shadow git repository; treat it as
binary.

## 6. Format versions

Hash directories became slug directories (copied, both remain); single-object
`session-*.json` became `.jsonl`; `$set.messages` full-history checkpoints are
deprecated ([chatRecordingTypes.ts:150-153](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingTypes.ts#L150-L153)); `checkpoint-<tag>` moved from a
raw array to `{history, authType}` ([logger.ts:359-372](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L359-L372)); legacy un-encoded
`checkpoint-<tag>.json` names ([logger.ts:312-313](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L312-L313)). No explicit version field.

## 7. Secrets

`~/.gemini/oauth_creds.json` ([storage.ts:22](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L22),[255-257](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L255-L257)), `mcp-oauth-tokens.json`,
`a2a-oauth-tokens.json` ([70-76](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L70-L76)), `gemini-credentials.json`
([`services/fileKeychain.ts:20`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/fileKeychain.ts#L20)), `google_accounts.json`. Checkpoints
(`clientHistory`) and `toolCalls[].result` embed full tool output.

## 8. Parser plan

Globs (home-relative): `.gemini/tmp/*/chats/**/*.jsonl`,
`.gemini/tmp/*/chats/**/*.json`, `.gemini/tmp/*/logs.json`,
`.gemini/tmp/*/checkpoints/*.json`, `.cache/.gemini/tmp/*/chats/**/*.jsonl`.

Rows: one per user, info, error or warning message; one `assistant` row per
gemini message plus one `thinking` row per `thoughts[]` entry; one `tool_use`
per `toolCalls[]` element and one `tool_result` when `result` is non-null,
sharing the `tool_use_id`; `logs.json` entries as `user` rows when no session
file covers that `sessionId`.

| Column | Source |
| --- | --- |
| timestamp_utc | `timestamp` (ISO); `toolCalls[].timestamp`, `thoughts[].timestamp` |
| session_id | line-1 `sessionId`, overridden by later `$set.sessionId` |
| project_path | `.project_root` or `projects.json`; else `projectHash` |
| git_branch | empty |
| turn_type | user → user; gemini → assistant; info/error/warning → system; toolCalls → tool_use/tool_result; thoughts → thinking |
| model | `model` |
| tool_name, tool_use_id | `toolCalls[].name`, `toolCalls[].id` |
| text | `content` text; for tool_use `displayName` plus args; `summary` on `$set` |

Fixture (one JSON object per line):

```json
{"sessionId":"a1b2c3d4-0000-4000-8000-000000000001","projectHash":"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08","startTime":"2026-10-01T09:00:00.000Z","lastUpdated":"2026-10-01T09:00:00.000Z","kind":"main"}
{"id":"6a0e3e5a-1111-4000-8000-000000000002","timestamp":"2026-10-01T09:00:05.000Z","type":"user","content":[{"text":"list files in src"}]}
{"id":"7b1f4f6b-2222-4000-8000-000000000003","timestamp":"2026-10-01T09:00:07.000Z","type":"gemini","content":"Listing now.","thoughts":[{"subject":"Plan","description":"Use the ls tool.","timestamp":"2026-10-01T09:00:06.500Z"}],"tokens":{"input":120,"output":12,"cached":0,"thoughts":8,"tool":0,"total":140},"model":"gemini-2.5-pro","toolCalls":[{"id":"list_directory-1759309207000","name":"list_directory","args":{"path":"/home/alice/proj/src"},"status":"success","timestamp":"2026-10-01T09:00:07.100Z","result":[{"functionResponse":{"id":"list_directory-1759309207000","name":"list_directory","response":{"output":"main.ts\nutil.ts"}}}],"displayName":"ReadFolder","description":"Lists files"}]}
{"$set":{"lastUpdated":"2026-10-01T09:00:08.000Z","summary":"List src files"}}
{"$patch":{"id":"7b1f4f6b-2222-4000-8000-000000000003","toolCalls":[{"id":"list_directory-1759309207000","result":null}]}}
{"$rewindTo":"7b1f4f6b-2222-4000-8000-000000000003"}
```

`logs.json`: `[{"sessionId":"a1b2c3d4-0000-4000-8000-000000000001","messageId":0,"timestamp":"2026-10-01T09:00:05.000Z","type":"user","message":"list files in src"}]`

Confidence. High (type definitions and writers): record field names, file
paths, status values, ISO timestamps, slug registry and `.project_root`.
Medium: whether current Gemini ever writes `functionCall` parts into
`content` (the reader supports it, the examined writer does not). Not
determined: the `activityLogger` JSONL schema and whether it is on by
default; the `a2a-server` and `sdk` packages' separate storage.
