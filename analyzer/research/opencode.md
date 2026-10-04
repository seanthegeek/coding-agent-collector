# OpenCode transcript schema

Catalog agent: `opencode`. Researched together with Crush, which began as
an OpenCode fork but no longer shares any storage code
([crush.md](crush.md)); Kilo Code's current store is an OpenCode fork and
shares this schema ([kilo-code.md](kilo-code.md)). Paths cited are relative
to the clone.

Paths, credentials and the rest of the per-user state are in
[`collectors/research/opencode.md`](../../collectors/research/opencode.md).

## 1. Source

sst/opencode at [`907b3bc518fa48e90e8ec24dd327d13eee71c36c`](https://github.com/sst/opencode/commit/907b3bc518fa48e90e8ec24dd327d13eee71c36c), MIT. Open
source. The schema has moved out of `packages/opencode` into
`packages/core` (tables) and `packages/schema` (JSON shapes).

## 2. Transcript stores

One SQLite file for all projects: `~/.local/share/opencode/opencode.db`
([`packages/core/src/global.ts:3`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/global.ts#L3),[`11`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/global.ts#L11) uses `xdg-basedir` with no platform
branching, so the same path on macOS and Windows;
[`packages/core/src/database/database.ts:49-54`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/database.ts#L49-L54)). Non-release channels use
`opencode-<channel>.db` in the same directory ([`database.ts:54`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/database.ts#L54));
`OPENCODE_DB` can relocate it ([`:43-47`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/database.ts#L43-L47)). One `message` row per message, one
`part` row per content part. A legacy JSON tree
`~/.local/share/opencode/storage/` ([`packages/opencode/src/storage/storage.ts:224`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L224))
still exists (section 6).

## 3. Record schema

Drizzle tables in [`packages/core/src/session/sql.ts`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts).

`session` ([`:22-66`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts#L22-L66)): `id` (`ses_...`), `project_id` → `project.id`,
`workspace_id`, `parent_id`, `slug`, `directory` (cwd, stored with `/` on
Windows, [`database/path.ts:5-8`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/path.ts#L5-L8)), `path`, `title`, `version` (OpenCode
version), `share_url`, `summary_*`, `metadata` JSON, `cost`, `tokens_*`,
`revert` JSON, `permission` JSON, `agent`, `model` JSON `{id, providerID,
variant?}` ([`:52-56`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts#L52-L56)), `time_created`, `time_updated` (epoch milliseconds,
[`database/schema.sql.ts:3-10`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/schema.sql.ts#L3-L10) uses `Date.now()`), `time_compacting`,
`time_archived`.

`project` ([`project/sql.ts:6-18`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/project/sql.ts#L6-L18)): `id`, `worktree` (absolute repository
root), `vcs`, `name`, `time_*`, `sandboxes` JSON array.

`message` ([`sql.ts:68-80`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts#L68-L80); CREATE in
[`database/migration/20260127222353_familiar_lady_ursula.ts:22-31`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/migration/20260127222353_familiar_lady_ursula.ts#L22-L31)): `id`
(`msg_...`), `session_id`, `time_created`, `time_updated` (ms), `data` JSON =
the V1 message minus `id` and `sessionID` ([`session/projector.ts:77-82`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/projector.ts#L77-L82)).
`data` ([`packages/schema/src/v1/session.ts`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts)): user ([`:332-354`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L332-L354))
`role:"user"`, `time.created` (ms), `agent`, `model:{providerID, modelID,
variant?}`, `format?`, `summary?`, `system?`, `tools?`; assistant
([`:453-485`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L453-L485)) `role:"assistant"`, `time.{created, completed?}`, `parentID`
(the user message), `modelID`, `providerID`, `mode`, `agent`, `path.{cwd,
root}`, `cost`, `tokens.{input, output, reasoning, cache.{read, write}}`,
`error?` (`{name, data}`), `finish?`, `variant?`.

`part` ([`sql.ts:82-98`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts#L82-L98); CREATE [`...ursula.ts:33-42`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/migration/20260127222353_familiar_lady_ursula.ts#L33-L42)): `id` (`prt_...`),
`message_id`, `session_id`, `time_created`, `time_updated`, `data` JSON = the
part minus `id`, `messageID` and `sessionID` ([`projector.ts:84-87`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/projector.ts#L84-L87)).
`data.type` discriminator ([`v1/session.ts:357-370`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L357-L370)): `text` ([`:102-115`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L102-L115):
`text`, `synthetic?`, `ignored?`, `time.{start,end?}`); `reasoning`
([`:118-127`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L118-L127): `text`, `time.{start,end?}`); `tool` ([`:315-322`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L315-L322): `callID`,
`tool` (name), `state.status` in `pending|running|completed|error`
([`:259-302`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L259-L302)), `state.input` on all, `completed` adds `output`, `title`,
`metadata`, `time.{start,end}`, `error` adds `error`, `time.{start,end}`);
the tool call and its result are the same part, mutated in place;
`step-start` ([`:233-237`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L233-L237), `snapshot?`), `step-finish` ([`:240-256`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L240-L256), `reason`,
`cost`, `tokens`), `subtask` ([`:204-217`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L204-L217), `prompt`, `description`, `agent`),
`compaction` ([`:195-201`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L195-L201)), `snapshot`, `patch`, `file`, `agent`, `retry`.

Newer V2 projection in the same database: `session_message`
([`sql.ts:119-138`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/sql.ts#L119-L138)): `id`, `session_id`, `type` in
`agent-switched|model-switched|user|synthetic|system|shell|assistant|compaction`
([`packages/schema/src/session-message.ts:200-213`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/session-message.ts#L200-L213)), `seq`, `time_created`
(ms, [`projector.ts:203`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/session/projector.ts#L203)), `data` JSON. Assistant `data`
([`session-message.ts:165-189`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/session-message.ts#L165-L189)): `agent`, `model.{id, providerID}`,
`content[]` with `type` in `text|reasoning|tool` ([`:122-157`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/session-message.ts#L122-L157)); tool items
carry `id`, `name`, `state.status`, `state.input`, `state.content[]`
(`{type:"text",text}`), `state.error.message`, `time.{created, ran?,
completed?}`. User `data`: `text`, `files?`, `agents?` ([`:44-51`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/session-message.ts#L44-L51)). Migration
[`20260622170816_reset_v2_session_state.ts:8-14`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/migration/20260622170816_reset_v2_session_state.ts#L8-L14) wipes `session_message`,
`session_input` and `event` on upgrade, so `message`/`part` are the durable
transcript; treat `session_message` as supplementary.

`event` ([`core/src/event/sql.ts:10-25`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/event/sql.ts#L10-L25)): `aggregate_id` = session id, `seq`,
`type` such as `message.updated.1` and `message.part.updated.1`
([`schema/src/event.ts:94-96`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/event.ts#L94-L96)), `data` JSON with full message or part copies
([`core/src/event.ts:336-348`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/event.ts#L336-L348)). Also wiped by the reset migration.

Git branch is not recorded anywhere. Role: `message.data.role`. Project
path: `project.worktree`; cwd: `session.directory` or assistant
`data.path.cwd`.

## 4. Joins

`session.project_id → project.id` (worktree); `message.session_id →
session.id`; `part.message_id → message.id` (`part.session_id` is
denormalised). Order parts by `part.id` (ids are time-ordered,
[`v1/session.ts:17-27`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/v1/session.ts#L17-L27)) or `time_created`. Tool call and result are one `part`
row; assistant → user through `data.parentID`. `session_message` joins on
`session_id`, ordered by `seq`.

## 5. SQLite specifics

`journal_mode=WAL` ([`database.ts:27`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/database.ts#L27), also at open [`sqlite.bun.ts:164`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/sqlite.bun.ts#L164));
`wal_checkpoint(PASSIVE)` runs at startup only ([`database.ts:32`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/database.ts#L32)). Rows
written since the last checkpoint live only in `opencode.db-wal`, so a copy
without the sidecar loses recent messages. No encryption or compression.

## 6. Format versions

Legacy JSON under `~/.local/share/opencode/storage/`, one file per key:
`project/<projectID>.json` (`{id, vcs, worktree, time}`),
`session/<projectID>/<sessionID>.json`, `message/<sessionID>/<msgID>.json`,
`part/<msgID>/<partID>.json`, `session_diff/<sessionID>.json`, marker
`storage/migration` (integer) ([`storage.ts:63-65`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L63-L65),[`81-211`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L81-L211),[`224-225`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L224-L225)). Before
that, per-project `~/.local/share/opencode/project/<slug>/storage/session/{info,message,part}/...`
([`storage.ts:97`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L97),[`139`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L139),[`150`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L150),[`165`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/storage/storage.ts#L165); [`packages/web/src/content/docs/troubleshooting.mdx:35-36`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/web/src/content/docs/troubleshooting.mdx#L35-L36)).
JSON records carry `id`, `sessionID` and `messageID` inline (the database
`data` column strips them). The SQLite `migration` table
([`database/migration.ts:30`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/core/src/database/migration.ts#L30)) lists applied schema migrations;
`data_migration` tracks data moves. At this commit no code imports
`storage/` JSON into SQLite; `storage/` is still written for `session_diff`
([`session/revert.ts:77`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/session/revert.ts#L77)), so both trees coexist. `opencode import`
([`cli/cmd/import.ts:196-225`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/cli/cmd/import.ts#L196-L225)) loads exported JSON into `message`/`part`.

## 7. Secrets

`credential.value` JSON (`{type:"oauth", access, refresh}` or `{type:"key",
key}`, [`schema/src/credential.ts:16-34`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/schema/src/credential.ts#L16-L34)), `account.access_token` and
`refresh_token`, `control_account.*`, `session_share.secret`, plus the legacy
files `~/.local/share/opencode/auth.json` ([`auth/index.ts:10`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/auth/index.ts#L10),[`14-35`](https://github.com/sst/opencode/blob/907b3bc518fa48e90e8ec24dd327d13eee71c36c/packages/opencode/src/auth/index.ts#L14-L35)) and
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
| text | text, input JSON, output or error |

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
