# Kilo Code transcript schema

Catalog agent: `kilo-code`. Kilo Code began as a Roo Code fork but its
current CLI, TUI and server are an OpenCode fork, so the SQLite schema in
[opencode.md](opencode.md) applies; the VS Code extension only reads
Roo-style task directories for import
([`packages/kilo-vscode/src/legacy-migration/task-store.ts:6-7`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/src/legacy-migration/task-store.ts#L6-L7)). Paths cited
are relative to the clone.

Paths, credentials and the rest of the per-user state are in
[`collectors/research/kilo-code.md`](../../collectors/research/kilo-code.md).

## 1. Source

Kilo-Org/kilocode at [`76bcfd40be616a72f4697b3041565f322245b462`](https://github.com/Kilo-Org/kilocode/commit/76bcfd40be616a72f4697b3041565f322245b462), MIT. Open
source. CLI, TUI and server in `packages/core`; VS Code extension
`kilocode.kilo-code` ([`packages/kilo-vscode/package.json:2`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/package.json#L2),[`11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/package.json#L11)).

## 2. Transcript files

XDG with no platform branching ([`packages/core/src/global.ts:3`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L3),[`12`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L12),[`22-26`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L22-L26)):
data `~/.local/share/kilo`, config `~/.config/kilo`, cache `~/.cache/kilo`,
state `~/.local/state/kilo` (fallback `<data>/state`, [`:26`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L26)). Transcripts
are SQLite: `<data>/kilo.db` on release channels, else `kilo-<channel>.db`
or a pre-existing `opencode-<channel>.db`; `KILO_DB` overrides
([`packages/core/src/database/database.ts:52-66`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/database/database.ts#L52-L66)). Legacy JSON store
`<data>/storage/session/<projectID>/<sesID>.json`,
`storage/message/<sesID>/<msgID>.json`, `storage/part/<msgID>/<prtID>.json`,
older `storage/session/info/*.json` and `storage/session/message/<ses>/*.json`,
marker `storage/migration` ([`packages/opencode/src/storage/storage.ts:65`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L65),[`140-170`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L140-L170),[`193-197`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L193-L197),[`234-236`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L234-L236)).
The VS Code globalStorage `kilocode.kilo-code/tasks/<id>/` holds only
pre-migration Roo-style files.

## 3. Record schema

V1 `message.data` and `part.data` ([`packages/schema/src/v1/session.ts`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts)):
user [`:374-400`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L374-L400) `{role:"user", time{created}, agent, model{providerID,
modelID, variant?}, system?, tools?, editorContext?, summary?}`; assistant
[`:499-535`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L499-L535) `{role:"assistant", time{created, completed?}, parentID,
modelID, providerID, mode, agent, path{cwd, root}, cost, tokens{input,
output, reasoning, cache{read, write}}, error?, finish?}`. Parts (all with
`id, sessionID, messageID` [`:80-86`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L80-L86)): `text{text, synthetic?,
time{start,end}}` [`:102`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L102), `reasoning{text, time}` [`:118`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L118), `tool{callID, tool,
state{status: pending|running|completed|error, input, output?, title?,
error?, time{start,end}}}` [`:289-362`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L289-L362), `step-start`, `step-finish{reason,
snapshot (git hash), model, cost, tokens}` [`:241-288`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L241-L288), `file`, `agent`,
`subtask`, `compaction`, `retry`, `patch`, `snapshot`.

V2 `session_message.data` ([`packages/schema/src/session-message.ts`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-message.ts)): base
`{id, time{created}}` [`:24-27`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-message.ts#L24-L27); `type` in `agent-switched, model-switched,
user{text, files, agents}, synthetic{text}, system{text}, shell{callID,
command, output, time{created, completed}}, assistant{agent, model,
content[], snapshot{start, end, files}, finish, cost, tokens, error,
time{created, completed}}, compaction{reason, summary, recent}` [`:45-213`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-message.ts#L45-L213).
Assistant `content[]`: `text{id, text}`, `reasoning{id, text, time}`,
`tool{id, name, state{status, input, content[], structured, error, result},
time{created, ran, completed}}` [`:122-158`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-message.ts#L122-L158). Times are millisecond epochs.

No git branch is recorded; `snapshot` holds commit hashes.

## 4. Joins

`session.id` ← `message.session_id` ← `part.message_id`; `session.directory`
is the cwd and `session.project_id` → `project.worktree`
([`project/sql.ts:8`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/project/sql.ts#L8)). A V1 `tool` part carries both call and result in
`state`; V2 `assistant.content[].tool.id` likewise.

## 5. SQLite stores

`kilo.db` ([`packages/core/src/session/sql.ts`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/sql.ts)): `session(id, project_id,
workspace_id, parent_id, slug, directory, path, title, version, share_url,
summary_*, metadata JSON, cost, tokens_*, revert JSON, permission JSON,
agent, model JSON{id, providerID, variant}, time_created, time_updated,
time_compacting, time_archived)` [`:24-71`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/sql.ts#L24-L71); `message(id, session_id,
time_created, time_updated, data JSON)` [`:73-90`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/sql.ts#L73-L90); `part(id, message_id,
session_id, time_*, data JSON)` [`:92-114`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/sql.ts#L92-L114); `session_message(id, session_id,
type, seq, time_*, data JSON)` [`:135-154`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/sql.ts#L135-L154); `session_input(prompt JSON)`,
`session_context_epoch(snapshot JSON)`, `todo`; `project(id, worktree, vcs,
name, sandboxes)`; `credential(value JSON)` ([`credential/sql.ts:5-14`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/credential/sql.ts#L5-L14));
`account(access_token, refresh_token)` and legacy `control_account`
([`account/sql.ts:6-39`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/account/sql.ts#L6-L39)). The projector writes V2 `session_message` and V1
`message`/`part` for every event ([`session/projector.ts:213-230`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/projector.ts#L213-L230),[`285-300`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/projector.ts#L285-L300),[`335-345`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/session/projector.ts#L335-L345)),
so either set is complete. WAL mode as in OpenCode; collect the `-wal`
sidecar.

## 6. Format versions

JSON `storage/` (two internal migrations, [`storage.ts:83-200`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L83-L200)) became SQLite
through drizzle migrations under `packages/core/src/database/migration/2026...`
(39 files); `opencode-*.db` was renamed `kilo-*.db`; `message`/`part` are
kept beside `session_message` ("legacy-writer-compat", migration
[`20260714141136`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/database/migration/20260714141136_session-message-legacy-writer-compat.ts)). Id prefixes: session `ses`, message `msg`/`msg_`, part
`prt` ([`schema/src/session-id.ts:5`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-id.ts#L5), [`v1/session.ts:17`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L17),[`23`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/v1/session.ts#L23),
[`session-message.ts:12`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/schema/src/session-message.ts#L12)). `.kilocodemodes` has no references in current
source and is legacy only.

## 7. Secrets

`auth.json` ([`packages/opencode/src/auth/index.ts:11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/auth/index.ts#L11)), `credential.value`,
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
| text | `text` or `state.title` |

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
`storage/` into SQLite ([`packages/opencode/src/storage/db.ts`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/db.ts), not traced).
