# Ollama transcript schema

Catalog agent: `ollama`. Ollama is a local model server, a terminal REPL
(`ollama run`), a launcher for other agents (`ollama launch`) and, on macOS
and Windows only, a desktop chat app. Only the desktop app keeps
transcripts, in one SQLite database. The REPL keeps a prompt history
without times. The server keeps nothing. Paths, credentials and exclusions
are in
[`collectors/research/ollama.md`](../../collectors/research/ollama.md).

## 1. Source

ollama/ollama at tag `v0.35.1`, commit
[`b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce`](https://github.com/ollama/ollama/commit/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce)
(2026-10-01), the latest release and the version installed on the
workstation used for the local check below. MIT, Go. The code was only
read, never built or run. The SQLite driver is mattn/go-sqlite3 v1.14.24
([`go.mod:12`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/go.mod#L12)), read at
[`846fea6c1443e8cc366fc1966fe078d7f825f6a9`](https://github.com/mattn/go-sqlite3/commit/846fea6c1443e8cc366fc1966fe078d7f825f6a9).
The HTTP router is gin v1.10.0 ([`go.mod:8`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/go.mod#L8)), read at
[`75ccf94d605a05fe24817fc2f166f6f2959d5cea`](https://github.com/gin-gonic/gin/commit/75ccf94d605a05fe24817fc2f166f6f2959d5cea).
The collector document cites
[`42e911bc3d05798cad729cb474bf62f378cb2e26`](https://github.com/ollama/ollama/commit/42e911bc3d05798cad729cb474bf62f378cb2e26),
two commits after `v0.35.1` that change only one documentation page, so
its line numbers hold for this release.

What a reader with an older install sees differently, by the release
that introduced the change (each is described at `v0.35.1` in the section
that covers it):

- `v0.31.2` to `v0.34.0` shipped a built-in agent that replaced the
  `ollama run --experimental` loop and was removed before `v0.34.1`
  (section 2). It kept no transcript.
- `v0.32.0` renamed the `codex-app` integration to `chatgpt`; `v0.32.11`
  added `muse` and `dsh` (DeepSeek Harness); `v0.33.0` added the
  per-integration `automode` key; `v0.34.0` added the Codex desktop proxy
  and its `logs/codex-proxy.log`; `v0.34.2` added the onboarding marker
  (section 7).
- The desktop database went from schema version 16 to 17 in `v0.32.15`,
  18 in `v0.33.0` and 19 in `v0.34.0`. Each step adds one `settings`
  column; the transcript tables did not change (section 3).
- The saved REPL session layer moved from `server/create.go` to
  `create/manifest.go`, same media type and content.

## 2. Transcript stores

| Store | Path | Written by | Unit |
| --- | --- | --- | --- |
| Desktop chat database | macOS `Library/Application Support/Ollama/db.sqlite`, Windows `AppData/Local/Ollama/db.sqlite`, plus `-wal` and `-shm` | the desktop app only ([`internal/onboarding/app_state.go:26-37`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/internal/onboarding/app_state.go#L26-L37)); the store package is built only for Windows and macOS ([`app/store/database.go:1`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1)) | `chats` row = conversation, `messages` row = one message |
| REPL prompt history | `.ollama/history` | `ollama run` interactive mode, as the invoking user ([`readline/history.go:40-53`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/history.go#L40-L53)) | one line per entered input, last 100 kept |
| Saved REPL session | a model layer `application/vnd.ollama.image.messages` under the server's `models/blobs` | only on an explicit `/save <model>` in the REPL ([`cmd/interactive.go:254-277`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/interactive.go#L254-L277), [`create/manifest.go:252-263`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/create/manifest.go#L252-L263)) | a JSON array of `api.Message` |
| Launch state | `.ollama/config.json`, `.ollama/backup/`, `.ollama/launch/` | `ollama launch` | configuration only, see section 7 |

Linux has no desktop app and therefore no `db.sqlite`; this could not be
checked against a real database here. Before `v0.34.2` the store's default
path on any other OS was `.ollama/db.sqlite`, but the package does not
build there. The saved REPL session lives in the models directory of the
server process (for a systemd install,
`/usr/share/ollama/.ollama/models`). The collector keeps its manifest
under `models/manifests` but excludes the message layer with the weights
(`.ollama/models/blobs`), so the saved messages are a manual follow-up,
not a parser input.

`v0.35.1` has no agent loop of its own: `ollama run` is the REPL above.
Older releases had one. Up to `v0.31.1`, `ollama run --experimental` ran
an agent loop with a bash tool that persisted nothing but the readline
history. From `v0.31.2` to `v0.34.0`, a built-in agent with bash and file
tools replaced it; it was removed in commit
[`c16bf9892a560a11c208618968966246e485540c`](https://github.com/ollama/ollama/commit/c16bf9892a560a11c208618968966246e485540c)
(2026-09-11), first absent from `v0.34.1`. At its last state, commit
[`b68b112bd8868d6278250d7d4bdfafa5cbf035c8`](https://github.com/ollama/ollama/commit/b68b112bd8868d6278250d7d4bdfafa5cbf035c8),
its prompt history was rebuilt in memory from the session's messages
([`cmd/tui/chat/input.go:375-383`](https://github.com/ollama/ollama/blob/b68b112bd8868d6278250d7d4bdfafa5cbf035c8/cmd/tui/chat/input.go#L375-L383)) and
its only writes were skills under `.ollama/skills` (or
`$XDG_CONFIG_HOME/ollama/skills`,
[`agent/skills.go:80-92`](https://github.com/ollama/ollama/blob/b68b112bd8868d6278250d7d4bdfafa5cbf035c8/agent/skills.go#L80-L92)), a temporary
working-directory file for the bash tool
([`agent/tools/bash.go:85`](https://github.com/ollama/ollama/blob/b68b112bd8868d6278250d7d4bdfafa5cbf035c8/agent/tools/bash.go#L85)) and, on an
explicit `/save <file>`, the raw request JSON in the current working
directory ([`cmd/tui/chat/debug.go:28-48`](https://github.com/ollama/ollama/blob/b68b112bd8868d6278250d7d4bdfafa5cbf035c8/cmd/tui/chat/debug.go#L28-L48)).
There is no session store from those releases to parse.

## 3. Record schema

### `db.sqlite`

Created by `database.init`, schema version 19
([`database.go:17`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L17),[`64-155`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L64-L155)).
Tables a parser needs:

```sql
CREATE TABLE chats (
  id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, browser_state TEXT);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL DEFAULT '', thinking TEXT NOT NULL DEFAULT '',
  stream BOOLEAN NOT NULL DEFAULT 0, model_name TEXT,
  model_cloud BOOLEAN, model_ollama_host BOOLEAN,           -- deprecated
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  thinking_time_start TIMESTAMP, thinking_time_end TIMESTAMP, tool_result TEXT,
  FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE);
CREATE TABLE tool_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL, type TEXT NOT NULL,
  function_name TEXT NOT NULL, function_arguments TEXT NOT NULL, function_result TEXT,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE);
CREATE TABLE attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL,
  filename TEXT NOT NULL, data BLOB NOT NULL,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE);
CREATE TABLE users (name TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
  plan TEXT NOT NULL DEFAULT '', cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);
```

`settings` is a single row (`id = 1`) holding `device_id`, `working_dir`,
`selected_model`, `schema_version`, `onboarding_version`,
`claude_desktop_used`, `codex_desktop_used` and UI preferences
([`database.go:65-95`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L65-L95)). Migrations 16 to
19 add only `onboarding_version`, `claude_desktop_used` and
`codex_desktop_used` to `settings`
([`database.go:563-604`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L563-L604)); a database
last opened by a release before `v0.34.0` has a lower `schema_version` and
lacks those columns, with the same transcript tables. A parser should not
require any `settings` column.

- `chats.id`: a UUIDv7 string created when the UI posts to chat `new`
  ([`app/ui/ui.go:717-726`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L717-L726)). `chats.title` is set
  by the UI ([`ui.go:1404`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1404)). `browser_state` is
  JSON for the built-in browser tool's pages.
- `messages.role`: `user`, `assistant` or `tool`; `system` is accepted when
  replayed but the UI does not create one
  ([`ui.go:805`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L805),[`836`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L836),[`1113`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1113),[`1173`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1173),[`1889-1918`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1889-L1918)).
- `messages.content`: the text. For a `tool` row it is the text sent back to
  the model, falling back to the JSON result
  ([`ui.go:1162-1175`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1162-L1175)); a failed tool writes
  `Error: <err>` ([`ui.go:1111-1118`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1111-L1118)).
- `messages.thinking`: reasoning text accumulated from the stream
  ([`ui.go:1268`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1268)), with
  `thinking_time_start`/`thinking_time_end`.
- `messages.model_name`: the model chosen in the UI, NULL when empty
  ([`database.go:1044-1047`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1044-L1047)).
- `messages.tool_result`: JSON of the tool's structured result on `tool`
  rows, or the JSON `null` when the browser tool ran
  ([`ui.go:1140-1161`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1140-L1161); marshalled at
  [`database.go:1049-1056`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1049-L1056)).
- `tool_calls`: one row per call on the `assistant` message that requested
  it. `type` is `function`, `function_arguments` is the arguments as a JSON
  string ([`ui.go:1083-1092`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1083-L1092);
  [`store.go:90-99`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L90-L99)). `function_result` is
  written only when `Function.Result` is set
  ([`database.go:1187-1211`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1187-L1211)), which
  the UI never does, so expect NULL.
- The tools the desktop app can run are web search, web fetch and the
  browser tools (`browser.search`, `browser.open`, `browser.find`)
  ([`ui.go:946-952`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L946-L952)); there is no shell or
  file tool.
- `attachments`: user-supplied files as BLOBs on the `user` message
  ([`database.go:1178-1185`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1178-L1185)).

Sensitive columns: `users.name`, `users.email` and `users.plan` identify
the Ollama account ([`database.go:1383-1397`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1383-L1397));
`attachments.data` holds whole user files; `settings.device_id` is a
stable device identifier. The parser must not emit any of them in full: an
attachment becomes its `filename` and byte length, and the `users` table
is not read.

### `.ollama/history`

Plain text, one entry per line, no header, no timestamps, no working
directory, no escaping. `Save` writes every buffered entry with
`fmt.Fprintln` to `history.tmp` and renames it over the file
([`history.go:125-150`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/history.go#L125-L150)); only the last
100 entries are kept ([`history.go:24-31`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/history.go#L24-L31),[`92-99`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/history.go#L92-L99)).
Each line submitted at the prompt is added, including slash commands such
as `/bye` and `/set` ([`readline/readline.go:317-325`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/readline.go#L317-L325)).
A pasted multi-line block is joined with `\n` into one entry
([`readline.go:319-322`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/readline.go#L319-L322)) and so is
written as several physical lines; a `"""` block arrives line by line from
the prompt, so each of its lines is a separate entry
([`cmd/interactive.go:171-199`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/interactive.go#L171-L199)). On load,
lines are trimmed and empty ones skipped
([`history.go:62-78`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/readline/history.go#L62-L78)), so the file cannot
tell a multi-line prompt from several prompts. `OLLAMA_NOHISTORY` or
`/set nohistory` stops saving ([`envconfig/config.go:223-224`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/envconfig/config.go#L223-L224);
[`cmd/interactive.go:128-130`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/interactive.go#L128-L130),[`288-295`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/interactive.go#L288-L295)).
The history is the invoking user's, written from `os.UserHomeDir()`,
whatever account runs the server. `readline/history.go` and
`readline/readline.go` are unchanged since `v0.30.7`.

## 4. Timestamps

- `db.sqlite`: `created_at`, `updated_at`, `thinking_time_*` and
  `chats.created_at` are bound from Go `time.Time` values made with
  `time.Now()` ([`store.go:65-73`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L65-L73),[`115-122`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L115-L122)).
  go-sqlite3 binds a `time.Time` as text in its first format,
  `2006-01-02 15:04:05.999999999-07:00`
  ([`sqlite3.go:228-232`](https://github.com/mattn/go-sqlite3/blob/846fea6c1443e8cc366fc1966fe078d7f825f6a9/sqlite3.go#L228-L232),[`1979-1981`](https://github.com/mattn/go-sqlite3/blob/846fea6c1443e8cc366fc1966fe078d7f825f6a9/sqlite3.go#L1979-L1981)):
  local time with a numeric offset, fractional seconds with trailing zeros
  trimmed, for example `2026-03-01 09:00:00.123456-08:00`. Convert with the
  offset. A `CURRENT_TIMESTAMP` default (`YYYY-MM-DD HH:MM:SS`, UTC) would
  only appear for a row inserted without a value, which the code never
  does.
- Order messages by `messages.id`. `saveChat` deletes and re-inserts every
  message of a chat on each save
  ([`database.go:789-809`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L789-L809)), so `id`
  values are not stable across saves but the order is preserved; the
  `created_at` values are carried over from the in-memory message.
- `.ollama/history`: none. File mtime is the time of the last entry only.

## 5. Session and project attribution

- Session: `messages.chat_id = chats.id`.
- Project: none per chat. `settings.working_dir` is one global value
  ([`store.go:147-148`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L147-L148)) and the desktop
  tools do not use the file system; leave `project_path` empty.
- Model: `messages.model_name` on `assistant` rows.
- Git branch: none.
- `.ollama/history`: no session, no project, no model.

## 6. Tool calls and results

There is no call id. An `assistant` message carries one or more
`tool_calls` rows (ordered by `tool_calls.id`); the results follow as
`role = 'tool'` messages in the same order. The tool name of a `tool` row is
not stored (`Message.ToolName` has no column,
[`store.go:44`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L44) against
[`database.go:1030-1034`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/database.go#L1030-L1034)); the UI
recovers it on reload from the last call of the nearest earlier assistant
message ([`ui.go:1343-1358`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L1343-L1358)). A parser
should pair the n-th `tool` message after an assistant message with that
message's n-th `tool_calls` row and synthesise `tool_use_id` as
`<chat_id>:<tool_calls.id>`.

Thinking: `messages.thinking`, non-empty only for thinking models; emit as
`thinking` rows only with `--include-thinking`.

## 7. Overlap with launched agents

Question: if `ollama launch claude|opencode|hermes|openclaw --model <local
model>` was used, would an Ollama parser repeat rows the `claude-code`,
`opencode`, `hermes` or `openclaw` parsers already produce? **No.**
Ollama keeps no copy of what a launched agent sends or receives; the
agent's own transcript is the only record, and an Ollama parser reading
the stores in section 2 cannot produce those turns. The same holds for the
integrations added since `v0.30.7`, `chatgpt` (the Codex desktop app),
`muse` and `dsh`. Each part:

**(a) The API handlers persist nothing under any home.** The routes that
`ollama launch` points agents at, `/api/chat`, `/api/generate`,
`/v1/chat/completions`, `/v1/completions`, `/v1/responses` and
`/v1/messages`, all end in `ChatHandler` or `GenerateHandler`
([`server/routes.go:2072-2092`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L2072-L2092)), as do
`/v1/responses/compact` and `/v1/systemone`, which are new since
`v0.30.7` and write no file either. None of the server, `middleware`,
`openai` or `anthropic` packages imports the desktop `app/store` package
(its only importers are under `app/`), so the server never writes
`db.sqlite`; `.ollama/history` is written only by the REPL's readline
(section 3). The server's file writes outside the models directory are the
model-recommendation cache, the Codex proxy log in (b) and, only when
`OLLAMA_DEBUG_LOG_REQUESTS` is set, request bodies in a fresh temporary
directory `ollama-request-logs-*`
([`server/inference_request_log.go:25`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/inference_request_log.go#L25),[`33-47`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/inference_request_log.go#L33-L47),[`104-123`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/inference_request_log.go#L104-L123)),
outside any home. What does reach a log is the server's stdout and stderr:
`gin.Default()` ([`routes.go:2030`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L2030)) adds gin's
request logger, which writes one
`[GIN] <local time> | <status> | <latency> | <client IP> | <method> "<path>"`
line per request
([`gin.go:221-226`](https://github.com/gin-gonic/gin/blob/75ccf94d605a05fe24817fc2f166f6f2959d5cea/gin.go#L221-L226),
[`logger.go:141-161`](https://github.com/gin-gonic/gin/blob/75ccf94d605a05fe24817fc2f166f6f2959d5cea/logger.go#L141-L161));
gin runs in debug mode unless `GIN_MODE` says otherwise
([`routes.go:96`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L96),[`106-115`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L106-L115)).
Only at `OLLAMA_DEBUG=2` (trace,
[`envconfig/config.go:199-212`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/envconfig/config.go#L199-L212)) does the
server log model output text
([`routes.go:2987`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L2987),[`3004`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L3004))
and `/v1/messages` responses
([`middleware/anthropic.go:64`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/middleware/anthropic.go#L64),[`75`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/middleware/anthropic.go#L75)).
For a systemd install that output goes to the journal; for the macOS
desktop app it goes to `.ollama/logs/server.log`
([`app/server/server_unix.go:20`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/server/server_unix.go#L20),
[`app/server/server.go:242`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/server/server.go#L242),[`288-294`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/server/server.go#L288-L294)).
That log is not a transcript and is not parsed.

**(b) `codex-proxy.log` is metadata only.** It exists since `v0.34.0`.
The Codex desktop proxy, mounted at `/api/codex/*` on the server's own
listener
([`routes.go:1997`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L1997),[`2045`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/routes.go#L2045)),
writes to `.ollama/logs/codex-proxy.log` under the home of the *server*
process ([`server/codex_proxy.go:19-33`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/server/codex_proxy.go#L19-L33)),
so for a systemd install it lands in `/usr/share/ollama/.ollama/logs`, not
the user's home. Its only writer is `logActivity`, one line per request:
`<RFC 3339 local time> route=<openai|chatgpt|ollama|none> model="<name>"
method=<m> path=<p> status=<n> duration=<d> result=<ok|canceled|...>`
([`internal/proxy/codex_desktop.go:481-516`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/internal/proxy/codex_desktop.go#L481-L516)).
No prompt, completion or tool call is written. It does not repeat Codex
session content. A parser may skip it; if read, one `system` row per line
(`codex proxy: <route> <model> <status> <result>`) is the most it supports,
with no session id. The Claude Desktop gateway in the same package writes
no file.

**(c) `launch/` and `backup/` hold configuration, not conversations.**
`.ollama/launch/` holds:

- `codex-app-restore.json`: the Codex app's previous `profile`, `model`,
  `model_provider`, `model_catalog_json`, `openai_base_url` and desktop
  reasoning-effort values, each with a `had_*` flag
  ([`cmd/launch/codex_app.go:2476-2489`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L2476-L2489),[`2617-2627`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L2617-L2627),[`2648-2654`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L2648-L2654)).
  `v0.30.7` wrote the first four pairs only.
- `muse-config/muse/settings.json` (since `v0.32.11`): a private
  `XDG_CONFIG_HOME` for Muse that holds provider settings while Muse's
  sessions stay in its own data directory
  ([`muse.go:24-34`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/muse.go#L24-L34),[`211-219`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/muse.go#L211-L219)).
- `dsh/` (since `v0.32.11`): DeepSeek Harness settings only, its sessions
  untouched
  ([`deepseek_harness.go:33-36`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/deepseek_harness.go#L33-L36),[`498-504`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/deepseek_harness.go#L498-L504)).
- `chatgpt-session-start` (since `v0.34.0`): a single RFC 3339 UTC time,
  see (d)
  ([`codex_app_profile.go:28-33`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app_profile.go#L28-L33),[`81-87`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app_profile.go#L81-L87)).

On macOS, the desktop app's ChatGPT integration
([`app/cmd/app/codex_app_darwin.go:201`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/cmd/app/codex_app_darwin.go#L201),
[`codex_app.go:700-722`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L700-L722)) also makes
`.ollama/chatgpt-ollama/` with an `electron-data/` directory and, when it
finds a matching process, a `chatgpt.pid` file
([`codex_app.go:38-39`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L38-L39),[`916-938`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L916-L938),[`1909-1926`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L1909-L1926),[`1976-1988`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L1976-L1988)).
`v0.35.1` uses them only to detect and stop a ChatGPT process started
with that profile by an earlier build
([`codex_app.go:792-800`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L792-L800),[`1953-1965`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L1953-L1965));
no release from `v0.34.0` to `v0.35.1` starts ChatGPT with
`--user-data-dir` pointing there, so the directory should be empty. If an
`electron-data/` with content is found, it is a ChatGPT Electron profile
and may hold that app's state; it is not an Ollama transcript.

`backup/` holds the previous version of every file `ollama launch` (or the
config writer) overwrote: `backup/<integration>/<file name>.<unix
seconds>`, or `backup/<file name>.<unix seconds>` when no integration is
given (Ollama's own `config.json`, Codex `config.toml`), five per file
([`cmd/internal/fileutil/files.go:17-19`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/internal/fileutil/files.go#L17-L19),[`46-71`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/internal/fileutil/files.go#L46-L71),[`76-94`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/internal/fileutil/files.go#L76-L94)).
The ChatGPT integration still backs up under `backup/codex-app/`. The
backed-up files are the agents' configs: Hermes `config.yaml`
([`hermes.go:268-311`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/hermes.go#L268-L311)), OpenClaw
`openclaw.json` ([`openclaw.go:652-663`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/openclaw.go#L652-L663),[`747`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/openclaw.go#L747)),
OpenCode's `.local/state/opencode/model.json` recent-model list
([`opencode.go:208-214`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/opencode.go#L208-L214),[`216-280`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/opencode.go#L216-L280)).
They can hold API keys from those configs, but no conversation content,
session id or working directory. Claude Code gets nothing on disk: it is
started with `--model <model>` and `ANTHROPIC_BASE_URL`,
`ANTHROPIC_AUTH_TOKEN=ollama` and the `ANTHROPIC_DEFAULT_*_MODEL`
variables in its environment ([`claude.go:20-27`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/claude.go#L20-L27),[`52-87`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/claude.go#L52-L87)).
One launch edits another agent's session state: for OpenClaw,
`clearSessionModelOverride` rewrites `.openclaw/agents/main/sessions/sessions.json`
without a backup, setting each session's `model` to the launched model and
dropping `modelOverride`/`providerOverride`
([`openclaw.go:757-792`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/openclaw.go#L757-L792)), unchanged
since `v0.30.7`. That changes OpenClaw's own evidence (the session index's
model field), not Ollama's.

**(d) There is no per-launch record.** `config.json` holds
`integrations{<name>: {models[], aliases{}, onboarded, automode}}`,
`last_model`, `last_selection` and, on Linux, `onboarding_version`, with
no time field ([`cmd/config/config.go:19-34`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/config/config.go#L19-L34)).
A `codex-app` entry from an older release is copied to `chatgpt` on the
next load ([`launch.go:1525-1555`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/launch.go#L1525-L1555)).
The file is rewritten only when something changes: `SaveIntegration` when
the model chosen for an integration differs from the saved one
([`launch.go:734-739`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/launch.go#L734-L739)), `SetLastModel`
when the REPL model changes ([`launch.go:717-720`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/launch.go#L717-L720)),
`SetLastSelection` from the menu ([`cmd/cmd.go:2324-2327`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/cmd.go#L2324-L2327)),
and `WriteWithBackup` skips a write whose bytes are unchanged
([`files.go:84-87`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/internal/fileutil/files.go#L84-L87)). So the
file says which integrations were configured with which local model, the
`backup/config.json.<epoch>` names give the times the configuration
changed (the epoch is when the old version was replaced), and the mtime
gives the last change. Repeated launches with the same model leave no
trace in Ollama's files. Three newer markers add a little:

- `launch/chatgpt-session-start` is rewritten each time the macOS desktop
  app applies Ollama models to ChatGPT, not on a CLI `ollama launch
  chatgpt` ([`codex_app.go:653-662`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L653-L662),[`700-722`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app.go#L700-L722)). Ollama
  then counts prompts by reading, never writing, Codex's
  `sessions/*.jsonl` newer than that time
  ([`codex_app_profile.go:54-79`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app_profile.go#L54-L79),[`111-142`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/launch/codex_app_profile.go#L111-L142)).
- `settings.claude_desktop_used` and `settings.codex_desktop_used` in
  `db.sqlite` are set once Claude Desktop or ChatGPT has been connected
  through the desktop app
  ([`store.go:180-185`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/store/store.go#L180-L185)), booleans
  without a time.
- On macOS and Windows, `.ollama/onboarding-v1.completed` is an empty file
  whose mtime is when onboarding was first completed in the app or CLI
  ([`internal/onboarding/state.go:12-29`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/internal/onboarding/state.go#L12-L29),[`50-75`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/internal/onboarding/state.go#L50-L75);
  [`cmd/config/config.go:36-60`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/cmd/config/config.go#L36-L60)).

The launched agent's own transcript is where the model shows: Claude Code
`message.model`, OpenCode `providerID/modelID` (provider `ollama`), Hermes
`sessions.model`, OpenClaw `responseModel`
(see [claude-code.md](claude-code.md), [opencode.md](opencode.md),
[hermes.md](hermes.md), [openclaw.md](openclaw.md); for `chatgpt` and
`muse`, [codex-cli.md](codex-cli.md) and [muse-code.md](muse-code.md)); the
local experiment below confirms the server echoes the requested local
model name.

Bottom line: an Ollama parser built on section 8 never duplicates
launched-agent rows. The only Ollama files that touch launched sessions
are configuration (attribution of integration to model) and a
metadata-only proxy log for the ChatGPT integration. The exceptions are
opt-in and outside the parser's inputs: `OLLAMA_DEBUG_LOG_REQUESTS`
request bodies in a temp directory and `OLLAMA_DEBUG=2` server logs would
repeat prompt or output content, and a parser should not read them.

### Local check

On this workstation (Linux, Ollama 0.35.1, systemd service user `ollama`,
home `/usr/share/ollama`), the user's `.ollama/config.json` has the keys
`integrations` (empty), `last_model` and `last_selection`;
`backup/config.json.<epoch>` has `integrations` and `last_selection`;
`history` has five entries, four of them slash commands; there is no
`launch/`, `logs/` or `chatgpt-ollama/` directory and no
`onboarding_version` key. After a marker file was
created, one request each was sent to `/api/chat`,
`/v1/chat/completions` and `/v1/messages` with a unique marker string in
the prompt. Afterwards nothing under `~/.ollama` or
`/usr/share/ollama` was newer than the marker, and nothing new under
`/tmp` came from Ollama. The marker string was not found in any readable
file under those three trees, nor in `journalctl -u ollama`, which held
only the three `[GIN]` request lines and llama-server slot and sampler
lines without prompt text. All three responses named the requested local
model. The same check against 0.30.7 gave the same result.

## 8. Parser plan

Globs (relative to the home): `Library/Application Support/Ollama/db.sqlite`,
`AppData/Local/Ollama/db.sqlite` (with their `-wal`; open through
`sqlite_util.py`), and `.ollama/history`. Do not read `.ollama/logs/*`,
`.ollama/config.json`, `.ollama/backup/**`, `.ollama/launch/**`,
`.ollama/chatgpt-ollama/**` or `.ollama/onboarding-v*.completed` for rows.

`db.sqlite`: join `messages` to `chats` on `chat_id`, order by `chat_id`,
`messages.id`. One row per message, plus one `tool_use` row per
`tool_calls` row and one `thinking` row where `thinking` is non-empty.
Read schema versions 16 to 19 the same way.

| Column | Source |
| --- | --- |
| timestamp_utc | `messages.created_at` parsed with its offset (`YYYY-MM-DD HH:MM:SS[.f]±HH:MM`), converted to UTC; `tool_use` rows take their message's time |
| session_id | `chats.id` |
| project_path | empty |
| git_branch | empty |
| turn_type | `user` → user; `assistant` with content → assistant; each `tool_calls` row → tool_use; `tool` → tool_result; non-empty `thinking` → thinking (opt-in); `system` → system |
| model | `messages.model_name` on assistant, thinking and tool_use rows |
| tool_name | `tool_calls.function_name`; on tool_result rows, the paired call's name |
| tool_use_id | `<chat_id>:<tool_calls.id>`, paired by position (section 6) |
| text | `content`; for tool_use the `url` or `query` argument when present, else `function_arguments`; for user rows with attachments, append `[attachment: <filename>, <n> bytes]` per row, never the BLOB |
| source_line | `messages.id` (or `tool_calls.id` for tool_use rows) |

An assistant message with empty `content`, no thinking and no tool calls
(the placeholder written while the model is being pulled,
[`ui.go:832-841`](https://github.com/ollama/ollama/blob/b0c1ca4f7549d7acdfa52a7dcffc934bc63a43ce/app/ui/ui.go#L832-L841)) yields no row. A chat with
`title` yields nothing extra; the title is not a turn.

`.ollama/history`: one `user` row per non-empty line, `timestamp_utc` and
`session_id` empty, `source_line` the line number, text the line. Lines
starting with `/` become `system` rows labelled `slash command:`. The
rows carry no time, so they sort last and drop out of any time-window
filter; the parser docstring must say that the file keeps only the last
100 entries and splits pasted multi-line prompts across lines.

Fixture `Library/Application Support/Ollama/db.sqlite`:

```sql
CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK (id = 1), device_id TEXT NOT NULL DEFAULT '', working_dir TEXT NOT NULL DEFAULT '', selected_model TEXT NOT NULL DEFAULT '', onboarding_version INTEGER NOT NULL DEFAULT 0, claude_desktop_used BOOLEAN NOT NULL DEFAULT 0, codex_desktop_used BOOLEAN NOT NULL DEFAULT 0, schema_version INTEGER NOT NULL DEFAULT 19);
INSERT INTO settings (id, device_id) VALUES (1, '0190a000-0000-7000-8000-00000000d001');
CREATE TABLE chats (id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, browser_state TEXT);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', thinking TEXT NOT NULL DEFAULT '', stream BOOLEAN NOT NULL DEFAULT 0, model_name TEXT, model_cloud BOOLEAN, model_ollama_host BOOLEAN, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, thinking_time_start TIMESTAMP, thinking_time_end TIMESTAMP, tool_result TEXT);
CREATE TABLE tool_calls (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL, type TEXT NOT NULL, function_name TEXT NOT NULL, function_arguments TEXT NOT NULL, function_result TEXT);
CREATE TABLE attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL, filename TEXT NOT NULL, data BLOB NOT NULL);
CREATE TABLE users (name TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', plan TEXT NOT NULL DEFAULT '', cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO users VALUES ('Alice Example', 'alice@example.invalid', 'free', '2026-03-01 08:59:00-08:00');
INSERT INTO chats VALUES ('0190a000-0000-7000-8000-00000000c001', 'Release notes', '2026-03-01 09:00:00.5-08:00', NULL);
INSERT INTO messages (id, chat_id, role, content, thinking, model_name, created_at, updated_at, tool_result) VALUES
 (1, '0190a000-0000-7000-8000-00000000c001', 'user', 'summarise https://example.invalid/notes', '', NULL, '2026-03-01 09:00:00.5-08:00', '2026-03-01 09:00:00.5-08:00', NULL),
 (2, '0190a000-0000-7000-8000-00000000c001', 'assistant', '', 'need to fetch the page', 'gemma4:e4b', '2026-03-01 09:00:01.25-08:00', '2026-03-01 09:00:02-08:00', NULL),
 (3, '0190a000-0000-7000-8000-00000000c001', 'tool', 'Release 2.0 adds X.', '', NULL, '2026-03-01 09:00:03-08:00', '2026-03-01 09:00:03-08:00', '{"title":"Notes","content":"Release 2.0 adds X."}'),
 (4, '0190a000-0000-7000-8000-00000000c001', 'assistant', 'Release 2.0 adds X.', '', 'gemma4:e4b', '2026-03-01 09:00:04.125-08:00', '2026-03-01 09:00:05-08:00', NULL);
INSERT INTO tool_calls VALUES (1, 2, 'function', 'web_fetch', '{"url":"https://example.invalid/notes"}', NULL);
INSERT INTO attachments VALUES (1, 1, 'notes.txt', X'68656c6c6f');
```

Expected rows: user (17:00:00.500Z), thinking (opt-in, 17:00:01.250Z),
tool_use `web_fetch` with id `0190a000-0000-7000-8000-00000000c001:1` and
text `https://example.invalid/notes`, tool_result with the same id
(17:00:03.000Z), assistant (17:00:04.125Z, model `gemma4:e4b`). The user
row's text ends with `[attachment: notes.txt, 5 bytes]`; the `users` row
and the BLOB appear nowhere in the output. Truncation case: a
`db.sqlite` that is not a database becomes one `system` row. A second
fixture with the `settings` table at schema version 16 (without the three
newer columns) must give the same rows.

Fixture `.ollama/history` (noise beside it: `.ollama/config.json`
`{"integrations":{"claude":{"models":["gemma4:e4b"]}},"last_model":"gemma4:e4b","last_selection":"claude"}`,
`.ollama/backup/config.json.1772355600` and an empty
`.ollama/onboarding-v1.completed`, which the parser must not want):

```text
why is the sky blue
/set nohistory
/bye
```

Confidence. High: the DDL, write paths, timestamp binding, the tool
pairing rule, the history format, the absence of server-side persistence
(source plus the local experiment on 0.30.7 and 0.35.1), the
`config.json` and backup shapes, the `codex-proxy.log` line format, and
the release in which each change since `v0.30.7` appeared (from the tag
history). Medium: that the UI never sets `tool_calls.function_result` (no
writer found in `app/`); that the built-in agent of `v0.31.2` to
`v0.34.0` left no session store (read at its last commit only, not at
each release). Not determined: a real `db.sqlite`, because the desktop
app does not exist on Linux; what fills `chats.browser_state` in detail;
whether a Windows build of the app writes `server.log` with the same gin
lines (the path differs,
[`collectors/research/ollama.md`](../../collectors/research/ollama.md));
what a pre-release build may have left in `.ollama/chatgpt-ollama/electron-data`.
