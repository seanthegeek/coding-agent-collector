# Twinny transcript schema

Catalog agent: `twinny`. A VS Code extension; its chats live inside the
editor's own SQLite state database, not in a file of its own. Paths are in
[`collectors/research/twinny.md`](../../collectors/research/twinny.md).

## 1. Source

twinnydotdev/twinny at [`9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6`](https://github.com/twinnydotdev/twinny/commit/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6),
MIT, open source. VS Code storage behaviour from microsoft/vscode at the
commit cited in [vscode.md](vscode.md).

## 2. Transcript stores

- `<editor User dir>/globalStorage/state.vscdb`, `ItemTable` row whose `key`
  is `rjmacarthy.twinny`. Its `value` is one JSON object holding every
  `globalState` key of the extension
  ([extHostMemento.ts:118](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/api/common/extHostMemento.ts#L118);
  [extensionStorage.ts:159-176](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/extensionManagement/common/extensionStorage.ts#L159-L176)).
  Inside it, `twinny.conversations` is an object of conversations keyed by
  id, and `twinny.active-conversation` a copy of the open one
  ([src/common/constants/storage.ts:1](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/constants/storage.ts#L1), [6](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/constants/storage.ts#L6);
  [src/extension/chat/conversation-history.ts:80-104](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/conversation-history.ts#L80-L104)).
  Home-relative globs: `.config/*/User/globalStorage/state.vscdb`,
  `Library/Application Support/*/User/globalStorage/state.vscdb`,
  `AppData/Roaming/*/User/globalStorage/state.vscdb`,
  `.*-server*/data/User/globalStorage/state.vscdb`, all collected as agent
  `vscode`.
- Optional `twinny-server` recordings (`~/.twinny/server/recordings/`), off by
  default, cover requests from every team member; see section 5.

One row holds all conversations; deleting a conversation removes it from the
object ([conversation-history.ts:150-156](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/conversation-history.ts#L150-L156)), and
"clear all" writes `{}` ([:167-170](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/conversation-history.ts#L167-L170)).

## 3. Record schema

`Conversation` ([src/common/types.ts:127-135](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L127-L135)): `id` (uuid v4,
[src/webview/chat.tsx:494](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/webview/chat.tsx#L494)), `title`, `messages[]`, `pinnedTitle?`,
`updatedAt?` (Unix ms, set on every save,
[conversation-history.ts:97](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/conversation-history.ts#L97)).

`messages[]` are `ChatCompletionMessage`: the OpenAI-style
`ChatCompletionMessageParam` from `fluency.js` (`role`, `content`) plus
Twinny fields ([types.ts:50-76](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L50-L76)):

- `role`: `user` or `assistant` ([src/common/constants/misc.ts:8-11](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/constants/misc.ts#L8-L11);
  user turns [chat.tsx:496-503](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/webview/chat.tsx#L496-L503), replies
  [src/extension/chat/generation.ts:151-157](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/generation.ts#L151-L157)). The system prompt sits
  only in the extension's in-memory turn list ([src/extension/chat/index.ts:192-195](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/extension/chat/index.ts#L192-L195));
  saves come from the webview's message list
  ([src/webview/hooks/useConversationHistory.ts:44](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/webview/hooks/useConversationHistory.ts#L44)).
- `content`: string. Reasoning models' output stays inline as
  `<think>...</think>` or `<thinking>...</thinking>`; the UI splits it
  ([src/webview/utils.ts:116-121](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/webview/utils.ts#L116-L121)).
- `id?`, `images?`, `prompt?` (what was actually sent when the UI shows a
  shorter text), `context?` (workspace search hits used),
  `toolNotes?` (tool inputs and outputs carried to the next turn).
- `meta?` `ReplyMeta` ([types.ts:104-125](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L104-L125)): `model`, `provider`,
  `durationMs`, `completionTokens`, `promptTokens`, `contextWindow`,
  `stopped`, `withheld[]` (counts of credentials the secret shield masked).
- `toolSteps?[]` `ToolStepView` ([types.ts:79-101](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L79-L101)): `id`, `name`,
  `summary`, `args` (string map), `output`, `status`
  (`running|waiting|done|failed|skipped|stopped`), `command`, `approval`.

There is no per-message timestamp; only the conversation's `updatedAt`.

## 4. Joins

Conversation `id` is the session. Tool steps are embedded in the assistant
message that used them, so there is no call/result join. No project path is
stored with a conversation; Twinny's per-workspace state is in
`workspaceStorage/<id>/state.vscdb` under the same key (`contextItems`,
`chatMessage`, [storage.ts:35-47](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/constants/storage.ts#L35-L47)), and `workspace.json` beside it
names the folder. The conversation list itself is global.

## 5. SQLite and other stores

`state.vscdb` is VS Code's SQLite `ItemTable(key, value)`; open through
`sqlite_util` so `-wal` is applied. The value is UTF-8 JSON text. VS Code
warns above 512 KB per extension ([extensionStorage.ts:47](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/extensionManagement/common/extensionStorage.ts#L47), [163-165](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/extensionManagement/common/extensionStorage.ts#L163-L165)),
so long histories are common in that one row.

`twinny-server` recordings, when enabled: SQLite `recordings.sqlite` (WAL)
with `recordings(id, ts, at, key, route, alias, model, provider, outcome,
ended, ms, prompt_tokens, completion_tokens, request, response, preview,
thread)`, or JSONL day files with the same `RecordingRecord` fields
([src/gateway/recording/store.ts:25-50](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/gateway/recording/store.ts#L25-L50), [336-355](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/gateway/recording/store.ts#L336-L355), [369-370](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/gateway/recording/store.ts#L369-L370), [207-211](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/gateway/recording/store.ts#L207-L211)).
`id` is `<ms, zero-padded to 14>-<hex>` ([:99-100](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/gateway/recording/store.ts#L99-L100)); `key` is
the client key's name, which attributes the request to a team member.

## 6. Format versions

No version field on conversations. `updatedAt` is absent on conversations
from older builds ([types.ts:133-134](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L133-L134)); `contextItems` was previously
`contextFiles` ([storage.ts:38](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/constants/storage.ts#L38)).

## 7. Secrets in the store

The same `rjmacarthy.twinny` JSON holds `twinny.inference-providers` and the
`twinny.active-*-provider` objects, each with `apiKey`
([types.ts:255-272](https://github.com/twinnydotdev/twinny/blob/9339bd108e60781ec4d693fbec3f0bc7a0d7d3e6/src/common/types.ts#L255-L272)). Redact `apiKey` wherever it appears in the
value. Gateway tokens and P2P seeds are separate encrypted `secret://` rows.

## 8. Parser plan

Select `state.vscdb` (and `-wal`) under any `User/globalStorage/`, read the
row `key = 'rjmacarthy.twinny'`, parse JSON, iterate
`twinny.conversations`. Attribute rows to `twinny`, not `vscode`.

| Column | Source |
| --- | --- |
| timestamp_utc | `updatedAt` (ms) on the last message of the conversation only; empty for the rest |
| session_id | conversation `id` |
| project_path | empty |
| git_branch | empty |
| turn_type | `role`; `<think>` block → thinking; each `toolSteps[]` → tool_use plus tool_result |
| model | `meta.model` (assistant) |
| tool_name, tool_use_id | `toolSteps[].name`, `toolSteps[].id` |
| text | `content` with think block removed; tool_use: `command` or `args` JSON; tool_result: `output` |
| source_line | empty (one SQLite row) |

Fixture, the `value` of the `rjmacarthy.twinny` row:

```json
{"twinny.conversations":{"7d1c2b3a-1111-4000-8000-000000000001":{"id":"7d1c2b3a-1111-4000-8000-000000000001","title":"List the tests","updatedAt":1759999205000,"messages":[{"role":"user","content":"which tests fail?"},{"role":"assistant","content":"<think>run the suite</think>Two tests fail.","meta":{"model":"qwen2.5-coder:7b","provider":"Ollama","durationMs":5200},"toolSteps":[{"id":"step-1","name":"run_command","summary":"ran `npm test`","args":{"command":"npm test"},"output":"2 failing","status":"done"}]}]}},"twinny.active-conversation":{"id":"7d1c2b3a-1111-4000-8000-000000000001"},"twinny.inference-providers":{"p1":{"id":"p1","label":"Ollama","provider":"ollama","type":"chat","modelName":"qwen2.5-coder:7b","apiHostname":"localhost","apiPort":11434,"apiKey":"REDACTME"}}}
```

Confidence. High: row key, globalState key names, Conversation and message
fields, roles, `updatedAt` unit (all source). Medium: `content` is always a
string in saved chats (the `fluency.js` type also allows part arrays; Twinny
writes strings at the cited sites). Not determined: how `toolSteps[].args`
names the command for each tool; whether other editors running the
extension (VSCodium, Cursor) store it identically (they share the VS Code
storage code, so likely).
