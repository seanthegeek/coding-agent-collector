# Kilo Code transcript schema

Catalog agent: `kilo-code`. Kilo Code began as a Roo Code fork but its
current CLI, TUI and server are an OpenCode fork, so the SQLite schema in
[opencode.md](opencode.md) applies; the VS Code extension only reads
Roo-style task directories for import
(`packages/kilo-vscode/src/legacy-migration/task-store.ts:6-7`). Paths cited
are relative to the clone.

## 1. Source

Kilo-Org/kilocode at `76bcfd40be616a72f4697b3041565f322245b462`, MIT. Open
source. CLI, TUI and server in `packages/core`; VS Code extension
`kilocode.kilo-code` (`packages/kilo-vscode/package.json:2,11`).

## 2. Transcript files

XDG with no platform branching (`packages/core/src/global.ts:3,12,22-26`):
data `~/.local/share/kilo`, config `~/.config/kilo`, cache `~/.cache/kilo`,
state `~/.local/state/kilo` (fallback `<data>/state`, `:26`). Transcripts
are SQLite: `<data>/kilo.db` on release channels, else `kilo-<channel>.db`
or a pre-existing `opencode-<channel>.db`; `KILO_DB` overrides
(`packages/core/src/database/database.ts:52-66`). Legacy JSON store
`<data>/storage/session/<projectID>/<sesID>.json`,
`storage/message/<sesID>/<msgID>.json`, `storage/part/<msgID>/<prtID>.json`,
older `storage/session/info/*.json` and `storage/session/message/<ses>/*.json`,
marker `storage/migration` (`packages/opencode/src/storage/storage.ts:65,140-170,193-197,234-236`).
The VS Code globalStorage `kilocode.kilo-code/tasks/<id>/` holds only
pre-migration Roo-style files.

## 3. Record schema

V1 `message.data` and `part.data` (`packages/schema/src/v1/session.ts`):
user `:374-400` `{role:"user", time{created}, agent, model{providerID,
modelID, variant?}, system?, tools?, editorContext?, summary?}`; assistant
`:499-535` `{role:"assistant", time{created, completed?}, parentID,
modelID, providerID, mode, agent, path{cwd, root}, cost, tokens{input,
output, reasoning, cache{read, write}}, error?, finish?}`. Parts (all with
`id, sessionID, messageID` `:80-86`): `text{text, synthetic?,
time{start,end}}` `:102`, `reasoning{text, time}` `:118`, `tool{callID, tool,
state{status: pending|running|completed|error, input, output?, title?,
error?, time{start,end}}}` `:289-362`, `step-start`, `step-finish{reason,
snapshot (git hash), model, cost, tokens}` `:241-288`, `file`, `agent`,
`subtask`, `compaction`, `retry`, `patch`, `snapshot`.

V2 `session_message.data` (`packages/schema/src/session-message.ts`): base
`{id, time{created}}` `:24-27`; `type` in `agent-switched, model-switched,
user{text, files, agents}, synthetic{text}, system{text}, shell{callID,
command, output, time{created, completed}}, assistant{agent, model,
content[], snapshot{start, end, files}, finish, cost, tokens, error,
time{created, completed}}, compaction{reason, summary, recent}` `:45-215`.
Assistant `content[]`: `text{id, text}`, `reasoning{id, text, time}`,
`tool{id, name, state{status, input, content[], structured, error, result},
time{created, ran, completed}}` `:122-158`. Times are millisecond epochs.

No git branch is recorded; `snapshot` holds commit hashes.

## 4. Joins

`session.id` ← `message.session_id` ← `part.message_id`; `session.directory`
is the cwd and `session.project_id` → `project.worktree`
(`project/sql.ts:8`). A V1 `tool` part carries both call and result in
`state`; V2 `assistant.content[].tool.id` likewise.

## 5. SQLite stores

`kilo.db` (`packages/core/src/session/sql.ts`): `session(id, project_id,
workspace_id, parent_id, slug, directory, path, title, version, share_url,
summary_*, metadata JSON, cost, tokens_*, revert JSON, permission JSON,
agent, model JSON{id, providerID, variant}, time_created, time_updated,
time_compacting, time_archived)` `:24-71`; `message(id, session_id,
time_created, time_updated, data JSON)` `:73-90`; `part(id, message_id,
session_id, time_*, data JSON)` `:92-114`; `session_message(id, session_id,
type, seq, time_*, data JSON)` `:135-154`; `session_input(prompt JSON)`,
`session_context_epoch(snapshot JSON)`, `todo`; `project(id, worktree, vcs,
name, sandboxes)`; `credential(value JSON)` (`credential/sql.ts:5-14`);
`account(access_token, refresh_token)` and legacy `control_account`
(`account/sql.ts:6-39`). The projector writes V2 `session_message` and V1
`message`/`part` for every event (`session/projector.ts:213-230,285-300,335-345`),
so either set is complete. WAL mode as in OpenCode; collect the `-wal`
sidecar.

## 6. Format versions

JSON `storage/` (two internal migrations, `storage.ts:83-200`) became SQLite
through drizzle migrations under `packages/core/src/database/migration/2026...`
(39 files); `opencode-*.db` was renamed `kilo-*.db`; `message`/`part` are
kept beside `session_message` ("legacy-writer-compat", migration
`20260714141136`). Id prefixes: session `ses`, message `msg`/`msg_`, part
`prt` (`schema/src/session-id.ts:5`, `v1/session.ts:17,23`,
`session-message.ts:12`). `.kilocodemodes` has no references in current
source and is legacy only.

## 7. Secrets

`auth.json` (`packages/opencode/src/auth/index.ts:11`), `credential.value`,
`account.access_token`/`refresh_token`, `control_account`, and
`session.share_url`. The database is collected unflagged like Cursor's
`state.vscdb`; the tables above are the redaction targets (issue 23).

## 8. Parser plan

Globs: `.local/share/kilo/kilo*.db`, `.local/share/kilo/opencode-*.db`,
`.local/share/kilo/storage/{session,message,part}/**/*.json`; also
`<GS>/kilocode.kilo-code/tasks/**` for pre-migration tasks, parsed with the
Roo mapping.

Rows: one per V1 `part`, or per V2 `session_message` content item.

| Column | V1 |
| --- | --- |
| timestamp_utc | `part.data.time.start` or `message.time_created` |
| session_id | `session_id` (`parent_id` for subtasks) |
| project_path | `session.directory` or `project.worktree` |
| git_branch | empty |
| turn_type | text → by role; reasoning → thinking; tool → tool_use plus tool_result; step-*/compaction → system |
| model | `assistant.modelID` |
| tool_name, tool_use_id | `part.data.tool`, `callID` |
| summary | `text` or `state.title` |

Fixtures:

```json
{"_table":"session","record":{"id":"ses_01JAX","project_id":"prj_01JAX","parent_id":null,"slug":"fix-tests","directory":"/home/u/proj","title":"fix tests","version":"1.0.0","agent":"build","model":"{\"id\":\"claude-sonnet-4-5\",\"providerID\":\"anthropic\"}","time_created":1760000000000,"time_updated":1760000005000}}
{"_table":"message","record":{"id":"msg_01JAXA","session_id":"ses_01JAX","time_created":1760000002000,"data":"{\"role\":\"assistant\",\"parentID\":\"msg_01JAXU\",\"modelID\":\"claude-sonnet-4-5\",\"providerID\":\"anthropic\",\"mode\":\"build\",\"agent\":\"build\",\"path\":{\"cwd\":\"/home/u/proj\",\"root\":\"/home/u/proj\"},\"cost\":0.0041,\"tokens\":{\"input\":1200,\"output\":80,\"reasoning\":0,\"cache\":{\"read\":900,\"write\":0}},\"time\":{\"created\":1760000002000,\"completed\":1760000003000}}"}}
{"_table":"part","record":{"id":"prt_01JAXT","message_id":"msg_01JAXA","session_id":"ses_01JAX","time_created":1760000002500,"data":"{\"type\":\"tool\",\"callID\":\"call_1\",\"tool\":\"bash\",\"state\":{\"status\":\"completed\",\"input\":{\"command\":\"pytest -q\"},\"output\":\"3 passed\",\"title\":\"pytest -q\",\"metadata\":{},\"time\":{\"start\":1760000002500,\"end\":1760000003000}}}"}}
{"_table":"session_message","record":{"id":"msg_01JAXB","session_id":"ses_01JAX","type":"assistant","seq":4,"time_created":1760000002000,"data":"{\"agent\":\"build\",\"model\":{\"providerID\":\"anthropic\",\"modelID\":\"claude-sonnet-4-5\"},\"content\":[{\"type\":\"tool\",\"id\":\"call_1\",\"name\":\"bash\",\"state\":{\"status\":\"completed\",\"input\":{\"command\":\"pytest -q\"},\"content\":[{\"type\":\"text\",\"text\":\"3 passed\"}],\"structured\":{}},\"time\":{\"created\":1760000002500,\"completed\":1760000003000}}],\"time\":{\"created\":1760000002000,\"completed\":1760000003000}}"}}
```

Confidence. High: drizzle columns and V1/V2 struct fields (read from
source). Medium: V2 `session_message.data` serialised key order and the
`Model.Ref` shape. Not determined: the code path that imports legacy JSON
`storage/` into SQLite (`packages/opencode/src/storage/db.ts`, not traced).
