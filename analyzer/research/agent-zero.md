# Agent Zero transcript schema

Catalog agent: `agent-zero`. One JSON file per chat holds two parallel
records of the conversation: the UI log (timestamped, truncated, last 1000
items) and each agent's LLM history (full text, no timestamps, compressed
over time). Paths in
[`collectors/research/agent-zero.md`](../../collectors/research/agent-zero.md).

## 1. Source

agent0ai/agent-zero at [`e3051fb584b1a36be2b0a0c90606f1c2c2d356ec`](https://github.com/agent0ai/agent-zero/commit/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec),
MIT ([`LICENSE:1-4`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/LICENSE#L1-L4)). Open source, Python. Read only, not run.

## 2. Transcript files

Relative to the install directory (`/a0` in Docker; on the host usually
`~/agent-zero/<instance>/` for installer and launcher setups):

- `usr/chats/<ctxid>/chat.json`, one per chat or task context; background
  contexts are never saved
  ([`helpers/persist_chat.py:17-19`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L17-L19),[`50-60`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L50-L60),[`95-96`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L95-L96)). The file is
  rewritten whole and atomically ([`99-120`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L99-L120)). `ctxid` is 8 random
  alphanumerics ([`agent.py:150-158`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/agent.py#L150-L158)).
- `usr/chats/<ctxid>/messages/<n>.txt`: full text of each tool result of 500
  characters or more; the history record gets a `file` key pointing at it
  ([`extensions/python/hist_add_tool_result/_90_save_tool_call_file.py:23-43`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/extensions/python/hist_add_tool_result/_90_save_tool_call_file.py#L23-L43)).
- Legacy: `usr/chats/<ctxid>.json` (v0.8.0, moved into the folder layout on
  load, [`persist_chat.py:134-140`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L134-L140)) and `tmp/chats/` (moved to
  `usr/chats`, [`helpers/migration.py:24`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/migration.py#L24)).

The catalog globs are therefore `agent-zero/*/usr/chats/*/chat.json`,
`agent-zero/usr/chats/*/chat.json` and the `Desktop/agent-zero` equivalents.

## 3. Record schema

`chat.json` top level ([`persist_chat.py:179-219`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L179-L219)): `id`, `name`,
`created_at`, `last_message` (ISO 8601 with the user's UTC offset,
[`helpers/localization.py:195-212`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/localization.py#L195-L212)), `type` (`user` or `task`,
[`agent.py:50-53`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/agent.py#L50-L53)), `agents`, `streaming_agent`, `agent_profile`, `log`,
`data` (includes `project`), `output_data`.

**`agents[]`** ([`persist_chat.py:222-232`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L222-L232)): agent 0 first, then each
subordinate. Fields `number`, `agent_profile`, `data`, and `history`, which
is a **JSON string** (compact dump, [`helpers/history.py:520-522`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L520-L522),[`810-811`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L810-L811)) that
decodes to `{"_cls":"History","counter","bulks":[],"topics":[],"current":{}}`
([`history.py:512-518`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L512-L518)). A `Topic` is `{_cls, summary, messages}`
([`290-295`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L290-L295)), a `Bulk` is `{_cls, summary, records}` of topics or bulks
([`340-345`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L340-L345)). A `Message` is `{_cls:"Message", id, ai, content, metadata,
sequence, summary, tokens}` ([`138-149`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L138-L149)), no timestamp. Chronological order
is bulks, then topics, then current, messages in list order.

Message content by kind:

- User (`ai=false`): dict from `fw.user_message.md`, `{system_message?,
  user_message, attachments?}` with empty keys removed
  ([`agent.py:746-773`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/agent.py#L746-L773), [`prompts/fw.user_message.md`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/prompts/fw.user_message.md#L1-L7)).
- Assistant (`ai=true`): the model's text, which in the default prompt mode
  is a JSON object `{thoughts, headline, tool_name, tool_args}`
  ([`prompts/agent.system.main.communication.md:9-12`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/prompts/agent.system.main.communication.md#L9-L12)); with native
  function calling it is `{"tool_name","tool_args"}` rendered from the calls,
  or `parallel_tool_calls` wrapping several
  ([`agent.py:775-795`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/agent.py#L775-L795), [`helpers/llm_result.py:197-209`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/llm_result.py#L197-L209)).
  `metadata.responses` carries `response_id`, `provider_model_key`, `usage`
  ([`llm_result.py:227-239`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/llm_result.py#L227-L239)).
- Tool result (`ai=false`): dict `{tool_name, tool_result, file?, ...}`
  ([`agent.py:802-825`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/agent.py#L802-L825)); the message `id` is the tool's log item id
  ([`helpers/tool.py:56`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/tool.py#L56),[`61-68`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/tool.py#L61-L68)).

**`log`** ([`persist_chat.py:235-247`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L235-L247)): `{guid, logs, progress, progress_no}`,
`logs` being the last 1000 items ([`persist_chat.py:18`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L18)). Each item
([`helpers/log.py:199-209`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L199-L209)): `no`, `id`, `type`, `heading`, `content`, `kvps`,
`timestamp` (float epoch seconds, `time.time()`, [`log.py:157-162`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L157-L162)),
`agentno`. `type` is one of `agent`, `browser`, `code_exe`, `subagent`,
`error`, `hint`, `info`, `progress`, `response`, `tool`, `mcp`, `input`,
`user`, `util`, `warning` ([`log.py:44-60`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L44-L60)). Content is cut to 15,000
characters ([`log.py:66`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L66),[`124-135`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L124-L135)). Keys passed as keyword arguments
are merged into `kvps` ([`log.py:336-340`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L336-L340)):

- `user` items: `content` is the message, `id` the history message id
  ([`helpers/message_queue.py:141-147`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/message_queue.py#L141-L147)).
- `agent` items: the streamed generation; `kvps` holds the parsed response
  (`thoughts`, `headline`, `tool_name`, `tool_args`), `step`, `reasoning`
  ([`extensions/python/response_stream/_10_log_from_stream.py:47-69`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/extensions/python/response_stream/_10_log_from_stream.py#L47-L69)).
- `tool` items: `kvps` is the tool arguments plus `_tool_name`; `content`
  is later set to the result ([`helpers/tool.py:56-59`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/tool.py#L56-L59),[`68`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/tool.py#L68)).
- `response` items: the final answer to the user.

## 4. Joins

- Chat to project: `data.project` is a project name; path
  `/a0/usr/projects/<name>` ([`helpers/projects.py:457`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L457)). Without a project the
  working directory is `usr/workdir`.
- Log to history: `log.logs[].id` equals the history `Message.id` for user
  messages and tool results (above).
- Tool use to result: one `tool` log item holds both; in history the
  assistant message's `tool_name` and the next tool-result message.
- Parent to subordinate: `agents[n]` is the subordinate of `agents[n-1]`
  ([`persist_chat.py:189-194`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L189-L194)); log items carry `agentno`.

## 5. SQLite or binary stores

None for transcripts. Memory is a FAISS index plus a pickled LangChain
docstore (`usr/memory/<subdir>/index.pkl`); reading it means unpickling
untrusted data, so leave it to manual analysis.

## 6. Format versions

No version field. History compression summarises topics into bulks and drops
the oldest bulk when merging fails
([`history.py:600-607`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/history.py#L600-L607)), so early turns may survive only as
summaries in history and only in the log while it is under 1000 items.
Older chats used `chat.json`-less `<ctxid>.json` files (section 2).

## 7. Secrets

Values from `secrets.env` are masked in history content and log items before
storage ([`extensions/python/hist_add_before/_10_mask_content.py:20-28`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/extensions/python/hist_add_before/_10_mask_content.py#L20-L28),
[`log.py:420-435`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/log.py#L420-L435)). API keys in `usr/.env` are not in that set, so any key the
user pastes or a tool prints stays in clear text. `user_message` and tool
`kvps` are the places to look.

## 8. Parser plan

Rows from `log.logs` (timestamped); when `len(log.logs) == 1000`, also emit
history messages that have no matching log id, with an empty timestamp and
a `system` row saying the log was trimmed.

| Column | Source |
| --- | --- |
| timestamp_utc | log `timestamp` (epoch s) |
| session_id | `chat.json` `id` |
| project_path | `/a0/usr/projects/<data.project>`, else empty |
| git_branch | empty |
| turn_type | `user` → user; `response` → assistant; `agent` → assistant (`kvps.headline`/`thoughts`), and thinking for `kvps.reasoning`; `tool`, `mcp`, `code_exe`, `browser`, `subagent` → tool_use then tool_result from `content`; others → system |
| model | `metadata.responses.provider_model_key` of the matching assistant message, else empty |
| tool_name | `kvps._tool_name` |
| tool_use_id | log item `id` |
| text | `content`; for tool_use the `code`/`command`/`url` key of `kvps`, else `kvps` as JSON |
| source_line | log item `no` |

Fixture `usr/chats/AbCd1234/chat.json`:

```json
{"id":"AbCd1234","name":"List files","created_at":"2026-10-01T14:00:00+02:00","type":"user",
 "last_message":"2026-10-01T14:00:05+02:00","streaming_agent":0,"agent_profile":"agent0",
 "data":{"project":"demo"},"output_data":{},
 "agents":[{"number":0,"agent_profile":"agent0","data":{},
   "history":"{\"_cls\":\"History\",\"counter\":3,\"bulks\":[],\"topics\":[],\"current\":{\"_cls\":\"Topic\",\"summary\":\"\",\"messages\":[{\"_cls\":\"Message\",\"id\":\"u1\",\"ai\":false,\"content\":{\"user_message\":\"list files\"},\"metadata\":{},\"sequence\":0,\"summary\":\"\",\"tokens\":5},{\"_cls\":\"Message\",\"id\":\"a1\",\"ai\":true,\"content\":\"{\\\"thoughts\\\":[\\\"list\\\"],\\\"headline\\\":\\\"Listing\\\",\\\"tool_name\\\":\\\"code_execution_tool\\\",\\\"tool_args\\\":{\\\"runtime\\\":\\\"terminal\\\",\\\"code\\\":\\\"ls\\\"}}\",\"metadata\":{},\"sequence\":0,\"summary\":\"\",\"tokens\":30},{\"_cls\":\"Message\",\"id\":\"t1\",\"ai\":false,\"content\":{\"tool_name\":\"code_execution_tool\",\"tool_result\":\"a.txt\"},\"metadata\":{},\"sequence\":0,\"summary\":\"\",\"tokens\":8}]}}"}],
 "log":{"guid":"6b0f0c1e-0000-4000-8000-000000000001","progress":"","progress_no":3,"logs":[
  {"no":0,"id":"u1","type":"user","heading":"","content":"list files","kvps":{"attachments":[]},"timestamp":1759320001.0,"agentno":0},
  {"no":1,"id":"g1","type":"agent","heading":"A0: Listing","content":"","kvps":{"step":"Writing terminal command... (2)","thoughts":["list"],"headline":"Listing","tool_name":"code_execution_tool","tool_args":{"runtime":"terminal","code":"ls"}},"timestamp":1759320002.0,"agentno":0},
  {"no":2,"id":"t1","type":"tool","heading":"A0: Using tool 'code_execution_tool'","content":"a.txt","kvps":{"runtime":"terminal","code":"ls","_tool_name":"code_execution_tool"},"timestamp":1759320003.0,"agentno":0}]}}
```

Confidence. High: file layout, top-level keys, history and log item shapes,
timestamp units, masking. Medium: the exact `type` and `heading` of
`code_execution_tool` items (they come from a tool subclass not traced; the
generic `tool` path is shown). Not determined: content of task-scheduler
contexts beyond `type="task"`; the `responses` metadata for every provider.
