# Codex CLI transcript schema

Catalog agent: `codex-cli`. OpenAI Codex CLI (the Rust `codex-rs`
workspace, also behind the VS Code extension and the desktop app) writes one
append-only JSONL "rollout" per thread, each line an envelope around a
tagged item, plus a global prompt history. Open Interpreter is a fork that
keeps the format byte for byte under `~/.openinterpreter`; see
[open-interpreter.md](open-interpreter.md), which records only what differs.
The parser is `doubleagent/parsers/codex.py` (`CodexParser`, built on the
shared `RolloutParser`).

Paths and the rest of the per-user state are in
[`collectors/research/codex-cli.md`](../../collectors/research/codex-cli.md).

## 1. Evidence

- **Source**: openai/codex at
  [`3e238776e857eccd3bde6bff3026e2e9798f6524`](https://github.com/openai/codex/commit/3e238776e857eccd3bde6bff3026e2e9798f6524)
  (2026-10-03), Apache-2.0, open source, the commit the collector document
  cites. Paths below are relative to `codex-rs/`. Every schema claim is
  from source unless marked **local**.
- **Local**: the real install on the development host, Codex 0.160.0
  (`session_meta.cli_version`), one rollout of 20 lines, a 1-line
  `history.jsonl` and a 1-line `session_index.jsonl`, plus scratchpad copies
  of `state_5.sqlite` and `thread_history_1.sqlite`. Only record types, key
  paths, value types and enum values were tabulated; no content was read
  into this document. The one rollout is `history_mode: "paginated"` and
  has no `git` block, so the legacy event set and `git` are source only.

## 2. Transcript files

Paths relative to the home; `$CODEX_HOME` replaces `.codex` when set.

- `.codex/sessions/YYYY/MM/DD/rollout-<YYYY-MM-DDThh-mm-ss>-<thread id>.jsonl`,
  one per thread, the directory date and file-name time in **local** time
  ([rollout/src/recorder.rs:1722-1734](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L1722-L1734),
  [rollout_file_name.rs:62-73](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/rollout_file_name.rs#L62-L73)).
  `thread/revert` writes a new file `rollout-<time>-<thread id>_<rollout id>.jsonl`
  that keeps the thread id and points back at its prefix
  ([recorder.rs:95-104](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L95-L104),
  [rollout_file_name.rs:40-47](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/rollout_file_name.rs#L40-L47)).
  Subagent threads get their own rollout in the same tree. **Parser reads.**
- `.codex/archived_sessions/`, same layout
  ([rollout/src/lib.rs:86-87](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/lib.rs#L86-L87)). **Parser reads.**
- `*.jsonl.zst`: zstd level 3, written by a background worker for rollouts
  idle seven days, in both trees
  ([compression.rs:29](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/compression.rs#L29),
  [362-363](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/compression.rs#L362-L363),
  [500-501](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/compression.rs#L500-L501)).
  The worker runs only with the `local_thread_store_compression` feature,
  which is under development and off by default
  ([features/src/lib.rs:1212-1217](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/features/src/lib.rs#L1212-L1217),
  [core/src/thread_manager.rs:461-503](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/thread_manager.rs#L461-L503)). **Parser reads** (needs `zstandard`).
- `.codex/history.jsonl`: one line per submitted prompt, all threads
  (section 5). **Parser reads.**
- `.codex/session_index.jsonl`: thread renames (section 5). Not read.
- `.codex/state_5.sqlite`, `.codex/thread_history_1.sqlite`: thread metadata
  and a projection of paginated rollouts (section 5). Not read.

## 3. Record envelope and types

Each line is a `RolloutLine`: `timestamp`, optional `ordinal`, and the item
flattened beside them
([history/src/lib.rs:356-367](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/lib.rs#L356-L367),
[recorder.rs:2062-2091](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L2062-L2091)).
The item serialises as `{"type": <snake_case variant>, "payload": {...}}`;
`response_item` lines may also carry a sibling `metadata` object
([history/src/rollout_payload.rs:30-72](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/rollout_payload.rs#L30-L72)).
Codex's own reader requires `timestamp` and treats `ordinal` as optional
([rollout/src/lib.rs:52-74](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/lib.rs#L52-L74)).
`ordinal` is written only in paginated rollouts, counting from 0 or from the
`history_base` the file continues
([rollout/src/ordinal.rs:22-44](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/ordinal.rs#L22-L44)).

Line types ([history/src/lib.rs:209-227](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/lib.rs#L209-L227));
which ones are written is decided in
[rollout/src/policy.rs:22-50](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L22-L50):

| `type` | `payload` | Seen locally |
| --- | --- | --- |
| `session_meta` | thread header, below | yes |
| `turn_context` | per-turn settings, below | yes |
| `response_item` | a Responses API item (section 4) | yes |
| `event_msg` | a UI event, tagged by its own `type` (below) | yes |
| `token_usage_record` | `thread_id`, `turn_id`, `session_id`, `root_turn_id`, `response_id`, `usage`, `turn_token_usage`, `thread_token_usage` ([protocol.rs:2263-2273](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2263-L2273)) | yes |
| `world_state` | `full`, `state` (model-visible environment snapshot or patch, [protocol.rs:3272-3278](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3272-L3278)) | yes |
| `compacted` | `message` (the compaction summary), `replacement_history`, window ids ([history/src/lib.rs:285-306](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/lib.rs#L285-L306), [rollout_payload.rs:238-266](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/rollout_payload.rs#L238-L266)) | no |
| `inter_agent_communication` | `author`, `recipient`, `other_recipients`, `content` (plain text), `encrypted_content`, `trigger_turn` ([protocol.rs:806-822](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L806-L822)) | no |
| `inter_agent_communication_metadata` | `trigger_turn` | no |
| `retained_context` | verified answers and delivered messages for the guardian reviewer ([history/src/retained_context.rs:145-162](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/retained_context.rs#L145-L162)) | no |
| `security_risk_score` | `scores`, `call_id`, `action`, `sampled_at` ([security_risk.rs:12-25](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/security_risk.rs#L12-L25)) | no |
| `realtime_item` | `id`, `realtime_session_id`, tagged content incl. `transcript_segment` (`role`, `text`); paginated only ([realtime.rs:6-31](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/realtime.rs#L6-L31)) | no |

**`session_meta`** (line 1;
[protocol.rs:3117-3198](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3117-L3198)):
`id` (this thread), `session_id` (the root thread's id; filled from `id`
when absent in old files,
[3243-3269](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3243-L3269)),
`forked_from_id`, `parent_thread_id`, `timestamp`, `cwd`,
`runtime_workspace_roots`, `originator` (`codex-tui` locally), `cli_version`,
`source` (`cli`, `vscode`, `exec`, `mcp`, a custom string, or
`{"subagent": ...}`; [2824-2837](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2824-L2837), [2905-2923](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2905-L2923)),
`thread_source` (`user`, `subagent`, `guardian_review`,
`memory_consolidation` or a feature name; [2843-2849](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2843-L2849)),
`agent_nickname`, `agent_role`, `agent_path`, `model_provider`,
`base_instructions`, `dynamic_tools`, `memory_mode`, `history_mode`
(`legacy` or `paginated`), `history_base`, `context_window`, and the account
fields `creator_user_id`, `creator_account_id`. Beside them, `git`
(`commit_hash`, `branch`, `repository_url`;
[3436-3452](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3436-L3452)) is written only when `cwd` is inside a
git repository
([recorder.rs:1978-1990](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L1978-L1990)).

**`turn_context`** (once per user turn and after mid-turn compaction;
[protocol.rs:3296-3358](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3296-L3358)):
`turn_id`, `root_turn_id`, `cwd`, `workspace_roots`, `current_date`,
`timezone`, `approval_policy`, `sandbox_policy`, `permission_profile`,
`network`, `model`, `collaboration_mode` (with its own `settings.model`),
`effort`, `summary`, `personality` and more.

**`event_msg`** (tagged enum,
[protocol.rs:1352-1358](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L1352-L1358)). Persisted in every mode
([policy.rs:127-139](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L127-L139)):
`task_started` (`turn_id`, `root_turn_id`, `trace_id`, `started_at` epoch
s, `model_context_window`, `collaboration_mode_kind`), `task_complete`
(`turn_id`, `last_agent_message`, `error`, `started_at`, `completed_at`,
`duration_ms`, `time_to_first_token_ms`)
([2152-2197](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2152-L2197); the wire names
are kept from v1, [1407-1418](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L1407-L1418)),
`turn_aborted` (`turn_id`, `reason`, `error`, times;
[4243-4263](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L4243-L4263)),
`thread_rolled_back` (`num_turns`;
[3692-3696](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3692-L3696)),
`token_count`, `thread_goal_updated`, `thread_settings_applied`, and
`item_completed` (below). Legacy-mode rollouts also keep `user_message`
(`message`, `images`), `agent_message` (`message`, `phase`),
`agent_reasoning` and `agent_reasoning_raw_content` (`text`),
`entered_review_mode`, `exited_review_mode`, `patch_apply_end`,
`context_compacted`, `mcp_tool_call_end`, `web_search_end`,
`image_generation_end` and `sub_agent_activity`
([policy.rs:141-158](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L141-L158);
[protocol.rs:2518-2544](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2518-L2544),
[2637-2645](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L2637-L2645)).
These repeat what the `response_item` lines carry.

`item_completed` (`thread_id`, `turn_id`, `item`, `started_at_ms`,
`completed_at_ms`;
[protocol.rs:1947-1960](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L1947-L1960))
carries a `TurnItem` tagged by PascalCase `type`: `UserMessage`,
`AgentMessage`, `Reasoning`, `CommandExecution` (`command`, `cwd`,
`aggregated_output`, `exit_code`, `duration`), `McpToolCall` (`server`,
`tool`, `arguments`, `result`), `FileChange` (`changes`, `stdout`,
`stderr`), `WebSearch`, `Extension` (`kind` `web.search`, `clock.sleep` or
`image_gen.generation`), `Plan`, `CollabAgentToolCall` (`prompt`, `model`,
receiver thread ids) and others
([items.rs:42-78](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/items.rs#L42-L78),
[243-281](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/items.rs#L243-L281),
[337-422](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/items.rs#L337-L422),
[443-486](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/items.rs#L443-L486);
[ext/items/src/lib.rs:32-45](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/ext/items/src/lib.rs#L32-L45)).
Paginated rollouts persist every completed item, with command output and
MCP results cut to 64 KiB; legacy rollouts keep only `FunctionCallOutput`,
`Plan`, `clock.sleep` and completed `SubAgentActivity` items
([policy.rs:16-19](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L16-L19),
[227-283](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L227-L283)).
Locally the paginated rollout held `UserMessage`, `Extension`
(`web.search`, with `query`, `action` and `results`) and `AgentMessage`
items.

Everything else on the `EventMsg` enum (deltas, begin events, approvals,
`exec_command_end`, errors, warnings) is transient and never written
([policy.rs:160-223](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L160-L223)).

## 4. Message content and tool calls

`response_item.payload` is a `ResponseItem` tagged by snake_case `type`
([protocol/src/models.rs:1010-1256](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1010-L1256));
all variants but `compaction_trigger` and unknown ones are written
([policy.rs:78-100](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/policy.rs#L78-L100)).
Most variants carry an optional `id` and
`internal_chat_message_metadata_passthrough` (`turn_id`, `create_time` in
fractional epoch seconds, `content_item_kinds`;
[models.rs:954-994](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L954-L994)).

- `message`: `role` (`user`, `assistant`, `developer`; the harness's own
  instructions go in as `developer`), `content[]` of `input_text`,
  `input_image` (`image_url` or `file_id`), `input_audio` or `output_text`
  blocks, each with `text` where textual
  ([876-896](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L876-L896)),
  and `phase` (`commentary` or `final_answer`;
  [938-952](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L938-L952), [1021-1036](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1021-L1036)).
  A `role: "user"` message is not always typed by the user: the harness
  injects `AGENTS.md` instructions, `<environment_context>`, skill text,
  subagent notifications, turn-aborted notices and user shell commands as
  user-role messages
  ([core/src/context/contextual_user_message.rs:22-37](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/contextual_user_message.rs#L22-L37)).
  Current versions label each content block in
  `content_item_kinds`; typed input is `user.text`, the environment block
  `environments.environment_context`
  ([contextual_user_message.rs:51-82](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/contextual_user_message.rs#L51-L82),
  [core/src/context/world_state/environment.rs:200-203](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/world_state/environment.rs#L200-L203)).
  Locally the first turn had three `developer` messages and two `user`
  messages, of which one was `environments.environment_context` and one
  `user.text`.
- `reasoning`: `summary[]` of `summary_text` (`text`), `content[]` of
  `reasoning_text` or `text`, `encrypted_content`
  ([1048-1060](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1048-L1060), [1982-1993](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1982-L1993)).
  `content` is written only when it holds `reasoning_text` parts or is null
  ([1624-1631](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1624-L1631)).
- `function_call`: `name`, `namespace` (MCP and plugin tools), `arguments`
  (a JSON **string**), `call_id`
  ([1074-1093](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1074-L1093)).
- `custom_tool_call`: `status`, `call_id`, `name`, `namespace`, `input`
  (free text) ([1134-1151](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1134-L1151)).
  Code mode's `exec` tool
  ([code-mode-protocol/src/lib.rs:52](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/code-mode-protocol/src/lib.rs#L52))
  and the freeform `apply_patch` arrive this way; the one local call was
  `exec`.
- `local_shell_call`: `call_id`, `status`, `action` (`type: "exec"`,
  `command` array, `timeout_ms`, `working_directory`, `env`, `user`)
  ([1061-1073](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1061-L1073), [1937-1950](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1937-L1950)).
- `function_call_output`, `custom_tool_call_output`: `call_id`, `name`,
  `output`, which is a string or an array of `input_text`, `input_image`,
  `input_audio`, `encrypted_content` items
  ([1114-1133](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1114-L1133), [1155-1169](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1155-L1169), [2096-2118](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L2096-L2118), [2250-2263](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L2250-L2263)).
  Locally an array of two `input_text` items.
- `web_search_call`: `status`, `action` (`search` with `query`/`queries`,
  `open_page` with `url`, `find_in_page` with `url`, `pattern`)
  ([1191-1204](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1191-L1204), [1952-1980](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1952-L1980)). No output item.
- `tool_search_call` (`call_id`, `execution`, `arguments` object) and
  `tool_search_output` (`call_id`, `status`, `tools[]`)
  ([1094-1108](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1094-L1108), [1170-1182](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1170-L1182)).
- `agent_message`: `author`, `recipient`, `content[]` of `input_text` or
  `encrypted_content` ([906-911](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L906-L911), [1037-1047](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1037-L1047)).
- `image_generation_call`: `status`, `revised_prompt`, `result` (image data)
  ([1214-1226](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1214-L1226)).
- `additional_tools` (tool definitions), `compaction` and
  `context_compaction` (`encrypted_content`), `configuration_update`: no
  readable conversation content
  ([1013-1020](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1013-L1020), [1227-1253](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/models.rs#L1227-L1253)).

The `metadata` sibling on a `response_item` line is harness bookkeeping:
`client_authored`, `retained_source`, `user_input_order`,
`inherited_user_message` (copied from a parent thread), `mcp_attribution`
and others
([history/src/lib.rs:55-135](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/history/src/lib.rs#L55-L135)).

**Joins.** Tool call to result: `call_id`, equal on the call and its
`*_output`. Turn: `turn_id` on `turn_context`, `task_started`,
`task_complete`, `item_completed` and in each item's metadata passthrough.
An `item_completed` item that a code-mode `exec` call produced (the local
`web.search`) has its own id, not the call's `call_id`, so nothing joins it
to the call except its position between the call and its output (local).

## 5. Other files

- `history.jsonl`: `{session_id, ts, text}`, `ts` epoch **seconds**,
  `session_id` the thread id, one line per prompt typed into the TUI
  ([message-history/src/lib.rs:61-66](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/message-history/src/lib.rs#L61-L66),
  [127-138](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/message-history/src/lib.rs#L127-L138)).
  Written unless `history.persistence = "none"`
  ([config/src/types.rs:211-219](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/config/src/types.rs#L211-L219)); trimmed oldest-first when
  `history.max_bytes` is set
  ([message-history/src/lib.rs:191-195](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/message-history/src/lib.rs#L191-L195)). It can outlive the rollout it
  names (deleted or ephemeral threads), so it is the one place such a
  prompt survives. Local: one line, those three keys, 10-digit `ts`.
- `session_index.jsonl`: `{id, thread_name, updated_at}` appended per
  rename, newest wins, `updated_at` RFC 3339 UTC with nanoseconds
  ([rollout/src/session_index.rs:24-48](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/session_index.rs#L24-L48)). Titles only; local shape matches.
- `state_5.sqlite` `threads`: `id`, `rollout_path`, `created_at`, `cwd`,
  `title`, `git_sha`, `git_branch`, `git_origin_url` and later
  `first_user_message`, `preview`
  ([state/migrations/0001_threads.sql:1-19](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/state/migrations/0001_threads.sql#L1-L19),
  [0007_threads_first_user_message.sql:1](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/state/migrations/0007_threads_first_user_message.sql#L1),
  [0032_threads_preview.sql:1](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/state/migrations/0032_threads_preview.sql#L1)); `thread_spawn_edges`
  links parent and child threads
  ([0021_thread_spawn_edges.sql:1-5](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/state/migrations/0021_thread_spawn_edges.sql#L1-L5)). A row whose rollout is gone still holds the
  first prompt.
- `thread_history_1.sqlite`: `thread_turns`, `thread_items` (`item_json`,
  the app-server's camelCase `ThreadItem`), `thread_realtime_items`, keyed
  by `rollout_ordinal`
  ([state/thread_history_migrations/0001_thread_history.sql:1-38](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/state/thread_history_migrations/0001_thread_history.sql#L1-L38)).
  A projection of paginated rollouts; local item types were `userMessage`,
  `webSearch`, `agentMessage`, the same three items as the rollout's
  `item_completed` lines. Nothing found that is not in the rollout.

Opened only from scratchpad copies, and only for table names, row counts
and key names.

## 6. Timestamps, ids, project, branch, model, subagents

- **Timestamps.** Line `timestamp` and `session_meta.payload.timestamp`:
  UTC `YYYY-MM-DDThh:mm:ss.mmmZ`, the line one taken at write time
  ([recorder.rs:927-933](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L927-L933), [2077-2082](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L2077-L2082)); local values all had three fraction
  digits and `Z`. `task_*` `started_at`/`completed_at`: epoch seconds;
  `item_completed` `*_at_ms`: epoch ms; `create_time`: fractional epoch
  seconds; `history.jsonl` `ts`: epoch seconds.
- **Ids.** `session_meta.payload.id` is the thread id and the file-name
  UUID; `session_id` is the root thread's id, so a subagent's rollout has
  `id` ≠ `session_id`. Reverted rollouts end `<thread id>_<rollout id>`.
- **Project.** `session_meta.payload.cwd`, updated per turn by
  `turn_context.payload.cwd`; `workspace_roots` lists extra roots.
- **Branch.** `session_meta.payload.git.branch`, set once at thread
  creation, absent outside a git repository.
- **Model.** `turn_context.payload.model`; `model_provider` on
  `session_meta`. No per-message model.
- **Subagents.** Each spawned agent has its own rollout whose
  `session_meta` has `parent_thread_id`, `agent_nickname`, `agent_role`,
  `agent_path`, `thread_source: "subagent"` and `source:
  {"subagent": {"thread_spawn": {parent_thread_id, depth, ...}}}`;
  messages between agents are `inter_agent_communication` lines.
- **Forks.** `forked_from_id` on the child. A copied fork re-appends the
  parent's records into the child file at fork time, so they carry the
  fork's line timestamps; a referenced (paginated) fork keeps them in the
  parent file behind `history_base` (`thread_id`, `end_ordinal_exclusive`,
  `end_byte_offset`)
  ([core/src/session/mod.rs:1672-1695](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/session/mod.rs#L1672-L1695),
  [protocol.rs:3101-3115](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L3101-L3115)).
  Codex's own metadata sync only trusts a `session_meta` whose `id` is the
  file's thread, which implies copied files can hold an ancestor's
  `session_meta` too
  ([thread-store/src/thread_metadata_sync.rs:246-256](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/thread-store/src/thread_metadata_sync.rs#L246-L256)).

## 7. Variants and drift

- **History mode.** `session_meta.history_mode` (`legacy` default,
  `paginated`; [protocol.rs:775-782](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L775-L782)). The app server starts
  non-ephemeral threads paginated when the store supports it
  ([app-server/src/request_processors/thread_processor.rs:1462-1465](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/app-server/src/request_processors/thread_processor.rs#L1462-L1465)); the local TUI
  thread was paginated. Paginated files add `ordinal` and `item_completed`
  items and drop the legacy `user_message`/`agent_message` events. A
  background legacy-to-paginated rewrite exists behind
  `background_paginated_rollout_migration`, off by default
  ([features/src/lib.rs:1224-1229](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/features/src/lib.rs#L1224-L1229),
  [thread-store/src/local/rollout_migration.rs:1-9](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/thread-store/src/local/rollout_migration.rs#L1-L9)).
- **Compression and archive.** `.jsonl.zst` and `archived_sessions/`
  (section 2); Codex materialises a compressed file back to `.jsonl` before
  appending to it
  ([compression.rs:104-105](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/compression.rs#L104-L105)), so either form may be present.
- **Flat layout.** Older releases wrote `sessions/rollout-<time>-<uuid>.jsonl`
  without date directories (the example in
  [recorder.rs:82](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/recorder.rs#L82)); the current lister walks only
  `YYYY/MM/DD`
  ([list.rs:900-920](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/rollout/src/list.rs#L900-L920)).
- **Renames kept for compatibility.** `session_meta` without `session_id`,
  `agent_type` for `agent_role`, `turn_started`/`turn_complete` aliases,
  `compaction_summary` for `compaction`; `TurnContextItem.summary` is
  written only for older readers.
- **Not determined at this commit:** whether pre-envelope rollouts (no
  `type`/`payload` wrapper) exist on disk from very early releases; the
  current reader rejects lines without `timestamp`.

## 8. Parser plan (the existing parser)

`CodexParser` wants
`^\.codex/(?:archived_)?sessions/(?:.*/)?rollout-[^/]*\.jsonl(?:\.zst)?$`
and `.codex/history.jsonl`. Until `session_meta` is read, the session id is
the thread id in the file name: the last UUID, or the first of a reverted
rollout's `<thread id>_<rollout id>`. The parser reads the whole file before
emitting rows, so that an `item_completed` line can be checked against every
`response_item` id and `call_id` in the file.

| Column | Source |
| --- | --- |
| timestamp_utc | line `timestamp`; `session_meta.payload.timestamp` for the start, subagent and fork rows; `item_completed` `started_at_ms` / `completed_at_ms` for the rows built from a turn item; history `ts` (s) |
| session_id | the file's first `session_meta.payload.id`, else its `session_id`, else the file-name thread id; a later `session_meta` never changes it; history `session_id` |
| project_path | first `session_meta.payload.cwd`, replaced by each `turn_context.payload.cwd` |
| git_branch | first `session_meta.payload.git.branch` |
| model | `turn_context.payload.model` (empty before the first `turn_context`) |
| turn_type | coverage table below |
| tool_name | `name`; `shell` for `local_shell_call` and `CommandExecution`, `web_search` for `web_search_call` and web-search turn items, `tool_search`, `<server>.<tool>` for `McpToolCall`, `apply_patch` for `FileChange` |
| tool_use_id | `call_id` (call falls back to `id`); a turn item's `id` |
| text | message: `content[].text` joined, prefixed `<role>: ` for developer; user-role context `context: <kind>: <text>`; tool_use: `arguments` or `input`, `action.command` joined, `action.query`, `arguments` JSON; tool_result: `output` string or `[].text` joined, prefixed `[exit N]` when the matching `CommandExecution` item has a non-zero `exit_code`; thinking: `summary[].text`, else `content[].text` |

| Record | Row |
| --- | --- |
| first `session_meta` | `system` ("session start: originator version provider cwd"); plus `system` `subagent <id> of <parent> [agent_path= agent_role= agent_nickname=]` when `parent_thread_id`, `source.subagent.thread_spawn.parent_thread_id`, or a `session_id` other than `id` on a non-fork names a parent; plus `system` `forked from <id>` for `forked_from_id` |
| later `session_meta` | `system` `copied from ancestor: session start ... id= cwd=` when its id differs; none when it repeats the file's own |
| `turn_context` | none; sets project and model |
| `response_item` with `metadata.inherited_user_message` | none (copied from the parent thread) |
| `response_item` `message` user | per `content_item_kinds` run: `user` for `user.*`, `unknown` or empty kinds; `system` `context: <kind>: ...` for any other kind; without a kinds list as long as `content`, per block: `system` `context: <marker name>: ...` for a block that is wholly one of the harness wrappers below, else `user`. In a subagent file the first prompt is `system` `subagent task: ...`; later ones stay `user` (below) |
| `response_item` `message` assistant / developer | `assistant` / `system` (`developer: ...`); empty text skipped |
| `response_item` `function_call`, `custom_tool_call`, `local_shell_call`, `web_search_call`, `tool_search_call` | `tool_use` |
| `response_item` `function_call_output`, `custom_tool_call_output`, `local_shell_call_output`, `tool_search_output` (tool names) | `tool_result` |
| `response_item` `agent_message`, `inter_agent_communication` | `system` `agent message <author> -> <recipients>: ...` (`subagent task:` for a subagent's first prompt); an `inter_agent_communication` whose `id` a response item carries is skipped |
| `response_item` `image_generation_call` | `system` `image generation: <revised_prompt> status=...` |
| `response_item` `reasoning` | `thinking` with `--include-thinking` when it has text, else skipped |
| `response_item` `additional_tools`, `compaction`, `context_compaction`, `configuration_update` | skipped (no readable content) |
| `event_msg` `task_started`, `task_complete` | `system` |
| `event_msg` `turn_aborted` | `system` `turn aborted: <reason> [error message]` |
| `event_msg` `thread_rolled_back` | `system` `rolled back <n> turns`; earlier rows are not changed |
| `event_msg` `item_completed` `UserMessage`, `AgentMessage`, `Reasoning`, `HookPrompt`, `ContextCompaction` | skipped (repeat a response item or `compacted`) |
| `event_msg` `item_completed`, other items whose `id` a response item carries as `id` or `call_id` | skipped; a `CommandExecution` exit code still marks the call's `tool_result` |
| `event_msg` `item_completed` `CommandExecution`, `McpToolCall`, `DynamicToolCall`, `FileChange`, `WebSearch`, `Extension` `web.search` not carried | `tool_use` + `tool_result` on the item `id` |
| `event_msg` `item_completed` `FunctionCallOutput` not carried | `tool_result` |
| `event_msg` `item_completed` `Plan`, `SubAgentActivity`, image generation, `clock.sleep`, others not carried | `system` (`plan: ...`, `subagent activity: ...`, `image generation: ...`, `sleep: N ms`, `item <type>: <JSON>`) |
| `event_msg` legacy `user_message`, `agent_message`, `agent_reasoning`, and the rest | skipped |
| `compacted` | `system` `compaction summary: <message>`, or `compaction: replacement history of N items` |
| `realtime_item` `transcript_segment` | `user` or `assistant` by `role` |
| `realtime_item` other types | `system` `realtime: <type> <JSON>` |
| `token_usage_record`, `world_state`, `inter_agent_communication_metadata`, `retained_context`, `security_risk_score` | skipped |
| bad line or cut zstd frame | one `system` row at the end |
| `history.jsonl` line | `user` |

Rollouts without content kinds are classified per content block by the
wrappers Codex itself recognises as injected user-role context
([core/src/context/contextual_user_message.rs:22-37](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/contextual_user_message.rs#L22-L37)).
As in Codex's own check, the block must begin with the open marker after
leading whitespace and end with the close marker, ignoring ASCII case
([context-fragments/src/fragment.rs:116-130](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/context-fragments/src/fragment.rs#L116-L130)), so a tag a person types inside a prompt leaves it `user`:

| Marker name | Open … close | Source |
| --- | --- | --- |
| `agents_md_instructions` | `# AGENTS.md instructions` … `</INSTRUCTIONS>` | [core/src/context/user_instructions.rs:23-25](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/user_instructions.rs#L23-L25) |
| `environment_context` | `<environment_context>` … `</environment_context>` | [protocol/src/protocol.rs:120-121](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/protocol/src/protocol.rs#L120-L121), [core/src/context/world_state/environment.rs:524-529](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/world_state/environment.rs#L524-L529) |
| `agent_message_board_notification` | `<agent_message_board_notification>` … closing tag | [core/src/context/agent_message_board_notification.rs:19-25](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/agent_message_board_notification.rs#L19-L25) |
| `skill` | `<skill>` … `</skill>` | [ext/skills/src/fragments.rs:89-91](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/ext/skills/src/fragments.rs#L89-L91) |
| `user_shell_command` | `<user_shell_command>` … closing tag | [core/src/context/user_shell_command.rs:44](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/user_shell_command.rs#L44) |
| `turn_aborted` | `<turn_aborted>` … closing tag | [core/src/context/turn_aborted.rs:34](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/turn_aborted.rs#L34) |
| `subagent_notification` | `<subagent_notification>` … closing tag | [core/src/context/subagent_notification.rs:34-36](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/subagent_notification.rs#L34-L36) |
| `recommended_plugins` | `<recommended_plugins>` … closing tag | [core/src/context/recommended_plugins_instructions.rs:43](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/context/recommended_plugins_instructions.rs#L43) |

Later `role: "user"` messages in a subagent's rollout stay `user`: the
parent's v1 `send_input` tool submits plain user input to the child
([core/src/agent/control.rs:134-143](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/core/src/agent/control.rs#L134-L143)), and a person can also type into a subagent thread, because the TUI's
`/subagents` picker makes it the active thread and composer input is sent
to the active thread ([tui/src/multi_agents.rs:1-5](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/tui/src/multi_agents.rs#L1-L5), [tui/src/app/thread_routing.rs:475-497](https://github.com/openai/codex/blob/3e238776e857eccd3bde6bff3026e2e9798f6524/codex-rs/tui/src/app/thread_routing.rs#L475-L497)). The rollout records both alike.

A copied fork has no boundary beyond the ancestor's `session_meta` and the
per-message `inherited_user_message` flag, so the other copied records stay
in the fork's file under the fork's session id.

Expected rows from the sample below: `system` session start, `system`
`task_started`, `system` `developer: ...`, `system`
`context: environments.environment_context: ...`, `user` "run the tests",
`tool_use` `exec_command` (`call_1`), `tool_result` "[exit 1] 1 failing"
(the `CommandExecution` item has id `call_1`, so it adds only the exit
code), `thinking` "one test fails" with `--include-thinking`, `assistant`,
`system` `task_complete`, `system`
`agent message /root -> /root/tester: rerun only the failing test`, and
one `system` row for the cut last line. The `UserMessage` item and the
`token_usage_record` give no row.

Sample rollout, paginated shape
(`.codex/sessions/2026/10/02/rollout-2026-10-02T11-00-00-0199b2c3-1111-7aaa-8bbb-000000000001.jsonl`):

```json
{"timestamp":"2026-10-02T09:00:00.000Z","ordinal":0,"type":"session_meta","payload":{"session_id":"0199b2c3-1111-7aaa-8bbb-000000000001","id":"0199b2c3-1111-7aaa-8bbb-000000000001","timestamp":"2026-10-02T09:00:00.000Z","cwd":"/srv/proj","originator":"codex-tui","cli_version":"0.150.0","source":"cli","thread_source":"user","model_provider":"openai","history_mode":"paginated","git":{"commit_hash":"0a1b2c3d","branch":"main"}}}
{"timestamp":"2026-10-02T09:00:01.000Z","ordinal":1,"type":"event_msg","payload":{"type":"task_started","turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","started_at":1790931601,"model_context_window":272000,"collaboration_mode_kind":"default"}}
{"timestamp":"2026-10-02T09:00:01.100Z","ordinal":2,"type":"response_item","payload":{"type":"message","id":"m1","role":"developer","content":[{"type":"input_text","text":"<permissions instructions>sandboxed</permissions instructions>"}]}}
{"timestamp":"2026-10-02T09:00:01.200Z","ordinal":3,"type":"turn_context","payload":{"turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","cwd":"/srv/proj","approval_policy":"on-request","sandbox_policy":{"type":"workspace-write"},"model":"gpt-5.5-codex","summary":"auto"}}
{"timestamp":"2026-10-02T09:00:01.300Z","ordinal":4,"type":"response_item","payload":{"type":"message","id":"m2","role":"user","content":[{"type":"input_text","text":"<environment_context>\n<cwd>/srv/proj</cwd>\n</environment_context>"}],"internal_chat_message_metadata_passthrough":{"turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","content_item_kinds":["environments.environment_context"]}}}
{"timestamp":"2026-10-02T09:00:01.400Z","ordinal":5,"type":"response_item","payload":{"type":"message","id":"m3","role":"user","content":[{"type":"input_text","text":"run the tests"}],"internal_chat_message_metadata_passthrough":{"turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","content_item_kinds":["user.text"]}},"metadata":{"client_authored":true,"user_input_order":0}}
{"timestamp":"2026-10-02T09:00:01.500Z","ordinal":6,"type":"event_msg","payload":{"type":"item_completed","thread_id":"0199b2c3-1111-7aaa-8bbb-000000000001","turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","item":{"type":"UserMessage","id":"u1","content":[{"type":"text","text":"run the tests","text_elements":[]}]},"started_at_ms":1790931601500,"completed_at_ms":1790931601500}}
{"timestamp":"2026-10-02T09:00:03.000Z","ordinal":7,"type":"response_item","payload":{"type":"function_call","id":"fc1","name":"exec_command","arguments":"{\"cmd\":\"npm test\"}","call_id":"call_1"}}
{"timestamp":"2026-10-02T09:00:06.000Z","ordinal":8,"type":"response_item","payload":{"type":"function_call_output","call_id":"call_1","output":"1 failing"}}
{"timestamp":"2026-10-02T09:00:06.100Z","ordinal":9,"type":"event_msg","payload":{"type":"item_completed","thread_id":"0199b2c3-1111-7aaa-8bbb-000000000001","turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","item":{"type":"CommandExecution","id":"call_1","command":["npm","test"],"cwd":"/srv/proj","parsed_cmd":[],"source":"agent","status":"failed","aggregated_output":"1 failing","exit_code":1},"started_at_ms":1790931603000,"completed_at_ms":1790931606000}}
{"timestamp":"2026-10-02T09:00:07.000Z","ordinal":10,"type":"response_item","payload":{"type":"reasoning","id":"rs1","summary":[{"type":"summary_text","text":"one test fails"}],"encrypted_content":"gAAAA"}}
{"timestamp":"2026-10-02T09:00:08.000Z","ordinal":11,"type":"response_item","payload":{"type":"message","id":"m4","role":"assistant","phase":"final_answer","content":[{"type":"output_text","text":"One test fails in src/a.test.ts."}]}}
{"timestamp":"2026-10-02T09:00:08.100Z","ordinal":12,"type":"token_usage_record","payload":{"thread_id":"0199b2c3-1111-7aaa-8bbb-000000000001","turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","session_id":"0199b2c3-1111-7aaa-8bbb-000000000001","root_turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","response_id":"resp_1","usage":{"input_tokens":900,"cached_input_tokens":0,"output_tokens":40,"reasoning_output_tokens":10,"total_tokens":940}}}
{"timestamp":"2026-10-02T09:00:08.200Z","ordinal":13,"type":"event_msg","payload":{"type":"task_complete","turn_id":"0199b2c3-2222-7aaa-8bbb-000000000001","last_agent_message":"One test fails in src/a.test.ts.","started_at":1790931601,"completed_at":1790931608,"duration_ms":7200}}
{"timestamp":"2026-10-02T09:00:09.000Z","ordinal":14,"type":"inter_agent_communication","payload":{"author":"/root","recipient":"/root/tester","other_recipients":[],"content":"rerun only the failing test","trigger_turn":true}}
this line is cut mid-wri
```

`history.jsonl`:
`{"session_id":"0199b2c3-1111-7aaa-8bbb-000000000001","ts":1790931601,"text":"run the tests"}`

## Confidence

High: file layout and naming, envelope, the written type set and the
legacy/paginated split, `session_meta`, `turn_context` and `ResponseItem`
field names, timestamp formats and units, `history.jsonl` and
`session_index.jsonl` shapes (source, and the local tabulation agrees for
every type it contains). Medium: that copied forks can contain an
ancestor's `session_meta` (inferred from the metadata sync guard, not from a
file); the exact payload of `item_completed` for item kinds not seen locally
(read from the structs, not from files); `AgentPath` string form in the
sample (`/root/...` is illustrative). Not determined: pre-envelope rollouts
from the earliest releases; whether `local_shell_call_output` exists (the
parser lists it but `ResponseItem` has no such variant at this commit; it
is harmless); how often the harness emits `agent_message` response items
versus `inter_agent_communication` lines.
