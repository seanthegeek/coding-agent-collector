# Transcript schemas: Continue, VS Code chat (Copilot Chat), Aider

Paths below are relative to the clone root in `scratchpad/repos/`.

## 1. Repo, commit, license, scope

| Tool | Repo | Commit | License | Findings apply to |
|---|---|---|---|---|
| Continue | continuedev/continue | `5522c6f44ca0ac3528b37244818fbfa39b5af470` | Apache-2.0 (`LICENSE`) | IDE extensions and `cn` CLI (CLI reuses `core/util/history.ts`, `extensions/cli/src/session.ts:12,50-51`) |
| VS Code chat | microsoft/vscode | `d7622a529314a4abcefd7ca9e3d7344bc9ccba9e` | MIT (`LICENSE.txt`) | Built-in chat store used by Copilot Chat and any chat participant |
| Aider | Aider-AI/aider | `5dc9490bb35f9729ef2c95d00a19ccd30c26339c` | Apache-2.0 (`LICENSE.txt`) | `aider` CLI |

## 2. Transcript files

**Continue** (`~/.continue`, overridable by `CONTINUE_GLOBAL_DIR`, `core/util/paths.ts:27-35`):
- `sessions/<sessionId>.json`: one session, pretty-printed JSON (`paths.ts:102-103`, `history.ts:131-134`).
- `sessions/sessions.json`: JSON array of session metadata (`paths.ts:106-112`, `history.ts:168-181`).
- `logs/prompt.log`: human-readable LLM interaction log (`paths.ts:397-399`), written only by the binary used by JetBrains (`binary/src/index.ts:35-38`); not by the VS Code extension.
- `dev_data/0.2.0/<eventName>.jsonl`: one JSON object per line per event (`paths.ts:240-249`, `core/data/log.ts:20,73-97`). Events include `chatInteraction`, `chatFeedback`, `toolUsage`, `tokensGenerated`, `autocomplete`, `editInteraction`, `quickEdit` (dir listing of `packages/config-yaml/src/schemas/data/`). Legacy `dev_data/0.1.0/*.jsonl` and pre-version `dev_data/*.jsonl` (`paths.ts:437-461`).
- `dev_data/devdata.sqlite` table `tokens_generated` (`paths.ts:236-238`, `core/data/devdataSqlite.ts:16-20`).

**VS Code** (`common/model/chatSessionStore.ts`), under the user data dir (`~/.config/Code/`, `Library/Application Support/Code/`, `AppData/Roaming/Code/`, same for Insiders/VSCodium):
- Workspace: `User/workspaceStorage/<hash>/chatSessions/<sessionId>.jsonl` (>= 1.109 append log) or `<sessionId>.json` (< 1.109 flat JSON) (`:72-73`, `:731-741`). Log mode is default: `getValue('chat.useLogSessionStorage') !== false` and the setting is registered nowhere else.
- Empty window: `User/globalStorage/emptyWindowChatSessions/<sessionId>.jsonl|json` (`:72`); older `User/workspaceStorage/no-workspace/chatSessions/*.json` (`:75-76`, `:714-729`).
- Transferred: `User/globalStorage/transferredChatSessions/<sessionId>.json` (`:78`, `:745-750`).
- One file = one chat session.

**Aider** (`aider/args.py:271-275`): in the git root, else cwd. `.aider.chat.history.md` (markdown), `.aider.input.history` (prompt_toolkit FileHistory text), `.aider.llm.history` (text; **default `None`**, only written when `--llm-history-file` is set, `args.py:295-299`). One file = all sessions in that repo, appended.

## 3. Record schema

### Continue session (`core/index.d.ts`)
`Session` `:279-290`: `sessionId: string`, `title: string`, `workspaceDirectory: string`, `history: ChatHistoryItem[]`, `mode?: "chat"|"agent"|"plan"|"background"`, `chatModelTitle?: string|null`, `usage?: SessionUsage` (`promptTokens`, `completionTokens`, `totalCost`, `:275-277,407-422`). Key order is forced (`history.ts:115-129`).

`ChatHistoryItem` `:534-545`: `message: ChatMessage`, `contextItems: ContextItemWithId[]` (`content, name, description, uri?{type,value}`, `id{providerTitle,itemId}` `:459-473`), `editorState?`, `promptLogs?: PromptLog[]` (`modelTitle, modelProvider, prompt, completion`, `:488-493`), `toolCallStates?: ToolCallState[]`, `reasoning?: {active, text, startAt: number(ms epoch), endAt?}` (`:527-532`; `gui/src/redux/slices/sessionSlice.ts:561`), `conversationSummary?`, `appliedRules?`.

`ChatMessage` `:440-445` by `role` (`:335-340`): `user` {`content: string | {type:"text",text}|{type:"imageUrl",imageUrl:{url}}[]`}; `assistant` {`content`, `toolCalls?: [{id?, type?:"function", function?:{name?, arguments?: string(JSON)}}]`, `usage?`}; `thinking` {`content`, `signature?`, `redactedThinking?`, `reasoning_details?`}; `system` {`content: string`}; `tool` {`content: string`, `toolCallId: string`}. All may carry `metadata?: Record<string,unknown>`.

`ToolCallState` `:516-525`: `toolCallId`, `toolCall: {id, type:"function", function:{name, arguments}}`, `status: "generating"|"generated"|"calling"|"errored"|"done"|"canceled"`, `parsedArgs`, `processedArgs?`, `output?: ContextItem[]` (tool result text in `content`).

**No per-message timestamp exists** in session files. `sessions.json` entry (`BaseSessionMetadata` `:292-298`): `sessionId`, `title`, `dateCreated: string` (= `String(Date.now())`, ms epoch as string, `history.ts:171`), `workspaceDirectory`, `messageCount?` (assistant messages only, `:154-156`). The CLI drops `system` messages before saving and copies user content into `editorState` (`extensions/cli/src/session.ts:211-231`).

`dev_data/0.2.0/chatInteraction.jsonl` (`schemas/data/chatInteraction/v0.2.0.ts`, `index.ts:4-19`, `base.ts:3-11`): `eventName`, `schema`, `timestamp` (ISO 8601, `log.ts:50`), `userId`, `userAgent`, `selectedProfileId`, `prompt`, `completion`, `modelName`, `modelTitle`, `modelProvider`, `sessionId`, `tools?: string[]`, `rules?`. `toolUsage.jsonl` (`toolUsage/v0.2.0.ts:13-19`): `toolCallId`, `functionName`, `functionParams`, `toolCallArgs`, `accepted`, `succeeded`, `output`. `chatFeedback` adds `feedback`.

`prompt.log` (`core/llm/logFormatter.ts:43-75`): `HH:MM:SS.s [Chat]` (UTC, `:29-41`), `Options: {json}`, `Role: user`, text lines prefixed `| `, relative `+N.N` deltas, `Success`, `PromptTokens: N`; overlapping interactions get a column prefix char from `" |&%#"` (`:19`). No date, no session id.

### VS Code session (`common/model/chatModel.ts`)
Top level `ISerializableChatData3` `:2196-2227`: `version: 3`, `sessionId: string`, `creationDate: number` (ms epoch), `initialLocation`, `requests: ISerializableChatRequestData[]`, `responderUsername: string`, `customTitle?`, `hasPendingEdits?`, `inputState?`, `repoData?`, `pendingRequests?`, `workingDirectory?: string` (URI string). Written in that order by `storageSchema` (`chatSessionOperationLog.ts:284-296`).

`ISerializableChatRequestData` `:2037-2094` (one user turn + response): `requestId`, `timestamp?: number` (ms, request start), `message: string | {text, parts[]}` (`requestParser/chatParserTypes.ts:20-23`), `variableData: {variables: [{id, name, fullName?, value, range?}]}` (`attachments/chatVariableEntries.ts:63-75`), `agent?: {id, name, fullName?, extensionId, ...}` (`participants/chatAgents.ts:63-71`), `modelId?: string` (user-selected LM id, `chatServiceImpl.ts:1291`), `modeInfo?: {kind, telemetryModeId: 'ask'|'agent'|'edit'|'custom'|...}` (`chatModel.ts:394-401`), `response: SerializedChatResponsePart[]`, `responseId?`, `responseTimestamp?: number`, `result?: {errorDetails?, timings?, metadata?}`, `modelState?`, `vote?`, `followups?`, `usedContext?`, `contentReferences?`, `codeCitations?`, `promptTokens?`, `completionTokens?`, `latestModelCall?`, `elapsedMs?`, `editedFileEvents?: [{uri, eventKind}]`, `isSystemInitiated?`, `requestSource?`, `terminalExecutionId?`, `confirmation?`, deprecated `isHidden?`, `isCanceled?`.

Response parts (`:2064`): a bare `IMarkdownString` `{value, isTrusted?, supportThemeIcons?...}` for assistant text (`chatSessionOperationLog.ts:45`); objects keyed by `kind`: `"thinking"` {`value?: string|string[]`, `id?`, `reasoningDurationMs?`} (`chatService.ts:635-644`); `"toolInvocationSerialized"` {`toolCallId`, `toolId`, `invocationMessage`, `pastTenseMessage?`, `isComplete: boolean`, `isConfirmed`, `resultDetails?` (URI[] | `{input: string, output: [...], isError?}` `tools/languageModelToolsService.ts:283-290`), `resultError?`, `toolSpecificData?` (`{kind:'terminal', commandLine:{original, userEdited?}, cwd?}` `chatService.ts:686-700`; `{kind:'input', rawInput}` `:847-850`), `subAgentInvocationId?`} (`chatService.ts:1196-1215`); plus `textEditGroup`, `codeblockUri`, `progressMessage`, `confirmation`, `undoStop`, `inlineReference` etc. (`chatSessionOperationLog.ts:62-95`). Tool call and result are the **same object**: the call is `toolCallId`+`toolId`+`toolSpecificData`, the result is `resultDetails`/`resultError`/`isComplete`. No git branch field; `repoData` is unspecified here.

JSONL framing (`common/model/objectMutationLog.ts:196-215`, read `:340-385`): each line `{"kind":0,"v":<full session>}` (Initial), `{"kind":1,"k":[path...],"v":...}` (Set), `{"kind":2,"k":[...],"v":[items],"i"?:index}` (Push; `i` truncates from that index), `{"kind":3,"k":[...]}` (Delete). Replay in order to rebuild the object; `k` is a path of keys and array indexes, e.g. `["requests",3,"response"]`.

### Aider (`aider/io.py`)
`.aider.chat.history.md` (append-only, `:1117-1136`):
- Session header: `\n# aider chat started at YYYY-MM-DD HH:MM:SS\n\n` (local time, `:335-336`). Only date line in the file.
- User prompt: `\n#### <line1>  \n#### <line2>  \n`; empty input is `#### <blank>` (`:775-791`). Slash commands appear the same way (`#### /add foo.py`).
- Tool/system output (incl. `Applied edit to <path>`, `Commit <hash> <msg>`, errors, confirmations): `> text  \n` blockquote lines (`:964-973`, `:995-999`, `base_coder.py:2334`, `repo.py:313`).
- Assistant: raw markdown with no prefix, `\n<content>\n\n` (`:793-795`, called from `base_coder.py:1829`), so SEARCH/REPLACE edit blocks appear verbatim inside fenced code. Function-call fallback writes `json.dumps(args)` (`:1834`).
- Aider's own reader (`utils.py:148-188`) uses: skip lines starting `# `; `> ` = tool; `#### ` = user; anything else = assistant.

`.aider.input.history` (prompt_toolkit `FileHistory`, `io.py:19,356,740`; format in `prompt_toolkit/history.py:298-307`, fetched from upstream, not vendored): entry = `\n# YYYY-MM-DD HH:MM:SS.ffffff\n` then one `+<line>` per input line (local time).

`.aider.llm.history` (`io.py:753-764`): `TO LLM YYYY-MM-DDTHH:MM:SS\n` followed by `format_messages` output (`utils.py:112-134`): `-------` separator, then `ROLE <line>` per content line (`SYSTEM`, `USER`, `ASSISTANT`), and `LLM RESPONSE <ts>\n` + `ASSISTANT <line>` lines (`base_coder.py:1793`, `:1822-1826`).

## 4. Joins
- Continue: `sessions.json[].sessionId` ↔ `sessions/<sessionId>.json`; `workspaceDirectory` is in both. Tool call ↔ result: `assistant.toolCalls[].id` = `toolCallStates[].toolCallId` = next `tool` message `toolCallId`. `chatInteraction.sessionId` ↔ session file. `toolUsage.toolCallId` ↔ `toolCallStates[].toolCallId`.
- VS Code: `workspaceStorage/<hash>/workspace.json` `{"folder": "<file URI>"}` or `{"workspace": "<.code-workspace URI>"}` (`platform/storage/electron-main/storageMain.ts:416,472-474`). Also `workingDirectory` in the session (agents window). Tool call and result share one object; `toolCallId` is the join key to extension telemetry. `agent.id`/`responderUsername` identify the participant (Copilot).
- Aider: project = directory containing the files (git root). No session id; synthesise one per `# aider chat started at` header. Input-history timestamps join to `#### ` prompts by order and text.

## 5. SQLite / binary stores
- VS Code `state.vscdb` (`ItemTable(key, value)`, `base/parts/storage/node/storage.ts:73`): workspace `workspaceStorage/<hash>/state.vscdb` and `globalStorage/state.vscdb` (`storageMain.ts:285,353,415`). Keys: `interactive.sessions` = legacy JSON blob of all sessions, pre file-store (`chatServiceImpl.ts:67,341`, migrated by `chatSessionStore.ts:611-633`); `chat.ChatSessionStore.index` = `{version:1, entries:{<sessionId>:{sessionId,title,lastMessageDate(ms),timing:{created,lastRequestStarted,lastRequestEnded},workingDirectory?,isEmpty?,isExternal?,...}}}` (`:36,780-836`); `ChatSessionStore.transferIndex` (`:37`).
- Continue `dev_data/devdata.sqlite` `tokens_generated(model, provider, tokens_prompt, tokens_generated, timestamp)` (`devdataSqlite.ts:16-49`).
- Aider: none (`.aider.tags.cache.v*` is a repo-map cache, not chat).

## 6. Versions and migrations
- VS Code: `version` absent = v1, `2` (`computedTitle`), `3` (`customTitle`); `normalizeSerializableChatData` (`chatModel.ts:2422-2461`) fills missing `sessionId`/`creationDate` (defaults to one year ago). `message` may be a plain string in old data (`:2069`); `response` may be a string or string[] (`chatSessionStore.ts:688-699`). Storage: state.vscdb → `.json` → `.jsonl` (1.109+); flat `.json` is still read as fallback (`:653-675`). `isConfirmed` boolean pre-1.104; `source` undefined pre-1.104 (`chatService.ts:1204-1209`).
- Continue: `sessions.json` entries with `session_id` are an old format and are filtered (`history.ts:34-36`); `dev_data` schema `0.1.0` → `0.2.0` dirs; no version field inside session files.
- Aider: none; format unchanged across sessions.

## 7. Secrets to redact
- Continue: `promptLogs[].prompt` and `dev_data/*/chatInteraction.jsonl` `prompt` embed full context (file contents, possibly `.env`). `dev_data` `userId` is the Continue hub `userToken` (`log.ts:64-66`). Session files have no API keys.
- VS Code: `variableData.variables[].value` and `usedContext` may hold attached file contents; `toolSpecificData.rawInput`/`commandLine` may hold command-line secrets. `state.vscdb` also stores extension auth material in other keys (out of scope here).
- Aider: `.aider.llm.history` contains the complete system prompt with every added file; `.aider.chat.history.md` contains any pasted secrets. No keys written by Aider itself.

## 8. Parser plan

Globs: Continue `~/.continue/sessions/*.json` (skip `sessions.json`, read it for `dateCreated`), `~/.continue/dev_data/*/chatInteraction.jsonl`, `toolUsage.jsonl`. VS Code `**/User/workspaceStorage/*/chatSessions/*.{json,jsonl}`, `**/User/globalStorage/emptyWindowChatSessions/*.{json,jsonl}`, `**/User/workspaceStorage/no-workspace/chatSessions/*.json`, `**/User/globalStorage/transferredChatSessions/*.json`, plus sibling `workspace.json`. Aider `**/.aider.chat.history.md`, `**/.aider.input.history`, `**/.aider.llm.history`.

Rows: Continue one per `history[]` item (user/assistant/thinking/tool), plus one `tool_use` per `toolCalls[]`. VS Code one `user` per request, one `assistant` per contiguous markdown run, one `thinking` per thinking part, one `tool_use`+`tool_result` per `toolInvocationSerialized`. Aider one per `#### ` block (user), per assistant run, per `> ` run (tool_result); `# aider chat started` → `system`.

Columns: `timestamp_utc`: Continue = `sessions.json dateCreated` (session-level only; message rows inherit; `reasoning.startAt` if present); VS Code = `timestamp` for user, `responseTimestamp` for response parts (ms → UTC); Aider = last `# aider chat started at` / `# ` input-history line converted from local time. `session_id`: `sessionId` / `sessionId` / synthesised `<path>#<header ts>`. `project_path`: `workspaceDirectory` / `workspace.json folder` (file URI → path) or `workingDirectory` / file directory. `git_branch`: none in any store (empty). `model`: `chatModelTitle` or `promptLogs[].modelTitle` / `modelId` / none (only in `.aider.llm.history`? no: absent; use empty). `tool_name`/`tool_use_id`: `toolCall.function.name`+`toolCallId` / `toolId`+`toolCallId` / none. `summary`: first 200 chars of text, `function.arguments`, `invocationMessage`, or `commandLine.original`.

Fixtures:

Continue `sessions/0f1e.json`:
```json
{"sessionId":"0f1e","title":"Fix bug","workspaceDirectory":"/home/u/proj","history":[
 {"message":{"role":"user","content":"rename foo"},"contextItems":[]},
 {"message":{"role":"assistant","content":"","toolCalls":[{"id":"call_1","type":"function","function":{"name":"edit_existing_file","arguments":"{\"filepath\":\"a.py\"}"}}]},"contextItems":[],
  "toolCallStates":[{"toolCallId":"call_1","toolCall":{"id":"call_1","type":"function","function":{"name":"edit_existing_file","arguments":"{\"filepath\":\"a.py\"}"}},"status":"done","parsedArgs":{"filepath":"a.py"},"output":[{"name":"Edit","description":"","content":"ok"}]}]},
 {"message":{"role":"tool","content":"ok","toolCallId":"call_1"},"contextItems":[]}],"chatModelTitle":"GPT-4o"}
```
`sessions.json`: `[{"sessionId":"0f1e","title":"Fix bug","dateCreated":"1759400000000","workspaceDirectory":"/home/u/proj","messageCount":1}]`
`dev_data/0.2.0/chatInteraction.jsonl`: `{"eventName":"chatInteraction","schema":"0.2.0","timestamp":"2026-10-02T10:00:00.000Z","userId":"","userAgent":"vscode/1.1 (Continue/1.0)","selectedProfileId":"local","prompt":"rename foo","completion":"done","modelName":"gpt-4o","modelTitle":"GPT-4o","modelProvider":"openai","sessionId":"0f1e"}`

VS Code `chatSessions/9ab.jsonl`:
```
{"kind":0,"v":{"version":3,"creationDate":1759400000000,"customTitle":null,"initialLocation":"panel","responderUsername":"GitHub Copilot","sessionId":"9ab","requests":[{"requestId":"request_1","timestamp":1759400001000,"message":{"text":"run tests","parts":[]},"agent":{"id":"github.copilot.default","name":"GitHub Copilot","extensionId":{"value":"GitHub.copilot-chat"}},"modelId":"copilot/gpt-4.1","modeInfo":{"kind":"agent","telemetryModeId":"agent","isBuiltin":true},"variableData":{"variables":[]},"response":[{"kind":"thinking","value":"Need pytest","id":"t1"},{"kind":"toolInvocationSerialized","toolCallId":"call_a","toolId":"run_in_terminal","invocationMessage":"Running command","isComplete":true,"isConfirmed":true,"toolSpecificData":{"kind":"terminal","commandLine":{"original":"pytest"}},"resultDetails":{"input":"pytest","output":[{"type":"embed","value":"3 passed"}]}},{"value":"All tests pass."}],"responseId":"response_1","responseTimestamp":1759400002000,"modelState":{"value":"complete"}}],"workingDirectory":"file:///home/u/proj"}}
{"kind":2,"k":["requests"],"v":[{"requestId":"request_2","timestamp":1759400010000,"message":{"text":"thanks","parts":[]},"variableData":{"variables":[]},"response":[{"value":"You're welcome."}]}]}
```
`workspace.json`: `{"folder": "file:///home/u/proj"}`

Aider `.aider.chat.history.md`:
```

# aider chat started at 2026-10-02 12:00:00

#### rename foo to bar  
Here is the change:

a.py
```python
<<<<<<< SEARCH
foo
=======
bar
>>>>>>> REPLACE
```

> Applied edit to a.py  
> Commit abc1234 refactor: rename foo to bar  
```
`.aider.input.history`: `\n# 2026-10-02 12:00:05.123456\n+rename foo to bar\n`
`.aider.llm.history`: `TO LLM 2026-10-02T12:00:05\n-------\nSYSTEM Act as an expert\n-------\nUSER rename foo to bar\nLLM RESPONSE 2026-10-02T12:00:09\nASSISTANT Here is the change:\n`

**Confidence**: Continue session/sessions.json/dev_data schema: high (typed source). Continue prompt.log: medium (format from doc comment; only written by the JetBrains binary). VS Code field set and JSONL framing: high; actual `modelId`, `agent.id`, `responderUsername` string values come from the closed-source Copilot extension: low (invented in fixture). VS Code `response[]` markdown as bare `{value}` object: high (`chatSessionOperationLog.ts:45`). Aider chat/llm history: high; input history: medium-high (upstream prompt_toolkit source, not pinned to Aider's dependency version). **Not determined**: git branch (no store records it); per-message timestamps in Continue (absent); exact release where `.jsonl` became default beyond the `1.109` code comment; Copilot's own Chat data in `state.vscdb` keys other than `interactive.sessions`.
