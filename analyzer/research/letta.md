# Letta transcript schema

Catalog agent: `letta`. Letta Code (the current `letta` CLI) keeps
conversations on the Letta server by default, but writes two parseable
JSONL stores under `~/.letta` and, in local-backend mode, the full message
history. The retired Letta V1 Python server kept messages in SQLite. Paths
are in [`collectors/research/letta.md`](../../collectors/research/letta.md).

## 1. Source

letta-ai/letta-code at [`77faf36e34378946c8e69c0bfaa5595a7be4c326`](https://github.com/letta-ai/letta-code/commit/77faf36e34378946c8e69c0bfaa5595a7be4c326), Apache-2.0. The local-backend
message types are `@earendil-works/pi-ai`, read in earendil-works/pi at
[`200387122ca450d6387f033949423114a270b96c`](https://github.com/earendil-works/pi/commit/200387122ca450d6387f033949423114a270b96c) (letta-code pins `^0.99.1`; the
pi checkout is newer, so optional fields may differ). V1 SQLite from
letta-ai/letta tag 0.11.7 at [`bf9356ceaf8ac4c80f1b418f209ad49b04986885`](https://github.com/letta-ai/letta/commit/bf9356ceaf8ac4c80f1b418f209ad49b04986885).

## 2. Transcript files

| Glob (relative to home) | One file per | Mode |
| --- | --- | --- |
| `.letta/transcripts/*/*/transcript.jsonl` | agent and conversation | every turn, both backends |
| `.letta/lc-local-backend/conversations/*/messages.jsonl` | conversation | local backend only |
| `.letta/sessions.jsonl` | user (two lines per session) | always |
| `.letta/logs/chunk-logs/*/*.jsonl` | agent and CLI session, last 5 kept | always, truncated |
| `.letta/sqlite.db` | user | V1 server up to at least 0.11.7 |

`transcripts/<agent>/<conversation>/` names are the ids with anything outside
`[a-zA-Z0-9._-]` replaced by `_`
([reflection-transcript.ts:578-581](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/reflection-transcript.ts#L578-L581), [911-925](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/reflection-transcript.ts#L911-L925)); `state.json` and
`payload-*.json` sit beside it. Local-backend conversation directories are
base64url of `conversation:<id>`, or `default:<agent id>` for an agent's
default conversation ([local-store.ts:283-285](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-store.ts#L283-L285), [3262-3266](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-store.ts#L3262-L3266)), next to
`conversation.json`, `manifest.json` and `system-prompt.json`.

## 3. Record schema

**Reflection transcript** (`transcript.jsonl`). Appended after each completed
turn ([use-conversation-loop.ts:1443-1452](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/app/use-conversation-loop.ts#L1443-L1452), [reflection-transcript.ts:927-952](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/reflection-transcript.ts#L927-L952)).
One object per line ([reflection-transcript.ts:54-71](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/reflection-transcript.ts#L54-L71)):
`kind` in `user|assistant|reasoning|error` with `text`; or `kind:"tool_call"`
with `name`, `argsText`, `resultText`, `resultOk`. Every line has
`captured_at` (ISO 8601 UTC string, the same value for all lines of one turn
batch) and optional `source_line_id`, `source_message_id`. No model, no cwd,
no tool call id: a call and its result share one line.

**Local-backend transcript** (`messages.jsonl`, `message_format`
`pi-session-entry-jsonl`, `schema_version` 2 in `manifest.json`;
[local-transcript.ts:24-46](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L24-L46)). Line 1 is the header
`{type:"session", version:3, id, timestamp, cwd}`; later lines are
`{type:"message", id, parentId, timestamp, message}` or
`{type:"compaction", id, parentId, timestamp, summary, firstKeptEntryId, tokensBefore, message, details}`
([local-transcript.ts:122-157](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L122-L157), [236-246](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L236-L246), [local-store.ts:3036-3061](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-store.ts#L3036-L3061)).
Entry `id` is 8 hex characters; entry `timestamp` is ISO, taken from
`message.metadata.created_at` or `message.timestamp`
([local-transcript.ts:479-494](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L479-L494)).

`message` ([local-message.ts:26-86](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-message.ts#L26-L86)) has `id` (prefix `letta-msg-`,
[local-store.ts:135-137](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-store.ts#L135-L137)), `role`, `timestamp` (Unix ms), optional
`metadata` {`created_at`, `agent_id`, `conversation_id`, `provider`{`provider_id`,`model_id`,`usage`}}, and:

- `role:"user"`: `content` string or array of `text`/`image` parts ([pi types.ts:542-546](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L542-L546)).
- `role:"assistant"`: `content` array of `{type:"text",text}`,
  `{type:"thinking",thinking,thinkingSignature?,redacted?}`,
  `{type:"toolCall",id,name,arguments}`; plus `api`, `provider`, `model`,
  `usage`, `stopReason` ([types.ts:397-427](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L397-L427), [548-571](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L548-L571)).
- `role:"toolResult"`: `toolCallId`, `toolName`, `content` (text/image), `isError` ([types.ts:596-609](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/types.ts#L596-L609)).

**sessions.jsonl** ([session-history.ts:6-35](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/agent/session-history.ts#L6-L35)): `agent_id`, `session_id`,
`timestamp` (ms), `project`, `model`, `provider`, `usage`, `duration`, `cost`,
and on the exit line `message_count`, `tool_call_count`, `exit_reason`
([116-158](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/agent/session-history.ts#L116-L158)). Session metadata, not turns.

**Chunk logs** hold the last 100 server stream chunks with content cut to
200 characters ([chunk-log.ts:1-12](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/chunk-log.ts#L1-L12), [27-30](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/chunk-log.ts#L27-L30)). Useful for message ids
and timing only; not parsed into turns.

## 4. Joins

- Reflection transcript: agent and conversation from the two directory names.
  Project path: the `sessions.jsonl` line with the same `agent_id` whose
  `timestamp` is nearest before `captured_at` (heuristic; a session id is not
  stored in the transcript).
- Local backend: session id is the header `id` (conversation id); project
  path is the header `cwd`; `conversation.json` gives `agent_id`
  ([local-types.ts:30-43](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-types.ts#L30-L43)) and `lc-local-backend/agents/*.json` the agent
  `name`, `model`, `system` ([local-types.ts:18-28](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-types.ts#L18-L28)). `toolCall.id` joins
  `toolResult.toolCallId`. Entries chain by `parentId`.
- Subagents: `conversation.json` `parent_agent_id`, `is_subagent`.

## 5. SQLite or binary stores

No SQLite in Letta Code. V1 `~/.letta/sqlite.db` ([0.11.7 db.py:149](https://github.com/letta-ai/letta/blob/bf9356ceaf8ac4c80f1b418f209ad49b04986885/letta/server/db.py#L149)), table
`messages` ([orm/message.py:15-61](https://github.com/letta-ai/letta/blob/bf9356ceaf8ac4c80f1b418f209ad49b04986885/letta/orm/message.py#L15-L61)): `id`, `agent_id`, `role`
(`user|assistant|system|tool`), `text`, `content` (JSON parts), `model`,
`tool_calls` (OpenAI-shaped JSON), `tool_call_id`, `tool_returns`, `step_id`,
`sequence_id`, `created_at` ([orm/base.py:16](https://github.com/letta-ai/letta/blob/bf9356ceaf8ac4c80f1b418f209ad49b04986885/letta/orm/base.py#L16)). Proposed as a later parser;
the JSON column encodings were not verified.

## 6. Format versions

Local backend: schema 1 (`pi-ai-message-jsonl`, bare message per line) and
schema 2 (session entries); `letta local-backend migrate-transcripts`
converts 1 to 2 and leaves `messages.jsonl.pre-pi-backup-*`
([local-transcript.ts:24-81](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L24-L81)). Messages may be re-appended
with the same `message.id` as replacement snapshots
([local-transcript.ts:173-182](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/backend/local/local-transcript.ts#L173-L182)); keep the last. Reflection
`state.json` `schema_version` is `v3_assistant_steps`
([reflection-transcript.ts:28-38](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/cli/helpers/reflection-transcript.ts#L28-L38)).

## 7. Secrets

`thinkingSignature` and `textSignature` are opaque provider blobs. Tool
arguments and results can hold pasted keys. V1 `sqlite.db` table `providers`
column `api_key` ([0.11.7 orm/provider.py:30-32](https://github.com/letta-ai/letta/blob/bf9356ceaf8ac4c80f1b418f209ad49b04986885/letta/orm/provider.py#L30-L32)).

## 8. Parser plan

Parse `transcript.jsonl` and `messages.jsonl`; when both exist for one
conversation, prefer `messages.jsonl` (it has models, tool ids and per-message
times). Use `sessions.jsonl` only for project attribution.

| Column | transcript.jsonl | messages.jsonl |
| --- | --- | --- |
| timestamp_utc | `captured_at` | entry `timestamp` |
| session_id | conversation directory name | header `id` |
| project_path | `sessions.jsonl` `project` (heuristic) | header `cwd` |
| git_branch | empty | empty |
| turn_type | `user`, `assistant`; `reasoning` → thinking; `error` → system; `tool_call` → one tool_use and one tool_result row | role/part type; `compaction` → system |
| model | empty | `message.model` |
| tool_name, tool_use_id | `name`, empty | `toolCall.name`/`id`, `toolResult.toolName`/`toolCallId` |
| text | `text`; `argsText`; `resultText` | text, thinking, arguments JSON, result text |

Fixture `.letta/transcripts/agent-1a2b/conv-9f/transcript.jsonl`:

```json
{"kind":"user","text":"list the repo","captured_at":"2026-10-01T12:00:05.120Z","source_line_id":"ui-1"}
{"kind":"tool_call","name":"Bash","argsText":"{\"command\":\"ls\"}","resultText":"README.md","resultOk":true,"captured_at":"2026-10-01T12:00:05.120Z","source_line_id":"ui-2"}
{"kind":"assistant","text":"One file: README.md","captured_at":"2026-10-01T12:00:05.120Z","source_line_id":"ui-3","source_message_id":"message-77"}
```

Fixture `.letta/lc-local-backend/conversations/Y29udmVyc2F0aW9uOmxvY2FsLWNvbnYtMQ/messages.jsonl`:

```json
{"type":"session","version":3,"id":"local-conv-1","timestamp":"2026-10-01T12:00:00.000Z","cwd":"/home/alice/repo"}
{"type":"message","id":"a1b2c3d4","parentId":null,"timestamp":"2026-10-01T12:00:01.000Z","message":{"id":"letta-msg-1","role":"user","content":"list the repo","timestamp":1759320001000}}
{"type":"message","id":"b2c3d4e5","parentId":"a1b2c3d4","timestamp":"2026-10-01T12:00:02.000Z","message":{"id":"letta-msg-2","role":"assistant","content":[{"type":"thinking","thinking":"use ls"},{"type":"toolCall","id":"call_1","name":"Bash","arguments":{"command":"ls"}}],"api":"anthropic-messages","provider":"anthropic","model":"claude-sonnet-4-5","usage":{"input":10,"output":5,"cacheRead":0,"cacheWrite":0,"totalTokens":15,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"toolUse","timestamp":1759320002000}}
{"type":"message","id":"c3d4e5f6","parentId":"b2c3d4e5","timestamp":"2026-10-01T12:00:03.000Z","message":{"id":"letta-msg-3","role":"toolResult","toolCallId":"call_1","toolName":"Bash","content":[{"type":"text","text":"README.md"}],"isError":false,"timestamp":1759320003000}}
```

Fixture `.letta/sessions.jsonl`:

```json
{"agent_id":"agent-1a2b","session_id":"s-1","timestamp":1759320000000,"project":"/home/alice/repo","model":"claude-sonnet-4-5","provider":"anthropic","usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0,"cached_input_tokens":0,"cache_write_tokens":0,"reasoning_tokens":0,"steps":0},"duration":{"api_ms":0,"wall_ms":0},"cost":{"type":"hosted"}}
```

Confidence. High: file locations, line shapes, field names, timestamp units
(source). Medium: pi-ai optional fields at the pinned version; the
`api` value in the fixture is illustrative. Not determined: V1 `content`
and `tool_calls` JSON encodings; whether reflection transcripts are written
on Windows when auto-reflection is off (`LETTA_ENABLE_WINDOWS_AUTO_REFLECTION`,
[reflection-settings.ts:9](https://github.com/letta-ai/letta-code/blob/77faf36e34378946c8e69c0bfaa5595a7be4c326/src/reflection-settings.ts#L9),
exists, but the append path at the cited loop is unconditional).
