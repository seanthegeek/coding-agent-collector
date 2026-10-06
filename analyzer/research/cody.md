# Sourcegraph Cody transcript schema

Catalog agent: `cody`. Cody keeps all chats of all accounts in one JSON
object, `AccountKeyedChatHistory`, stored under the key
`cody-local-chatHistory-v2`. In VS Code that object sits inside the
`sourcegraph.cody-ai` row of `User/globalStorage/state.vscdb`; in the
JetBrains plugin and CLI it is a file of the same name. Source is the
frozen public snapshot, so later releases may differ. Paths are in
[`collectors/research/cody.md`](../../collectors/research/cody.md).

## 1. Source

sourcegraph/cody-public-snapshot at
[`8e20ac6c1460c08b0db581c0204658112a246eda`](https://github.com/sourcegraph/cody-public-snapshot/commit/8e20ac6c1460c08b0db581c0204658112a246eda)
(2025-08-01), archived copy of the now-private Cody repository
([`README.md:1-5`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/README.md#L1-L5)).

## 2. Transcript files

- VS Code (and forks): `<User>/globalStorage/state.vscdb`, table
  `ItemTable`, row `key = 'sourcegraph.cody-ai'`; `value` is the
  extension's whole global state as JSON
  ([PearAI VS Code fork `extensionStorage.ts:170-175`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/extensionManagement/common/extensionStorage.ts#L170-L175)),
  and `value["cody-local-chatHistory-v2"]` is the history
  ([`vscode/src/services/LocalStorageProvider.ts:29`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L29),
  [`190-212`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L190-L212)).
  Collected today under `vscode`.
- JetBrains: `<Cody-nodejs data>/JetBrains-globalState/cody-local-chatHistory-v2`,
  a file whose whole content is the JSON-encoded history
  ([`agent/src/global-state/AgentGlobalState.ts:115-121`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/global-state/AgentGlobalState.ts#L115-L121),
  [`134-140`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/global-state/AgentGlobalState.ts#L134-L140)).
  Home-relative globs: `.local/share/Cody-nodejs/JetBrains-globalState/cody-local-chatHistory-v2`,
  `Library/Application Support/Cody-nodejs/JetBrains-globalState/...`,
  `AppData/Local/Cody-nodejs/Data/JetBrains-globalState/...`.
- The whole history is rewritten on every save
  ([`vscode/src/chat/chat-view/ChatHistoryManager.ts:94-108`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/chat/chat-view/ChatHistoryManager.ts#L94-L108)).

## 3. Record schema

`AccountKeyedChatHistory` = `{ "<endpoint>-<username>": { "chat": { "<chatID>": SerializedChatTranscript } } }`
([`lib/shared/src/chat/transcript/messages.ts:193-204`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/chat/transcript/messages.ts#L193-L204);
key built at [`LocalStorageProvider.ts:393-397`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L393-L397)).
The endpoint is a URL such as `https://sourcegraph.com/`, so split the key
on the last `-` only with care: usernames may contain hyphens, endpoints
rarely end in one.

`SerializedChatTranscript`
([`lib/shared/src/chat/transcript/index.ts:7-24`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/chat/transcript/index.ts#L7-L24)):
`id`, `chatTitle?`, `lastInteractionTimestamp`, `interactions[]` of
`{humanMessage, assistantMessage|null}`. `id` and
`lastInteractionTimestamp` are both the chat's **creation** time as
`Date.toUTCString()`, e.g. `"Fri, 03 Oct 2026 10:00:00 GMT"` (UTC, second
resolution), despite the name
([`vscode/src/chat/chat-view/ChatBuilder.ts:97`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/chat/chat-view/ChatBuilder.ts#L97),
[`337-341`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/chat/chat-view/ChatBuilder.ts#L337-L341)).
Chats whose human message errored are not saved
([`ChatBuilder.ts:325-331`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/chat/chat-view/ChatBuilder.ts#L325-L331)).

`SerializedChatMessage`
([`messages.ts:156-171`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/chat/transcript/messages.ts#L156-L171);
serialiser [`index.ts:26-42`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/chat/transcript/index.ts#L26-L42)):
`speaker` (`human`, `assistant`, `system`), `text`, `model`,
`intent` (`search`, `chat`, `edit`, `insert`, `agentic`),
`manuallySelectedIntent`, `contextFiles` (context items with `type`,
`uri`, `content`, ...), `editorState`, `error` (`ChatError`:
`name`, `message`, rate-limit fields), `search` (`query`, `response`),
`agent`, `processes`, `subMessages`, `content`.

Agentic tool use appears two ways:

- `processes[]` (`ProcessingStep`,
  [`messages.ts:92-140`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/chat/transcript/messages.ts#L92-L140)):
  `type` (`tool`, `confirmation`, `step`), `id`, `title`,
  `description`, `content`, `state` (`pending`/`success`/`error`),
  `items`.
- `content[]` (`MessagePart`,
  [`lib/shared/src/sourcegraph-api/completions/types.ts:63-97`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/sourcegraph-api/completions/types.ts#L63-L97)):
  `{type:"text",text}`, `{type:"context_file",uri,content?}`,
  `{type:"tool_call",tool_call:{id,name,arguments}}` (assistant),
  `{type:"tool_result",tool_result:{id,content}}` (human).

No per-message timestamp. `model` is on the assistant message.

## 4. Joins

- Account: the outer key; it names the server and the user that owned
  the chat, which is attribution evidence in its own right.
- Session to project: none recorded; infer from `contextFiles[].uri`
  paths.
- Tool call to result: `tool_call.id` = `tool_result.id`.
- No subagents.

## 5. SQLite or binary stores

VS Code: read `ItemTable` from `state.vscdb` through
`doubleagent/sqlite_util.py` (WAL sidecars). The value is UTF-8 JSON
text in a BLOB column. History over 50 MB triggers a size warning
([`LocalStorageProvider.ts:40`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L40);
[`ChatHistoryManager.ts:104`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/chat/chat-view/ChatHistoryManager.ts#L104)),
so expect large values.

## 6. Format versions

The key suffix `-v2` is the version
([`LocalStorageProvider.ts:28-29`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L28-L29)).
JetBrains histories imported from the pre-agent plugin had UUID chat ids;
the agent migration rewrites them to `toUTCString()` ids and records
`migrated-chat-history-cody-3538`
([`agent/src/global-state/migrations/chat-id-migration-CODY3538.ts:7-41`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/global-state/migrations/chat-id-migration-CODY3538.ts#L7-L41)).
Older VS Code keys (`cody-local-chatHistory` without `-v2`) were not
traced.

## 7. Secrets

The access token is not in the history; it is in SecretStorage. Do not
treat `SOURCEGRAPH_CODY_ENDPOINT` as a secret: it is a URL, and the
extension refuses to save a token there
([`LocalStorageProvider.ts:92-100`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L92-L100)).
`contextFiles[].content` and `tool_result.content` carry file and command
output.

## 8. Parser plan

Inputs: the `sourcegraph.cody-ai` row of any collected `state.vscdb`
(attribute it to `cody` even though the file is under `vscode`), and
`*/Cody-nodejs/**/JetBrains-globalState/cody-local-chatHistory-v2`.

| Column | Source |
| --- | --- |
| timestamp_utc | chat `id` parsed as RFC 1123 date, for every row of the chat |
| session_id | chat `id` (prefix with the account key if ids collide across accounts) |
| project_path | empty, or the common parent of `contextFiles[].uri.fsPath` |
| git_branch | empty |
| turn_type | `human` → user; `assistant` → assistant; `system` → system; `tool_call` part → tool_use; `tool_result` part → tool_result; `processes[]` with `type:"tool"` → tool_use |
| model | `assistantMessage.model` |
| tool_name | `tool_call.name` or process `title` |
| tool_use_id | `tool_call.id` / `tool_result.id` / process `id` |
| text | `text`; for tool_use the `arguments`; for tool_result its `content` |
| source_line | 1 (single JSON value) |

Fixture (`JetBrains-globalState/cody-local-chatHistory-v2`):

```json
{"https://sourcegraph.com/-alice":{"chat":{"Fri, 03 Oct 2026 10:00:00 GMT":{"id":"Fri, 03 Oct 2026 10:00:00 GMT","chatTitle":"Fix flaky test","lastInteractionTimestamp":"Fri, 03 Oct 2026 10:00:00 GMT","interactions":[{"humanMessage":{"speaker":"human","text":"why is test_login flaky?","intent":"chat","contextFiles":[{"type":"file","uri":{"$mid":1,"fsPath":"/home/alice/proj/tests/test_login.py","path":"/home/alice/proj/tests/test_login.py","scheme":"file"},"source":"user"}]},"assistantMessage":{"speaker":"assistant","model":"anthropic::2024-10-22::claude-sonnet-4-latest","text":"It depends on wall-clock time.","intent":"chat"}}]}}}}
```

Agentic variant of an interaction:

```json
{"humanMessage":{"speaker":"human","text":"run the tests","intent":"agentic"},"assistantMessage":{"speaker":"assistant","model":"anthropic::2024-10-22::claude-sonnet-4-latest","text":"Running tests.","content":[{"type":"text","text":"Running tests."},{"type":"tool_call","tool_call":{"id":"toolu_01","name":"run_terminal_command","arguments":"{\"command\":\"pytest -q\"}"}}],"processes":[{"type":"tool","id":"toolu_01","title":"run_terminal_command","content":"pytest -q","state":"success"}]}}
```

Confidence. High (frozen source): key names, transcript and message
fields, `toUTCString` ids, tool part shapes, the JetBrains file location.
Medium: the serialised form of `uri` (a VS Code URI's JSON form; field set
not traced), the tool name `run_terminal_command` and the model string in
the fixture, and how tool results are threaded into the next
`humanMessage.content` in agentic chats. Not determined: anything after
August 2025.
