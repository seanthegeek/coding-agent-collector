# OpenClaw transcript schema

Catalog agent: `openclaw`. OpenClaw's transcript record shape (`type:
"session"` header, then `message`, `model_change`, `compaction` and other
entries linked by `id`/`parentId`) is the tree-structured session format of
its agent core; since mid-2026 the records live as rows in a per-agent SQLite
database rather than in `.jsonl` files, which remain only as legacy import
sources and archives. Path research is in
[../../collectors/research/openclaw.md](../../collectors/research/openclaw.md).

## 1. Source

openclaw/openclaw at [`3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9`](https://github.com/openclaw/openclaw/commit/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9)
(2026-10-04, version `2026.9.8`, agent schema version 24 per
[`package.json:5-9`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/package.json#L5-L9)), MIT, open source.

## 2. Transcript stores

Home-relative, with `.openclaw` replaceable by `.openclaw-<profile>` or the
legacy `.clawdbot`:

- `.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite` with `-wal`/`-shm`:
  the live store. One database per agent; one `session_windows` row per
  transcript generation; one `transcript_events` row per record
  ([`src/state/openclaw-agent-schema.sql:159-188`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L159-L188),[`566-604`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L566-L604)). `agentDir` can be
  moved by config ([`agents/agent-scope-config.ts:577-588`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/agent-scope-config.ts#L577-L588)).
- `.openclaw/agents/<agentId>/sessions/<sessionId>.jsonl`: legacy one-file-per-session
  transcripts, imported into SQLite by `openclaw doctor --fix` and then
  removed ([`docs/cli/doctor/state-migrations.md:60`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/doctor/state-migrations.md#L60)); a host that never ran
  doctor after upgrading still has them. `sessions/` at the state root is
  the older single-agent equivalent ([`docs/openclaw-agent-runtime.md:58-59`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/openclaw-agent-runtime.md#L58-L59)).
- Same directory, archives of reset or deleted sessions:
  `<sessionId>.jsonl.reset.<YYYY-MM-DDTHH-MM-SS[.mmm]Z>[.<32 hex generation>][.zst]`
  and `.jsonl.deleted.<...>` ([`config/sessions/artifacts.ts:10-32`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/artifacts.ts#L10-L32); naming
  [`session-accessor.sqlite-archive-artifact.ts:47`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-accessor.sqlite-archive-artifact.ts#L47),[`70`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-accessor.sqlite-archive-artifact.ts#L70)). `.zst` files are a
  single zstd frame of the JSONL ([`config/sessions/archive-compression.ts:11-30`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/archive-compression.ts#L11-L30)). The
  canonical copy of each archive is also a blob in `session_transcript_archives`
  ([`openclaw-agent-schema.sql:606-624`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L606-L624)). Deleting a session keeps a `.deleted`
  archive unless it was incognito ([`docs/cli/sessions.md:212-217`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/sessions.md#L212-L217)).
- Also there: `<id>.checkpoint.<uuid>.jsonl` compaction checkpoints,
  `<id>.trajectory.jsonl` runtime trajectories, `*.migrated[.N]` and
  `*.pre-doctor-*-repair-*.bak` rollback copies ([`artifacts.ts:13-17`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/artifacts.ts#L13-L17),[`96-116`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/artifacts.ts#L96-L116)),
  and a legacy `sessions.json` index.
- Not transcripts but useful: `state/openclaw.sqlite` `audit_events`
  ([`openclaw-state-schema.sql:149-171`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L149-L171)) and `channel_ingress_events.payload_json`
  (raw inbound chat messages, [`:1301-1323`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L1301-L1323)); `logs/raw-stream.jsonl`,
  `logs/anthropic-payload.jsonl`, `logs/cache-trace.jsonl` debug traces.

## 3. Record schema

Each `transcript_events.event_json` (or decompressed `event_zstd`) and each
legacy JSONL line is one entry ([`agents/sessions/session-manager-types.ts:9-119`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/sessions/session-manager-types.ts#L9-L119)):

- Header: `{type:"session", version, id, timestamp, cwd, parentSession?}`,
  always the first record ([`config/sessions/transcript-header.ts:20-29`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/transcript-header.ts#L20-L29);
  [`session-accessor.sqlite-transcript-header.ts:7-35`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-accessor.sqlite-transcript-header.ts#L7-L35)). `cwd` defaults to the
  process cwd when the caller gives none.
- Every other entry: `type`, `id`, `parentId` (null at the root), `timestamp`
  (ISO 8601 string, UTC from `toISOString()`), optional `appendMode:"side"`.
  Types: `message`, `thinking_level_change {thinkingLevel}`,
  `model_change {provider, modelId}`, `compaction {summary, firstKeptEntryId,
  tokensBefore, tokensAfter?, details?, fromHook?}`, `reset {reason:
  new|reset|idle|daily|cron-stale}`, `branch_summary {fromId, summary}`,
  `custom {customType, data}`, `custom_message {customType, content, display}`,
  `label {targetId, label}`, `session_info {name}`. Unknown records with
  `id`/`parentId` (for example `leaf`) are preserved opaquely
  ([`config/sessions/session-entry-codec.ts:181-221`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-entry-codec.ts#L181-L221)).
- `message.message` is an `AgentMessage`
  ([`packages/agent-core/src/types.ts:467-479`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/agent-core/src/types.ts#L467-L479)), discriminated by `role`
  ([`packages/llm-core/src/types.ts:369-390`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/llm-core/src/types.ts#L369-L390),[`516-561`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/llm-core/src/types.ts#L516-L561)):
  - `user`: `content` string or blocks, `timestamp` (epoch ms).
    `runtimeContext` marks injected runtime context, not human input.
  - `assistant`: `content` blocks, `api`, `provider`, `model`,
    `responseModel?`, `responseId?`, `turnId?`, `usage {input, output,
    cacheRead, cacheWrite, totalTokens, cost{...}}`, `stopReason`
    (`stop|length|toolUse|error|aborted`, [`:357`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/llm-core/src/types.ts#L357)), `errorMessage?`,
    `errorBody?`, `providerReplay?`, `timestamp` ms.
  - `toolResult`: `toolCallId`, `toolName`, `content` (text/image blocks),
    `details?`, `isError`, `timestamp` ms.
  - `bashExecution`: `command`, `output`, `exitCode`, `cancelled`,
    `truncated`, `fullOutputPath?`, `timestamp` ms (user-run `!` commands,
    [`agent-core/src/types.ts:397-416`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/agent-core/src/types.ts#L397-L416)).
  - `custom {customType, content, display, details?}`, `branchSummary
    {summary, fromId}`, `compactionSummary {summary, tokensBefore}` (its
    `timestamp` may be a string, [`:418-461`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/agent-core/src/types.ts#L418-L461)).
- Content blocks ([`llm-core/src/types.ts:264-313`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/llm-core/src/types.ts#L264-L313)): `text {text}`, `thinking
  {thinking, thinkingSignature?, redacted?}`, `image {data (base64),
  mimeType}`, `toolCall {id, name, arguments (object)}`.

Row metadata: `transcript_events.created_at` is epoch ms, taken from the
record's timestamp or `Date.now()`
([`session-accessor.sqlite-transcript-store.ts:173`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-accessor.sqlite-transcript-store.ts#L173)); `seq` orders a session from 0.
`session_windows`: `session_key`, `previous_session_id`, `reason`
(`initial|reset|rollover|fork|rewind|switch|recovery|compaction`), `channel`,
`account_id`, `chat_type`, `model_provider`, `model`, `started_at`,
`ended_at`, `status`, `parent_session_key`, `spawned_by`, `display_name`.
`session_nodes` ([`:16-49`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L16-L49)): `session_key`, `current_session_id`,
`entry_json` (session metadata), `created_via`
(`operator|spawn|channel|cron|...`), `created_actor_type/id`, `label`.

## 4. Joins

- Session: `transcript_events.session_id = session_windows.session_id`; the
  header `id` equals it. Generations of one conversation share
  `session_key` and chain through `previous_session_id`.
- Session key encodes the origin: `agent:<agentId>:<channel>:<accountId>:direct:<peerId>`,
  `agent:<agentId>:<channel>:<peerKind>:<peerId>`, or `agent:<agentId>:main`-style
  keys ([`routing/session-key.ts:206-261`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/routing/session-key.ts#L206-L261)). This is how a responder ties a
  transcript to a Telegram chat or WhatsApp number.
- Tool call to result: `toolCall.id` in an assistant message equals
  `toolResult.toolCallId` in a later `message` entry.
- Tree: `parentId → id`; `transcript_event_identities` indexes it
  ([`openclaw-agent-schema.sql:684-694`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L684-L694)).
- Subagents: `session_nodes.parent_session_key`/`spawned_by`, and
  `fork_source_session_id`/`fork_source_entry_id` for forks; header
  `parentSession`.
- Project: header `cwd`. No git branch is recorded.

## 5. SQLite and compression

WAL journal ([`infra/sqlite-wal.ts:169`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/sqlite-wal.ts#L169)), read through
`sqlite_util.py` with sidecars. Payloads of 1 KiB to 4 MiB that shrink by at
least 10% are stored as `event_zstd` (one zstd frame, level 1, checksum,
no dictionary) with `event_json` NULL and the original length in
`event_utf8_bytes`; others stay in `event_json`
([`config/sessions/transcript-payload.ts:22-24`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/transcript-payload.ts#L22-L24),[`215-272`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/transcript-payload.ts#L215-L272); [`infra/zstd-codec.ts:22-37`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/zstd-codec.ts#L22-L37)).
The parser needs `zstandard`. Cold storage moves old generations into
`session_transcript_cold_archives` (blob, or a file in the sessions directory
when `storage='file'`, [`:633-648`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L633-L648)); `archive_blob` in both archive tables
is JSONL, zstd when `encoding='zstd'`.

## 6. Format versions

Header `version`: current 4, minimum readable 3; versions 1-2 need doctor
import and may lack `id`/`parentId`; the old `hookMessage` role becomes
`custom` with `customType:"hook"` ([`config/sessions/version.ts:1-4`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/version.ts#L1-L4); [`session-entry-codec.ts:154-179`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/session-entry-codec.ts#L154-L179)).
Database schema version is in `schema_meta.schema_version`
([`openclaw-agent-schema.sql:6-14`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L6-L14)). Test fixtures for schema v1, v14, v15, v19,
v21 and v22 are in `test/fixtures/sqlite/`.

## 7. Secrets

In the same database as the transcripts: `auth_profile_store.store_json`,
`auth_profile_state.state_json` and `session_suggestions`
([`state/secret-state-tables.ts:31-35`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/secret-state-tables.ts#L31-L35)); do not emit them. In records:
`thinkingSignature` and `providerReplay.data` are opaque provider state;
`image.data` is base64 media; `toolResult.content` and `bashExecution.output`
are raw tool output and may contain anything the agent read, including
`.env` files.

## 8. Parser plan

Selection: `*/agent/openclaw-agent.sqlite` under an `openclaw` artifact
(plus `-wal`); `*/sessions/*.jsonl`, `*.jsonl.reset.*`, `*.jsonl.deleted.*`
(decompress `.zst`). Skip `*.trajectory.jsonl`, `*.checkpoint.*.jsonl` and
`*.migrated*` to avoid duplicates. SQL: `SELECT e.rowid, e.session_id, e.seq,
e.event_json, e.event_zstd, e.created_at, w.model, w.channel, w.session_key
FROM transcript_events e LEFT JOIN session_windows w USING (session_id) ORDER
BY e.session_id, e.seq`. Then archive blobs.

| Column | Source |
| --- | --- |
| timestamp_utc | entry `timestamp`; else `message.timestamp` (ms); else `created_at` (ms) |
| session_id | `session_id` / header `id` |
| project_path | header `cwd` of the session |
| git_branch | empty |
| turn_type | role `user` → user; `assistant` text → assistant, `toolCall` block → tool_use, `thinking` block → thinking; `toolResult` → tool_result; `bashExecution` → tool_use (tool `bash`); other entry types and roles → system |
| model | assistant `responseModel` or `model`; `model_change.modelId` |
| tool_name | `toolCall.name` / `toolResult.toolName` |
| tool_use_id | `toolCall.id` / `toolResult.toolCallId` |
| text | text blocks; `toolCall.arguments.command`/`path`/`url` else JSON; tool result text; `summary` for compaction; `reason` for reset |
| source_line | `transcript_events.rowid`, or the JSONL line number |

Put `session_key` (channel and peer) into the system row for each session.
The shell tool is named `exec` ([`agents/core-tool-factory-descriptors.ts:20`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/core-tool-factory-descriptors.ts#L20)); `api` values include
`anthropic-messages` ([`llm-core/src/types.ts:23`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/llm-core/src/types.ts#L23)).

Fixture (JSONL form; the SQLite form stores the same strings in `event_json`):

```json
{"type":"session","version":4,"id":"7d0c2a8e-1111-4000-8000-000000000001","timestamp":"2026-10-01T09:00:00.000Z","cwd":"/home/alice/.openclaw/workspace"}
{"type":"message","id":"a1b2c3d4","parentId":null,"timestamp":"2026-10-01T09:00:01.000Z","message":{"role":"user","content":[{"type":"text","text":"check disk space on the server"}],"timestamp":1759309201000}}
{"type":"message","id":"b2c3d4e5","parentId":"a1b2c3d4","timestamp":"2026-10-01T09:00:04.000Z","message":{"role":"assistant","content":[{"type":"thinking","thinking":"Use exec with df."},{"type":"text","text":"Checking."},{"type":"toolCall","id":"call_01","name":"exec","arguments":{"command":"df -h"}}],"api":"anthropic-messages","provider":"anthropic","model":"claude-sonnet-4-5","usage":{"input":900,"output":40,"cacheRead":0,"cacheWrite":0,"totalTokens":940,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"toolUse","timestamp":1759309204000}}
{"type":"message","id":"c3d4e5f6","parentId":"b2c3d4e5","timestamp":"2026-10-01T09:00:05.000Z","message":{"role":"toolResult","toolCallId":"call_01","toolName":"exec","content":[{"type":"text","text":"/dev/sda1  50G  20G  30G  40% /"}],"isError":false,"timestamp":1759309205000}}
{"type":"model_change","id":"d4e5f6a7","parentId":"c3d4e5f6","timestamp":"2026-10-01T09:01:00.000Z","provider":"openai","modelId":"gpt-5"}
```

Confidence. High: table and column names, entry and message field names,
compression rule, archive naming, version constants. Medium: that legacy
`.jsonl` files are removed after import on every path; `cwd` meaning the
workspace. Not
determined: the shapes of `trajectory_runtime_events`,
`acp_parent_stream_events` and `custom.data` per `customType`; whether
cold-archived generations keep any `transcript_events` rows.
