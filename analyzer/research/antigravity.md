# Antigravity CLI transcript schema

Evidence level: shipped binary (protobuf descriptors extracted from `agy`),
confirmed against a real install on the author's WSL workstation, October
2026. No public source exists. Extraction: `tools/proto_descriptors.py extract
~/.local/bin/agy descriptors.json`, then `show` on the names below.

Paths, credentials and the rest of the per-user state are in
[`collectors/research/antigravity.md`](../../collectors/research/antigravity.md).

## 1. Binary and version

`~/.local/bin/agy`, ELF x86-64, about 200 MB, Google Antigravity CLI, installed
2026-10-03. 1300 embedded `.proto` descriptors; the relevant packages are
`gemini_coder` (`third_party/gemini_coder/proto/trajectory.proto`),
`exa.cortex_pb` (`third_party/jetski/cortex_pb/cortex.proto`),
`exa.codeium_common_pb` and `exa.jetski_cortex_pb`. The `jetski`, `cascade`
and `codeium` names show the lineage from Windsurf's Cascade agent.

## 2. Stores, relative to home

| Path | Content |
| --- | --- |
| `.gemini/antigravity-cli/conversations/<uuid>.db` (+`-wal`, `-shm`) | one SQLite database per conversation, WAL mode |
| `.gemini/antigravity-cli/conversation_summaries.db` | one row per conversation |
| `.gemini/antigravity-cli/history.jsonl` | `{display, timestamp (ms), workspace}` per prompt |
| `.gemini/antigravity-cli/jetbox_summaries_proto.pb` | `jetbox_summaries_pb.SummariesState`, same summaries as the database |
| `.gemini/antigravity-cli/brain/<uuid>/` | per-conversation artifacts and logs |
| `.gemini/antigravity-cli/antigravity-oauth-token` | credential, flagged secret by the collector |
| `.gemini/antigravity-cli/bin/` | binaries, excluded |

## 3. Conversation database

```sql
CREATE TABLE trajectory_meta (trajectory_id text, cascade_id text, trajectory_type integer, source integer, PRIMARY KEY (trajectory_id));
CREATE TABLE steps (idx integer, step_type integer, status integer, has_subtrajectory numeric, metadata blob, error_details blob,
                    permissions blob, task_details blob, render_info blob, step_payload blob, step_format integer, PRIMARY KEY (idx));
CREATE TABLE gen_metadata (idx integer, data blob, size integer, PRIMARY KEY (idx));
CREATE TABLE executor_metadata (idx integer, data blob, PRIMARY KEY (idx));
CREATE TABLE parent_references (idx integer, data blob, PRIMARY KEY (idx));
CREATE TABLE trajectory_metadata_blob (id text DEFAULT "main", data blob, PRIMARY KEY (id));
CREATE TABLE battle_mode_infos (idx integer, data blob, PRIMARY KEY (idx));
```

The tables mirror `gemini_coder.Trajectory`: `steps` (field 2),
`generator_metadata` (3), `trajectory_type` (4), `parent_references` (5),
`cascade_id` (6), `metadata` (7), `source` (8), `executor_metadatas` (9),
`battle_mode_infos` (10). `cascade_id` equals the conversation id and the
file name. `source` 17 is `CORTEX_TRAJECTORY_SOURCE_CLI`; `trajectory_type`
4 is `CORTEX_TRAJECTORY_TYPE_CASCADE`.

`steps.step_payload` is a serialized `gemini_coder.Step`:

| Field | Name | Type |
| --- | --- | --- |
| 1 | `type` | `exa.cortex_pb.CortexStepType` (14 USER_INPUT, 15 PLANNER_RESPONSE, 132 GENERIC, 2 FINISH, 23 CHECKPOINT, 28 COMMAND_STATUS, ...) |
| 4 | `status` | `CortexStepStatus` (1 PENDING, 2 RUNNING, 3 DONE, 6 CANCELED, 7 ERROR, 9 WAITING, 12 INTERRUPTED) |
| 5 | `metadata` | `CortexStepMetadata` |
| 7..159 | oneof `step` | one message per step kind, field numbers in the parser's `SCHEMA["Step"]` |

`steps.metadata` duplicates field 5. `CortexStepMetadata`: 1 `created_at`,
3 `source` (`CortexStepSource`: 2 MODEL, 3 USER_IMPLICIT, 4 USER_EXPLICIT,
5 SYSTEM), 4 `tool_call` (`ChatToolCall`: 1 `id`, 2 `name`, 3
`arguments_json`, 9 `original_name`), 7 `finished_generating_at`, 8
`completed_at`, 11 `generator_model` (enum), 12 `execution_id`, 20
`source_trajectory_step_info`, 26 `internal_metadata.status_transitions`,
30 `tool_summary`, 31 `tool_action`, 32 `started_at`. All timestamps are
`google.protobuf.Timestamp` (seconds, nanos).

Step kinds seen on a real install: `user_input` (19: 1 `query`, 2
`user_response`, 12 `user_config`), `planner_response` (20: 1 `response`,
3 `thinking`, 6 `message_id`, 7 `tool_calls[]`, 12 `stop_reason`, 16
`raw_thinking`) and `generic` (140: 1 `args[]` key/value, 2 `result`
with 1 `result` text and 6 `payload` as `google.protobuf.Any` holding the
typed tool step, here `view_file`). The tool executed by a step is in its
`metadata.tool_call`; its `id` matches the `tool_calls[].id` proposed by the
preceding planner step. Tool payload messages the parser understands:
`run_command` (1 `command`, 2 `cwd`, 6 `exit_code`, 21 `combined_output`,
23 `command_line`, 14 `user_rejected`), `command_status`, `shell_exec`,
`view_file` (1 `absolute_path_uri`), `list_directory`, `grep_search`,
`find`, `write_to_file` (1 `target_file_uri`, 4 `file_created`),
`file_change`, `code_action` (1 `action_spec` with `command.file`,
`create_file.path`, `delete_file.path`, `sed.path` as `PathScopeItem` 5
`absolute_uri`), `read_url_content`, `search_web`, `mcp_tool` (1
`server_name`, 2 `tool_call`, 3 `result_string`), `agency_tool_call`,
`invoke_subagent` (5 `conversation_id`, 10 `results[].conversation_id`),
`ask_question`, `checkpoint`, `system_message`, `ephemeral_message`,
`task_boundary`, `notify_user`, `error_message`, `finish`, `memory`,
`directory_rules`, `conversation_history`, `send_command_input`.

`gen_metadata.data` is `CortexStepGeneratorMetadata`: 1 `chat_model`
(`ChatModelMetadata`: 19 `response_model` such as `gemini-3.8-flash`, 21
`model_display_name`, 1 `system_prompt`, 2 `message_prompts[]`), 2
`step_indices[]` (packed). This is the only place the model name appears.

`trajectory_metadata_blob.data` is `CortexTrajectoryMetadata`: 1
`workspaces[]` (`CortexWorkspaceMetadata`: 1 `workspace_folder_absolute_uri`,
2 `git_root_absolute_uri`, 4 `branch_name`), 2 `created_at`, 5
`parent_conversation_id`, 6 `root_conversation_id`, 7 `workspace_uris[]`,
17 `nesting_depth`, 18 `project_id`.

## 4. Summaries database

```sql
CREATE TABLE conversation_summaries (conversation_id text PRIMARY KEY, title text, preview text, step_count integer,
  last_modified_time datetime, workspace_uris text, status text, source text, project_id text, agent_name text,
  parent_conversation_id text, nesting_depth integer, battle_id text, winning_conversation_id text, not_fully_idle numeric,
  killed numeric, last_user_input_time datetime, last_user_input_step_index integer, app_data_dir text, raw_summary blob, group_id text);
```

Times are text like `2026-10-03 16:43:44.002530482+00:00`. `workspace_uris`
is a JSON array of `file://` URIs. `status` is a `CascadeRunStatus` name.
`raw_summary` is `exa.jetski_cortex_pb.CascadeTrajectorySummary` (1
`summary`, 2 `step_count`, 3 `last_modified_time`, 7 `created_time`, 9
`workspaces[]`, 10 `last_user_input_time`, 17 `trajectory_metadata`, 22
`trajectory_type`, 24 `fork_parent_conversation_id`).

## 5. Joins and gaps

Conversation id = `cascade_id` = file name = `conversation_summaries.
conversation_id`. Subagent conversations are separate databases linked by
`parent_conversation_id` and by `invoke_subagent.results[].conversation_id`.
Git branch is available only when the trajectory metadata records a
workspace `branch_name`; the sample run from a non-git directory left it
empty. `history.jsonl` has no conversation id, so its rows carry only the
workspace. Only one conversation existed on the test machine, so step kinds
other than user_input, planner_response and generic are decoded from the
descriptors but have not been seen in real data.

## 6. Secrets

`antigravity-oauth-token` (collector secret glob). `ChatModelMetadata.
system_prompt` and `message_prompts` in `gen_metadata` hold the full prompt
including file contents; the parser does not read them. Tool outputs in
`generic.result` and `run_command` contain whatever the agent read.
