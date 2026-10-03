# Crush transcript schema

Catalog agent: `crush`. Crush began as an OpenCode fork
([opencode.md](opencode.md)) but shares no storage code with it any more:
Go, sqlc and goose migrations, one database per project. Paths cited are
relative to the clone.

## 1. Source

charmbracelet/crush at `ca6ae26ce016b980407ce32f012a467ec10c1e2f`,
Functional Source License 1.1 with MIT future license (`LICENSE.md`). Open
source.

## 2. Transcript stores

Per project: `<project>/.crush/crush.db` (`internal/config/config.go:25`
default `.crush`; `internal/db/connect.go:93` `crush.db`). The data
directory is found by walking up from the cwd (`internal/config/load.go:590-593`)
and can be overridden by `data_directory` (`config.go:470`). The global
registry `~/.local/share/crush/projects.json` (Windows
`%LOCALAPPDATA%\crush\projects.json`; `load.go:1259-1278`,
`internal/projects/projects.go:14,31-33`) maps each project `path` to its
`data_dir`. One `messages` row per message; parts are a JSON array in the
`parts` column.

## 3. Record schema

`internal/db/migrations/20250424200609_initial.sql`.

`sessions` (`:4-14` plus ALTERs): `id` (uuid; task sub-sessions use the tool
call id, `internal/session/session.go:103,117`), `parent_session_id`,
`title`, `message_count`, `prompt_tokens`, `completion_tokens`, `cost`,
`updated_at`, `created_at` (epoch seconds, `strftime('%s','now')`,
`internal/db/sql/sessions.sql:22-23`), `summary_message_id`, `todos` JSON,
`channel`.

`messages` (`:47-57` plus ALTERs; `internal/db/models.go:29-44`): `id`
uuid (`internal/message/message.go:206`), `session_id`, `role` in
`assistant|user|system|tool` (`internal/message/content.go:20-27`), `parts`
JSON, `model`, `provider` (`20250627000000_add_provider_to_messages.sql`),
`created_at`, `updated_at`, `finished_at` (seconds, copied from the `finish`
part's `time`, `message.go:435-439`), `is_summary_message`, `prism_model_id`,
`prism_model_name`, `prism_*_savings`.

`parts` is `[{"type":...,"data":{...}}]` (`message.go:613-629`). Types and
`data` keys (`content.go`): `text`: `text`, `hidden?` (`:70-74`);
`reasoning`: `thinking`, `signature`, `thought_signature`, `tool_id`,
`responses_data`, `started_at`, `finished_at` (seconds; `:55-63`);
`tool_call`: `id`, `name`, `input` (JSON string), `provider_executed`,
`finished` (`:109-115`); `tool_result`: `tool_call_id`, `name`, `content`,
`data` (base64 media), `mime_type`, `metadata`, `is_error` (`:119-127`);
`finish`: `reason` in `end_turn|max_tokens|tool_use|canceled|error|content_filter|unknown`,
`time` (seconds), `message?`, `details?` (`:33-49,131-136`);
`shell_command`: `command`, `output`, `exit_code` (`:142-146`); `image_url`:
`url`, `detail`; `binary`: untagged Go fields `Path`, `MIMEType`, `Data`
(`:93-97`).

Other tables: `files` (session file snapshots: `path`, `content`,
`version`), `read_files`, `mcp_enabled_servers`, `mcp_disabled_servers`. No
project path, cwd or git branch column anywhere.

## 4. Joins

`messages.session_id → sessions.id`; `sessions.parent_session_id` for
sub-agents. `tool_call` parts live in the assistant message; the result is a
separate `role='tool'` message with a `tool_result` part
(`internal/agent/agent.go:1032-1038`), joined on
`tool_result.data.tool_call_id = tool_call.data.id`. Project path is the
parent directory of the `.crush` holding the database, or `projects.json`
`projects[].path` / `data_dir`.

## 5. SQLite specifics

`journal_mode=WAL` (`connect.go:20`) with Go defaults (auto-checkpoint at
1000 pages), so a copy without `crush.db-wal` loses recent messages.
`secure_delete=ON` (`connect.go:25`) zeroes deleted rows. Writes are
debounced about 33 ms (`message.go:21`) and serialised on one connection
(`connect.go:142`). No encryption or compression.

## 6. Format versions

Goose migrations only (12 files); no JSON era, no version field;
`goose_db_version` table.

## 7. Secrets

`crush.json` `providers.<name>.api_key` (`config.go:102`) at
`~/.config/crush/`, `~/.local/share/crush/` and `<project>/.crush/`.
`reasoning.signature` and `thought_signature` are opaque provider blobs. Tool
input and output can contain pasted tokens.

## 8. Parser plan

Globs: `.local/share/crush/projects.json`,
`AppData/Local/crush/projects.json`, project-level `.crush/crush.db{,-wal,-shm}`.

Rows: one per part in `parts`.

| Column | Source |
| --- | --- |
| timestamp_utc | `messages.created_at` (s); tool_call and tool_result use `finished_at` or `finish.time` |
| session_id | `sessions.id` |
| project_path | directory containing `.crush`, or `projects.json` `path` |
| git_branch | empty |
| turn_type | `user`/`assistant` text; `reasoning` → thinking; `tool_call` → tool_use; `tool_result` → tool_result; role `system`, `finish`, `shell_command` → system |
| model | `provider`/`model` (or `prism_model_id`) |
| tool_name, tool_use_id | `data.name`, `data.id` or `data.tool_call_id` |
| summary | text, input JSON, output |

Fixture rows:

```sql
INSERT INTO sessions(id,title,message_count,prompt_tokens,completion_tokens,cost,updated_at,created_at) VALUES('6f1c0001','Fix bug',3,10,5,0.01,1760000005,1760000001);
INSERT INTO messages(id,session_id,role,parts,model,provider,created_at,updated_at,finished_at,is_summary_message) VALUES
('m1','6f1c0001','user','[{"type":"text","data":{"text":"list files"}},{"type":"finish","data":{"reason":"stop","time":0}}]','claude-sonnet-4','anthropic',1760000001,1760000001,NULL,0),
('m2','6f1c0001','assistant','[{"type":"tool_call","data":{"id":"call_x1","name":"bash","input":"{\"command\":\"ls\"}","provider_executed":false,"finished":true}},{"type":"finish","data":{"reason":"tool_use","time":1760000003}}]','claude-sonnet-4','anthropic',1760000002,1760000003,1760000003,0),
('m3','6f1c0001','tool','[{"type":"tool_result","data":{"tool_call_id":"call_x1","name":"bash","content":"a.txt","data":"","mime_type":"","metadata":"","is_error":false}},{"type":"finish","data":{"reason":"stop","time":0}}]','','',1760000003,1760000003,NULL,0);
```

`projects.json`: `{"projects":[{"path":"/home/u/repo","data_dir":"/home/u/repo/.crush","last_accessed":"2026-10-01T12:00:00Z"}]}`

Confidence. High: table columns, part JSON field names, timestamp units,
WAL, tool result as a separate message, absence of git branch. Not
determined: `binary` part key casing in shipped builds (inferred from an
untagged Go struct).
