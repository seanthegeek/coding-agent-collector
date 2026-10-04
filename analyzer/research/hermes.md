# Hermes Agent transcript schema

Catalog agent: `hermes`. Hermes stores every conversation (CLI, TUI,
desktop, messaging gateway, cron, subagents) in one SQLite database per
profile home, in OpenAI chat-completions message shape. Paths in
[`collectors/research/hermes.md`](../../collectors/research/hermes.md).

## 1. Source

NousResearch/hermes-agent at [`8b66a51036c1e20920a17cdd049fdf55c968d683`](https://github.com/NousResearch/hermes-agent/commit/8b66a51036c1e20920a17cdd049fdf55c968d683),
MIT ([`LICENSE`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/LICENSE#L1-L3)). Open source, Python. Read only, not run.

## 2. Transcript files

Globs relative to the user home:

- `.hermes/state.db` (+ `-wal`, `-shm`), and the same under
  `.hermes/profiles/*/` and `AppData/Local/hermes/`
  ([`hermes_state.py:176`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state.py#L176); home resolution in
  [`hermes_constants.py:51-58`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_constants.py#L51-L58)). One database holds all sessions; it
  is canonical for the gateway too
  ([`gateway/session_transcript.py:573-575`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/gateway/session_transcript.py#L573-L575)).
- `.hermes/sessions/<session_id>.jsonl`: written only when `state.db` was
  replaced under a running process; one JSON message dict per line
  ([`hermes_state.py:429-444`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state.py#L429-L444)).
- `.hermes/sessions/<id>.json`, `session_<id>.json` (legacy snapshots) and
  `request_dump_<id>_<ts>.json` (redacted API request on error)
  ([`hermes_state_sessions.py:1573-1585`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_sessions.py#L1573-L1585),
  [`agent/agent_runtime_helpers.py:1628-1633`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/agent_runtime_helpers.py#L1628-L1633)).
- `.hermes/sessions/saved/hermes_conversation_<YYYYmmdd_HHMMSS>.json`
  (`{id, model, started_at, messages}`) from `/save`
  ([`hermes_cli/cli_session_mixin.py:669-689`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_cli/cli_session_mixin.py#L669-L689)).
- `.hermes/response_store.db`: API-server response store
  ([`gateway/platforms/api_server.py:732`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/gateway/platforms/api_server.py#L732)); schema not examined.

Session ids are `<YYYYmmdd_HHMMSS>_<hex>` from local time
([`hermes_state_ids.py:56-60`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_ids.py#L56-L60)).

## 3. Record schema

Schema in [`hermes_state_common.py:372-480`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L372-L480).

`sessions` ([`382-447`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L382-L447)): `id`, `source` (`cli`, `cron`, `kanban`,
`acp`, `api_server`, `subagent`, `tool`, `recovered` or a messaging
platform; [`hermes_state.py:471-473`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state.py#L471-L473)), `user_id`, `session_key`,
`chat_id`, `chat_type`, `thread_id`, `display_name`, `origin_json`, `model`,
`model_config`, `system_prompt_hash` (joins `system_prompts.hash`),
`parent_session_id`, `started_at`, `ended_at` (REAL epoch seconds),
`end_reason`, token and cost counters, `cwd`, `git_branch`,
`git_repo_root`, `title`, `profile_name`, `archived`, `hidden`,
`tool_names`. `cwd` and `git_branch` are set at creation and updated by
`update_session_cwd` ([`hermes_state_sessions.py:326`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_sessions.py#L326),[`558-566`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_sessions.py#L558-L566)).

`messages` ([`449-480`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L449-L480)), one row per OpenAI message:

| Column | Meaning |
| --- | --- |
| `id` | INTEGER autoincrement, order of writing |
| `session_id` | `sessions.id` |
| `role` | `user`, `assistant`, `tool`, `system` ([`hermes_state_messages.py:644`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L644)) |
| `content` | TEXT; list or dict content (multimodal parts) is stored as `"\x00json:"` + JSON ([`hermes_state_messages.py:138-147`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L138-L147), prefix at [`hermes_state.py:1612`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state.py#L1612)) |
| `tool_calls` | JSON list on assistant rows ([`hermes_state_messages.py:266`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L266)); each `{id, call_id, response_item_id, type, function: {name, arguments}}` with `arguments` a JSON string ([`agent/chat_completion_helpers.py:1642-1644`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/chat_completion_helpers.py#L1642-L1644)) |
| `tool_call_id`, `tool_name` | on `role='tool'` result rows ([`agent/turn_tool_round.py:115-118`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/turn_tool_round.py#L115-L118)) |
| `timestamp` | REAL, `time.time()` epoch seconds, UTC ([`hermes_state_messages.py:399`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L399)) |
| `reasoning`, `reasoning_content` | thinking text; `reasoning_details`, `codex_reasoning_items`, `codex_message_items` are JSON ([`hermes_state_messages.py:278-280`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L278-L280)) |
| `finish_reason`, `token_count` | provider values |
| `active`, `compacted` | rewind and compaction set `active=0, compacted=1` instead of deleting ([`hermes_state_messages.py:70`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L70)) |
| `api_content` | exact string sent to the API when it differed from `content` ([`hermes_state_messages.py:390-392`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_messages.py#L390-L392)) |
| `platform_message_id`, `display_kind`, `display_metadata`, `message_uid`, `tool_call_uid(s)` | gateway and UI bookkeeping |

Model per message is not stored; use `sessions.model`, or
`session_model_usage.model` ([`hermes_state_common.py:482-502`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L482-L502)) when a
session switched models.

## 4. Joins

- Message to session: `messages.session_id = sessions.id`; project path is
  `sessions.cwd` (or `git_repo_root`), branch `sessions.git_branch`.
- Tool use to result: `messages.tool_calls[].id` (or `call_id`) equals a
  later `role='tool'` row's `tool_call_id`. Hermes pairs on `call_id` then
  `id`, splitting at `|` ([`agent/message_sanitization.py:520-528`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/message_sanitization.py#L520-L528)).
- Parent to child: `sessions.parent_session_id`. A parent whose
  `end_reason='compression'` continues in its child; `'branched'` marks a
  `/branch` fork ([`hermes_state_common.py:169-174`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L169-L174)); `source='subagent'`
  rows are delegated tasks.
- System prompt: `sessions.system_prompt_hash = system_prompts.hash`.

## 5. SQLite specifics

WAL by default with a DELETE fallback on filesystems that refuse it
([`hermes_state_wal.py:254-262`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_wal.py#L254-L262)); read `state.db-wal` with the main file.
FTS5 tables `messages_fts` and `messages_fts_trigram`
([`hermes_state_common.py:785`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L785),[`905`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L905)) are indexes; skip them. Ended sessions
idle 90 days are pruned and the file may be VACUUMed
([`hermes_cli/config_defaults.py:2276-2285`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_cli/config_defaults.py#L2276-L2285),
[`hermes_state_maintenance.py:421-445`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_maintenance.py#L421-L445)); older copies live in
`state-snapshots/*/state.db`. No compression or encryption.

## 6. Format versions

`schema_version.version`, currently 31
([`hermes_state_common.py:283`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_common.py#L283)); migrations add columns in
place ([`hermes_state_schema.py:1018-1059`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_schema.py#L1018-L1059)), so a parser must select
columns that exist (`PRAGMA table_info`). Gateway metadata was in
`sessions/sessions.json` before v18 ([`hermes_state_schema.py:1308-1311`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/hermes_state_schema.py#L1308-L1311)).
The legacy `session_<id>.json` layout was not examined.

## 7. Secrets

Tool-call `arguments` are stored unredacted on purpose
([`agent/chat_completion_helpers.py:1641-1642`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/chat_completion_helpers.py#L1641-L1642)); tool results,
`api_content` and `system_prompts.prompt` (which embeds memory and context
files) can carry secrets. `request_dump_*` files are redacted before
writing ([`agent_runtime_helpers.py:1629-1633`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/agent/agent_runtime_helpers.py#L1629-L1633)). `sessions.origin_json`
holds messaging user and chat identifiers.

## 8. Parser plan

Inputs: `state.db` (via `sqlite_util`, so the WAL is read) under any Hermes
home; optionally `sessions/*.jsonl`. Rows: one per message; an assistant row
with N `tool_calls` yields one `assistant` row (when `content` is non-empty),
one `thinking` row (when `reasoning`/`reasoning_content` is set), and N
`tool_use` rows. Order by `timestamp, id`. Include `active=0` rows: they are
evidence of rewound or compacted turns.

| Column | Source |
| --- | --- |
| timestamp_utc | `messages.timestamp` (epoch s) |
| session_id | `messages.session_id` |
| project_path | `sessions.cwd`, else `git_repo_root` |
| git_branch | `sessions.git_branch` |
| turn_type | `role`: `user` → user, `assistant` → assistant, `tool` → tool_result, `system` → system; `tool_calls[]` → tool_use; reasoning → thinking |
| model | `sessions.model` |
| tool_name | `tool_calls[].function.name`, or `messages.tool_name` |
| tool_use_id | `tool_calls[].id` / `messages.tool_call_id` |
| text | `content` (strip `\x00json:` and join text parts); for tool_use the `command`/`path` key of `arguments`, else the arguments |
| source_line | `messages.id` |

Fixture:

```sql
CREATE TABLE schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version VALUES (31);
CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, model TEXT,
  parent_session_id TEXT, started_at REAL NOT NULL, ended_at REAL, end_reason TEXT,
  cwd TEXT, git_branch TEXT, git_repo_root TEXT, title TEXT);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
  role TEXT NOT NULL, content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT,
  timestamp REAL NOT NULL, finish_reason TEXT, reasoning TEXT, reasoning_content TEXT,
  active INTEGER NOT NULL DEFAULT 1, compacted INTEGER NOT NULL DEFAULT 0);
INSERT INTO sessions VALUES ('20261001_120000_a1b2c3d4','cli','anthropic/claude-sonnet-4',NULL,
  1759320000.0,NULL,NULL,'/home/u/repo','main','/home/u/repo','List files');
INSERT INTO messages (session_id,role,content,tool_call_id,tool_calls,tool_name,timestamp,finish_reason,reasoning) VALUES
 ('20261001_120000_a1b2c3d4','user','list files',NULL,NULL,NULL,1759320001.25,NULL,NULL),
 ('20261001_120000_a1b2c3d4','assistant','',NULL,
  '[{"id":"call_1","call_id":"call_1","response_item_id":null,"type":"function","function":{"name":"terminal","arguments":"{\"command\":\"ls\"}"}}]',
  NULL,1759320002.5,'tool_calls','User wants a listing.'),
 ('20261001_120000_a1b2c3d4','tool','a.txt\nb.txt','call_1',NULL,'terminal',1759320003.0,NULL,NULL),
 ('20261001_120000_a1b2c3d4','assistant','Two files: a.txt, b.txt.',NULL,NULL,NULL,1759320004.0,'stop',NULL);
```

Confidence. High: table and column names, timestamp unit, content prefix,
tool-call shape, joins, WAL. Medium: the full set of `role` values (only the
four above seen in queries) and `source` values beyond the stale-open list.
The shell tool is registered as `terminal`
([`tools/terminal_tool.py:1634`](https://github.com/NousResearch/hermes-agent/blob/8b66a51036c1e20920a17cdd049fdf55c968d683/tools/terminal_tool.py#L1634)). Not determined: `response_store.db` and legacy
`session_<id>.json` schemas.
