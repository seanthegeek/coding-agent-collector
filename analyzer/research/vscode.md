# VS Code chat session schema (Copilot Chat)

Catalog agent: `vscode`. VS Code's built-in chat store is used by GitHub
Copilot Chat and by any other chat participant, so parsing it covers Copilot
Chat without touching the closed-source extension. The same layout exists in
VSCodium, Cursor, Windsurf and the other forks whose `User` directories the
catalog collects. Paths cited are relative to the microsoft/vscode clone.

## 1. Source

microsoft/vscode at [`d7622a529314a4abcefd7ca9e3d7344bc9ccba9e`](https://github.com/microsoft/vscode/commit/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e), MIT
([`LICENSE.txt`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/LICENSE.txt)). Open source. The Copilot Chat extension itself is closed;
the `modelId`, `agent.id` and `responderUsername` string values in the
fixture are therefore invented.

## 2. Transcript files

[`common/model/chatSessionStore.ts`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts), under the user data directory
(`~/.config/Code/`, `Library/Application Support/Code/`,
`AppData/Roaming/Code/`, likewise for Insiders and VSCodium):

- Workspace: `User/workspaceStorage/<hash>/chatSessions/<sessionId>.jsonl`
  (1.109 and later, an append log) or `<sessionId>.json` (before 1.109, flat
  JSON) ([`:72-73`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L72-L73), [`:731-741`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L731-L741)). Log mode is the default
  (`getValue('chat.useLogSessionStorage') !== false`, registered nowhere
  else).
- Empty window: `User/globalStorage/emptyWindowChatSessions/<sessionId>.jsonl|json`
  ([`:72`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L72)); older `User/workspaceStorage/no-workspace/chatSessions/*.json`
  ([`:75-76`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L75-L76), [`:714-729`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L714-L729)).
- Transferred: `User/globalStorage/transferredChatSessions/<sessionId>.json`
  ([`:78`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L78), [`:745-750`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L745-L750)).

One file is one chat session.

## 3. Record schema

[`common/model/chatModel.ts`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts). Top level `ISerializableChatData3`
[`:2196-2227`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L2196-L2227): `version: 3`, `sessionId`, `creationDate` (ms epoch),
`initialLocation`, `requests: ISerializableChatRequestData[]`,
`responderUsername`, `customTitle?`, `hasPendingEdits?`, `inputState?`,
`repoData?`, `pendingRequests?`, `workingDirectory?` (URI string). Written in
that order by `storageSchema` ([`chatSessionOperationLog.ts:203-216`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionOperationLog.ts#L203-L216)).

`ISerializableChatRequestData` [`:2037-2094`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L2037-L2094), one user turn plus response:
`requestId`, `timestamp?` (ms, request start), `message: string | {text,
parts[]}` ([`requestParser/chatParserTypes.ts:20-23`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/requestParser/chatParserTypes.ts#L20-L23)), `variableData:
{variables: [{id, name, fullName?, value, range?}]}`
([`attachments/chatVariableEntries.ts:63-75`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/attachments/chatVariableEntries.ts#L63-L75)), `agent?: {id, name, fullName?,
extensionId, ...}` ([`participants/chatAgents.ts:63-71`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/participants/chatAgents.ts#L63-L71)), `modelId?`
(user-selected model id, [`chatServiceImpl.ts:1291`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatServiceImpl.ts#L1291)), `modeInfo?: {kind,
telemetryModeId: 'ask'|'agent'|'edit'|'custom'|...}` ([`chatModel.ts:394-401`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L394-L401)),
`response: SerializedChatResponsePart[]`, `responseId?`,
`responseTimestamp?` (ms), `result?: {errorDetails?, timings?, metadata?}`,
`modelState?`, `vote?`, `followups?`, `usedContext?`, `contentReferences?`,
`codeCitations?`, `promptTokens?`, `completionTokens?`, `latestModelCall?`,
`elapsedMs?`, `editedFileEvents?: [{uri, eventKind}]`, `isSystemInitiated?`,
`requestSource?`, `terminalExecutionId?`, `confirmation?`, deprecated
`isHidden?`, `isCanceled?`.

Response parts ([`:2064`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L2064)): a bare `IMarkdownString` `{value, isTrusted?, ...}`
for assistant text ([`chatSessionOperationLog.ts:45`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionOperationLog.ts#L45)); objects keyed by
`kind`: `"thinking"` `{value?: string|string[], id?, reasoningDurationMs?}`
([`chatService.ts:635-644`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatService.ts#L635-L644)); `"toolInvocationSerialized"` `{toolCallId,
toolId, invocationMessage, pastTenseMessage?, isComplete, isConfirmed,
resultDetails?` (URI[] or `{input: string, output: [...], isError?}`,
[`tools/languageModelToolsService.ts:283-290`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/tools/languageModelToolsService.ts#L283-L290)), `resultError?`,
`toolSpecificData?` (`{kind:'terminal', commandLine:{original,
userEdited?}, cwd?}` [`chatService.ts:686-700`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatService.ts#L686-L700); `{kind:'input', rawInput}`
[`:847-850`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatService.ts#L847-L850)), `subAgentInvocationId?}` ([`chatService.ts:1196-1215`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatService.ts#L1196-L1215)); plus
`textEditGroup`, `codeblockUri`, `progressMessage`, `confirmation`,
`undoStop`, `inlineReference` and others ([`chatSessionOperationLog.ts:62-95`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionOperationLog.ts#L62-L95)).
Tool call and result are the same object: the call is `toolCallId`, `toolId`
and `toolSpecificData`, the result is `resultDetails`, `resultError` and
`isComplete`. No git branch field; `repoData` is unspecified here.

JSONL framing ([`common/model/objectMutationLog.ts:196-215`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/objectMutationLog.ts#L196-L215), read
[`:340-385`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/objectMutationLog.ts#L340-L385)): each line is `{"kind":0,"v":<full session>}` (Initial),
`{"kind":1,"k":[path...],"v":...}` (Set), `{"kind":2,"k":[...],"v":[items],
"i"?:index}` (Push; `i` truncates from that index) or `{"kind":3,"k":[...]}`
(Delete). Replay in order to rebuild the object; `k` is a path of keys and
array indexes, for example `["requests",3,"response"]`.

## 4. Joins

`workspaceStorage/<hash>/workspace.json` is `{"folder": "<file URI>"}` or
`{"workspace": "<.code-workspace URI>"}`
([`platform/storage/electron-main/storageMain.ts:416`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/storage/electron-main/storageMain.ts#L416),[`472-474`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/storage/electron-main/storageMain.ts#L472-L474)); the agents
window also records `workingDirectory` in the session. Tool call and result
share one object; `toolCallId` is the join key to extension telemetry.
`agent.id` and `responderUsername` identify the participant (Copilot).

## 5. SQLite stores

`state.vscdb` (`ItemTable(key, value)`, [`base/parts/storage/node/storage.ts:73`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/base/parts/storage/node/storage.ts#L73))
in `workspaceStorage/<hash>/` and `globalStorage/`
([`storageMain.ts:285`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/storage/electron-main/storageMain.ts#L285),[`353`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/storage/electron-main/storageMain.ts#L353),[`415`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/platform/storage/electron-main/storageMain.ts#L415)). Keys: `interactive.sessions` is the legacy
JSON blob of all sessions from before the file store
([`chatServiceImpl.ts:67`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatServiceImpl.ts#L67),[`341`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatServiceImpl.ts#L341), migrated by [`chatSessionStore.ts:611-633`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L611-L633));
`chat.ChatSessionStore.index` is `{version:1, entries:{<sessionId>:{sessionId,
title, lastMessageDate (ms), timing:{created, lastRequestStarted,
lastRequestEnded}, workingDirectory?, isEmpty?, isExternal?, ...}}}`
([`:39`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L39),[`780-836`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L780-L836)); `ChatSessionStore.transferIndex` ([`:40`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L40)).

## 6. Format versions

`version` absent means v1, `2` adds `computedTitle`, `3` adds `customTitle`;
`normalizeSerializableChatData` ([`chatModel.ts:2422-2461`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L2422-L2461)) fills a missing
`sessionId` or `creationDate` (defaulting to one year ago). `message` may be
a plain string in old data ([`:2069`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatModel.ts#L2069)); `response` may be a string or string[]
([`chatSessionStore.ts:688-699`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L688-L699)). Storage moved from `state.vscdb` to `.json`
to `.jsonl` (1.109 and later); flat `.json` is still read as a fallback
([`:653-675`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/model/chatSessionStore.ts#L653-L675)). `isConfirmed` was boolean before 1.104; `source` was undefined
before 1.104 ([`chatService.ts:1204-1209`](https://github.com/microsoft/vscode/blob/d7622a529314a4abcefd7ca9e3d7344bc9ccba9e/src/vs/workbench/contrib/chat/common/chatService/chatService.ts#L1204-L1209)).

## 7. Secrets

`variableData.variables[].value` and `usedContext` may hold attached file
contents; `toolSpecificData.rawInput` and `commandLine` may hold command-line
secrets. `state.vscdb` stores extension auth material under other keys (out
of scope here; see the Cursor and Windsurf notes in the collectors README).

## 8. Parser plan

Globs: `**/User/workspaceStorage/*/chatSessions/*.{json,jsonl}`,
`**/User/globalStorage/emptyWindowChatSessions/*.{json,jsonl}`,
`**/User/workspaceStorage/no-workspace/chatSessions/*.json`,
`**/User/globalStorage/transferredChatSessions/*.json`, plus the sibling
`workspace.json`.

Rows: one `user` per request, one `assistant` per contiguous markdown run,
one `thinking` per thinking part, one `tool_use` plus `tool_result` per
`toolInvocationSerialized`.

| Column | Source |
| --- | --- |
| timestamp_utc | `timestamp` for the user row, `responseTimestamp` for response parts (ms) |
| session_id | `sessionId` |
| project_path | `workspace.json` `folder` (file URI to path) or `workingDirectory` |
| git_branch | empty |
| model | `modelId` |
| tool_name, tool_use_id | `toolId`, `toolCallId` |
| text | text, `invocationMessage` or `commandLine.original` |

Fixture `chatSessions/9ab.jsonl`:

```jsonl
{"kind":0,"v":{"version":3,"creationDate":1759400000000,"customTitle":null,"initialLocation":"panel","responderUsername":"GitHub Copilot","sessionId":"9ab","requests":[{"requestId":"request_1","timestamp":1759400001000,"message":{"text":"run tests","parts":[]},"agent":{"id":"github.copilot.default","name":"GitHub Copilot","extensionId":{"value":"GitHub.copilot-chat"}},"modelId":"copilot/gpt-4.1","modeInfo":{"kind":"agent","telemetryModeId":"agent","isBuiltin":true},"variableData":{"variables":[]},"response":[{"kind":"thinking","value":"Need pytest","id":"t1"},{"kind":"toolInvocationSerialized","toolCallId":"call_a","toolId":"run_in_terminal","invocationMessage":"Running command","isComplete":true,"isConfirmed":true,"toolSpecificData":{"kind":"terminal","commandLine":{"original":"pytest"}},"resultDetails":{"input":"pytest","output":[{"type":"embed","value":"3 passed"}]}},{"value":"All tests pass."}],"responseId":"response_1","responseTimestamp":1759400002000,"modelState":{"value":"complete"}}],"workingDirectory":"file:///home/u/proj"}}
{"kind":2,"k":["requests"],"v":[{"requestId":"request_2","timestamp":1759400010000,"message":{"text":"thanks","parts":[]},"variableData":{"variables":[]},"response":[{"value":"You're welcome."}]}]}
```

`workspace.json`: `{"folder": "file:///home/u/proj"}`

Confidence. High: field set, JSONL framing, bare `{value}` markdown parts.
Low: the actual `modelId`, `agent.id` and `responderUsername` values, which
come from the closed Copilot extension. Not determined: the exact release in
which `.jsonl` became the default beyond the `1.109` code comment; Copilot's
own data in `state.vscdb` keys other than `interactive.sessions`.
