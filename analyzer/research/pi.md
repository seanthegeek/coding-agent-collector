# pi transcript schema

Catalog agent: `pi`. pi writes one append-only JSONL file per session, a
tree of entries linked by `id`/`parentId`. The same format is written
by little-coder (pi itself, in pi's directory) and by Letta Code's local
backend (its own writer, its own directory); section 8 says how to tell
them apart. Paths are in `collectors/research/pi.md`.

## 1. Source

earendil-works/pi at [`200387122ca450d6387f033949423114a270b96c`](https://github.com/earendil-works/pi/commit/200387122ca450d6387f033949423114a270b96c)
(2026-10-04, coding-agent 1.0.2), MIT, open source. Tag `v0.83.0`
([`845d6ff1f6643aba440341cce877ce1c43ebbc39`](https://github.com/earendil-works/pi/commit/845d6ff1f6643aba440341cce877ce1c43ebbc39)) is cited where the schema differs.
All claims from source.

## 2. Transcript files

- `.pi/agent/sessions/--<encoded cwd>--/<ISO time, : and . as ->_<session id>.jsonl`,
  e.g. `2026-10-01T09-00-00-000Z_0199a1b2-....jsonl`
  ([session-manager.ts:589-594](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L589-L594), [1077-1080](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1077-L1080)).
  One file per session; forks and branches get new files.
- With `--session-dir`, `PI_CODING_AGENT_SESSION_DIR` or the `sessionDir`
  setting the files sit flat in that directory, anywhere on disk.
- Legacy: `.pi/agent/*.jsonl` (v0.30.0 bug, moved on next start).
- Exports in project directories: `session-<time>.jsonl` (same format,
  one branch) and `pi-session-*.html`.
- Experimental durable sessions are SQLite, section 5.

## 3. Record schema

Every line is one JSON object. Malformed lines are skipped by pi
([session-manager.ts:616-624](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L616-L624)).

**Header** (line 1): `type:"session"`, `version` (3; absent in v1),
`id` (session id), `timestamp` (ISO 8601 UTC with ms and `Z`, from
`toISOString`), `cwd`, optional `parentSession` (absolute path of the
session file this one was forked or branched from)
([43-50](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L43-L50), [1061-1069](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1061-L1069)). The session id is a UUIDv7
([264-266](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L264-L266)) unless given with `--session-id`
([main.ts:448](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/main.ts#L448), [session-manager.ts:268-274](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L268-L274)). There
is no producer name or pi version in the header.

**Entries**: `type`, `id` (8 hex characters, [276-284](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L276-L284)),
`parentId` (null at a root), `timestamp` (ISO, written at append time)
([57-62](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L57-L62), [1204-1213](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1204-L1213)). Types
([64-195](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L64-L195)):

| `type` | Fields |
| --- | --- |
| `message` | `message`: one of the roles below |
| `thinking_level_change` | `thinkingLevel` |
| `model_change` | `provider`, `modelId` |
| `usage` | `kind` (e.g. `cache_warm`), `provider`, `model`, `usage`, `note`; HEAD only |
| `compaction` | `summary`, `firstKeptEntryId`, `tokensBefore`, `details`, `usage`, `fromHook`, `systemMessage` (HEAD only) |
| `branch_summary` | `fromId`, `summary`, `details`, `usage`, `fromHook` |
| `custom` | `customType`, `data`: extension state, not in model context |
| `custom_message` | `customType`, `content` (string or text/image parts), `display`, `details`: extension-injected context |
| `context_edit` | `targetId`, `replacement` (`{content}` or null = omitted from context); HEAD only |
| `label` | `targetId`, `label` (undefined clears) |
| `session_info` | `name` (user-set session title) |

**Message roles** (`message.message.role`), every one with `timestamp`
in Unix milliseconds:

- `user`: `content` string or `[{type:"text",text}|{type:"image",data,mimeType}]`
  ([types.ts:542-546](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L542-L546), [397-417](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L397-L417)). Images are inline base64.
- `assistant`: `content[]` of `text` (`text`, `textSignature`),
  `thinking` (`thinking`, `thinkingSignature`, `redacted`), `toolCall`
  (`id`, `name`, `arguments` object, `thoughtSignature`, `namespace`);
  `api`, `provider`, `model`, `responseModel`, `responseId`,
  `thinkingLevel`, `diagnostics`, `usage` (`input`, `output`,
  `cacheRead`, `cacheWrite`, `totalTokens`, `cost{...}`), `stopReason`
  (`pending|stop|length|toolUse|error|aborted|deferred`), `errorMessage`
  ([types.ts:403-452](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L403-L452), [548-572](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L548-L572)).
- `toolResult`: `toolCallId`, `toolName`, `content[]` (text/image),
  `details` (tool-specific, e.g. edit `diff`/`patch`, bash
  `fullOutputPath`), `usage`, `nestedCalls` (calls a codemode script
  made), `isError` ([596-610](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L596-L610); [tools/edit.ts:70-77](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/edit.ts#L70-L77),
  [tools/bash.ts:66-69](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/bash.ts#L66-L69)).
- `system`: `content` (the system prompt on the first one, added
  instructions later), `sections`, `toolsAdded`, `toolsRemoved`
  ([types.ts:524-540](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L524-L540)). Persisted since the system-message
  change ([agent-session.ts:1126-1133](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/agent-session.ts#L1126-L1133)); v0.83.0 persisted only
  user, assistant and toolResult ([0.83.0 agent-session.ts:635-641](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/agent-session.ts#L635-L641)).
- `bashExecution`: a user `!command`: `command`, `output`,
  `exitCode`, `cancelled`, `truncated`, `fullOutputPath`,
  `excludeFromContext` ([messages.ts:29-40](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/messages.ts#L29-L40); [agent-session.ts:3848](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/agent-session.ts#L3848)).
- `custom` (v2 `hookMessage` renamed), `branchSummary`,
  `compactionSummary` ([messages.ts:46-67](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/messages.ts#L46-L67)).

Built-in tool arguments: `bash` `command`, `timeout`
([tools/bash.ts:40-43](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/bash.ts#L40-L43)); `read` `path`, `offset`, `limit`
([read.ts:14-18](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/read.ts#L14-L18)); `write` `path`, `content`
([write.ts:11-14](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/write.ts#L11-L14)); `edit` `path`, `edits[{oldText,newText}]`
([edit.ts:21-37](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/edit.ts#L21-L37)); `grep` `pattern`, `path`, `glob`
([grep.ts:21-24](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/grep.ts#L21-L24)); `find` `pattern`, `path` ([find.ts:26-30](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/find.ts#L26-L30)); `ls`
`path` ([ls.ts:11-12](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/tools/ls.ts#L11-L12)); `codemode` `code`
([extensions/codemode/tool.ts:87-90](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/codemode/tool.ts#L87-L90)).

## 4. Joins

- Session: header `id`, also the file-name suffix. Project: header `cwd`.
- Tool use to result: `toolCall.id` = `toolResult.toolCallId`.
- Tree: `parentId` → `id`; the file holds every branch; the active
  path is the walk up from the last entry. `label` and `context_edit`
  point at `targetId`; `compaction.firstKeptEntryId` marks the cut.
- Fork/branch: child header `parentSession` = parent file path.
  `forkFrom` copies every parent entry verbatim, ids and timestamps
  included ([session-manager.ts:1844-1863](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1844-L1863)); branching copies the path to
  the chosen entry ([1632-1681](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1632-L1681)). The same entry therefore
  appears in several files.
- little-coder checkpoints: `.little-coder/checkpoints/<session file name>/`
  ([checkpoint/index.ts:63-65](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L63-L65)).
- Sub-agents: pi has none built in; little-coder's run with `--no-session`.

## 5. SQLite or binary stores

The main format has none. The experimental server and `vacation` mode
(`PI_EXPERIMENTAL=1`, HEAD only) keep `session.sqlite` in WAL mode
([packages/durable/src/storage/sqlite/node.ts:181-193](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/durable/src/storage/sqlite/node.ts#L181-L193)) with tables
`conversations`, `entries(conversation_id, head, commit_seq, record JSON)`,
`tasks`, `submissions`, `documents`, `document_revisions`
([migrations.ts:10-82](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/durable/src/storage/sqlite/migrations.ts#L10-L82)). Not parsed in this plan;
open through `sqlite_util.py` with sidecars when it is.

## 6. Format versions

Header `version`: 1 (no field, no ids), 2 (`id`/`parentId` added), 3
(`hookMessage` role renamed `custom`)
([session-manager.ts:41](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L41), [286-345](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L286-L345)). pi rewrites old files in
place on open, so a collected v1/v2 file means nobody resumed it. Within v3
fields were added without a bump: `usage` and `context_edit` entries,
`system` role, `compaction.systemMessage`, `stopReason:"deferred"`
(absent at v0.83.0, [0.83.0 types.ts:391](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L391)). A parser must ignore
unknown types and fields.

## 7. Secrets

Tool arguments and outputs are stored verbatim (`cat .env`, `write`
contents, bash output). `system` messages carry the full system prompt,
including AGENTS.md and skill text. `thinkingSignature`,
`thoughtSignature`, `textSignature` are opaque provider blobs (redacted
thinking is encrypted there). Credentials are in `auth.json` and
`mcp-auth.json`, not in sessions.

## 8. Parser plan

Glob `.pi/agent/sessions/*/*.jsonl` and `.pi/agent/*.jsonl`; read line 1 as
the header and skip files whose first record is not `type:"session"`.
For files elsewhere (custom session dir) detect by that header shape.

| Column | Source |
| --- | --- |
| timestamp_utc | entry `timestamp`; fall back to `message.timestamp` (ms) |
| session_id | header `id` |
| project_path | header `cwd` |
| git_branch | empty (not recorded) |
| turn_type | `user`; `assistant` text parts; `toolCall` → tool_use; `toolResult` → tool_result; `thinking` → thinking; `bashExecution` → tool_use + tool_result; `system` role, `custom` role, `custom_message`, `model_change`, `thinking_level_change`, `compaction`, `branch_summary`, `context_edit`, `session_info` → system; skip `custom` entries, `label`, `usage` |
| model | assistant `model`; `model_change.modelId` |
| tool_name | `toolCall.name`, `toolResult.toolName`; `bash` for `bashExecution` |
| tool_use_id | `toolCall.id` / `toolResult.toolCallId`; entry `id` for `bashExecution` |
| text | text parts joined; tool_use: `command`, `path`, `pattern` or `code`, else JSON; tool_result: text parts; compaction/branch: `summary` |

When a file's `parentSession` parent is also in the collection, drop
child entries whose `id` and `timestamp` match a parent entry, so a fork
does not double the timeline.

**Wrapper attribution.** The header names no producer, so attribution
rests on what the wrapper leaves:

- *little-coder* writes into pi's own directory. Label a session
  `little-coder` when a `custom_message` has `customType` starting
  `lc-` ([_shared/inject.ts:49-64](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/_shared/inject.ts#L49-L64); full list in
  [little-coder.md](little-coder.md)), when an assistant `provider` is
  `llamacpp` ([llama-cpp-provider/index.ts:172](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/llama-cpp-provider/index.ts#L172); pi's own built-in is
  `llama.cpp`, [llama/provider.ts:22](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/llama/provider.ts#L22)), or when
  `.little-coder/checkpoints/<this file name>/` exists in the same home.
- *Letta Code* writes the format under `.letta/lc-local-backend/conversations/*/messages.jsonl`,
  so the path already gives `letta`; inside, `message.id` starts
  `letta-msg-` and `message.metadata.agent_id` is set, fields pi never
  writes ([local-store.ts:135-137](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-store.ts#L135-L137), [local-message.ts:26-46](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-message.ts#L26-L46);
  `manifest.json` `message_format:"pi-session-entry-jsonl"`,
  [local-transcript.ts:24-46](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L24-L46)). Share the pi parser, keep the agent from
  the catalog.
- Otherwise `pi`. An SDK embedder or rebranded build is not
  distinguishable from the file alone.

Fixture `.pi/agent/sessions/--home-alice-proj--/2026-10-01T09-00-00-000Z_0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a1b.jsonl`:

```json
{"type":"session","version":3,"id":"0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a1b","timestamp":"2026-10-01T09:00:00.000Z","cwd":"/home/alice/proj"}
{"type":"model_change","id":"1a2b3c4d","parentId":null,"timestamp":"2026-10-01T09:00:00.100Z","provider":"anthropic","modelId":"claude-sonnet-4-5"}
{"type":"message","id":"2b3c4d5e","parentId":"1a2b3c4d","timestamp":"2026-10-01T09:00:01.000Z","message":{"role":"user","content":"fix the failing test","timestamp":1759309201000}}
{"type":"message","id":"3c4d5e6f","parentId":"2b3c4d5e","timestamp":"2026-10-01T09:00:04.000Z","message":{"role":"assistant","content":[{"type":"thinking","thinking":"run the tests first"},{"type":"toolCall","id":"toolu_01","name":"bash","arguments":{"command":"npm test"}}],"api":"anthropic-messages","provider":"anthropic","model":"claude-sonnet-4-5","usage":{"input":900,"output":40,"cacheRead":0,"cacheWrite":0,"totalTokens":940,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"toolUse","timestamp":1759309204000}}
{"type":"message","id":"4d5e6f70","parentId":"3c4d5e6f","timestamp":"2026-10-01T09:00:07.000Z","message":{"role":"toolResult","toolCallId":"toolu_01","toolName":"bash","content":[{"type":"text","text":"1 failing"}],"isError":false,"timestamp":1759309207000}}
{"type":"message","id":"5e6f7081","parentId":"4d5e6f70","timestamp":"2026-10-01T09:00:09.000Z","message":{"role":"bashExecution","command":"git status","output":"M src/a.ts","exitCode":0,"cancelled":false,"truncated":false,"timestamp":1759309209000}}
{"type":"session_info","id":"6f708192","parentId":"5e6f7081","timestamp":"2026-10-01T09:00:10.000Z","name":"test fix"}
this line is cut mid-wri
```

The last line exercises the bad-line `system` row.

Confidence. High: file naming, header, entry types, roles, field names and
timestamp units (source). Medium: `system`-role persistence on versions
between 0.83.0 and HEAD (taken from the ai changelog's 0.86.0 note, not
bisected); that `lc-` markers appear in every little-coder session (see
little-coder.md). Not determined: the durable SQLite `record` JSON shape.
