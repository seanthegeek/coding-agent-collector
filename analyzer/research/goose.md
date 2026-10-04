# Goose transcript schema

Catalog agent: `goose`. Researched together with Zed ([zed.md](zed.md)); the
two share nothing but Rust and SQLite. Paths cited are relative to the clone.

## 1. Source

block/goose at [`591edd47cf2cfea4957d720c607cf2a4def8673d`](https://github.com/block/goose/commit/591edd47cf2cfea4957d720c607cf2a4def8673d), Apache-2.0. Open
source. Rust; sqlx 0.9.0, rmcp 3.4.1, etcetera 0.11.0, rustyline 18.0.1
([`Cargo.lock`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/Cargo.lock)). Third-party crate sources were read to verify serialisation.

## 2. Transcript stores

Directories come from etcetera `choose_app_strategy`
([`crates/goose/src/config/paths.rs:22-32`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/config/paths.rs#L22-L32)), which is XDG on Linux and macOS
and the Windows strategy on Windows ([`etcetera-0.11.0/src/app_strategy.rs:151-163`](https://github.com/lunacookies/etcetera/blob/07b3f54999e4f3ff0f027de0144c9349d820ce80/src/app_strategy.rs#L151-L163)).
macOS therefore uses `~/.config/goose`, `~/.local/share/goose` and
`~/.local/state/goose`, not `Library/Application Support` (that catalog entry
covers only the Electron desktop shell). Windows: `AppData/Roaming/Block/goose/{config,data}`;
state has no Windows equivalent and falls back to data ([`paths.rs:32`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/config/paths.rs#L32);
[`etcetera/.../windows.rs:126-165`](https://github.com/lunacookies/etcetera/blob/07b3f54999e4f3ff0f027de0144c9349d820ce80/src/app_strategy/windows.rs#L126-L165)). `GOOSE_PATH_ROOT` overrides to
`$ROOT/{config,data,state}` ([`paths.rs:9-17`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/config/paths.rs#L9-L17)).

| Store | Linux and macOS | Windows | Unit |
| --- | --- | --- | --- |
| Sessions database | `.local/share/goose/sessions/sessions.db` (+`-wal`, `-shm`) | `AppData/Roaming/Block/goose/data/sessions/sessions.db` | `sessions` row = session; `messages` row = one message ([`session_manager.rs:29-30`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L29-L30),[`961-963`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L961-L963)) |
| Legacy sessions | `.local/share/goose/sessions/<YYYYMMDD_HHMMSS>.jsonl` | same directory | line 1 metadata, then one message per line ([`legacy.rs:62-100`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/legacy.rs#L62-L100),[`111`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/legacy.rs#L111)) |
| LLM request log | `.local/state/goose/logs/llm_request.<N>.jsonl` (rotated; temp `llm_request.<uuid>.jsonl`) | `AppData/Roaming/Block/goose/data/logs/` | one file per provider call ([`providers/utils.rs:86`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/providers/utils.rs#L86),[`121-131`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/providers/utils.rs#L121-L131)) |
| CLI history | `.local/state/goose/history.txt` (old `.config/goose/history.txt`) | `AppData/Roaming/Block/goose/data/history.txt` | rustyline V2: `#V2` header, one entry per line, `\n` and `\\` escaped ([`goose-cli/src/session/mod.rs:196-197`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-cli/src/session/mod.rs#L196-L197); [`rustyline-18.0.1/src/history.rs:463-465`](https://github.com/kkawakam/rustyline/blob/cc1aab036d62aff3dbdc681b08949076ec275030/src/history.rs#L463-L465)) |

## 3. Record schema

`sessions.db`, schema version 16 ([`session_manager.rs:28`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L28),[`1012-1098`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1012-L1098)):

```sql
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE sessions (
  id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
  user_set_name BOOLEAN DEFAULT FALSE, session_type TEXT NOT NULL DEFAULT 'user',
  working_dir TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, extension_data TEXT DEFAULT '{}',
  total_tokens INTEGER, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
  cache_write_tokens INTEGER, accumulated_total_tokens INTEGER, accumulated_input_tokens INTEGER,
  accumulated_output_tokens INTEGER, accumulated_cache_read_tokens INTEGER,
  accumulated_cache_write_tokens INTEGER, accumulated_cost REAL, schedule_id TEXT, recipe_json TEXT,
  user_recipe_values_json TEXT, provider_name TEXT, model_config_json TEXT,
  goose_mode TEXT NOT NULL DEFAULT 'auto', archived_at TIMESTAMP, project_id TEXT, parent_session_id TEXT);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, message_id TEXT, session_id TEXT NOT NULL REFERENCES sessions(id),
  role TEXT NOT NULL, content_json TEXT NOT NULL, created_timestamp INTEGER NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, tokens INTEGER, metadata_json TEXT);
CREATE TABLE usage_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  created_timestamp INTEGER NOT NULL, model TEXT, input_tokens INTEGER, output_tokens INTEGER,
  total_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, cost REAL,
  cost_source TEXT, is_compaction INTEGER DEFAULT 0);
```

Migration v10 also creates `threads` and `thread_messages` ([`:1462-1487`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1462-L1487))
with no writer; treat as empty. v11 adds `provider_inventory_*` (model
lists, no secrets).

- Timestamp: `messages.created_timestamp` is epoch seconds (`Message::user()`
  uses `Utc::now().timestamp()`, [`goose-provider-types/src/conversation/message.rs:1035`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L1035));
  some clients write milliseconds, normalised with `> 10_000_000_000 → /1000`
  ([`session_manager.rs:31`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L31),[`729-741`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L729-L741)). `messages.timestamp` and
  `sessions.created_at`/`updated_at` are SQLite `CURRENT_TIMESTAMP` text
  `YYYY-MM-DD HH:MM:SS` UTC ([`:1958`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1958)); legacy-imported sessions bind chrono
  values, which sqlx writes as RFC 3339 ([`sqlx-sqlite-0.9.0/src/types/chrono.rs:69`](https://github.com/launchbadge/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/types/chrono.rs#L69)).
  Order within a second by `id` ([`:1887-1890`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1887-L1890)).
- Session id: `sessions.id` is `YYYYMMDD_<n>` ([`:1633-1647`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1633-L1647));
  `messages.message_id` is `msg_<session_id>_<uuid>` ([`:1941-1943`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1941-L1943)).
- Working directory: `sessions.working_dir`. Git branch: none.
- Model and provider: `sessions.provider_name`, `sessions.model_config_json`
  `{"model_name","temperature","max_tokens","toolshim","toolshim_model",
  "request_params"?,"reasoning"?,"supports_vision"?}`
  ([`goose-provider-types/src/model.rs:41-59`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/model.rs#L41-L59); `request_headers` is
  `#[serde(skip)]`); per message `metadata_json.inference.{provider,
  requestedModel, resolvedModel?, providerSessionId?}` ([`message.rs:768-775`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L768-L775));
  per request `usage_ledger.model`.
- Role: `messages.role` in `user`, `assistant` ([`:720-725`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L720-L725)). `session_type`
  in `user, scheduled, sub_agent, hidden, terminal, gateway, acp` ([`:46-57`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L46-L57)).
- `content_json`: JSON array, `"type"` tag in camelCase ([`message.rs:317-330`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L317-L330)):
  `text` `{"type":"text","text":"...","annotations"?,"_meta"?}` (rmcp
  [`content.rs:23-34`](https://github.com/modelcontextprotocol/rust-sdk/blob/9427a929959e665e0d12e9395f674026baf4bd48/crates/rmcp/src/model/content.rs#L23-L34)); `image` `{"data","mimeType"}`; `document` `{"data",
  "mimeType","name"?}`; `toolRequest` `{"id","toolCall":{"status":"success",
  "value":{"name","arguments":{...}}} | {"status":"error","error":"..."},
  "metadata"?,"_meta"?}` ([`message.rs:131-141`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L131-L141); [`tool_result_serde.rs:7-25`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/tool_result_serde.rs#L7-L25);
  rmcp [`model.rs:4142-4150`](https://github.com/modelcontextprotocol/rust-sdk/blob/9427a929959e665e0d12e9395f674026baf4bd48/crates/rmcp/src/model.rs#L4142-L4150)); `toolResponse` `{"id","toolResult":{"status":
  "success","value":{"content":[{"type":"text","text":..}|{"type":"image",..}|
  resource|resource_link|audio],"structuredContent"?,"isError"?}} |
  {"status":"error","error"}}` ([`message.rs:175-183`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L175-L183); rmcp [`model.rs:3886-3897`](https://github.com/modelcontextprotocol/rust-sdk/blob/9427a929959e665e0d12e9395f674026baf4bd48/crates/rmcp/src/model.rs#L3886-L3897),
  [`content.rs:256-264`](https://github.com/modelcontextprotocol/rust-sdk/blob/9427a929959e665e0d12e9395f674026baf4bd48/crates/rmcp/src/model/content.rs#L256-L264)), with older rows holding a bare content array in
  `value` ([`tool_result_serde.rs:142-145`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/tool_result_serde.rs#L142-L145)); `thinking` `{"thinking",
  "signature"}`; `redactedThinking` `{"data"}`; `toolConfirmationRequest`
  `{"id","toolName","arguments","prompt"}`; `actionRequired`
  `{"data":{"actionType":...}}`; `systemNotification` `{"notificationType",
  "msg","data"?}`; `error` `{"kind","message"}`.
- `metadata_json`: `{"userVisible","agentVisible","inference"?,
  "outputTokenLimitReached"?,"steer"?,"turnContext"?,"usage"?,"operations"?}`
  ([`message.rs:826-854`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/conversation/message.rs#L826-L854)).

## 4. Joins

`messages.session_id = sessions.id`; `usage_ledger.session_id` likewise.
Tool pairing: `toolRequest.id` (assistant row) with `toolResponse.id` (user
row). Project path: `sessions.working_dir`.

## 5. SQLite specifics

Opened with `journal_mode=WAL`, `busy_timeout` 30 s, directory mode 0700
([`session_manager.rs:945-955`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L945-L955)). Recent rows live in `sessions.db-wal` until
checkpoint; collect `sessions.db*`. No encryption.

## 6. Format versions

`schema_version` table, `CURRENT_SCHEMA_VERSION=16`; migrations 1-16 are
additive `ALTER TABLE ADD COLUMN` ([`session_manager.rs:1318-1613`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1318-L1613)), so older
databases lack `message_id`, `metadata_json`, `provider_name`,
`model_config_json`, `parent_session_id` and `usage_ledger`. Legacy JSONL
sessions are imported once when `schema_version` is absent
([`:982-989`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L982-L989),[`1145-1250`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/session_manager.rs#L1145-L1250)): line 1 `{"description","id"?,"created_at",
"updated_at","extension_data","message_count","working_dir"?, token fields}`,
then `{"id","role","created","content":[...],"metadata"?}`
([`legacy.rs:62-100`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/legacy.rs#L62-L100),[`128-130`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/legacy.rs#L128-L130)); the file name `YYYYMMDD_HHMMSS` gives the
created time ([`legacy.rs:111`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/legacy.rs#L111)). Imports from Claude Code, Codex and Pi JSONL
also land in `sessions.db` ([`import_formats/mod.rs:1-12`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/session/import_formats/mod.rs#L1-L12)). The catalog
entries `~/.goose` and `.config/Goose` were not found anywhere in the source
at this commit (issue 23).

## 7. Secrets

`llm_request.*.jsonl` holds the entire provider request body (system prompt,
all messages, tool outputs) and responses ([`request_log.rs:81-86`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/request_log.rs#L81-L86),[`110-113`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/request_log.rs#L110-L113));
headers and keys are not logged (`ModelConfig.request_headers` is
`#[serde(skip)]`, [`model.rs:58-59`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose-provider-types/src/model.rs#L58-L59)). Credentials live in the keyring or
`.config/goose/secrets.yaml` ([`config/base.rs:89-91`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/config/base.rs#L89-L91),[`394`](https://github.com/block/goose/blob/591edd47cf2cfea4957d720c607cf2a4def8673d/crates/goose/src/config/base.rs#L394)). `recipe_json` and
`user_recipe_values_json` can carry user-entered parameters.

## 8. Parser plan

Globs: `.local/share/goose/sessions/sessions.db*`,
`.local/share/goose/sessions/*.jsonl`,
`.local/state/goose/logs/llm_request.*.jsonl`,
`.local/state/goose/history.txt`, `.config/goose/history.txt`,
`AppData/Roaming/Block/goose/data/sessions/sessions.db*`,
`AppData/Roaming/Block/goose/data/logs/llm_request.*.jsonl`,
`AppData/Roaming/Block/goose/data/history.txt`.

Rows: one per `content_json` block, plus one `system` row per session from
`sessions`.

| Column | Source |
| --- | --- |
| timestamp_utc | `created_timestamp` (divide by 1000 if above 1e10) |
| session_id | `messages.session_id` |
| project_path | `sessions.working_dir` |
| git_branch | empty |
| turn_type | role `user` → user; `assistant` text → assistant; `toolRequest` → tool_use; `toolResponse` → tool_result; `thinking`/`redactedThinking` → thinking; `systemNotification`/`error`/`actionRequired` → system |
| model | `metadata_json.inference.requestedModel`, else `model_config_json.model_name` prefixed with `provider_name/` |
| tool_name | `toolCall.value.name` (responses look the name up by id) |
| tool_use_id | `toolRequest.id` / `toolResponse.id` |
| text | text, `arguments` JSON, result text |

Fixture:

```sql
INSERT INTO schema_version(version) VALUES (16);
INSERT INTO sessions(id,name,session_type,working_dir,created_at,updated_at,extension_data,provider_name,model_config_json,goose_mode)
VALUES ('20260301_1','Fix flaky test','user','/home/alice/proj','2026-03-01 09:00:00','2026-03-01 09:01:05','{}','anthropic',
 '{"model_name":"claude-sonnet-4-5","temperature":null,"max_tokens":null,"toolshim":false,"toolshim_model":null}','auto');
INSERT INTO messages(message_id,session_id,role,content_json,created_timestamp,metadata_json) VALUES
('msg_20260301_1_a1','20260301_1','user','[{"type":"text","text":"run the tests"}]',1772355600,'{"userVisible":true,"agentVisible":true}'),
('msg_20260301_1_a2','20260301_1','assistant','[{"type":"toolRequest","id":"call_1","toolCall":{"status":"success","value":{"name":"developer__shell","arguments":{"command":"pytest -q"}}}}]',1772355601,
 '{"userVisible":true,"agentVisible":true,"inference":{"provider":"anthropic","requestedModel":"claude-sonnet-4-5"}}'),
('msg_20260301_1_a3','20260301_1','user','[{"type":"toolResponse","id":"call_1","toolResult":{"status":"success","value":{"content":[{"type":"text","text":"3 passed"}]}}}]',1772355603,'{"userVisible":true,"agentVisible":true}'),
('msg_20260301_1_a4','20260301_1','assistant','[{"type":"thinking","thinking":"all green","signature":"sig"},{"type":"text","text":"All 3 tests pass."}]',1772355605,'{"userVisible":true,"agentVisible":true}');
INSERT INTO usage_ledger(session_id,created_timestamp,model,input_tokens,output_tokens,total_tokens) VALUES ('20260301_1',1772355605,'claude-sonnet-4-5',120,30,150);
```

Legacy `20260301_090000.jsonl`:

```
{"description":"old chat","working_dir":"/home/alice/old","created_at":"2026-03-01T09:00:00Z","updated_at":"2026-03-01T09:00:10Z","extension_data":{},"message_count":1}
{"id":"m1","role":"user","created":1772355600,"content":[{"type":"text","text":"hello"}]}
```

`llm_request.0.jsonl`: `{"model_config":{"model_name":"gpt-4.1"},"input":{"model":"gpt-4.1","messages":[{"role":"user","content":"hello"}]}}` then `{"data":{"role":"assistant","created":1772355601,"content":[{"type":"text","text":"hi"}]},"usage":{"input_tokens":5,"output_tokens":1}}`.

Confidence. High: DDL, content and metadata field names, path derivation,
WAL, version handling. Not determined: `LOGS_TO_KEEP` for `llm_request`
rotation; whether Goose desktop writes millisecond timestamps (only the
normaliser proves that some client does).
