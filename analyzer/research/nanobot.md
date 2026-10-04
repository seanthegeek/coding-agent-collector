# nanobot transcript schema

Catalog agent: `nanobot`. nanobot stores each conversation as a JSONL file of
OpenAI chat-completions messages behind one metadata line, rewritten whole on
every save. Path research is in
[../../collectors/research/nanobot.md](../../collectors/research/nanobot.md).

## 1. Source

HKUDS/nanobot at [`acdae3d0ae2714b6dde672428e921dbf705c096f`](https://github.com/HKUDS/nanobot/commit/acdae3d0ae2714b6dde672428e921dbf705c096f) (2026-10-04,
`nanobot-ai` 0.3.5), MIT, open source.

## 2. Transcript files

Home-relative; `.nanobot` may be `.nanobot-<instance>` when `--config` points
elsewhere ([`nanobot/config/paths.py:20-27`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L20-L27)).

- `.nanobot/sessions/<workspace-id>/<stem>.jsonl`: one file per session key.
  `<workspace-id>` is 32 hex characters; `<stem>` is the URL-safe base64 of the
  session key without padding ([`nanobot/session/manager.py:74`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L74),[`903-924`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L903-L924)), so
  `cli:direct` is `Y2xpOmRpcmVjdA.jsonl`. The sibling `.workspace` file gives
  the workspace path ([`:606-607`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L606-L607)).
- Sidecar `<stem>.checkpoint.json`: volatile mid-turn checkpoint, deleted on
  the next full save ([`:60`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L60),[`926-927`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L926-L927),[`1233-1235`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L1233-L1235)). Not a transcript.
- Legacy: `.nanobot/sessions/<key with ":" → "_">.jsonl` (global, before
  per-workspace namespaces) and `<workspace>/sessions/*.jsonl` (older still),
  both migrated into the namespaced directory ([`config/paths.py:69-71`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L69-L71);
  [`session/manager.py:806-855`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L806-L855),[`929-933`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L929-L933)). Same record format. Conflicting copies
  are kept in `.migration-conflicts/` ([`:777-779`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L777-L779)).
- `<workspace>/memory/history.jsonl`: compressed long-term journal, lines
  `{cursor, timestamp: "YYYY-MM-DD HH:MM", content, session_key?}`
  ([`agent/memory.py:311-322`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/memory.py#L311-L322)); legacy `memory/HISTORY.md`.
- `.nanobot/webui/<safe key>.jsonl` and `<safe key>.segments/NNNNNN.jsonl`:
  WebUI display transcript, schema version 3, a rendering mirror of the
  session ([`webui/transcript.py:1`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/transcript.py#L1),[`31-39`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/transcript.py#L31-L39),[`172-188`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/transcript.py#L172-L188)). Not parsed in v1 of the parser.
- `.nanobot/history/cli_history`: prompt_toolkit input history, user prompts
  only ([`config/paths.py:64-66`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L64-L66)).

## 3. Record schema

Line 1 is metadata ([`session/manager.py:1207-1220`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L1207-L1220)): `{"_type":"metadata", key,
created_at, updated_at, metadata, last_archived, last_consolidated}`. An
optional line 2 is `{"_type":"provider_state", state}` ([`:1221-1226`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L1221-L1226)).
Every other line is one message dict ([`:1227-1228`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L1227-L1228); loader treats any line
without a known `_type` as a message, [`:961-987`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L961-L987)):

- `role`: `user`, `assistant`, `tool` (and `system` if a caller adds one).
- `content`: string, or a list of OpenAI content blocks (`{type:"text",
  text}`; inline images are replaced on save, [`agent/loop.py:2409-2427`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/loop.py#L2409-L2427)).
- `timestamp`: `datetime.now().isoformat()`, **naive local time with no
  zone**, for example `2026-10-01T10:15:02.123456`
  ([`session/manager.py:208-217`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L208-L217); [`agent/loop.py:2430`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/loop.py#L2430)). `created_at` and
  `updated_at` in the metadata line are the same form ([`:177-178`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L177-L178)).
- assistant: `tool_calls: [{id, type:"function", function:{name, arguments
  (JSON string)}, extra_content?, provider_specific_fields?}]`
  ([`providers/base.py:94-112`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/providers/base.py#L94-L112)), `reasoning_content` (thinking text),
  `thinking_blocks` ([`utils/helpers.py:753-771`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/utils/helpers.py#L753-L771)). Empty assistant messages
  are dropped ([`loop.py:2391-2392`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/loop.py#L2391-L2392)).
- tool: `tool_call_id`, `name`, `content` ([`agent/runner.py:541-550`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/runner.py#L541-L550)).
- Flags: `_hidden_history: true` marks the synthetic user message that stands
  in for summarised history ([`session/history_visibility.py:10`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/history_visibility.py#L10);
  [`session/manager.py:219-238`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L219-L238)); `_runtime_context` marks injected runtime
  context on a user message ([`runtime_context.py:14`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/runtime_context.py#L14); [`loop.py:2428-2429`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/loop.py#L2428-L2429)).

No model is recorded per message. The session's model preset is
`metadata._nanobot_model_preset` ([`session/model_selection.py:9`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/model_selection.py#L9)); the
summary is `metadata._last_summary {text, last_active}` and the last
delivery route `metadata.last_channel` ([`session/keys.py:10`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/keys.py#L10),[`38`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/keys.py#L38)).

## 4. Joins

- Session: file = metadata `key`. Keys are `<channel>:<chat_id>`, or
  `unified:default`, `heartbeat`, `cli:direct` ([`session/keys.py:8-9`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/keys.py#L8-L9),[`23-27`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/keys.py#L23-L27);
  [`cli/agent.py:146`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/agent.py#L146)). The channel and chat id identify the external sender.
- Project: `.workspace` in the same directory.
- Tool call to result: `tool_calls[].id` = `tool_call_id`.
- Model: by time, against `.nanobot/llm_usage.sqlite3` `llm_calls.started_at_ms`
  (UTC epoch ms, [`providers/base.py:1283`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/providers/base.py#L1283); [`llm_usage/store.py:196-218`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/llm_usage/store.py#L196-L218)), which also
  gives the host's clock offset.
- Subagents: not persisted as separate session files as far as traced.

## 5. SQLite or binary stores

None for transcripts. `llm_usage.sqlite3` (WAL, [`store.py:190`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/llm_usage/store.py#L190)) holds only
call metadata.

## 6. Format versions

No version field in session files. The metadata line writes both
`last_archived` and the older `last_consolidated` for downgrade
compatibility ([`session/manager.py:1215-1218`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L1215-L1218)). Legacy file names differ (section 2).
`Session.clear()` empties the messages and the next save rewrites the file
([`:374-380`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L374-L380)), so a `/new` in a chat erases the previous transcript; only
`memory/history.jsonl` and the WebUI mirror keep a trace.

## 7. Secrets

`provider_state.state` is opaque provider conversation state. Tool `content`
holds raw tool output. `tool_calls[].function.arguments` can contain whatever
the agent passed to a shell. Credentials themselves are not in session files.

## 8. Parser plan

Globs (home-relative): `.nanobot*/sessions/*/*.jsonl`,
`.nanobot*/sessions/*.jsonl`, `.nanobot*/sessions/*/.migration-conflicts/*.jsonl`.
Skip `*.checkpoint.json`. Read `.workspace` from the same directory.

**Timestamps are host local time.** The collector does not record the host
zone, so follow the aider parser's documented convention (local time emitted
as if UTC, stated in the README parser table) and let the analyst correct it;
`llm_usage.sqlite3` gives true UTC for the same calls to derive the offset.

| Column | Source |
| --- | --- |
| timestamp_utc | message `timestamp` (naive local; see above) |
| session_id | metadata `key` |
| project_path | `.workspace` file content |
| git_branch | empty |
| turn_type | `user` → user (`_hidden_history` → system); `assistant` → assistant, plus tool_use per `tool_calls[]`, thinking from `reasoning_content`; `tool` → tool_result |
| model | empty, or `metadata._nanobot_model_preset` |
| tool_name | `tool_calls[].function.name` / tool `name` |
| tool_use_id | `tool_calls[].id` / `tool_call_id` |
| text | `content` text; for tool_use the `command`/`path`/`url` key of the parsed `arguments`, else the arguments string |
| source_line | line number |

Fixture, file `.nanobot/sessions/0123456789abcdef0123456789abcdef/dGVsZWdyYW06MTIzNDU2Nzg5.jsonl`,
with `.workspace` containing `/home/alice/.nanobot/workspace`:

```json
{"_type":"metadata","key":"telegram:123456789","created_at":"2026-10-01T10:15:00.000001","updated_at":"2026-10-01T10:15:09.500000","metadata":{"last_channel":"telegram:123456789"},"last_archived":0,"last_consolidated":0}
{"role":"user","content":"what is using port 8080?","timestamp":"2026-10-01T10:15:01.200000"}
{"role":"assistant","content":"","tool_calls":[{"id":"call_abc123","type":"function","function":{"name":"exec","arguments":"{\"command\": \"ss -ltnp | grep 8080\"}"}}],"reasoning_content":"Check listening sockets.","timestamp":"2026-10-01T10:15:04.000000"}
{"role":"tool","tool_call_id":"call_abc123","name":"exec","content":"LISTEN 0 128 *:8080 users:((\"python3\",pid=4242))","timestamp":"2026-10-01T10:15:05.000000"}
{"role":"assistant","content":"python3 (pid 4242) is listening on 8080.","timestamp":"2026-10-01T10:15:09.400000"}
```

Confidence. High: file naming, metadata and message field names, naive
local timestamps, tool call shape. The shell tool is
named `exec` ([`agent/tools/shell.py:247-248`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/tools/shell.py#L247-L248)). Medium: `thinking_blocks` element
shape is provider-defined. Not determined: whether
subagent runs are persisted anywhere; the WebUI transcript record shape.
