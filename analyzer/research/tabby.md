# Tabby transcript schema

Catalog agent: `tabby`. A self-hosted completion and chat server; transcripts
live on the server host, in its SQLite database and a daily event log.
Editor clients keep none. Paths are in `collectors/research/tabby.md`.

## 1. Source

TabbyML/tabby at [`21b29048d7bcf6b94f9f482f2d0fd05efadfd19f`](https://github.com/TabbyML/tabby/commit/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f).
Apache-2.0 outside `ee/`, Tabby Enterprise licence inside; source public.

## 2. Transcript files

- `.tabby/ee/db.sqlite` (`-wal`, `-shm`), and `.tabby/ee/db.backup-YYYYMMDD.sqlite`
  copies made before each migration
  ([ee/tabby-webserver/src/path.rs:9-15](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/path.rs#L9-L15); [ee/tabby-db/src/lib.rs:189-221](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/lib.rs#L189-L221)).
  Chat threads (`threads`, `thread_messages`), AI-written pages
  (`pages`, `page_sections`), and per-user completion events
  (`user_events`, `user_completions`). Source builds without the `prod`
  feature use `dev-db.sqlite`.
- `.tabby/events/YYYY-MM-DD.json`: JSON Lines, one `LogEntry` per line, a new
  file per UTC day ([crates/tabby/src/services/event.rs:68-93](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/services/event.rs#L68-L93)), no
  retention. Written whether or not the database is in use
  ([ee/tabby-webserver/src/webserver.rs:34-46](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/webserver.rs#L34-L46); [crates/tabby/src/serve.rs:139-152](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/serve.rs#L139-L152)).

## 3. Record schema

**`threads`** ([ee/tabby-db/schema/schema.sql:167-178](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L167-L178)): `id` integer,
`is_ephemeral` (sidebar chats start ephemeral,
[ee/tabby-webserver/src/service/thread.rs:123](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/service/thread.rs#L123)), `user_id`, `created_at`,
`updated_at`, `relevant_questions` (JSON array of strings).

**`thread_messages`** ([schema.sql:179-190](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L179-L190)): `id`, `thread_id`, `role`
(`user` or `assistant`, [ee/tabby-schema/src/dao.rs:719-734](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-schema/src/dao.rs#L719-L734)), `content`
(Markdown; assistant content is appended while streaming,
[ee/tabby-db/src/threads.rs:274](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/threads.rs#L274)), `code_source_id`, `attachment` JSON
(`code[]`, `client_code[]`, `doc[]`, `code_file_list`,
[ee/tabby-db/src/attachment.rs:5-10](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/attachment.rs#L5-L10)), `created_at`, `updated_at`. `code[]`
items: `git_url`, `commit`, `language`, `filepath`, `content`,
`start_line`; `client_code[]`: `filepath`, `start_line`, `content`
([attachment.rs:84-100](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/attachment.rs#L84-L100)). Messages alternate roles; two in a row
with the same role are rejected ([threads.rs:150-153](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/threads.rs#L150-L153)). No model,
tool calls or thinking are stored.

**`user_events`** ([schema.sql:116-123](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L116-L123)): `user_id`, `kind` in
`completion|chat_completion|select|view|dismiss`
([dao.rs:597-606](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-schema/src/dao.rs#L597-L606)), `created_at`, `payload` (pretty JSON of the
`Event`, [ee/tabby-webserver/src/service/event_logger.rs:21-25](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/service/event_logger.rs#L21-L25)).

**Event log line** `LogEntry` ([crates/tabby-common/src/api/event.rs:106-111](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/api/event.rs#L106-L111)):
`user` (server user id or null), `ts` (Unix ms, [:113-120](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/api/event.rs#L113-L120)), `event`, an
externally tagged snake_case enum ([:32-73](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/api/event.rs#L32-L73)): `{"completion":{...}}`
with `completion_id`, `language`, `prompt` (the full prompt sent to the
model), `segments` (`prefix`, `suffix`, `clipboard`, `git_url`,
`declarations[]`, `filepath`, [:81-98](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/api/event.rs#L81-L98)), `choices[]` (`index`, `text`),
`user_agent`; `view`, `select`, `dismiss` with `completion_id`,
`choice_index`, `view_id`, `elapsed`; `chat_completion` is empty
([crates/tabby/src/routes/chat.rs:83](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/routes/chat.rs#L83)).

Timestamps: SQLite columns are `DATETIME('now')` defaults or
`%F %X` strings, both UTC without zone, `YYYY-MM-DD HH:MM:SS`
([ee/tabby-db/src/lib.rs:307-310](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/lib.rs#L307-L310); [user_events.rs:27-31](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/user_events.rs#L27-L31)).

## 4. Joins

`thread_messages.thread_id → threads.id`; `threads.user_id → users.id`
(`users.email`, `users.name` attribute the chat,
[schema.sql:17-30](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L17-L30)). `user_events.payload.completion.completion_id`
joins `user_completions.completion_id` and the `view`/`select`/`dismiss`
events of the same completion. Project identity is the `git_url` and
`filepath` in attachments or `segments`; no local cwd is recorded.
`page_sections.page_id → pages.id` for pages.

## 5. SQLite specifics

WAL journal ([lib.rs:165-176](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/lib.rs#L165-L176)); collect `-wal` or lose recent rows.
`thread_messages.attachment` is TEXT JSON written with `JSON_OBJECT`
([threads.rs:159-166](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/threads.rs#L159-L166)). Ephemeral threads untouched for 7 days are
deleted by a background job ([threads.rs:393-430](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/threads.rs#L393-L430);
[background_job/db.rs:33-35](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/service/background_job/db.rs#L33-L35)), so the pre-migration backups and
the event log can hold chats and completions the live database no longer
has. Migrations are sqlx (`_sqlx_migrations`).

## 6. Format versions

Migrations under `ee/tabby-db/migrations/`; `thread_messages` arrived in
`0035` ([0035_add-thread-message-table.up.sql](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/migrations/0035_add-thread-message-table.up.sql)), and the separate
`code_attachments`, `client_code_attachments`, `doc_attachments` columns
were deprecated in 0.25 in favour of `attachment`
([threads.rs:34-38](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/threads.rs#L34-L38)) and are absent from the current schema. A backup
from before 0.25 can carry attachments only in the old columns. Event log lines have no version.

## 7. Secrets in transcript stores

The database also holds `users.auth_token`, `registration_token.token`,
`refresh_tokens.token`, `integrations.access_token`,
`email_setting.smtp_password`, `oauth_credential.client_secret`,
`ldap_credential.bind_password` (see collectors research, section 3).
Redact those columns. Completion prompts and `clipboard` segments can carry
pasted secrets.

## 8. Parser plan

Globs: `.tabby/ee/db.sqlite`, `.tabby/ee/db.backup-*.sqlite`,
`.tabby/ee/dev-db.sqlite`, `.tabby/events/*.json`.

| Column | Source |
| --- | --- |
| timestamp_utc | `thread_messages.created_at`; event log `ts` (ms) |
| session_id | `threads.id`; for completions `completion_id` |
| project_path | `attachment.code[0].git_url` or `segments.git_url`, else empty |
| git_branch | empty |
| turn_type | `role`; completion `prompt` → user, `choices[].text` → assistant; view/select/dismiss → system |
| model | empty (not recorded) |
| tool_name, tool_use_id | empty |
| text | `content`; completion `prompt` and choice text; others the event kind |

Add the thread owner's `users.email` to `text` or a note, since one
server serves many people.

Fixtures:

```sql
INSERT INTO users(id,email,is_admin,auth_token,active,name) VALUES(1,'alice@example.com',1,'auth_REDACT',1,'Alice');
INSERT INTO threads(id,is_ephemeral,user_id,created_at,updated_at,relevant_questions) VALUES(7,0,1,'2026-10-01 10:00:00','2026-10-01 10:00:09','["How is the cache invalidated?"]');
INSERT INTO thread_messages(id,thread_id,role,content,created_at,updated_at,attachment) VALUES
(1,7,'user','Where is the cache cleared?','2026-10-01 10:00:00','2026-10-01 10:00:00','{"code":null,"client_code":[{"filepath":"src/cache.rs","start_line":10,"content":"fn clear()"}],"doc":null}'),
(2,7,'assistant','In `clear()` in src/cache.rs.','2026-10-01 10:00:02','2026-10-01 10:00:09','{"code":[{"git_url":"https://github.com/acme/app","commit":"abc123","language":"rust","filepath":"src/cache.rs","content":"fn clear() {}","start_line":10}],"client_code":null,"doc":null}');
```

```json
{"user":"1","ts":1759312800123,"event":{"completion":{"completion_id":"cmpl-7f3a","language":"python","prompt":"def add(a, b):\n    ","segments":{"prefix":"def add(a, b):\n    ","suffix":"\n","git_url":"https://github.com/acme/app","filepath":"app/math.py"},"choices":[{"index":0,"text":"return a + b"}],"user_agent":"tabby-agent/1.9"}}}
{"user":"1","ts":1759312801500,"event":{"select":{"completion_id":"cmpl-7f3a","choice_index":0,"view_id":"view-1","elapsed":1377}}}
```

Confidence. High: table and column names, role values, event JSON shape
and `ts` unit, WAL, backups, ephemeral cleanup (source). Medium: the exact
form of `user` in the event log (an encoded user id string; not traced
through the auth middleware). Not determined: `pages` and `page_sections`
content shape beyond `title`/`content` ([schema.sql:267-288](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L267-L288)).
