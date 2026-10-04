# Muse Code transcript schema

Catalog agent: `muse-code`. Muse Code is Meta's closed-source coding agent
CLI (`muse`, models `muse-spark-*`). It writes one event-sourced JSONL log
per session, with each subagent in its own log under the session directory.
Paths and the rest of the per-user state are in
[`collectors/research/muse-code.md`](../../collectors/research/muse-code.md).
No other agent in the catalog shares this format.

## 1. Evidence

Closed source; no public repository, so there are no commit links. Each
claim below names its evidence level, best first:

- **Binary**: `~/.local/bin/muse-bin-1.4.2-R4684.1`, Muse Code 1.4.2
  (build sha `b538db0a2c` as recorded in the sessions), ELF x86-64,
  statically linked Rust (crate paths `fbcode/musecode/build/src/crates/...`
  in the strings), sha256
  `dfb3096c91f4767c4d98006460800b7ba906a0b1a408280a926a8dc19a1af64f`.
  Read with `strings -n 6`; serde leaves the variant and field names of
  every serialized enum and struct as concatenated literals (for example
  `struct variant AgentRunEvent::AssistantMessageCommitted with 5
  elements`), which is where the field lists for kinds not seen on disk
  come from. The binary was never executed.
- **Vendor skills** shipped in the binary and unpacked to
  `~/.local/share/muse/plugins/cache/builtin/muse-core/`:
  `read-session/0782fa625e56.../SKILL.md` (the session log format, written
  for the agent itself) and `doctor/362cd5a3ba33.../scripts/session-evidence.py`
  (Meta's own reader of `session.jsonl`, which shows the field fallbacks
  Meta itself expects). The directory names are content hashes.
- **Observed**: a real install on the author's Linux (WSL2) workstation,
  October 2026: two sessions (one failed on a 402 before any model output,
  one with web search, web fetch, bash and two reminder subagents),
  547 envelope lines plus 4 frames and 4 markers in total, every line
  tabulated by key path. Shapes marked observed were seen there; shapes
  marked binary were not exercised and rest on field names only.

## 2. Transcript files

All under `${XDG_DATA_HOME:-$HOME/.local/share}/muse/` (read-session skill;
binary literal `XDG_DATA_HOME:-$HOME/.local/share}/muse/sessions`). The
same layout applies on macOS and on Windows: the Windows build
(`muse-x86-windows.exe` 1.4.2-R4684.1) resolves its data directory from
`XDG_DATA_HOME`, then `HOME`, then `USERPROFILE`, so a Windows home holds
`.local\share\muse` too; the path evidence is in
[collectors/research/muse-code.md](../../collectors/research/muse-code.md).
Relative to the home:

| Path | Content | Parse |
| --- | --- | --- |
| `.local/share/muse/sessions/YYYY/MM/DD/<session id>/session.jsonl` | the session event log; date is local time of creation; id is a UUIDv7 (observed `01a1040f-aa0d-7d82-...`) | yes |
| `.../<session id>/subagent/<child id>/session.jsonl` | one log per subagent, same format; the session-evidence script walks `subagent/` recursively, so nesting is possible | yes |
| `.../<session id>/tool-outputs/<task id>/<call id>-<kind>.txt` | full output of a tool call whose inline result was cut (observed kind `web_fetch-page`); `.spool/<call id>-bash.txt.tmp` while running | no, section 4 |
| `.../<session id>/approval-review/<reviewer rollout id>.jsonl` | the automated approval reviewer's own run log, same envelope, synthetic clock | no, section 5 |
| `.../<session id>/session.peer-history.sqlite3` (+`-wal`, `-shm`) | byte-offset index into `session.jsonl`, no content | no |
| `.../<session id>/cron.db` | scheduled prompts (`cron_jobs`) | optional |
| `.../<session id>/cli-<uuid>.log` | text tracing log (`2026-10-04T20:20:31.242428Z INFO <target> <file:line> event="..." key=value`) | no |
| `.../<session id>/.session.jsonl.permission-init` | the first `retained_frame` line, staged before `session.jsonl` exists; a directory with only this and `.session.lock` is a session that never started (observed) | no |
| `.local/share/muse/sessions/.msp-view-v1/<session id>/` | `HEAD.json`, `snapshot-<uuid>.json`, `journal-NNNNNNNN.bin`, `index-NNNNNNNN.bin`: a derived TUI view rebuilt from `session.jsonl` | no, section 5 |
| `.local/share/muse/session-index.db` | one row per session: workspace, model, title, first prompt | no, section 5 |
| `.local/share/muse/session-name-authority/session-names.db` | session name claims | no |
| `.local/share/muse/tui-history.jsonl` | prompt history of the TUI composer | yes, as history |

The binary also names `goals.db` and `input-assets/` beside `cron.db` in the
session directory (binary; not observed).

## 3. Record schema

### Line kinds

Every line of `session.jsonl` is one JSON object of one of three shapes
(observed; `RawLogRecordEnvelope` with 11 fields in the binary):

**Envelope** (all but a handful of lines):

| Field | Value |
| --- | --- |
| `schema_version` | `1` |
| `id` | UUID of this record |
| `stream` | `{kind, id}`; `kind` is `session` in session logs (`approval.review.runtime` in approval-review logs), `id` is the session id, the subagent's own id in a subagent log |
| `sequence` | integer, 1-based, contiguous across envelopes, frame children and markers together (observed: frame holds 1-2, envelopes start at 3, markers fill gaps) |
| `recorded_at` | integer **microseconds** since the Unix epoch, UTC (observed `1791145226590500` = 2026-10-04T20:20:26.590Z; matches `session-index.db` `created_at_us`) |
| `record_type` | `event` (observed only); omitted ephemeral records were `status` |
| `durability` | `durable` (observed only); `ephemeral` records are not kept |
| `causation_id` | null, or the `id` of the record that caused this one |
| `payload_type` | dotted name, table below |
| `payload_schema_version` | 1, 2 (`route_facts`, `agent_tree_initialized`) or 3 (`approval` events) observed |
| `payload` | object; shape by `payload_type` |

**`retained_frame`** (line 1 of every log, observed in all four):
`{retained_frame:"session_permission_transaction", frame_schema_version:1,
outer_log_ordinal, transaction_id, children:[{child_index, record_json}],
content_sha256}`. `record_json` is a JSON **string** holding a complete
envelope; observed children are `runtime.session.permission_format_declared`
and `runtime.session.permission_profile_committed` (the session's starting
permission profile: approval mode, reviewer, filesystem and network rules).
The binary has frame and resume code (`retained permission frame has no
trusted physical head`), so a resumed or re-permissioned session can carry
more frames later in the file.

**`retained_marker`** (observed 4 times in one log):
`{retained_marker:"omitted_live_only", schema_version:1, stream,
position:{id, sequence}, omitted_record:{record_type:"status",
durability:"ephemeral", payload_type:"runtime.session",
payload_schema_version, payload_kind:"task",
omission_class:"task_tool_delta_v1"}}`. It stands in for a live-only
progress record (streamed tool output) that was not persisted, keeping the
`sequence` numbering contiguous. It carries no content and no timestamp.

### Payload families

`payload_type` values seen (observed, count over both sessions and both
subagents): `runtime.session` 462, `runtime.session.task` 12,
`tool_batch.effect.started`/`.terminal` 12 each, `run.model.configured` 5,
`runtime.session.metadata` 5, `runtime.session.capture_selection` 4,
`runtime.user_intent.accepted`/`.materialized` 3 each,
`runtime.retained_fact` 3, `session.workspace_branch.observed`,
`session.opened.observed`, `session.startup_phases.observed`,
`session.name.changed`, `session.end`,
`session.payment_gate.banner_shown`, `runtime.session.route_facts`,
`runtime.command_intake.session_name.received`,
`runtime.command_intake.settled` 2 each, and once each
`runtime.model_reconfigure.completed`, `session.login.completed`,
`session.payment_gate.unresolved_at_poll_cap`,
`reminder.cleanup_effect.started`/`.terminal`. The binary lists many more
(`user_shell.command`, `user_shell.result`, `user_shell.rejected`,
`session.resumed`, `session.fork.created`, `session.description.generated`,
`subagent.control.*`, `session.worktree.*`, `session.mailbox.*`,
`context.compact.manual.*`, `approval_wait.effect.*`, ...); a parser must
skip unknown types.

Two payload layouts occur (observed):

- **Fact records**: `payload = {kind, record:{...}}`, for example
  `runtime.session.metadata` `{kind:"metadata", record:{build:{semver,
  sha}, model_id, provider_id, tool_surface_version, web_search_mode,
  workspace_root}}`. Meta's script also accepts `workspace_root` directly
  on the payload (session-evidence.py `_workspace_metadata`), so read
  `payload.record.X` then `payload.X`.
- **`runtime.session`**: `payload = {kind, run_id, event:{kind, ...}}` with
  `payload.kind` one of `run` (also `source_run_record_id`,
  `source_run_record_sequence`), `task` (also `task_id`), `approval`, or
  a session-level kind without `event` (`agent_tree_initialized` with
  `record`). The conversation is in `payload.kind == "run"`.

### Run events (`payload_type:"runtime.session"`, `payload.kind:"run"`)

`payload.event.kind` (observed unless marked binary; the full
`AgentRunEvent` variant list is in the binary):

| `event.kind` | Fields | Meaning |
| --- | --- | --- |
| `started` | `prompt` (string); binary also `video` | start of a run (one agent turn); in a top-level log the text the user submitted (read-session skill: "every submitted prompt is recorded here"); in a subagent log the task the runtime gave the child |
| `user_prompt_display` (binary, skill) | one field, name undetermined | follows `started` only when the user-facing form differs (attachment placeholder `[Image 1]`) |
| `model_request_configured` | `base_instructions` (full system prompt), `base_instructions_source`, `toolset{active_tools[], mode, source}`, `run_context_messages[{id, role:"developer", source, lifecycle, order, text}]`, `reminder_roster` | the request setup; `run_context_messages` hold the injected AGENTS.md/rules file, workspace identity, sandbox policy, skills catalog, memory snapshot |
| `provider_request_options_configured`, `model_input_trace_recorded`, `context_block_diagnostic`, `goal_usage_attribution`, `resource_usage_sampled`, `task_stream_linked`, `reminder_proposal`, `reminder_reconciler_outcome`, `skill_reminder_decision`, `memory_reminder_child_session_linked` | bookkeeping | sizes, digests, usage, subagent links (section 4) |
| `model_response_created` | `response_id` | provider response opened |
| `reasoning_summary_delta` | `message_id`, `summary_index`, `text` | one summary paragraph, durable, written before the committed record |
| `reasoning_summary_committed` | `message_id`, `provider_item_id`, `response_id`, `text` | the readable reasoning summary; `text` equals the deltas of the same `message_id` joined by `\n\n` (5 of 5 observed) |
| `reasoning_committed` | `message_id`, `provider_item_id`, `response_id`, `text`, `encrypted_content` | raw reasoning; `text` was `""` in all 19 observed, the content is the opaque `encrypted_content` |
| `model_completed` | `model`, `finish_reason` (`tool_calls` observed), `duration_ms`, `usage{input_tokens, output_tokens, reasoning_tokens, cached_tokens, cache_read_tokens, cache_write_tokens}` | end of one model call; `model` absent in approval-review logs |
| `assistant_message_committed` | `message_id`, `provider_item_id`, `response_id`, `text`; binary 5th field `phase` | the full assistant reply text |
| `assistant_tool_calls_committed` | `message_id`, `response_id`, `tool_calls[{name, call_id, id, args}]` | tool calls; `args` is a JSON-encoded **string** (14 of 14 observed; Meta's script also accepts an object); `call_id` (`call_...`) is the join key, `id` (`fc_...`) is the provider item id |
| `tool_result_batch_committed` | `batch_id` (= the calls' `message_id`), `results[{tool_call_id, tool_call_index, text}]` | tool results, one batch per call batch; `text` is a string, sometimes JSON-encoded (below) |
| `tool_result` (binary, script) | binary fields `call_id`, `tool_result_model_visible_content`/`content`, `tool_search_tools_json` | single-result form; Meta's script reads `text`, `output` or `result` and `tool_call_id` or `call_id` |
| `tool_results_committed`, `tool_result_committed` (binary, script) | as the batch | older or alternative names the script still handles |
| `provider_tool_call_started`/`_completed` (binary) | `call_id`, `status`, `action`, `results`, `raw_item_json` | provider-hosted tool calls; not observed (web search ran client-side, `web_search_mode:"client"`) |
| `terminal` | `terminal` (`completed`, `failed`; binary also `cancelled`), `reason` (error text or null), `turn_duration_ms`, `time_to_first_token_ms`, `eot_gate_ms`, `failure_retryable` | end of the run |
| `inbox_item_queued` (binary, skill) | `source{source}`, `summary`, `delivery_segments`, `payload{prompt}` or `body`, `disposition` | a prompt typed while a run was active has `source.source:"user_steer"`; background and scheduled deliveries share the kind (skill) |
| `text_delta`, `reasoning_delta` (binary) | 2 fields each | live streaming; never observed in a durable log |
| `context_compaction_installed`, `context_compaction_candidate`, `context_compaction_fallback`, `tool_results_cleared`, `context_projection_checkpoint` (binary) | not observed; `context_projection_checkpoint.session_metadata.workspace_root` per the script | context management |
| `turn_task_died`, `run_retracted` (`retracted_prompt_sequence`), `run_fatal_error_classified` (`error_class`), `todo_snapshot_updated`, `user_input_prompt_requested`/`_settled`, `workflow_*`, `hook_*`, `code_mode_*` (binary) | not observed | |

### Tool call arguments and results (observed)

| Tool | `args` (decoded) | Result `text` |
| --- | --- | --- |
| `bash` | `command`, `description` | JSON string `{chunk_id, command, description, exit_code, terminal_status, output, original_output_bytes, original_output_tokens, truncated}` |
| `web_search` | `query` | JSON string `{query, results[{url, title, snippet, page_last_modified}]}` |
| `web_fetch` | `url` | plain text, cut at about 4.7 KB, ending in a `<system-reminder>` naming the spill file under `tool-outputs/` when `Truncated: true` |
| `submit_reminder_decision` (reminder subagents) | `decision`, `next_step`, `reason` | `"reminder decision recorded"` |
| any failed call | | plain text starting `tool failed: ` (observed for `web_fetch` 403 and TLS errors) |

The model's tool list (observed `toolset.active_tools`): `workflow`,
`read_file`, `search`, `write_file`, `edit_file`, `read_memory`,
`add_memory`, `edit_memory`, `list_peer_sessions`, `send_session_message`,
`work_stop`, `work_list`, `work_status`, `web_fetch`, `web_search`, `bash`,
`bash_input`, `monitor`, `cron_create`, `cron_delete`, `cron_list`,
`get_goal`, `create_goal`, `update_goal`, `report_progress`,
`request_user_input`, `subagent_spawn`, `subagent_status`,
`subagent_send_message`, `subagent_wait`, `subagent_read_result`,
`subagent_cancel`, `read_skill`, `snooze_reminder`, `write_todos`. Argument
names for tools not exercised are undetermined; Meta's script looks for a
path in `path`, `file_path`, `target_path`, `target`, `filename`, or the
`*** Add|Update|Delete File:` line of `patch`/`input`, and for a shell
command in `cmd` or `command`, and strips an MCP namespace by splitting the
tool name on `__`, `.` or `/` (session-evidence.py `_path_from_args`,
`_tool_name`).

### Task and effect events

`payload.kind:"task"` events (`proposed`, `accepted`, `scheduled`,
`side_effect_intent`, `started`, `status`, `output`, `tool_output_ref`,
`completed`, `failed`, `rejected`) track each model call and tool call as a
task (observed). `task/output` `{chunk, final_result}` repeats the tool
result text. `tool_output_ref` `{availability, output_ref{id, kind,
media_type, byte_len, digest, path, uri:"tool-output://local/<task
id>/<file>"}}` names the spill file. `tool_batch.effect.started`
`{kind:"tool_batch_effect", run_id, record{call_id, effect_id, task_id,
task_stream, tool_name, model_call_index, parallel_profile}}` and
`.terminal` `{record{call_id, outcome{kind:"completed"|"failed", reason,
output_ref_count, task_completion}}}` bracket each tool execution.
`runtime.session.task` (a separate `payload_type`) carries the same
lifecycle for session-level tasks such as naming the session.

### Approval events

`payload.kind:"approval"`, `payload_schema_version` 3 (observed):
`requested` `{approval_subject{kind:"tool_action", tool_name, network{host,
port, protocol}, origin{kind, url}}, available_choices[], tool_call_id,
tool_name, raw_args, pending_action_id, task_id, run_stream,
session_stream, presentation_phase}`; `automated_review_started`
`{review_id, reviewer_rollout_id, exact_action{...}, model{model_id,
provider_id, reasoning_effort}, started_at_ms}`;
`automated_review_completed` `{assessment{outcome, rationale, risk_level,
user_authorization}, status, duration_ms, completed_at_ms, usage}`;
`decision_applied` `{decision ("approved" observed), decision_source{kind:
"llm_judge", review_id}, policy_result ("allow"), amendment,
pending_action_id}`. A human decision's `decision_source.kind` is
undetermined (only the automated reviewer ran).

### Session-level records (observed)

| `payload_type` | `payload` |
| --- | --- |
| `runtime.session.metadata` | `record{workspace_root, model_id, provider_id, build{semver, sha}, ...}`; a subagent log's copy has only `model_id`, `provider_id`; may repeat |
| `runtime.session.route_facts` | `record{cwd, pid, local_runtime_command_socket_path, terminal_title_identity}` |
| `session.workspace_branch.observed` | `record{workspace_root, vcs:"git", commit (12 hex), reference{kind:"branch", name}, command_id}`; absent outside a repository; repeated at each run start |
| `session.opened.observed` | `record{session_id, resume, security_mode, workspace_kind, credential_backend, keychain_fallback_reason, ...}` |
| `session.name.changed` | `{session_id, new_name, previous_name, source ("automatic" or "user"), operation_id, authority_id}` |
| `run.model.configured` | `record{model_id, display_label, provider_id, profile_id, source, run_stream{id: run id, kind:"run"}, command_id}`, written before each run |
| `runtime.model_reconfigure.completed` | `record{effective{model_id, ...}, previous{...}, apply_outcome}` (a `/model` change) |
| `runtime.user_intent.accepted` | `{intent_id (= run id), surface:"main", semantic_kind{kind:"chat"}, model_messages[{content[{kind:"text", text}]}], refill_blocks, bindings, source_session_id}`, the same prompt as the run's `started` |
| `runtime.user_intent.materialized` | `{intent_id, outcome{kind:"top_level_turn_started", run_id, ...}}` |
| `session.end` | `record{exit_reason ("clean"), uptime_ms, resource_usage{..., session_log_bytes}}` |
| `session.login.completed`, `session.payment_gate.*`, `session.subscription_entrypoint.impression`, `session.startup_phases.observed`, `runtime.command_intake.*`, `runtime.retained_fact`, `runtime.session.capture_selection`, `reminder.cleanup_effect.*` | telemetry and bookkeeping |

`user_shell.command` `{command_id, command_text, client_id, queue_item_id}`
and `user_shell.result` `{terminal_state (completed, failed, timed_out,
cancelled), exit_code, exit_signal, duration_ms, visible_output, truncated,
output_ref}` record a shell command the user ran from the TUI (binary,
`UserShellCommandRecord`, `UserShellResultRecord`). Whether they sit under
`payload.record` like the other fact records is undetermined.

### Completeness and streaming

The JSONL is complete on its own. `session.peer-history.sqlite3` holds no
content (section 5); the only content outside the log is the full tool
output in `tool-outputs/`, whose cut-down form is already in the result
`text`. Streaming deltas are not reassembled: `text_delta` and
`reasoning_delta` never reach the durable log, ephemeral tool progress is
replaced by `retained_marker` lines, and `reasoning_summary_delta` records
are complete paragraphs whose join is the committed record. Each
`*_committed` record carries the full text.

## 4. Joins

- Session id: envelope `stream.id`; equals the directory name. A subagent
  log's `stream.id` is the subagent id (its directory name), and its runs
  use the same id as `run_id`.
- Turn: `payload.run_id` groups a run's records; `run.model.configured`
  `record.run_stream.id` gives that run's model.
- Tool call to result: `tool_calls[].call_id` =
  `results[].tool_call_id` (observed 14 of 14); also `tool_batch.effect.*`
  `record.call_id` and approval `tool_call_id`.
- Spill file: `tool_batch.effect.*` `record.call_id` gives `task_id`;
  `task/tool_output_ref` with that `task_id` gives `output_ref.path`, which
  is `tool-outputs/<task_id>/<call_id>-<kind>.txt` in the session directory
  (observed 5 of 5).
- Reminder subagent to parent (observed): parent `run/task_stream_linked`
  `{task_id, display{label, role:"reminder", path:"subagent/<id>/session.jsonl"}}`
  and `run/memory_reminder_child_session_linked` `{child_session_id,
  child_session_log_path, parent_session_id, parent_run_id,
  reminder_agent_id ("verify-reminder", "skill-reminder"), task_id}`. A
  linked child may have no directory when it failed before writing
  (observed once).
- Native subagent to parent (binary, not observed): `subagent.control.*`
  records; `spawn_accepted` has `command_id`, `parent_run_id`,
  `agent_path`, `description`, `task_id`, `task_stream`,
  `workflow_run_id`, `worktree_isolation_request`; `start_attested` has
  `subagent_session_id`, `dispatched_via_tool_call_id`, `run_stream`,
  `parent_trace_id`, `parent_span_id`. `dispatched_via_tool_call_id` is the
  parent's `subagent_spawn` `call_id`. A sample literal in the binary places
  such a child (`agent.dispatch.researcher`) at
  `subagent/<id>/session.jsonl` too.
- Project: `runtime.session.metadata` `record.workspace_root` (also
  `route_facts.record.cwd`). Subagent logs carry none; take the parent's.
- Approval review: `automated_review_started.reviewer_rollout_id` is the
  `approval-review/<id>.jsonl` file name and that log's `stream.id`.
- `tui-history.jsonl`: `session` = session id, `project` = workspace root.

## 5. SQLite and other stores

- `session.peer-history.sqlite3` (WAL; observed): `schema_meta(key,
  value)`, `source_snapshot(source_identity, source_len,
  source_modified_ns, target_stream_id, target_records_complete,
  anchor_start, anchor_end, anchor_sha256)`, `retained_records(line_start,
  line_end, event_id, stream_kind, stream_id, sequence, raw_sha256)`,
  `stable_ids(kind, stable_id, target_session_id, event_id, line_start)`.
  Byte offsets and hashes into `session.jsonl` only; useful to show a log
  was edited (`raw_sha256` per line), not for content.
- `session-index.db` (observed, no sidecars at rest): table `sessions`
  with `session_id`, `session_dir`, `session_log_path`, `layout`
  (`session_jsonl`), `workspace_root`, `provider_id`, `model_id`,
  `git_branch` (empty even for the git session), `title` and
  `first_user_prompt` (the first prompt), `search_text`, `created_at_us`,
  `updated_at_us`, `prompt_count`, `status`, `session_name`, `msp_*`
  fork columns. A cross-check, not a transcript.
- `session-names.db`: `session_name_claims_v2`,
  `session_name_operations_v2` (name history per session).
- `cron.db` (observed, empty): `cron_jobs(id, session_id, cron_expr,
  prompt, recurring, agent_id, kind ('user'), created_at_ms,
  next_fire_at_ms, last_fired_at_ms, fire_count, status,
  last_fire_run_id, ...)`. A scheduled prompt is user-authored text that
  fires later as a run.
- `.msp-view-v1/<id>/journal-*.bin`: length-prefixed JSON notifications
  (`turn/started`, `item/completed` with `item.kind` `userMessage`,
  `toolCall`, `reasoning`, `reminderChild`, `approval/requested`,
  `session/tokenUsage`, ...) each with `sourceRange` pointing back at
  `session.jsonl` sequences, and `recordedAt` as ISO 8601. Derived and
  redundant; `HEAD.json` `source_through.sequence` says how far it got.
- `approval-review/<id>.jsonl`: envelopes with
  `stream.kind:"approval.review.runtime"`, one run per review (7 runs in
  one file observed), each `started.prompt` a JSON
  `approval_review_context` document and a `submit_approval_assessment`
  tool call. `recorded_at` is a **synthetic clock**: 1780531500000000 µs
  (2026-06-04T00:05:00Z) plus `sequence - 1` (214 of 214 observed). The
  real times are the parent's `automated_review_started.started_at_ms` and
  `automated_review_completed.completed_at_ms` (milliseconds).
- `tui-history.jsonl` (observed): **two lines per entry**, a JSON string
  (the prompt text as typed) followed by an object `{project, session}`.
  No timestamp.

## 6. Format versions

Envelope `schema_version` 1 and frame `frame_schema_version` 1 only.
`payload_schema_version` differs per type (1 to 3 observed) and is bumped
in place; the approval payloads at 3 show three revisions. Meta's script
tolerates older names (`tool_results_committed`, `tool_result_committed`,
`payload.workspace_root`), so earlier builds wrote them. The binary also
carries the literal `XDG_DATA_HOME:-$HOME/.local/share}/metacode/...` in
its bundled skill text, an apparent earlier product name; no `metacode`
directory was present. The `read-session` skill names the export
`muse export --session <id> --redacted` with `export_schema_version`,
`redaction`, `unparseable_lines` and `unknown_payload_kinds` fields
(binary); exports were not observed.

## 7. Secrets

`model_request_configured.base_instructions` and `run_context_messages`
hold the full system prompt, the project's rules file, and the memory
snapshot. Tool arguments and outputs are verbatim (`bash` output, fetched
pages, file contents). `reasoning_committed.encrypted_content` is an
opaque provider blob. `approval/requested.raw_args` and
`automated_review_started.exact_action` repeat the command or URL under
review. No credential was found in any session file; the token is in
`~/.config/muse/auth.json` (collectors document). Meta's own export
redacts keys matching `api.?key|authorization|bearer|cookie|credential|
password|secret|token` and `sk-`, `ghp_`, `AKIA`, `AIza`, `xox`, JWT
shapes (session-evidence.py `SENSITIVE_KEY`, `STANDALONE_SECRET`), which is
a reasonable list of what tool output can contain.

## 8. Parser plan

`wants()` by `artifact.rel`:

```text
^\.local/share/muse/sessions/\d{4}/\d{2}/\d{2}/[^/]+/(?:subagent/[^/]+/)*session\.jsonl$
^\.local/share/muse/tui-history\.jsonl$
```

Not wanted: `approval-review/*.jsonl`, `tool-outputs/**`, `cli-*.log`,
`.msp-view-v1/**`, the SQLite files, `.session.jsonl.permission-init`.
Treat a file whose first parseable record has neither `retained_frame`
nor `stream`/`payload_type` as not Muse.

Read every line with `iter_jsonl`; a bad line (a log cut mid-write) is one
`system` row and reading continues. For each line:

1. `retained_marker`: skip (no content, no time).
2. `retained_frame`: decode each `children[].record_json` with
   `json.loads` and process the inner envelopes in `child_index` order with
   the outer `source_line`. They are permission records: no rows by
   default.
3. Envelope: dispatch on `payload_type`, then `payload.kind`, then
   `payload.event.kind`, per the table. Ignore unknown types silently.

Timestamp: `to_utc(recorded_at / 1_000_000)`. `to_utc` reads epoch numbers
above 1e11 as milliseconds, so the raw microsecond value must be divided
first.

Coverage:

| Record | `turn_type` |
| --- | --- |
| run `started`, top-level log | `user` |
| run `started`, subagent log | `system` (the runtime's task for the child, not typed by the person) |
| run `inbox_item_queued` with `source.source == "user_steer"` | `user`, text `payload.prompt` else `body` |
| run `inbox_item_queued`, other sources | `system` |
| run `assistant_message_committed` | `assistant` |
| run `reasoning_summary_committed` | `thinking` (only with `include_thinking`) |
| run `reasoning_committed` with non-empty `text` | `thinking`; skip when `text` is empty (always observed) |
| run `reasoning_summary_delta` | skip; duplicate of the committed record. If a `message_id` has deltas and no committed record (log cut), emit one `thinking` row with the deltas joined by `\n\n` |
| run `assistant_tool_calls_committed` | one `tool_use` per `tool_calls[]` |
| run `tool_result_batch_committed` | one `tool_result` per `results[]` |
| run `tool_result`, `tool_results_committed`, `tool_result_committed` | `tool_result`, Meta's field fallbacks |
| run `provider_tool_call_completed` | `tool_use` + `tool_result` on `call_id` |
| run `terminal` with `terminal != "completed"` | `system`, text `run <terminal>: <reason>` |
| run `context_compaction_installed`, `run_retracted`, `turn_task_died` | `system`, compact JSON of the event |
| approval `requested` | `system`, `tool_name` from `tool_name`, `tool_use_id` from `tool_call_id`, text `approval requested: <raw_args>` |
| approval `decision_applied` | `system`, text `approval <decision> by <decision_source.kind>` |
| `user_shell.command` / `user_shell.result` | `tool_use` / `tool_result`, `tool_name` `user_shell`, `tool_use_id` `command_id`, text `command_text` / `visible_output` |
| `session.name.changed` | `system`, text `session name: <new_name>` |
| `runtime.model_reconfigure.completed` | `system`, text `model: <effective.model_id>` |
| `subagent.control.spawn_accepted`, `.start_attested` | `system`, compact JSON (shape unverified) |
| `runtime.session.metadata`, `session.workspace_branch.observed`, `run.model.configured` | no row; fill `project_path`, `git_branch`, `model` |
| `runtime.user_intent.accepted` | skip; same prompt as `started` (use it for `user` text only if `started` is missing) |
| run `model_completed` | no row; fills `model` |
| all task events, `tool_batch.effect.*`, approval `automated_review_*`, `model_request_configured` and the other bookkeeping run events, `session.opened.observed`, `session.end`, telemetry, permission records | skip: duplicates or bookkeeping |
| `tui-history.jsonl` entry | `user`, empty `timestamp_utc` |

Columns:

| Column | Source |
| --- | --- |
| timestamp_utc | envelope `recorded_at` (µs) / 1e6 |
| session_id | envelope `stream.id`; `tui-history`: the object line's `session` |
| project_path | latest `runtime.session.metadata` `record.workspace_root` (fall back to `payload.workspace_root`, then `route_facts.record.cwd`); for a subagent log, read the parent log's metadata (the `session.jsonl` above the `subagent/` segments) with a bounded scan; `tui-history`: `project` |
| git_branch | latest `session.workspace_branch.observed` `record.reference.name` when `reference.kind == "branch"`; empty otherwise and in subagent logs unless taken from the parent |
| turn_type | coverage table |
| model | `run.model.configured` `record.model_id` keyed by `record.run_stream.id` = `payload.run_id`; else the run's `model_completed.model`; else `runtime.session.metadata` `record.model_id` when non-empty |
| tool_name | `tool_calls[].name`; on results, the name remembered for `tool_call_id` |
| tool_use_id | `tool_calls[].call_id` / `results[].tool_call_id` |
| text | `user`: `prompt`; `assistant`/`thinking`: `text`; `tool_use`: decode `args` when it is a string, then `command` or `cmd` (bash), `url` (web_fetch), `query` (web_search), `path`/`file_path` (file tools), else compact JSON of the arguments; `tool_result`: `text`, and when it decodes to an object with `output` (bash) use `output`, prefixed `[exit N] ` when `exit_code` is non-zero |
| source_line | 1-based line number of the outer line (frame children share it) |

A tool result whose text says `Full output saved to: <path>` is cut; the
parser leaves it as is (the collected `tool-outputs/` file holds the rest).

Sample fixture `.local/share/muse/sessions/2026/10/01/01a0f000-0000-7000-8000-000000000001/session.jsonl`
(frame, metadata, branch, name, model, intent, user prompt, reasoning
delta, summary, encrypted reasoning, model completion, bash call, effect,
marker, effect end, bash result, approval request and decision, subagent
link, assistant reply, run end, session end, then a cut line):

```json
{"retained_frame":"session_permission_transaction","frame_schema_version":1,"outer_log_ordinal":1,"transaction_id":"a1b2c3d4-0000-4000-8000-000000000001","children":[{"child_index":0,"record_json":"{\"schema_version\":1,\"id\":\"00000000-0000-4000-8000-000000000001\",\"stream\":{\"kind\":\"session\",\"id\":\"01a0f000-0000-7000-8000-000000000001\"},\"sequence\":1,\"recorded_at\":1790845200000000,\"record_type\":\"event\",\"durability\":\"durable\",\"causation_id\":null,\"payload_type\":\"runtime.session.permission_format_declared\",\"payload_schema_version\":1,\"payload\":{\"format\":\"profile_v1\",\"schema_version\":1}}"},{"child_index":1,"record_json":"{\"schema_version\":1,\"id\":\"00000000-0000-4000-8000-000000000002\",\"stream\":{\"kind\":\"session\",\"id\":\"01a0f000-0000-7000-8000-000000000001\"},\"sequence\":2,\"recorded_at\":1790845200000000,\"record_type\":\"event\",\"durability\":\"durable\",\"causation_id\":null,\"payload_type\":\"runtime.session.permission_profile_committed\",\"payload_schema_version\":1,\"payload\":{\"actor\":{\"id\":null,\"kind\":\"runtime\"},\"cause\":\"new_session_default\",\"permission_epoch\":1,\"resolved_snapshot\":{\"approval\":\"on_request\",\"reviewer\":\"auto_review\",\"schema_version\":1},\"schema_version\":1,\"source\":{\"display_name\":\"Auto-review\",\"id\":\":auto-review\",\"kind\":\"built_in\"}}}"}],"content_sha256":"sha256:0000000000000000000000000000000000000000000000000000000000000000"}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000003","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":3,"recorded_at":1790845200100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session.metadata","payload_schema_version":1,"payload":{"kind":"metadata","record":{"build":{"semver":"1.4.2","sha":"0123abcd45"},"model_id":"muse-spark-1.3-contributor","provider_id":"meta","tool_surface_version":"2","web_search_mode":"client","workspace_root":"/srv/proj"}}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000004","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":4,"recorded_at":1790845200200000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"session.workspace_branch.observed","payload_schema_version":1,"payload":{"kind":"workspace_branch","record":{"command_id":"01a0f000-0000-7000-8000-000000000001","commit":"0123456789ab","reference":{"kind":"branch","name":"main"},"vcs":"git","workspace_root":"/srv/proj"}}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000005","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":5,"recorded_at":1790845200300000,"record_type":"event","durability":"durable","causation_id":"f0f0f0f0-0000-4000-8000-000000000001","payload_type":"session.name.changed","payload_schema_version":1,"payload":{"authority_id":"d0d0d0d0-0000-4000-8000-000000000001","new_name":"quiet-lyra","operation_id":"e0e0e0e0-0000-4000-8000-000000000001","previous_name":null,"session_id":"01a0f000-0000-7000-8000-000000000001","source":"automatic"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000006","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":6,"recorded_at":1790845200900000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"run.model.configured","payload_schema_version":1,"payload":{"kind":"run_model","record":{"command_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","display_label":"muse-spark-1.3-contributor","model_id":"muse-spark-1.3-contributor","profile_id":"tbh","provider_id":"meta","run_stream":{"id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","kind":"run"},"source":"startup"}}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000007","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":7,"recorded_at":1790845201000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.user_intent.accepted","payload_schema_version":1,"payload":{"bindings":[],"delivery_policy":"session_current","intent_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","model_messages":[{"content":[{"kind":"text","text":"fix the failing test"}]}],"refill_blocks":[{"kind":"text","text":"fix the failing test"}],"semantic_kind":{"kind":"chat"},"source_session_id":"01a0f000-0000-7000-8000-000000000001","surface":"main","wake_policy":"start_once"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000008","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":8,"recorded_at":1790845201000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"started","prompt":"fix the failing test"},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000001","source_run_record_sequence":1}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000009","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":9,"recorded_at":1790845203000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"reasoning_summary_delta","message_id":"20000000-0000-4000-8000-000000000001","summary_index":0,"text":"Running the tests first."},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000005","source_run_record_sequence":5}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000010","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":10,"recorded_at":1790845203100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"reasoning_summary_committed","message_id":"20000000-0000-4000-8000-000000000001","provider_item_id":"rs_0001:rs_0002","response_id":"resp_0001","text":"Running the tests first."},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000006","source_run_record_sequence":6}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000011","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":11,"recorded_at":1790845203200000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"encrypted_content":"Q-AAAA","kind":"reasoning_committed","message_id":"20000000-0000-4000-8000-000000000002","provider_item_id":"rs_0001:rs_0002","response_id":"resp_0001","text":""},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000007","source_run_record_sequence":7}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000012","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":12,"recorded_at":1790845203300000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"duration_ms":2300,"finish_reason":"tool_calls","kind":"model_completed","model":"muse-spark-1.3-contributor","usage":{"cache_read_tokens":0,"cache_write_tokens":0,"cached_tokens":0,"input_tokens":900,"output_tokens":40,"reasoning_tokens":12}},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000008","source_run_record_sequence":8}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000013","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":13,"recorded_at":1790845203400000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"assistant_tool_calls_committed","message_id":"20000000-0000-4000-8000-000000000003","response_id":"resp_0001","tool_calls":[{"args":"{\"command\": \"npm test\", \"description\": \"Run the test suite\"}","call_id":"call_01","id":"fc_01","name":"bash"}]},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000009","source_run_record_sequence":9}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000014","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":14,"recorded_at":1790845203500000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"tool_batch.effect.started","payload_schema_version":1,"payload":{"kind":"tool_batch_effect","record":{"call_id":"call_01","effect_id":"30000000-0000-7000-8000-000000000001","kind":"started","model_call_index":0,"parallel_profile":{"kind":"ineligible"},"task_id":"30000000-0000-7000-8000-000000000001","task_stream":{"id":"30000000-0000-7000-8000-000000000001","kind":"task"},"tool_name":"bash"},"run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b"}}
{"retained_marker":"omitted_live_only","schema_version":1,"stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"position":{"id":"40000000-0000-4000-8000-000000000015","sequence":15},"omitted_record":{"record_type":"status","durability":"ephemeral","payload_type":"runtime.session","payload_schema_version":1,"payload_kind":"task","omission_class":"task_tool_delta_v1"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000016","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":16,"recorded_at":1790845204400000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"tool_batch.effect.terminal","payload_schema_version":1,"payload":{"kind":"tool_batch_effect","record":{"call_id":"call_01","effect_id":"30000000-0000-7000-8000-000000000001","kind":"terminal","model_call_index":0,"outcome":{"kind":"completed","output_ref_count":0,"task_completion":{"kind":"terminal","terminal":{"kind":"completed"}}},"task_id":"30000000-0000-7000-8000-000000000001","task_stream":{"id":"30000000-0000-7000-8000-000000000001","kind":"task"}},"run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000017","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":17,"recorded_at":1790845204500000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"batch_id":"20000000-0000-4000-8000-000000000003","kind":"tool_result_batch_committed","results":[{"text":"{\"chunk_id\": \"exec-1-1\", \"command\": \"npm test\", \"description\": \"Run the test suite\", \"exit_code\": 1, \"terminal_status\": \"completed\", \"output\": \"1 failing\", \"original_output_bytes\": 9, \"original_output_tokens\": 3, \"truncated\": false}","tool_call_id":"call_01","tool_call_index":0}]},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000014","source_run_record_sequence":14}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000018","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":18,"recorded_at":1790845205000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":3,"payload":{"event":{"approval_subject":{"kind":"tool_action","network":{"host":"registry.example.org","port":443,"protocol":"https"},"origin":{"kind":"url","url":"https://registry.example.org/pkg"},"tool_name":"network"},"kind":"requested","pending_action_id":"50000000-0000-7000-8000-000000000001","raw_args":"https registry.example.org:443","task_id":"30000000-0000-7000-8000-000000000002","tool_call_id":"call_02","tool_name":"network"},"kind":"approval","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000019","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":19,"recorded_at":1790845206000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":3,"payload":{"event":{"amendment":null,"decision":"approved","decision_source":{"kind":"llm_judge","review_id":"60000000-0000-4000-8000-000000000001"},"kind":"decision_applied","pending_action_id":"50000000-0000-7000-8000-000000000001","policy_result":"allow","session_stream":{"id":"01a0f000-0000-7000-8000-000000000001","kind":"session"}},"kind":"approval","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b"}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000020","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":20,"recorded_at":1790845207000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"child_session_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","child_session_log_path":"subagent/0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b/session.jsonl","generation_id":1,"kind":"memory_reminder_child_session_linked","parent_run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","parent_session_id":"01a0f000-0000-7000-8000-000000000001","reminder_agent_id":"verify-reminder","task_id":"30000000-0000-7000-8000-000000000003","task_stream":{"id":"30000000-0000-7000-8000-000000000003","kind":"task"}},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000020","source_run_record_sequence":20}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000021","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":21,"recorded_at":1790845209000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"assistant_message_committed","message_id":"20000000-0000-4000-8000-000000000004","provider_item_id":"msg_0001","response_id":"resp_0002","text":"The test fails because the fixture date is stale."},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000030","source_run_record_sequence":30}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000022","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":22,"recorded_at":1790845209100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"eot_gate_ms":3,"kind":"terminal","reason":null,"terminal":"completed","time_to_first_token_ms":800,"turn_duration_ms":8100},"kind":"run","run_id":"0b7e6f5a-4c3d-4e2f-9a1b-2c3d4e5f6a7b","source_run_record_id":"10000000-0000-4000-8000-000000000031","source_run_record_sequence":31}}
{"schema_version":1,"id":"00000000-0000-4000-8000-000000000023","stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"sequence":23,"recorded_at":1790845220000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"session.end","payload_schema_version":1,"payload":{"kind":"session_end","record":{"exit_reason":"clean","schema_version":1,"session_id":"01a0f000-0000-7000-8000-000000000001","uptime_ms":20000}}}
{"schema_version":1,"id":"00000000-0000-4000-8000-0000000000
```

Subagent fixture `.../01a0f000-0000-7000-8000-000000000001/subagent/0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b/session.jsonl`:

```json
{"retained_frame":"session_permission_transaction","frame_schema_version":1,"outer_log_ordinal":1,"transaction_id":"a1b2c3d4-0000-4000-8000-000000000002","children":[{"child_index":0,"record_json":"{\"schema_version\":1,\"id\":\"00000000-0000-4000-9000-000000000001\",\"stream\":{\"kind\":\"session\",\"id\":\"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b\"},\"sequence\":1,\"recorded_at\":1790845200000000,\"record_type\":\"event\",\"durability\":\"durable\",\"causation_id\":null,\"payload_type\":\"runtime.session.permission_format_declared\",\"payload_schema_version\":1,\"payload\":{\"format\":\"profile_v1\",\"schema_version\":1}}"},{"child_index":1,"record_json":"{\"schema_version\":1,\"id\":\"00000000-0000-4000-9000-000000000002\",\"stream\":{\"kind\":\"session\",\"id\":\"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b\"},\"sequence\":2,\"recorded_at\":1790845200000000,\"record_type\":\"event\",\"durability\":\"durable\",\"causation_id\":null,\"payload_type\":\"runtime.session.permission_profile_committed\",\"payload_schema_version\":1,\"payload\":{\"actor\":{\"id\":null,\"kind\":\"runtime\"},\"cause\":\"new_session_default\",\"permission_epoch\":1,\"resolved_snapshot\":{\"approval\":\"on_request\",\"reviewer\":\"auto_review\",\"schema_version\":1},\"schema_version\":1,\"source\":{\"display_name\":\"Auto-review\",\"id\":\":auto-review\",\"kind\":\"built_in\"}}}"}],"content_sha256":"sha256:0000000000000000000000000000000000000000000000000000000000000000"}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000003","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":3,"recorded_at":1790845207100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session.metadata","payload_schema_version":1,"payload":{"kind":"metadata","record":{"model_id":"muse-spark-1.3-contributor","provider_id":"meta"}}}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000004","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":4,"recorded_at":1790845207100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"run.model.configured","payload_schema_version":1,"payload":{"kind":"run_model","record":{"command_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","display_label":"muse-spark-1.3-contributor","model_id":"muse-spark-1.3-contributor","profile_id":"tbh","provider_id":"meta","run_stream":{"id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","kind":"run"},"source":"startup"}}}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000005","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":5,"recorded_at":1790845207200000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"started","prompt":"You are a reminder observer for the main agent."},"kind":"run","run_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","source_run_record_id":"10000000-0000-4000-8000-000000000001","source_run_record_sequence":1}}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000006","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":6,"recorded_at":1790845208000000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"assistant_tool_calls_committed","message_id":"20000000-0000-4000-8000-000000000010","response_id":"resp_0010","tool_calls":[{"args":"{\"decision\": \"none\", \"next_step\": null, \"reason\": \"Tests were run.\"}","call_id":"call_10","id":"fc_10","name":"submit_reminder_decision"}]},"kind":"run","run_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","source_run_record_id":"10000000-0000-4000-8000-000000000013","source_run_record_sequence":13}}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000007","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":7,"recorded_at":1790845208100000,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"batch_id":"20000000-0000-4000-8000-000000000010","kind":"tool_result_batch_committed","results":[{"text":"reminder decision recorded","tool_call_id":"call_10","tool_call_index":0}]},"kind":"run","run_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","source_run_record_id":"10000000-0000-4000-8000-000000000016","source_run_record_sequence":16}}
{"schema_version":1,"id":"00000000-0000-4000-9000-000000000008","stream":{"kind":"session","id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b"},"sequence":8,"recorded_at":1790845208199999,"record_type":"event","durability":"durable","causation_id":null,"payload_type":"runtime.session","payload_schema_version":1,"payload":{"event":{"kind":"terminal","reason":null,"terminal":"completed","time_to_first_token_ms":500,"turn_duration_ms":1000},"kind":"run","run_id":"0f3c2b1a-5d6e-4f70-8a9b-0c1d2e3f4a5b","source_run_record_id":"10000000-0000-4000-8000-000000000018","source_run_record_sequence":18}}
```

Prompt history fixture `.local/share/muse/tui-history.jsonl`:

```json
"fix the failing test"
{"project":"/srv/proj","session":"01a0f000-0000-7000-8000-000000000001"}
```

Noise the parser must not want:
`.local/share/muse/sessions/2026/10/01/01a0f000-0000-7000-8000-000000000001/approval-review/7a7a7a7a-0000-4000-8000-000000000001.jsonl`
(envelopes with `stream.kind:"approval.review.runtime"`) and
`.config/muse/settings.json`.

Expected rows from the main fixture: `system` (session name, line 4),
`user` (line 7), `thinking` (line 9, with `include_thinking`), `tool_use`
`bash` `call_01` text `npm test` (line 12), `tool_result` `call_01` text
`[exit 1] 1 failing` (line 16), two approval `system` rows (lines 17, 18),
`assistant` (line 20), and the bad-line `system` row (line 23); all with
`session_id` `01a0f000-...-000000000001`, `project_path` `/srv/proj`,
`git_branch` `main`, `model` `muse-spark-1.3-contributor`, first
timestamp `2026-10-01T09:00:00.300Z`. The subagent fixture yields a
`system` row for the started prompt, a `tool_use`
`submit_reminder_decision`, and a `tool_result`, with `session_id`
`0f3c2b1a-...` and `project_path` `/srv/proj` from the parent.

Confidence. High (observed and confirmed by the read-session skill and
Meta's script): envelope fields, microsecond `recorded_at`, frame and
marker shapes, `started`, `assistant_message_committed`,
`assistant_tool_calls_committed` with string `args`,
`tool_result_batch_committed`, reasoning records, `call_id` join,
metadata, branch, model and reminder-subagent linkage, the JSONL being
complete without the SQLite, the approval-review synthetic clock. Medium
(field names from the binary, not exercised): `inbox_item_queued`,
`user_prompt_display`, `tool_result`, `provider_tool_call_*`,
`user_shell.*`, `subagent.control.*`, compaction events, and where the
`user_shell` fields sit in the payload. Not determined: argument names of
tools other than `bash`, `web_search`, `web_fetch`; a native
`subagent_spawn` child's log (none was spawned); `reference.kind` values
other than `branch`; a human approval's `decision_source`; whether later
frames appear after a resume or permission change; `user_prompt_display`'s
field name.
