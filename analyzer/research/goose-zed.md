# Goose and Zed transcript schemas

Paths below are relative to the repo clones in `scratchpad/repos/`; third-party crate sources cited are in `scratchpad/crates/`.

## 1. Repos, commits, licenses

- **Goose** `block/goose` @ `591edd47cf2cfea4957d720c607cf2a4def8673d`, Apache-2.0 (`LICENSE`). Rust; sqlx 0.9.0, rmcp 3.4.1, etcetera 0.11.0, rustyline 18.0.1 (`Cargo.lock`).
- **Zed** `zed-industries/zed` @ `a84689073d296dfd39987bc7dd478e43ef76d83a`; agent crates GPL-3.0-or-later (`crates/agent/Cargo.toml:6`, `crates/agent_ui/Cargo.toml:6`). Rust; sqlez (own SQLite wrapper), zstd crate, agent-client-protocol-schema 1.9.1.

## 2. Transcript stores

**Goose.** Directories come from etcetera `choose_app_strategy` (`crates/goose/src/config/paths.rs:22-32`), which is **XDG on Linux and macOS**, Windows strategy on Windows (`etcetera-0.11.0/src/app_strategy.rs:151-163`). macOS therefore uses `~/.config/goose`, `~/.local/share/goose`, `~/.local/state/goose`, not `Library/Application Support` (that entry is the Electron desktop shell only). Windows: `AppData/Roaming/Block/goose/{config,data}` and state falls back to data (`paths.rs:32`; `etcetera/.../windows.rs:126-157`). `GOOSE_PATH_ROOT` overrides to `$ROOT/{config,data,state}` (`paths.rs:9-17`).

| Store | Path (Linux/macOS) | Windows | Unit |
|---|---|---|---|
| Sessions DB | `.local/share/goose/sessions/sessions.db` (+`-wal`,`-shm`) | `AppData/Roaming/Block/goose/data/sessions/sessions.db` | `sessions` row = session; `messages` row = one message (`session_manager.rs:29-30,961-963`) |
| Legacy sessions | `.local/share/goose/sessions/<YYYYMMDD_HHMMSS>.jsonl` | same dir | line 1 metadata, then one message per line (`legacy.rs:62-100,111`) |
| LLM request log | `.local/state/goose/logs/llm_request.<N>.jsonl` (rotated 0..n; temp `llm_request.<uuid>.jsonl`) | `AppData/Roaming/Block/goose/data/logs/` | one file per provider call (`providers/utils.rs:86,121-131`) |
| CLI history | `.local/state/goose/history.txt` (old `.config/goose/history.txt`) | `AppData/Roaming/Block/goose/data/history.txt` | rustyline V2: `#V2` header, one entry per line, `\n`/`\\` escaped (`goose-cli/src/session/mod.rs:196-197`; `rustyline-18.0.1/src/history.rs:463-465`) |

**Zed.** `data_dir` = `Library/Application Support/Zed` (macOS), `.local/share/zed` (Linux), `AppData/Local/Zed` (Windows) (`crates/paths/src/paths.rs:144-166`).

| Store | Path | Unit |
|---|---|---|
| Threads DB | `<data>/threads/threads.db` | `threads` row = one thread; `data` BLOB = zstd(JSON) of whole thread incl. all messages (`crates/agent/src/db.rs:444-457,535`) |
| Sidebar metadata | `<data>/db/0-{stable,preview,nightly,dev}/db.sqlite` table `sidebar_threads` | one row per thread incl. external-agent threads (`crates/db/src/db.rs:138,166`; `release_channel/src/lib.rs:216-223`; `agent_ui/src/thread_metadata_store.rs:1375-1465`) |

No separate text-thread/`contexts/*.json` store exists at this commit.

## 3. Record schema

### Goose `sessions.db` (schema v16, `session_manager.rs:28,1012-1098`)

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
Migration v10 also creates `threads`/`thread_messages` (`:1462-1487`); no INSERT into them exists, treat as empty. Migration v11 adds `provider_inventory_*` (model lists, no secrets).

- **Timestamp**: `messages.created_timestamp` = epoch **seconds** (`Message::user()` uses `Utc::now().timestamp()`, `goose-provider-types/src/conversation/message.rs:1035`); some clients write **ms**, normalised with `> 10_000_000_000 → /1000` (`session_manager.rs:31,729-741`). `messages.timestamp`, `sessions.created_at/updated_at` are SQLite `CURRENT_TIMESTAMP`/`datetime('now')` text `YYYY-MM-DD HH:MM:SS` UTC (`:1966`); legacy-imported sessions bind chrono values, written by sqlx as RFC 3339 (`sqlx-sqlite-0.9.0/src/types/chrono.rs:69`). Order within a second by `id` (`:1887-1890`).
- **Session id**: `sessions.id` = `YYYYMMDD_<n>` (`:1633-1647`); `messages.message_id` = `msg_<session_id>_<uuid>` (`:1941-1943`).
- **Working dir**: `sessions.working_dir`. **Git branch**: none.
- **Model/provider**: `sessions.provider_name`, `sessions.model_config_json` `{"model_name","temperature","max_tokens","toolshim","toolshim_model","request_params"?,"reasoning"?,"supports_vision"?}` (`goose-provider-types/src/model.rs:41-59`; headers are `#[serde(skip)]`); per message `metadata_json.inference.{provider,requestedModel,resolvedModel?,providerSessionId?}` (`message.rs:768-775`); per request `usage_ledger.model`.
- **Role**: `messages.role` ∈ `user`,`assistant` (`:720-725`). `session_type` ∈ `user,scheduled,sub_agent,hidden,terminal,gateway,acp` (`:46-57`).
- **content_json**: JSON array, tag `"type"` camelCase (`message.rs:317-330`):
  - `text`: `{"type":"text","text":"...","annotations"?:{audience,priority,lastModified},"_meta"?}` (rmcp `content.rs:23-34`)
  - `image`: `{"data","mimeType"}`; `document`: `{"data","mimeType","name"?}`
  - `toolRequest`: `{"id","toolCall":{"status":"success","value":{"name","arguments":{...}}} | {"status":"error","error":"..."},"metadata"?,"_meta"?}` (`message.rs:131-141`; `tool_result_serde.rs:7-25`; rmcp `model.rs:4142-4150`)
  - `toolResponse`: `{"id","toolResult":{"status":"success","value":{"content":[{"type":"text","text":..}|{"type":"image",..}|resource|resource_link|audio],"structuredContent"?,"isError"?}} | {"status":"error","error"}}` (`message.rs:175-183`; rmcp `model.rs:3886-3897`, `content.rs:256-264`). Older rows: `value` is a bare content array (`tool_result_serde.rs:142-145`).
  - `thinking`: `{"thinking","signature"}`; `redactedThinking`: `{"data"}`
  - `toolConfirmationRequest`: `{"id","toolName","arguments","prompt"}`; `actionRequired`: `{"data":{"actionType":...}}`; `systemNotification`: `{"notificationType","msg","data"?}`; `error`: `{"kind","message"}`
- **metadata_json**: `{"userVisible","agentVisible","inference"?,"outputTokenLimitReached"?,"steer"?,"turnContext"?,"usage"?,"operations"?}` (`message.rs:826-854`).

### Zed `threads.db` (`crates/agent/src/db.rs:450-485`)

```sql
CREATE TABLE threads (id TEXT PRIMARY KEY, summary TEXT NOT NULL, updated_at TEXT NOT NULL,
  data_type TEXT NOT NULL, data BLOB NOT NULL);
ALTER TABLE threads ADD COLUMN parent_id TEXT;
ALTER TABLE threads ADD COLUMN folder_paths TEXT; ALTER TABLE threads ADD COLUMN folder_paths_order TEXT;
ALTER TABLE threads ADD COLUMN created_at TEXT;
```
- `id` = ACP session id, UUID v4 string (`thread.rs:1430`; `#[serde(transparent)]` newtype, `agent-client-protocol-schema-1.9.1/src/v1/mod.rs:48-51`). `parent_id` = subagent parent (`db.rs:514-517`). `summary` = title. `updated_at`/`created_at` = `to_rfc3339()` e.g. `2026-01-02T03:04:05.123456789+00:00` (`db.rs:513,542`). `folder_paths` = sorted paths joined by `\n`; `folder_paths_order` = comma-separated display indices (`crates/util/src/path_list.rs:130-146`). `data_type` ∈ `zstd`,`json` (`db.rs:363-367`).
- Blob JSON = `DbThread` flattened + `"version":"0.3.0"` (`db.rs:53-89,189,505-510`): `title, messages[], updated_at (RFC 3339 "Z"), detailed_summary, initial_project_snapshot{worktree_snapshots:[{worktree_path, git_state:{remote_url,head_sha,current_branch,diff}}], timestamp}, cumulative_token_usage, request_token_usage{<user_msg_id>:{input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}}, model{provider,model}, profile, subagent_context{parent_thread_id,depth}, speed, thinking_enabled, thinking_effort, draft_prompt, ui_scroll_position, sandboxed_terminal_temp_dir, sandbox_grants{write_paths,network_hosts,...}` (`agent.rs:89-93`; `project/src/telemetry_snapshot.rs:33-45`; `legacy_thread.rs:45-49`; `language_model_core.rs:525-535`).
- **No per-message timestamps.** Only thread `updated_at`/`created_at` and `initial_project_snapshot.timestamp`.
- **Git branch**: `initial_project_snapshot.worktree_snapshots[].git_state.current_branch` (at thread start).
- `messages[]` are externally tagged serde enums with no renames (`thread.rs:202-208,287-301,743-759`):
  - `{"User":{"id":"<uuid>","content":[{"Text":"..."},{"Mention":{"uri":...,"content":"..."}},{"Image":{"source":"<base64 png>"}}]}}`
  - `{"Agent":{"content":[{"Text":"..."},{"Thinking":{"text":"...","signature":null}},{"RedactedThinking":"..."},{"ToolUse":{"id":"toolu_1","name":"terminal","raw_input":"{...}","input":{"type":"json","value":{...}},"is_input_complete":true,"thought_signature":null}}],"tool_results":{"toolu_1":{"tool_use_id":"toolu_1","tool_name":"terminal","is_error":false,"content":[{"Text":"..."}],"output":{...}}},"reasoning_details":null}}` (`language_model_core.rs:592-629`; `request.rs:67-76,148-152`; legacy single-value `content` accepted `request.rs:104-145`)
  - `"Resume"`, `{"Compaction":{"Summary":"..."}}` or `{"Compaction":{"ProviderNative":{...}}}`.

### Zed `db.sqlite` → `sidebar_threads` (final shape, `thread_metadata_store.rs:1424-1437,1459-1464`)

```sql
CREATE TABLE sidebar_threads(thread_id BLOB PRIMARY KEY, session_id TEXT, agent_id TEXT, title TEXT NOT NULL,
  updated_at TEXT NOT NULL, created_at TEXT, folder_paths TEXT, folder_paths_order TEXT, archived INTEGER DEFAULT 0,
  main_worktree_paths TEXT, main_worktree_paths_order TEXT, remote_connection TEXT) STRICT;
ALTER TABLE sidebar_threads ADD COLUMN interacted_at TEXT; ALTER TABLE sidebar_threads ADD COLUMN title_override TEXT;
CREATE TABLE archived_git_worktrees(id INTEGER PRIMARY KEY, worktree_path TEXT NOT NULL, main_repo_path TEXT NOT NULL,
  branch_name TEXT, staged_commit_hash TEXT, unstaged_commit_hash TEXT, original_commit_hash TEXT) STRICT;
CREATE TABLE thread_archived_worktrees(thread_id BLOB NOT NULL, archived_worktree_id INTEGER NOT NULL
  REFERENCES archived_git_worktrees(id), PRIMARY KEY (thread_id, archived_worktree_id)) STRICT;
```
`thread_id` = 16 raw UUID bytes (`sqlez/src/bindable.rs:360-370`); `session_id` = `threads.id`; `agent_id` NULL means native "Zed Agent", otherwise an external ACP agent whose transcript is *not* in `threads.db` (`:1499-1500,1725-1727`; `agent.rs:2742`); times RFC 3339 (`:1729-1740`); `remote_connection` JSON; `interacted_at` = last user send.

## 4. Joins

- Goose: `messages.session_id = sessions.id`; `usage_ledger.session_id` likewise. Tool pairing: `toolRequest.id` (assistant row) ↔ `toolResponse.id` (user row). Project path: `sessions.working_dir`.
- Zed: `sidebar_threads.session_id = threads.id` (+ `threads.parent_id` for subagents). Tool pairing inside one `Agent` message: `content[].ToolUse.id` ↔ `tool_results` key / `tool_use_id`. Project path: `threads.folder_paths` (split on `\n`), fallback `initial_project_snapshot.worktree_snapshots[].worktree_path`; branch from `git_state.current_branch` or `archived_git_worktrees.branch_name` via `thread_archived_worktrees`.

## 5. SQLite specifics

- Goose opens with `journal_mode=WAL`, `busy_timeout 30s`, dir chmod 0700 (`session_manager.rs:945-955`). Recent rows live in `sessions.db-wal` until checkpoint; a copy without `-wal` loses them. Collect `sessions.db*`.
- Zed `db.sqlite`: `PRAGMA journal_mode=WAL; synchronous=NORMAL` (`crates/db/src/db.rs:129-133`; `sqlez/src/thread_safe_connection.rs:339`) → same `-wal` caveat. `threads.db` is opened with plain `Connection::open_file` and no journal pragma in `agent/src/db.rs` (`sqlez/src/connection.rs:65`), so default rollback journal; a `threads.db-journal` may exist mid-write.
- Zed blobs: `zstd::encode_all(json, 3)` / `decode_all` (`db.rs:178-184,535,660`): standard zstd frames, no dictionary, content size present. Python: `zstandard.ZstdDecompressor().decompress(blob)`; fall back to `stream_reader` if the size header is missing. Rows with `data_type='json'` are raw UTF-8.
- No encryption in either tool.

## 6. Format versions

- Goose: `schema_version` table, `CURRENT_SCHEMA_VERSION=16`; migrations 1-16 are additive `ALTER TABLE ADD COLUMN` (`session_manager.rs:1318-1613`), so older DBs lack `message_id`, `metadata_json`, `provider_name`, `model_config_json`, `parent_session_id`, `usage_ledger`. Legacy JSONL sessions imported once when `schema_version` is absent (`:982-989,1145-1250`): line 1 `{"description","id"?,"created_at","updated_at","extension_data","message_count","working_dir"?, token fields}`, then `{"id","role","created","content":[...],"metadata"?}` (`legacy.rs:62-100,128-130`); filename `YYYYMMDD_HHMMSS` gives created time (`legacy.rs:111`). Imports from Claude Code/Codex/Pi JSONL also land in `sessions.db` (`import_formats/mod.rs:1-12`).
- Zed: blob `version` `"0.3.0"` current (`db.rs:189`); `"0.2.0"`/`"0.1.0"` = `SerializedThread {version, summary, updated_at, messages:[{id:int, role, segments:[{type:"text",text}|{type:"thinking",text,signature?}|{type:"RedactedThinking",data}], tool_uses:[{id,name,input}], tool_results:[{tool_use_id,is_error,content,output}], context, creases, is_hidden}], initial_project_snapshot, cumulative_token_usage, request_token_usage:[...], detailed_summary_state, model{provider,model}, profile}` (`legacy_thread.rs:23-164`); no `version` key = `LegacySerializedThread` with `messages[].text` (`:166-205`). Upgrade logic `db.rs:195-330`. Shared/exported threads use `SharedThread` version `"1.0.0"` (`db.rs:130-141`). `sidebar_threads` migrated in-place (`thread_metadata_store.rs:1373-1465`); cross-channel import copies rows between `0-<channel>` DBs (`thread_import.rs`).

## 7. Secrets to redact

- Goose: `llm_request.*.jsonl` holds the **entire provider request body** (system prompt, all messages, tool outputs) and responses (`request_log.rs:81-86,110-113`); headers/keys are not logged (`ModelConfig.request_headers` is `#[serde(skip)]`, `model.rs:58-59`). Credentials live in keyring or `.config/goose/secrets.yaml` (`config/base.rs:89-91,394`), and `config.yaml` may embed provider hosts. `recipe_json`/`user_recipe_values_json` can carry user-entered parameters; tool outputs in `content_json` may contain env dumps.
- Zed: blob fields `sandbox_grants.write_paths/network_hosts`, `draft_prompt`, `Mention.content` (inlined file contents), `initial_project_snapshot.git_state.diff` (full diff), `remote_connection` (host/user) in `sidebar_threads`. No API keys were found in thread storage.

## 8. Parser plan

**Globs (relative to home):** `.local/share/goose/sessions/sessions.db*`, `.local/share/goose/sessions/*.jsonl`, `.local/state/goose/logs/llm_request.*.jsonl`, `.local/state/goose/history.txt`, `.config/goose/history.txt`, `AppData/Roaming/Block/goose/data/sessions/sessions.db*`, `AppData/Roaming/Block/goose/data/logs/llm_request.*.jsonl`, `AppData/Roaming/Block/goose/data/history.txt`; Zed: `{Library/Application Support/Zed,.local/share/zed,AppData/Local/Zed}/threads/threads.db*` and `.../db/0-*/db.sqlite*`.

**Rows.** Goose: one CSV row per `content_json` block (plus one `system` row per session from `sessions`). Zed: one row per message content item and per `tool_results` entry; one `system` row per `sidebar_threads` entry with `agent_id` set (external agent, no transcript).

| CSV column | Goose | Zed |
|---|---|---|
| timestamp_utc | `created_timestamp` (÷1000 if >1e10) → ISO | thread `updated_at` for all messages (flag `approx`); `initial_project_snapshot.timestamp` for the thread-start row |
| session_id | `messages.session_id` | `threads.id` |
| project_path | `sessions.working_dir` | first of `folder_paths.split("\n")` |
| git_branch | empty | `git_state.current_branch` |
| turn_type | role `user`→`user`; `assistant`+`text`→`assistant`; `toolRequest`→`tool_use`; `toolResponse`→`tool_result`; `thinking`/`redactedThinking`→`thinking`; `systemNotification`/`error`/`actionRequired`→`system` | `User.Text/Mention/Image`→`user`; `Agent.Text`→`assistant`; `Thinking/RedactedThinking`→`thinking`; `ToolUse`→`tool_use`; `tool_results[*]`→`tool_result`; `Resume`/`Compaction`→`system` |
| model | `metadata_json.inference.requestedModel`, else `model_config_json.model_name` (prefix `provider_name/`) | `model.provider/model.model` |
| tool_name | `toolCall.value.name` (response: look up by id) | `ToolUse.name` / `tool_name` |
| tool_use_id | `toolRequest.id` / `toolResponse.id` | `ToolUse.id` / `tool_use_id` |
| summary | first 200 chars of text / `arguments` JSON / result text | same; `Mention.uri` for mentions |

Python: stdlib `sqlite3`, `json`; `zstandard` for Zed blobs. Open DBs read-only with `?immutable=1` after copying `-wal`.

**Fixtures.**
```sql
-- Goose sessions.db
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

Zed `threads.db` (store `data` = zstd of this JSON, `data_type='zstd'`):
```sql
INSERT INTO threads(id,parent_id,folder_paths,folder_paths_order,summary,updated_at,data_type,data,created_at)
VALUES ('6f1c0b2e-1111-4bbb-8ccc-000000000001',NULL,'/home/alice/proj','0','Fix flaky test','2026-03-01T09:01:05.000000000+00:00','zstd',X'<zstd>','2026-03-01T09:00:00.000000000+00:00');
```
```json
{"version":"0.3.0","title":"Fix flaky test","updated_at":"2026-03-01T09:01:05Z",
 "initial_project_snapshot":{"worktree_snapshots":[{"worktree_path":"/home/alice/proj","git_state":{"remote_url":"git@github.com:alice/proj.git","head_sha":"abc123","current_branch":"main","diff":null}}],"timestamp":"2026-03-01T09:00:00Z"},
 "model":{"provider":"anthropic","model":"claude-sonnet-4-5"},
 "messages":[
  {"User":{"id":"9a7d6c5b-2222-4ddd-9eee-000000000002","content":[{"Text":"run the tests"},{"Mention":{"uri":"file:///home/alice/proj/README.md","content":""}}]}},
  {"Agent":{"content":[{"Thinking":{"text":"use pytest","signature":null}},{"ToolUse":{"id":"toolu_01","name":"terminal","raw_input":"{\"command\":\"pytest -q\"}","input":{"type":"json","value":{"command":"pytest -q"}},"is_input_complete":true,"thought_signature":null}},{"Text":"All 3 tests pass."}],
   "tool_results":{"toolu_01":{"tool_use_id":"toolu_01","tool_name":"terminal","is_error":false,"content":[{"Text":"3 passed"}],"output":null}},"reasoning_details":null}},
  "Resume"]}
```
Zed `db.sqlite`:
```sql
INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,created_at,folder_paths,folder_paths_order,archived)
VALUES (randomblob(16),'6f1c0b2e-1111-4bbb-8ccc-000000000001',NULL,'Fix flaky test','2026-03-01T09:01:05+00:00','2026-03-01T09:00:00+00:00','/home/alice/proj','0',0);
INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,folder_paths,folder_paths_order)
VALUES (randomblob(16),'ext-claude-code-sess-1','claude-code','External thread','2026-03-01T10:00:00+00:00','/home/alice/proj','0');
```

**Confidence.** High: both DDLs, Goose content/metadata field names, Zed blob/enum shapes, zstd framing, path derivation, WAL settings, version handling. Medium: exact `agent_id` strings for external agents; `MentionUri` variant encoding (derive-default, variants not read); legacy `language_model::Role` spelling in 0.2.0 blobs. Not determined: `LOGS_TO_KEEP` value for `llm_request` rotation; whether Goose desktop writes ms timestamps (only the normaliser proves some client does); `~/.goose` and `.config/Goose` catalog entries were not found in Goose source at this commit.
