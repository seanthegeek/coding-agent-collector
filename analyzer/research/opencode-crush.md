# OpenCode and Crush transcript schemas

Paths below are relative to each clone in `scratchpad/repos/`. Every claim is from the checked commit; nothing is from memory.

## 1. Repo, commit, license, applicability

- **OpenCode** `sst/opencode` @ `907b3bc518fa48e90e8ec24dd327d13eee71c36c`, MIT (`LICENSE`). Open source. The schema has moved out of `packages/opencode` into `packages/core` (tables) and `packages/schema` (JSON shapes).
- **Crush** `charmbracelet/crush` @ `ca6ae26ce016b980407ce32f012a467ec10c1e2f`, Functional Source License 1.1 with MIT future license (`LICENSE.md`). Open source. Crush no longer shares any storage code with OpenCode: Go + sqlc + goose, one DB per project.

## 2. Transcript stores

**OpenCode.** One SQLite file for all projects: `~/.local/share/opencode/opencode.db` (`packages/core/src/global.ts:3,11` uses `xdg-basedir` with no platform branching, so the same path on macOS and Windows; `packages/core/src/database/database.ts:49-54`). Non-release channels use `opencode-<channel>.db` in the same directory (`database.ts:54`); `OPENCODE_DB` can relocate it (`:43-47`). One `message` row per message, one `part` row per content part. A legacy JSON tree `~/.local/share/opencode/storage/` (`packages/opencode/src/storage/storage.ts:224`) still exists; see section 6.

**Crush.** Per project: `<project>/.crush/crush.db` (`internal/config/config.go:25` default `.crush`; `internal/db/connect.go:93` `crush.db`). The data dir is found by walking up from cwd (`internal/config/load.go:590-593`) and can be overridden by `data_directory` (`config.go:470`). The global registry `~/.local/share/crush/projects.json` (Windows `%LOCALAPPDATA%\crush\projects.json`; `load.go:1259-1278`, `internal/projects/projects.go:14,31-33`) maps each project `path` to its `data_dir`. One `messages` row per message; parts are a JSON array in the `parts` column.

## 3. Record schema

### OpenCode (drizzle, `packages/core/src/session/sql.ts`)

`session` (`:22-66`): `id` (`ses_…`), `project_id` → `project.id`, `workspace_id`, `parent_id`, `slug`, `directory` (cwd, stored with `/` on Windows, `database/path.ts:5-8`), `path` (subdir relative to worktree), `title`, `version` (OpenCode version), `share_url`, `summary_*`, `metadata` JSON, `cost`, `tokens_*`, `revert` JSON, `permission` JSON, `agent`, `model` JSON `{id, providerID, variant?}` (`:52-56`), `time_created`, `time_updated` (epoch **milliseconds**, `database/schema.sql.ts:3-10` uses `Date.now()`), `time_compacting`, `time_archived`.

`project` (`project/sql.ts:6-18`): `id`, `worktree` (absolute repo root), `vcs`, `name`, `time_*`, `sandboxes` JSON array.

`message` (`sql.ts:68-80`, CREATE in `database/migration/20260127222353_familiar_lady_ursula.ts:22-31`): `id` (`msg_…`), `session_id`, `time_created`, `time_updated` (ms), `data` JSON = the V1 message minus `id`/`sessionID` (`session/projector.ts:77-82`). `data` fields (`packages/schema/src/v1/session.ts`):
- user (`:332-354`): `role:"user"`, `time.created` (ms), `agent`, `model:{providerID, modelID, variant?}`, `format?`, `summary?`, `system?`, `tools?`.
- assistant (`:453-485`): `role:"assistant"`, `time.{created, completed?}`, `parentID` (the user message), `modelID`, `providerID`, `mode`, `agent`, `path.{cwd, root}`, `cost`, `tokens.{input, output, reasoning, cache.{read, write}}`, `error?` (`{name, data}`), `finish?`, `variant?`.

`part` (`sql.ts:82-98`, CREATE `…ursula.ts:33-42`): `id` (`prt_…`), `message_id`, `session_id`, `time_created`, `time_updated`, `data` JSON = part minus `id`/`messageID`/`sessionID` (`projector.ts:84-87`). `data.type` discriminator (`v1/session.ts:357-370`):
- `text` (`:102-115`): `text`, `synthetic?`, `ignored?`, `time.{start,end?}`.
- `reasoning` (`:118-127`): `text`, `time.{start,end?}`.
- `tool` (`:315-322`): `callID`, `tool` (name), `state.status` ∈ `pending|running|completed|error` (`:259-302`). `state.input` (object) on all; `completed` adds `output` (string), `title`, `metadata`, `time.{start,end}`; `error` adds `error` (string), `time.{start,end}`. The tool call and its result are the **same part**, mutated in place.
- `step-start` (`:233-237`, `snapshot?`), `step-finish` (`:240-256`, `reason`, `cost`, `tokens`), `subtask` (`:204-217`, `prompt`, `description`, `agent`), `compaction` (`:195-201`), `snapshot`, `patch`, `file`, `agent`, `retry`.

**Newer V2 projection**, same DB: `session_message` (`sql.ts:119-138`): `id`, `session_id`, `type` column ∈ `agent-switched|model-switched|user|synthetic|system|shell|assistant|compaction` (`packages/schema/src/session-message.ts:200-213`), `seq`, `time_created` (ms, `projector.ts:203`), `data` JSON. Assistant `data` (`session-message.ts:165-189`): `agent`, `model.{id, providerID}`, `content[]` with `type` ∈ `text|reasoning|tool` (`:122-157`); tool items carry `id` (call id), `name`, `state.status`, `state.input`, `state.content[]` (`{type:"text",text}`), `state.error.message`, `time.{created, ran?, completed?}`. User `data`: `text`, `files?`, `agents?` (`:44-51`). Migration `20260622170816_reset_v2_session_state.ts:8-14` wipes `session_message`, `session_input`, `event` on upgrade, so `message`/`part` are the durable transcript; treat `session_message` as supplementary.

`event` (`core/src/event/sql.ts:10-25`): `aggregate_id` = session id, `seq`, `type` like `message.updated.1`, `message.part.updated.1` (`schema/src/event.ts:94-96`; names `v1/session.ts:597,613`), `data` JSON containing full message/part copies (`core/src/event.ts:336-348`). Also wiped by the reset migration.

Git branch: **not recorded** anywhere in OpenCode (grep of `branch` in schema/sql returned nothing). Role: `message.data.role`. Project path: `project.worktree`, cwd: `session.directory` / assistant `data.path.cwd`.

### Crush (`internal/db/migrations/20250424200609_initial.sql`)

`sessions` (`:4-14` + ALTERs): `id` (uuid; task sub-sessions use the tool call id, `internal/session/session.go:103,117`), `parent_session_id`, `title`, `message_count`, `prompt_tokens`, `completion_tokens`, `cost`, `updated_at`, `created_at` (epoch **seconds**, `strftime('%s','now')`, `internal/db/sql/sessions.sql:22-23`), `summary_message_id`, `todos` JSON, `channel`.

`messages` (`:47-57` + ALTERs; `internal/db/models.go:29-44`): `id` uuid (`internal/message/message.go:206`), `session_id`, `role` ∈ `assistant|user|system|tool` (`internal/message/content.go:20-27`), `parts` JSON, `model`, `provider` (`20250627000000_add_provider_to_messages.sql`), `created_at`, `updated_at`, `finished_at` (seconds, copied from the `finish` part's `time`, `message.go:435-439`), `is_summary_message`, `prism_model_id`, `prism_model_name`, `prism_*_savings`.

`parts` is `[{"type":…,"data":{…}}]` (`message.go:613-629`). Types and `data` keys (`content.go`):
- `text`: `text`, `hidden?` (`:70-74`).
- `reasoning`: `thinking`, `signature`, `thought_signature`, `tool_id`, `responses_data`, `started_at`, `finished_at` (seconds; `:55-63`).
- `tool_call`: `id`, `name`, `input` (JSON **string**), `provider_executed`, `finished` (`:109-115`).
- `tool_result`: `tool_call_id`, `name`, `content`, `data` (base64 media), `mime_type`, `metadata`, `is_error` (`:119-127`).
- `finish`: `reason` ∈ `end_turn|max_tokens|tool_use|canceled|error|content_filter|unknown`, `time` (seconds), `message?`, `details?` (`:33-49,131-136`).
- `shell_command`: `command`, `output`, `exit_code` (`:142-146`); `image_url`: `url`, `detail`; `binary`: untagged Go fields `Path`, `MIMEType`, `Data` (base64) (`:93-97`).

Other tables: `files` (session file snapshots: `path`, `content`, `version`), `read_files`, `mcp_enabled_servers`, `mcp_disabled_servers`. No project path, cwd or git branch column anywhere (grep of `branch` hit only the client/server protocol).

## 4. Joins

**OpenCode:** `session.project_id → project.id` (worktree); `message.session_id → session.id`; `part.message_id → message.id` (`part.session_id` is denormalised). Order parts by `part.id` (ids are time-ordered, `v1/session.ts:17-27`) or `time_created`. Tool call and result are one `part` row; assistant → user via `data.parentID`. `session_message` joins on `session_id`, order by `seq`.

**Crush:** `messages.session_id → sessions.id`; `sessions.parent_session_id` for sub-agents. `tool_call` parts live in the assistant message; the result is a **separate** `role='tool'` message with a `tool_result` part (`internal/agent/agent.go:1032-1038`), joined on `tool_result.data.tool_call_id = tool_call.data.id`. Project path = parent directory of the `.crush` holding the DB, or `projects.json` `projects[].path` / `data_dir`.

## 5. SQLite specifics

Both set `journal_mode=WAL` (OpenCode `database.ts:27`, also at open `sqlite.bun.ts:164`; Crush `connect.go:20`). OpenCode runs `wal_checkpoint(PASSIVE)` at startup only (`database.ts:32`); Crush uses Go defaults (auto-checkpoint at 1000 pages). Rows written since the last checkpoint live only in `-wal`, so a copy without `opencode.db-wal` / `crush.db-wal` **loses recent messages**; the collector must take `.db`, `.db-wal`, `.db-shm` together. Crush also sets `secure_delete=ON` (`connect.go:25`), so deleted rows are zeroed. Neither encrypts or compresses. Crush writes are debounced ~33 ms (`message.go:21`) and serialised on one connection (`connect.go:142`).

## 6. Format versions

**OpenCode legacy JSON** under `~/.local/share/opencode/storage/`, one file per key: `project/<projectID>.json` (`{id, vcs, worktree, time}`), `session/<projectID>/<sessionID>.json`, `message/<sessionID>/<msgID>.json`, `part/<msgID>/<partID>.json`, `session_diff/<sessionID>.json`, marker `storage/migration` (integer) (`storage.ts:63-65,81-211,224-225`). Before that, per-project `~/.local/share/opencode/project/<slug>/storage/session/{info,message,part}/…` (`storage.ts:97,139,150,165`; `packages/web/src/content/docs/troubleshooting.mdx:35-36`). JSON records carry `id`, `sessionID`, `messageID` inline (the DB `data` column strips them). The SQLite `migration` table (`database/migration.ts:30`) lists applied schema migrations; `data_migration` tracks data moves. At this commit no code imports `storage/` JSON into SQLite; `storage/` is still written for `session_diff` (`session/revert.ts:77`), so both trees coexist. `opencode import` (`cli/cmd/import.ts:196-225`) loads exported JSON into `message`/`part`.

**Crush:** goose migrations only (12 files); no JSON era, no version field, `goose_db_version` table.

## 7. Secrets to redact

OpenCode: `credential.value` JSON (`{type:"oauth", access, refresh}` or `{type:"key", key}`, `schema/src/credential.ts:16-34`), `account.access_token`/`refresh_token`, `control_account.*`, `session_share.secret`, plus the legacy file `~/.local/share/opencode/auth.json` (`auth/index.ts:10,14-35`) and `mcp-auth.json`. Crush: `crush.json` `providers.<name>.api_key` (`config.go:102`) at `~/.config/crush/`, `~/.local/share/crush/`, and `<project>/.crush/`; `reasoning.signature`/`thought_signature` are opaque provider blobs. Both: tool `input`/`output` text can contain pasted tokens.

## 8. Parser plan

Globs (home-relative): `.local/share/opencode/opencode*.db{,-wal,-shm}`, `.local/share/opencode/storage/{session,message,part,project}/**/*.json`, `.local/share/opencode/project/*/storage/session/**/*.json`. Crush: `.local/share/crush/projects.json`, `AppData/Local/crush/projects.json`, project-level `.crush/crush.db{,-wal,-shm}`.

Rows: OpenCode one per `part` (plus a `user` row per user message); Crush one per part in `parts`.

| CSV column | OpenCode | Crush |
|---|---|---|
| timestamp_utc | part `data.time.start` else `part.time_created`, ms | `messages.created_at` s; tool_call/result use `finished_at` or `finish.time` |
| session_id | `session.id` | `sessions.id` |
| project_path | `project.worktree` (fallback `session.directory`) | dir containing `.crush`, or `projects.json.path` |
| git_branch | empty | empty |
| turn_type | user msg→`user`; `text`→`assistant`; `reasoning`→`thinking`; `tool` pending/running→`tool_use`; `tool` completed/error→`tool_use` + `tool_result`; `step-*`→`system` | `user`/`assistant` text; `reasoning`→`thinking`; `tool_call`→`tool_use`; `tool_result`→`tool_result`; role `system`, `finish`/`shell_command`→`system` |
| model | `data.providerID/modelID` | `provider`/`model` (or `prism_model_id`) |
| tool_name / tool_use_id | `data.tool` / `data.callID` | `data.name` / `data.id` or `data.tool_call_id` |
| summary | text, input JSON, output or error, first 200 chars | same |

Fixture rows:

```sql
-- OpenCode opencode.db
INSERT INTO project(id,worktree,vcs,time_created,time_updated,sandboxes) VALUES('proj_a1','/home/u/repo','git',1760000000000,1760000000000,'[]');
INSERT INTO session(id,project_id,slug,directory,title,version,cost,tokens_input,tokens_output,tokens_reasoning,tokens_cache_read,tokens_cache_write,time_created,time_updated) VALUES('ses_01','proj_a1','fix-bug','/home/u/repo','Fix bug','1.2.0',0,0,0,0,0,0,1760000001000,1760000005000);
INSERT INTO message VALUES('msg_01','ses_01',1760000001000,1760000001000,'{"role":"user","time":{"created":1760000001000},"agent":"build","model":{"providerID":"anthropic","modelID":"claude-sonnet-4"}}');
INSERT INTO part VALUES('prt_01','msg_01','ses_01',1760000001000,1760000001000,'{"type":"text","text":"list files"}');
INSERT INTO message VALUES('msg_02','ses_01',1760000002000,1760000005000,'{"role":"assistant","time":{"created":1760000002000,"completed":1760000005000},"parentID":"msg_01","modelID":"claude-sonnet-4","providerID":"anthropic","mode":"build","agent":"build","path":{"cwd":"/home/u/repo","root":"/home/u/repo"},"cost":0.01,"tokens":{"input":10,"output":5,"reasoning":0,"cache":{"read":0,"write":0}}}');
INSERT INTO part VALUES('prt_02','msg_02','ses_01',1760000002000,1760000003000,'{"type":"tool","callID":"call_x1","tool":"bash","state":{"status":"completed","input":{"command":"ls"},"output":"a.txt","title":"ls","metadata":{},"time":{"start":1760000002500,"end":1760000003000}}}');
INSERT INTO credential VALUES('cred_01','anthropic','key','my key','{"type":"key","key":"sk-ant-REDACT"}',NULL,NULL,1,1760000000000,1760000000000);

-- Crush <project>/.crush/crush.db
INSERT INTO sessions(id,title,message_count,prompt_tokens,completion_tokens,cost,updated_at,created_at) VALUES('6f1c…','Fix bug',3,10,5,0.01,1760000005,1760000001);
INSERT INTO messages(id,session_id,role,parts,model,provider,created_at,updated_at,finished_at,is_summary_message) VALUES
('m1','6f1c…','user','[{"type":"text","data":{"text":"list files"}},{"type":"finish","data":{"reason":"stop","time":0}}]','claude-sonnet-4','anthropic',1760000001,1760000001,NULL,0),
('m2','6f1c…','assistant','[{"type":"tool_call","data":{"id":"call_x1","name":"bash","input":"{\"command\":\"ls\"}","provider_executed":false,"finished":true}},{"type":"finish","data":{"reason":"tool_use","time":1760000003}}]','claude-sonnet-4','anthropic',1760000002,1760000003,1760000003,0),
('m3','6f1c…','tool','[{"type":"tool_result","data":{"tool_call_id":"call_x1","name":"bash","content":"a.txt","data":"","mime_type":"","metadata":"","is_error":false}},{"type":"finish","data":{"reason":"stop","time":0}}]','','',1760000003,1760000003,NULL,0);
```
```json
{"projects":[{"path":"/home/u/repo","data_dir":"/home/u/repo/.crush","last_accessed":"2026-10-01T12:00:00Z"}]}
```

**Confidence.** High: table columns, JSON field names, timestamp units, part types, WAL, DB paths, Crush tool-result-as-separate-message, absence of git branch. Medium: which OpenCode table is authoritative over time (`session_message` is new and was reset once; `message`/`part` have been stable since the first migration). Not determined: exact byte layout of `session_message.data` for all types in a real install (no fixture DB present), whether a startup JSON→SQLite importer existed in an intermediate release (no code at this commit), and Crush `binary` part key casing in shipped builds (inferred from untagged Go struct).
