# Continue transcript schema

Catalog agent: `continue`. Covers the IDE extensions and the `cn` CLI, which
share [`core/util/history.ts`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts) ([`extensions/cli/src/session.ts:12`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/session.ts#L12),[`50-51`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/session.ts#L50-L51)).
Paths cited are relative to the clone.

## 1. Source

continuedev/continue at [`5522c6f44ca0ac3528b37244818fbfa39b5af470`](https://github.com/continuedev/continue/commit/5522c6f44ca0ac3528b37244818fbfa39b5af470),
Apache-2.0 ([`LICENSE`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/LICENSE)). Open source.

## 2. Transcript files

`~/.continue`, overridable by `CONTINUE_GLOBAL_DIR`
([`core/util/paths.ts:27-35`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L27-L35)):

- `sessions/<sessionId>.json`: one session, pretty-printed JSON
  ([`paths.ts:102-103`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L102-L103), [`history.ts:131-134`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L131-L134)).
- `sessions/sessions.json`: JSON array of session metadata
  ([`paths.ts:106-112`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L106-L112), [`history.ts:168-181`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L168-L181)).
- `logs/prompt.log`: human-readable LLM interaction log ([`paths.ts:397-399`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L397-L399)),
  written only by the binary used by JetBrains ([`binary/src/index.ts:35-38`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/binary/src/index.ts#L35-L38)),
  not by the VS Code extension.
- `dev_data/0.2.0/<eventName>.jsonl`: one JSON object per line per event
  ([`paths.ts:240-249`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L240-L249), [`core/data/log.ts:20`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/log.ts#L20),[`73-97`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/log.ts#L73-L97)). Events include
  `chatInteraction`, `chatFeedback`, `toolUsage`, `tokensGenerated`,
  `autocomplete`, `editInteraction`, `quickEdit`
  ([`packages/config-yaml/src/schemas/data/`](https://github.com/continuedev/continue/tree/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data)). Legacy `dev_data/0.1.0/*.jsonl`
  and pre-version `dev_data/*.jsonl` ([`paths.ts:441-460`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L441-L460)).
- `dev_data/devdata.sqlite`, table `tokens_generated` ([`paths.ts:236-238`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L236-L238),
  [`core/data/devdataSqlite.ts:16-20`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/devdataSqlite.ts#L16-L20)).

## 3. Record schema

Session ([`core/index.d.ts`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts)). `Session` [`:279-290`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L279-L290): `sessionId`, `title`,
`workspaceDirectory`, `history: ChatHistoryItem[]`, `mode?:
"chat"|"agent"|"plan"|"background"`, `chatModelTitle?`, `usage?: SessionUsage`
(`promptTokens`, `completionTokens`, `totalCost`, [`:275-277`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L275-L277),[`407-422`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L407-L422)). Key
order is forced ([`history.ts:115-129`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L115-L129)).

`ChatHistoryItem` [`:534-545`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L534-L545): `message: ChatMessage`, `contextItems:
ContextItemWithId[]` (`content, name, description, uri?{type,value},
id{providerTitle,itemId}` [`:459-473`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L459-L473)), `editorState?`, `promptLogs?:
PromptLog[]` (`modelTitle, modelProvider, prompt, completion`, [`:488-493`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L488-L493)),
`toolCallStates?: ToolCallState[]`, `reasoning?: {active, text, startAt:
number (ms epoch), endAt?}` ([`:527-532`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L527-L532); [`gui/src/redux/slices/sessionSlice.ts:561`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/gui/src/redux/slices/sessionSlice.ts#L561)),
`conversationSummary?`, `appliedRules?`.

`ChatMessage` [`:440-445`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L440-L445) by `role` ([`:335-340`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L335-L340)): `user` `{content: string |
{type:"text",text}|{type:"imageUrl",imageUrl:{url}}[]}`; `assistant`
`{content, toolCalls?: [{id?, type?:"function", function?:{name?, arguments?:
string (JSON)}}], usage?}`; `thinking` `{content, signature?,
redactedThinking?, reasoning_details?}`; `system` `{content}`; `tool`
`{content, toolCallId}`. All may carry `metadata?`.

`ToolCallState` [`:516-525`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L516-L525): `toolCallId`, `toolCall: {id, type:"function",
function:{name, arguments}}`, `status: "generating"|"generated"|"calling"|
"errored"|"done"|"canceled"`, `parsedArgs`, `processedArgs?`, `output?:
ContextItem[]` (tool result text in `content`).

No per-message timestamp exists in session files. `sessions.json` entry
(`BaseSessionMetadata` [`:292-298`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/index.d.ts#L292-L298)): `sessionId`, `title`, `dateCreated`
(`String(Date.now())`, millisecond epoch as a string, [`history.ts:171`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L171)),
`workspaceDirectory`, `messageCount?` (assistant messages only, [`:154-156`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L154-L156)).
The CLI drops `system` messages before saving and copies user content into
`editorState` ([`extensions/cli/src/session.ts:211-231`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/session.ts#L211-L231)).

`dev_data/0.2.0/chatInteraction.jsonl` ([`schemas/data/chatInteraction/v0.2.0.ts`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data/chatInteraction/v0.2.0.ts),
[`index.ts:4-19`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data/chatInteraction/index.ts#L4-L19), [`base.ts:3-11`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data/base.ts#L3-L11)): `eventName`, `schema`, `timestamp` (ISO
8601, [`log.ts:50`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/log.ts#L50)), `userId`, `userAgent`, `selectedProfileId`, `prompt`,
`completion`, `modelName`, `modelTitle`, `modelProvider`, `sessionId`,
`tools?`, `rules?`. `toolUsage.jsonl` ([`toolUsage/v0.2.0.ts:13-19`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data/toolUsage/v0.2.0.ts#L13-L19)):
`toolCallId`, `functionName`, `functionParams`, `toolCallArgs`, `accepted`,
`succeeded`, `output`. `chatFeedback` adds `feedback`.

`prompt.log` ([`core/llm/logFormatter.ts:43-75`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/llm/logFormatter.ts#L43-L75)): `HH:MM:SS.s [Chat]` (UTC,
[`:29-41`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/llm/logFormatter.ts#L29-L41)), `Options: {json}`, `Role: user`, text lines prefixed `| `,
relative `+N.N` deltas, `Success`, `PromptTokens: N`; overlapping
interactions get a column prefix character from `" |&%#"` ([`:19`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/llm/logFormatter.ts#L19)). No date,
no session id.

## 4. Joins

`sessions.json[].sessionId` with `sessions/<sessionId>.json`;
`workspaceDirectory` is in both. Tool call with result:
`assistant.toolCalls[].id` = `toolCallStates[].toolCallId` = the next `tool`
message's `toolCallId`. `chatInteraction.sessionId` joins the session file;
`toolUsage.toolCallId` joins `toolCallStates[].toolCallId`. No git branch is
recorded.

## 5. SQLite stores

`dev_data/devdata.sqlite` `tokens_generated(model, provider, tokens_prompt,
tokens_generated, timestamp)` ([`devdataSqlite.ts:16-49`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/devdataSqlite.ts#L16-L49)). Excluded by the
collector as low value.

## 6. Format versions

`sessions.json` entries with `session_id` are an old format and are filtered
([`history.ts:34-36`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L34-L36)); `dev_data` schema `0.1.0` became `0.2.0`; no version
field inside session files.

## 7. Secrets

`promptLogs[].prompt` and `dev_data/*/chatInteraction.jsonl` `prompt` embed
full context, possibly `.env` contents. `dev_data` `userId` is the Continue
hub `userToken` ([`log.ts:64-66`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/data/log.ts#L64-L66)). Session files hold no API keys; the
collector flags `config.yaml`, `config.json` and `index/globalContext.json`.

## 8. Parser plan

Globs: `.continue/sessions/*.json` (skip `sessions.json` itself, but read it
for `dateCreated`), `.continue/dev_data/*/chatInteraction.jsonl`,
`.continue/dev_data/*/toolUsage.jsonl`.

Rows: one per `history[]` item (user, assistant, thinking, tool), plus one
`tool_use` per `toolCalls[]`.

| Column | Source |
| --- | --- |
| timestamp_utc | `sessions.json` `dateCreated` (session level; message rows inherit); `reasoning.startAt` if present |
| session_id | `sessionId` |
| project_path | `workspaceDirectory` |
| git_branch | empty |
| turn_type | by `message.role`; `thinking` → thinking; `tool` → tool_result |
| model | `chatModelTitle` or `promptLogs[].modelTitle` |
| tool_name, tool_use_id | `toolCall.function.name`, `toolCallId` |
| text | text, `function.arguments`, output `content` |

Fixture `sessions/0f1e.json`:

```json
{"sessionId":"0f1e","title":"Fix bug","workspaceDirectory":"/home/u/proj","history":[
 {"message":{"role":"user","content":"rename foo"},"contextItems":[]},
 {"message":{"role":"assistant","content":"","toolCalls":[{"id":"call_1","type":"function","function":{"name":"edit_existing_file","arguments":"{\"filepath\":\"a.py\"}"}}]},"contextItems":[],
  "toolCallStates":[{"toolCallId":"call_1","toolCall":{"id":"call_1","type":"function","function":{"name":"edit_existing_file","arguments":"{\"filepath\":\"a.py\"}"}},"status":"done","parsedArgs":{"filepath":"a.py"},"output":[{"name":"Edit","description":"","content":"ok"}]}]},
 {"message":{"role":"tool","content":"ok","toolCallId":"call_1"},"contextItems":[]}],"chatModelTitle":"GPT-4o"}
```

`sessions.json`: `[{"sessionId":"0f1e","title":"Fix bug","dateCreated":"1759400000000","workspaceDirectory":"/home/u/proj","messageCount":1}]`

`dev_data/0.2.0/chatInteraction.jsonl`: `{"eventName":"chatInteraction","schema":"0.2.0","timestamp":"2026-10-02T10:00:00.000Z","userId":"","userAgent":"vscode/1.1 (Continue/1.0)","selectedProfileId":"local","prompt":"rename foo","completion":"done","modelName":"gpt-4o","modelTitle":"GPT-4o","modelProvider":"openai","sessionId":"0f1e"}`

Confidence. High: session, `sessions.json` and `dev_data` schemas (typed
source). Medium: `prompt.log` format (from a doc comment; only the JetBrains
binary writes it). Not determined: per-message timestamps (absent by
design).
