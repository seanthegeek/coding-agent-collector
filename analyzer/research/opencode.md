# OpenCode transcript schema

Catalog agent: `opencode`. Researched together with Crush, which began as
an OpenCode fork but no longer shares any storage code
([crush.md](crush.md)); Kilo Code's current store is an OpenCode fork and
shares this schema ([kilo-code.md](kilo-code.md)). Paths cited are relative
to the clone.

## 1. Source

sst/opencode at `907b3bc518fa48e90e8ec24dd327d13eee71c36c`, MIT. Open
source. The schema has moved out of `packages/opencode` into
`packages/core` (tables) and `packages/schema` (JSON shapes).

## 2. Transcript stores

One SQLite file for all projects: `~/.local/share/opencode/opencode.db`
(`packages/core/src/global.ts:3,11` uses `xdg-basedir` with no platform
branching, so the same path on macOS and Windows;
`packages/core/src/database/database.ts:49-54`). Non-release channels use
`opencode-<channel>.db` in the same directory (`database.ts:54`);
`OPENCODE_DB` can relocate it (`:43-47`). One `message` row per message, one
`part` row per content part. A legacy JSON tree
`~/.local/share/opencode/storage/` (`packages/opencode/src/storage/storage.ts:224`)
still exists (section 6).

## 3. Record schema

Drizzle tables in `packages/core/src/session/sql.ts`.

`session` (`:22-66`): `id` (`ses_...`), `project_id` → `project.id`,
`workspace_id`, `parent_id`, `slug`, `directory` (cwd, stored with `/` on
Windows, `database/path.ts:5-8`), `path`, `title`, `version` (OpenCode
version), `share_url`, `summary_*`, `metadata` JSON, `cost`, `tokens_*`,
`revert` JSON, `permission` JSON, `agent`, `model` JSON `{id, providerID,
variant?}` (`:52-56`), `time_created`, `time_updated` (epoch milliseconds,
`database/schema.sql.ts:3-10` uses `Date.now()`), `time_compacting`,
`time_archived`.

`project` (`project/sql.ts:6-18`): `id`, `worktree` (absolute repository
root), `vcs`, `name`, `time_*`, `sandboxes` JSON array.

`message` (`sql.ts:68-80`; CREATE in
`database/migration/20260127222353_familiar_lady_ursula.ts:22-31`): `id`
(`msg_...`), `session_id`, `time_created`, `time_updated` (ms), `data` JSON =
the V1 message minus `id` and `sessionID` (`session/projector.ts:77-82`).
`data` (`packages/schema/src/v1/session.ts`): user (`:332-354`)
`role:"user"`, `time.created` (ms), `agent`, `model:{providerID, modelID,
variant?}`, `format?`, `summary?`, `system?`, `tools?`; assistant
(`:453-485`) `role:"assistant"`, `time.{created, completed?}`, `parentID`
(the user message), `modelID`, `providerID`, `mode`, `agent`, `path.{cwd,
root}`, `cost`, `tokens.{input, output, reasoning, cache.{read, write}}`,
`error?` (`{name, data}`), `finish?`, `variant?`.

`part` (`sql.ts:82-98`; CREATE `...ursula.ts:33-42`): `id` (`prt_...`),
`message_id`, `session_id`, `time_created`, `time_updated`, `data` JSON = the
part minus `id`, `messageID` and `sessionID` (`projector.ts:84-87`).
`data.type` discriminator (`v1/session.ts:357-370`): `text` (`:102-115`:
`text`, `synthetic?`, `ignored?`, `time.{start,end?}`); `reasoning`
(`:118-127`: `text`, `time.{start,end?}`); `tool` (`:315-322`: `callID`,
`tool` (name), `state.status` in `pending|running|completed|error`
(`:259-302`), `state.input` on all, `completed` adds `output`, `title`,
`metadata`, `time.{start,end}`, `error` adds `error`, `time.{start,end}`);
the tool call and its result are the same part, mutated in place;
`step-start` (`:233-237`, `snapshot?`), `step-finish` (`:240-256`, `reason`,
`cost`, `tokens`), `subtask` (`:204-217`, `prompt`, `description`, `agent`),
`compaction` (`:195-201`), `snapshot`, `patch`, `file`, `agent`, `retry`.

Newer V2 projection in the same database: `session_message`
(`sql.ts:119-138`): `id`, `session_id`, `type` in
`agent-switched|model-switched|user|synthetic|system|shell|assistant|compaction`
(`packages/schema/src/session-message.ts:200-213`), `seq`, `time_created`
(ms, `projector.ts:203`), `data` JSON. Assistant `data`
(`session-message.ts:165-189`): `agent`, `model.{id, providerID}`,
`content[]` with `type` in `text|reasoning|tool` (`:122-157`); tool items
carry `id`, `name`, `state.status`, `state.input`, `state.content[]`
(`{type:"text",text}`), `state.error.message`, `time.{created, ran?,
completed?}`. User `data`: `text`, `files?`, `agents?` (`:44-51`). Migration
`20260622170816_reset_v2_session_state.ts:8-14` wipes `session_message`,
`session_input` and `event` on upgrade, so `message`/`part` are the durable
transcript; treat `session_message` as supplementary.

`event` (`core/src/event/sql.ts:10-25`): `aggregate_id` = session id, `seq`,
`type` such as `message.updated.1` and `message.part.updated.1`
(`schema/src/event.ts:94-96`), `data` JSON with full message or part copies
(`core/src/event.ts:336-348`). Also wiped by the reset migration.

Git branch is not recorded anywhere. Role: `message.data.role`. Project
path: `project.worktree`; cwd: `session.directory` or assistant
`data.path.cwd`.

## 4. Joins

`session.project_id → project.id` (worktree); `message.session_id →
session.id`; `part.message_id → message.id` (`part.session_id` is
denormalised). Order parts by `part.id` (ids are time-ordered,
`v1/session.ts:17-27`) or `time_created`. Tool call and result are one `part`
row; assistant → user through `data.parentID`. `session_message` joins on
`session_id`, ordered by `seq`.

## 5. SQLite specifics

`journal_mode=WAL` (`database.ts:27`, also at open `sqlite.bun.ts:164`);
`wal_checkpoint(PASSIVE)` runs at startup only (`database.ts:32`). Rows
written since the last checkpoint live only in `opencode.db-wal`, so a copy
without the sidecar loses recent messages. No encryption or compression.

## 6. Format versions

Legacy JSON under `~/.local/share/opencode/storage/`, one file per key:
`project/<projectID>.json` (`{id, vcs, worktree, time}`),
`session/<projectID>/<sessionID>.json`, `message/<sessionID>/<msgID>.json`,
`part/<msgID>/<partID>.json`, `session_diff/<sessionID>.json`, marker
`storage/migration` (integer) (`storage.ts:63-65,81-211,224-225`). Before
that, per-project `~/.local/share/opencode/project/<slug>/storage/session/{info,message,part}/...`
(`storage.ts:97,139,150,165`; `packages/web/src/content/docs/troubleshooting.mdx:35-36`).
JSON records carry `id`, `sessionID` and `messageID` inline (the database
`data` column strips them). The SQLite `migration` table
(`database/migration.ts:30`) lists applied schema migrations;
`data_migration` tracks data moves. At this commit no code imports
`storage/` JSON into SQLite; `storage/` is still written for `session_diff`
(`session/revert.ts:77`), so both trees coexist. `opencode import`
(`cli/cmd/import.ts:196-225`) loads exported JSON into `message`/`part`.

## 7. Secrets

`credential.value` JSON (`{type:"oauth", access, refresh}` or `{type:"key",
key}`, `schema/src/credential.ts:16-34`), `account.access_token` and
`refresh_token`, `control_account.*`, `session_share.secret`, plus the legacy
files `~/.local/share/opencode/auth.json` (`auth/index.ts:10,14-35`) and
`mcp-auth.json`. Tool `input` and `output` text can contain pasted tokens.

## 8. Parser plan

Globs: `.local/share/opencode/opencode*.db{,-wal,-shm}`,
`.local/share/opencode/storage/{session,message,part,project}/**/*.json`,
`.local/share/opencode/project/*/storage/session/**/*.json`.

Rows: one per `part`, plus a `user` row per user message.

| Column | Source |
| --- | --- |
| timestamp_utc | part `data.time.start`, else `part.time_created` (ms) |
| session_id | `session.id` |
| project_path | `project.worktree`, fallback `session.directory` |
| git_branch | empty |
| turn_type | user message → user; `text` → assistant; `reasoning` → thinking; `tool` pending/running → tool_use; `tool` completed/error → tool_use plus tool_result; `step-*` → system |
| model | `data.providerID/modelID` |
| tool_name, tool_use_id | `data.tool`, `data.callID` |
| summary | text, input JSON, output or error |

Fixture rows:

```sql
INSERT INTO project(id,worktree,vcs,time_created,time_updated,sandboxes) VALUES('proj_a1','/home/u/repo','git',1760000000000,1760000000000,'[]');
INSERT INTO session(id,project_id,slug,directory,title,version,cost,tokens_input,tokens_output,tokens_reasoning,tokens_cache_read,tokens_cache_write,time_created,time_updated) VALUES('ses_01','proj_a1','fix-bug','/home/u/repo','Fix bug','1.2.0',0,0,0,0,0,0,1760000001000,1760000005000);
INSERT INTO message VALUES('msg_01','ses_01',1760000001000,1760000001000,'{"role":"user","time":{"created":1760000001000},"agent":"build","model":{"providerID":"anthropic","modelID":"claude-sonnet-4"}}');
INSERT INTO part VALUES('prt_01','msg_01','ses_01',1760000001000,1760000001000,'{"type":"text","text":"list files"}');
INSERT INTO message VALUES('msg_02','ses_01',1760000002000,1760000005000,'{"role":"assistant","time":{"created":1760000002000,"completed":1760000005000},"parentID":"msg_01","modelID":"claude-sonnet-4","providerID":"anthropic","mode":"build","agent":"build","path":{"cwd":"/home/u/repo","root":"/home/u/repo"},"cost":0.01,"tokens":{"input":10,"output":5,"reasoning":0,"cache":{"read":0,"write":0}}}');
INSERT INTO part VALUES('prt_02','msg_02','ses_01',1760000002000,1760000003000,'{"type":"tool","callID":"call_x1","tool":"bash","state":{"status":"completed","input":{"command":"ls"},"output":"a.txt","title":"ls","metadata":{},"time":{"start":1760000002500,"end":1760000003000}}}');
INSERT INTO credential VALUES('cred_01','anthropic','key','my key','{"type":"key","key":"sk-ant-REDACT"}',NULL,NULL,1,1760000000000,1760000000000);
```

Confidence. High: table columns, JSON field names, timestamp units, part
types, WAL, paths, absence of git branch. Medium: which table is
authoritative over time (`session_message` is new and was reset once;
`message`/`part` have been stable since the first migration). Not
determined: exact byte layout of `session_message.data` for all types in a
real install; whether an intermediate release had a startup JSON to SQLite
importer.
