# Zed agent thread schema

Catalog agent: `zed`. Covers Zed's built-in agent panel threads. Researched
together with Goose ([goose.md](goose.md)). Paths cited are relative to the
clone.

## 1. Source

zed-industries/zed at [`a84689073d296dfd39987bc7dd478e43ef76d83a`](https://github.com/zed-industries/zed/commit/a84689073d296dfd39987bc7dd478e43ef76d83a); agent
crates GPL-3.0-or-later ([`crates/agent/Cargo.toml:6`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/Cargo.toml#L6),
[`crates/agent_ui/Cargo.toml:6`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/Cargo.toml#L6)). Rust; sqlez (Zed's own SQLite wrapper),
zstd crate, agent-client-protocol-schema 1.9.1.

## 2. Transcript stores

`data_dir` is `Library/Application Support/Zed` (macOS), `.local/share/zed`
(Linux), `AppData/Local/Zed` (Windows) ([`crates/paths/src/paths.rs:144-166`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/paths/src/paths.rs#L144-L166)).

| Store | Path | Unit |
| --- | --- | --- |
| Threads database | `<data>/threads/threads.db` | `threads` row = one thread; `data` BLOB = zstd(JSON) of the whole thread including all messages ([`crates/agent/src/db.rs:444-457`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L444-L457),[`535`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L535)) |
| Sidebar metadata | `<data>/db/0-{stable,preview,nightly,dev}/db.sqlite`, table `sidebar_threads` | one row per thread, including external-agent threads ([`crates/db/src/db.rs:138`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/db/src/db.rs#L138),[`166`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/db/src/db.rs#L166); [`release_channel/src/lib.rs:216-223`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/release_channel/src/lib.rs#L216-L223); [`agent_ui/src/thread_metadata_store.rs:1375-1465`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1375-L1465)) |

No separate text-thread or `contexts/*.json` store exists at this commit.

## 3. Record schema

`threads.db` ([`crates/agent/src/db.rs:450-485`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L450-L485)):

```sql
CREATE TABLE threads (id TEXT PRIMARY KEY, summary TEXT NOT NULL, updated_at TEXT NOT NULL,
  data_type TEXT NOT NULL, data BLOB NOT NULL);
ALTER TABLE threads ADD COLUMN parent_id TEXT;
ALTER TABLE threads ADD COLUMN folder_paths TEXT; ALTER TABLE threads ADD COLUMN folder_paths_order TEXT;
ALTER TABLE threads ADD COLUMN created_at TEXT;
```

`id` is the ACP session id, a UUID v4 string ([`thread.rs:1430`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/thread.rs#L1430);
`#[serde(transparent)]` newtype, [`agent-client-protocol-schema-1.9.1/src/v1/mod.rs:48-51`](https://github.com/agentclientprotocol/agent-client-protocol/blob/7e87dc205a7325bd07d0249fd20bb7486ee6ba95/agent-client-protocol-schema/src/v1/mod.rs#L48-L51)).
`parent_id` is the subagent parent ([`db.rs:514-517`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L514-L517)). `summary` is the
title. `updated_at` and `created_at` are `to_rfc3339()`, for example
`2026-01-02T03:04:05.123456789+00:00` ([`db.rs:513`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L513),[`542`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L542)). `folder_paths` is
sorted paths joined by `\n`; `folder_paths_order` is comma-separated display
indices ([`crates/util/src/path_list.rs:130-146`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/util/src/path_list.rs#L130-L146)). `data_type` is `zstd` or
`json` ([`db.rs:363-367`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L363-L367)).

Blob JSON is `DbThread` flattened plus `"version":"0.3.0"`
([`db.rs:53-89`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L53-L89),[`189`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L189),[`505-510`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L505-L510)): `title, messages[], updated_at (RFC 3339 "Z"),
detailed_summary, initial_project_snapshot{worktree_snapshots:[{worktree_path,
git_state:{remote_url, head_sha, current_branch, diff}}], timestamp},
cumulative_token_usage, request_token_usage{<user_msg_id>:{input_tokens,
output_tokens, cache_creation_input_tokens, cache_read_input_tokens}},
model{provider, model}, profile, subagent_context{parent_thread_id, depth},
speed, thinking_enabled, thinking_effort, draft_prompt, ui_scroll_position,
sandboxed_terminal_temp_dir, sandbox_grants{write_paths, network_hosts, ...}`
([`agent.rs:89-93`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/agent.rs#L89-L93); [`project/src/telemetry_snapshot.rs:33-45`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/project/src/telemetry_snapshot.rs#L33-L45);
[`legacy_thread.rs:45-49`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/legacy_thread.rs#L45-L49); [`language_model_core.rs:525-535`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/language_model_core/src/language_model_core.rs#L525-L535)).

There are no per-message timestamps, only the thread's `updated_at` and
`created_at` and `initial_project_snapshot.timestamp`. Git branch is
`initial_project_snapshot.worktree_snapshots[].git_state.current_branch`,
captured at thread start.

`messages[]` are externally tagged serde enums with no renames
([`thread.rs:202-208`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/thread.rs#L202-L208),[`287-301`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/thread.rs#L287-L301),[`743-759`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/thread.rs#L743-L759)):

- `{"User":{"id":"<uuid>","content":[{"Text":"..."},{"Mention":{"uri":...,"content":"..."}},{"Image":{"source":"<base64 png>"}}]}}`
- `{"Agent":{"content":[{"Text":"..."},{"Thinking":{"text":"...","signature":null}},{"RedactedThinking":"..."},{"ToolUse":{"id":"toolu_1","name":"terminal","raw_input":"{...}","input":{"type":"json","value":{...}},"is_input_complete":true,"thought_signature":null}}],"tool_results":{"toolu_1":{"tool_use_id":"toolu_1","tool_name":"terminal","is_error":false,"content":[{"Text":"..."}],"output":{...}}},"reasoning_details":null}}`
  ([`language_model_core.rs:592-629`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/language_model_core/src/language_model_core.rs#L592-L629); [`request.rs:67-76`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/language_model_core/src/request.rs#L67-L76),[`148-152`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/language_model_core/src/request.rs#L148-L152); a legacy
  single-value `content` is accepted, [`request.rs:104-145`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/language_model_core/src/request.rs#L104-L145))
- `"Resume"`, `{"Compaction":{"Summary":"..."}}` or `{"Compaction":{"ProviderNative":{...}}}`.

`db.sqlite` → `sidebar_threads` (final shape,
[`thread_metadata_store.rs:1424-1437`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1424-L1437),[`1459-1464`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1459-L1464)):

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

`thread_id` is 16 raw UUID bytes ([`sqlez/src/bindable.rs:360-370`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/sqlez/src/bindable.rs#L360-L370));
`session_id` equals `threads.id`; `agent_id` NULL means the native Zed Agent,
otherwise an external ACP agent whose transcript is not in `threads.db`
([`thread_metadata_store.rs:1499-1500`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1499-L1500),[`1725-1727`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1725-L1727); [`agent.rs:2742`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/agent.rs#L2742)); times are RFC 3339
([`:1729-1740`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1729-L1740)); `remote_connection` is JSON; `interacted_at` is the last user
send.

## 4. Joins

`sidebar_threads.session_id = threads.id` (plus `threads.parent_id` for
subagents). Tool pairing inside one `Agent` message: `content[].ToolUse.id`
with the `tool_results` key or `tool_use_id`. Project path:
`threads.folder_paths` split on `\n`, fallback
`initial_project_snapshot.worktree_snapshots[].worktree_path`; branch from
`git_state.current_branch` or `archived_git_worktrees.branch_name` through
`thread_archived_worktrees`.

## 5. SQLite and compression

`db.sqlite`: `PRAGMA journal_mode=WAL; synchronous=NORMAL`
([`crates/db/src/db.rs:129-133`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/db/src/db.rs#L129-L133); [`sqlez/src/thread_safe_connection.rs:61-62`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/sqlez/src/thread_safe_connection.rs#L61-L62)),
so collect the `-wal` sidecar. `threads.db` is opened with plain
`Connection::open_file` and no journal pragma ([`sqlez/src/connection.rs:65`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/sqlez/src/connection.rs#L65)),
so it uses the default rollback journal and a `threads.db-journal` may exist
mid-write. Blobs are `zstd::encode_all(json, 3)` / `decode_all`
([`db.rs:178-184`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L178-L184),[`535`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L535),[`660`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L660)): standard zstd frames, no dictionary, content size
present. In Python, `zstandard.ZstdDecompressor().decompress(blob)`, falling
back to `stream_reader` if the size header is missing. Rows with
`data_type='json'` are raw UTF-8. No encryption.

## 6. Format versions

Blob `version` `"0.3.0"` is current ([`db.rs:189`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L189)); `"0.2.0"` and `"0.1.0"`
are `SerializedThread {version, summary, updated_at, messages:[{id:int,
role, segments:[{type:"text",text}|{type:"thinking",text,signature?}|
{type:"RedactedThinking",data}], tool_uses:[{id,name,input}],
tool_results:[{tool_use_id,is_error,content,output}], context, creases,
is_hidden}], initial_project_snapshot, cumulative_token_usage,
request_token_usage:[...], detailed_summary_state, model{provider,model},
profile}` ([`legacy_thread.rs:23-164`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/legacy_thread.rs#L23-L164)); no `version` key means
`LegacySerializedThread` with `messages[].text` ([`:166-205`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/legacy_thread.rs#L166-L205)). Upgrade logic
[`db.rs:195-330`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L195-L330). Shared and exported threads use `SharedThread` version
`"1.0.0"` ([`db.rs:130-141`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent/src/db.rs#L130-L141)). `sidebar_threads` is migrated in place
([`thread_metadata_store.rs:1373-1465`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_metadata_store.rs#L1373-L1465)); cross-channel import copies rows
between `0-<channel>` databases ([`thread_import.rs`](https://github.com/zed-industries/zed/blob/a84689073d296dfd39987bc7dd478e43ef76d83a/crates/agent_ui/src/thread_import.rs)).

## 7. Secrets

Blob fields `sandbox_grants.write_paths`/`network_hosts`, `draft_prompt`,
`Mention.content` (inlined file contents), `initial_project_snapshot.git_state.diff`
(full diff), and `remote_connection` (host and user) in `sidebar_threads`. No
API keys were found in thread storage; the collector flags `settings.json`
separately.

## 8. Parser plan

Globs: `{Library/Application Support/Zed,.local/share/zed,AppData/Local/Zed}/threads/threads.db*`
and `.../db/0-*/db.sqlite*`. Requires the `zstandard` package.

Rows: one per message content item and per `tool_results` entry; one
`system` row per `sidebar_threads` entry with `agent_id` set (external agent,
no transcript).

| Column | Source |
| --- | --- |
| timestamp_utc | thread `updated_at` for all messages (approximate); `initial_project_snapshot.timestamp` for the thread-start row |
| session_id | `threads.id` |
| project_path | first of `folder_paths.split("\n")` |
| git_branch | `git_state.current_branch` |
| turn_type | `User.Text/Mention/Image` → user; `Agent.Text` → assistant; `Thinking`/`RedactedThinking` → thinking; `ToolUse` → tool_use; `tool_results[*]` → tool_result; `Resume`/`Compaction` → system |
| model | `model.provider/model.model` |
| tool_name, tool_use_id | `ToolUse.name` / `tool_name`, `ToolUse.id` / `tool_use_id` |
| text | text, `arguments` JSON, result text; `Mention.uri` for mentions |

Fixtures. `threads.db` (`data` is the zstd of the JSON below,
`data_type='zstd'`):

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

`db.sqlite`:

```sql
INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,created_at,folder_paths,folder_paths_order,archived)
VALUES (randomblob(16),'6f1c0b2e-1111-4bbb-8ccc-000000000001',NULL,'Fix flaky test','2026-03-01T09:01:05+00:00','2026-03-01T09:00:00+00:00','/home/alice/proj','0',0);
INSERT INTO sidebar_threads(thread_id,session_id,agent_id,title,updated_at,folder_paths,folder_paths_order)
VALUES (randomblob(16),'ext-claude-code-sess-1','claude-code','External thread','2026-03-01T10:00:00+00:00','/home/alice/proj','0');
```

Confidence. High: DDL, blob and enum shapes, zstd framing, path derivation,
WAL settings, version handling. Medium: exact `agent_id` strings for
external agents; `MentionUri` variant encoding; legacy `Role` spelling in
0.2.0 blobs.
