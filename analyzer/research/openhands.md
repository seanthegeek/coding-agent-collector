# OpenHands transcript schema

Catalog agent: `openhands`. Current OpenHands (Agent Canvas and the
`openhands` CLI) persists conversations through the Software Agent SDK as
one JSON file per event. Path research is in
[../../collectors/research/openhands.md](../../collectors/research/openhands.md).

## 1. Source

OpenHands/software-agent-sdk at
[`b347047e2dcdd8f4b2be810aa8bc6632bc756d41`](https://github.com/OpenHands/software-agent-sdk/commit/b347047e2dcdd8f4b2be810aa8bc6632bc756d41)
(SDK and Agent Server), OpenHands/OpenHands-CLI at
[`954f2ba646e8d749261a8f2b2b7e3031fa39be9f`](https://github.com/OpenHands/OpenHands-CLI/commit/954f2ba646e8d749261a8f2b2b7e3031fa39be9f),
and the legacy app at OpenHands/OpenHands tags `1.11.0`
([`11ca68ab2e15dcd85c21e4d7d3409e7a259369ac`](https://github.com/OpenHands/OpenHands/commit/11ca68ab2e15dcd85c21e4d7d3409e7a259369ac))
and `0.62.0` ([`7fbb48c40679afd674970966b96185657d92a487`](https://github.com/OpenHands/OpenHands/commit/7fbb48c40679afd674970966b96185657d92a487)). MIT, open source.

## 2. Transcript files

One directory per conversation, named by the conversation UUID as 32 hex
digits ([`openhands-sdk/openhands/sdk/conversation/base.py:331-345`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/base.py#L331-L345)), under:

- `.openhands/agent-canvas/dev_conversations/<hex>/` (Canvas, native) and
  `.openhands/agent-canvas/conversations/<hex>/` (Canvas in Docker);
- `.openhands/conversations/<hex>/` (CLI).

Inside ([`conversation/persistence_const.py:4-10`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/persistence_const.py#L4-L10)):

- `events/event-<idx, 5+ digits>-<event id>.json`, one compact JSON object
  per event ([`conversation/event_store.py:225-232`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/event_store.py#L225-L232),[`313-318`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/event_store.py#L313-L318)),
  plus an empty `.eventlog-len-<n>.marker` ([`event_store.py:27`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/event_store.py#L27)).
- `base_state.json`: `ConversationState` (agent with its LLM config,
  workspace, stats, secret registry)
  ([`conversation/state.py:82-225`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/state.py#L82-L225), [`435-447`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/state.py#L435-L447)).
- `meta.json` (Agent Server only): `StoredConversation`
  ([`openhands-agent-server/openhands/agent_server/event_service.py:276-297`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/event_service.py#L276-L297)).
- `bash_events/` for terminal sessions bound to the conversation
  ([`agent_server/dependencies.py:72-80`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/dependencies.py#L72-L80)); the global
  `.openhands/agent-canvas/bash_events/` has the same files.
- `TASKS.json` (CLI plan panel,
  [`openhands_cli/tui/panels/plan_side_panel.py:107`](https://github.com/OpenHands/OpenHands-CLI/blob/954f2ba646e8d749261a8f2b2b7e3031fa39be9f/openhands_cli/tui/panels/plan_side_panel.py#L107)).

The CLI also keeps `.openhands/projects/<sha256(cwd)>/prompt_history.json`
([`openhands_cli/locations.py:34-47`](https://github.com/OpenHands/OpenHands-CLI/blob/954f2ba646e8d749261a8f2b2b7e3031fa39be9f/openhands_cli/locations.py#L34-L47)).

## 3. Record schema

Every event has `kind` (the Python class name,
[`openhands-sdk/openhands/sdk/utils/models.py:202-205`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/utils/models.py#L202-L205)), `id` (UUID string),
`timestamp`, `source` in `agent|user|environment|hook`, `parent_id`
([`event/base.py:24-40`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/base.py#L24-L40); [`event/types.py:4-5`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/types.py#L4-L5)).
`timestamp` is `datetime.now().isoformat()`: **naive local time** with
microseconds and no zone ([`base.py:28-31`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/base.py#L28-L31)). The parser needs the
host's zone to convert it; `meta.json` `created_at`/`updated_at` are UTC
with offset ([`agent_server/models.py:120-121`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/models.py#L120-L121); [`agent_server/utils.py:53-55`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/utils.py#L53-L55))
and can anchor the offset. Files are written with `exclude_none`.

Kinds:

- `MessageEvent`: `source` user or agent, `llm_message` (`role`
  `user|system|assistant|tool`, `content` list of `{type:"text",text}` or
  `{type:"image",image_urls}`, `tool_calls?`, `reasoning_content?`,
  `thinking_blocks?`), `activated_skills`, `extended_content`, `sender`
  ([`event/llm_convertible/message.py:25-60`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/llm_convertible/message.py#L25-L60);
  [`llm/message.py:174-176`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/message.py#L174-L176), [`205-207`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/message.py#L205-L207), [`219-245`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/message.py#L219-L245)).
- `ActionEvent`: `thought` (text list), `reasoning_content`,
  `thinking_blocks` (`{type:"thinking",thinking,signature}` or
  `redacted_thinking`), `action` (object with its own `kind`, for example
  `TerminalAction` with `command`), `tool_name`, `tool_call_id`, `tool_call`
  (`id`, `name`, `arguments` JSON string, `origin`), `llm_response_id`,
  `security_risk`, `summary`
  ([`event/llm_convertible/action.py:24-80`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/llm_convertible/action.py#L24-L80);
  [`llm/message.py:25-40`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/message.py#L25-L40), [`123-147`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/message.py#L123-L147);
  [`openhands-tools/openhands/tools/terminal/definition.py:86-89`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-tools/openhands/tools/terminal/definition.py#L86-L89)).
  Tool names are the snake-cased class name without `_tool`, so
  `terminal`, `file_editor` ([`tool/tool.py:397`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/tool/tool.py#L397)).
- `ObservationEvent`: `tool_name`, `tool_call_id`, `action_id`,
  `observation` (own `kind`, `content` list, `is_error`; `TerminalObservation`
  adds `command`, `exit_code`)
  ([`event/llm_convertible/observation.py:17-40`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L17-L40);
  [`tool/schema.py:367-382`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/tool/schema.py#L367-L382); [`terminal/definition.py:146-152`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-tools/openhands/tools/terminal/definition.py#L146-L152)).
- `UserRejectObservation` (`rejection_reason`, `rejection_source`,
  `action_id`) and `AgentErrorEvent` (`error`, `classification`)
  ([`observation.py:86-147`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py#L86-L147)).
- `SystemPromptEvent`: `system_prompt`, `tools`, `dynamic_context`
  ([`event/llm_convertible/system.py:12-35`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/llm_convertible/system.py#L12-L35)).
- `ACPToolCallEvent` (Claude Code, Codex, Gemini driven over ACP):
  `tool_call_id`, `title`, `status`, `tool_kind`, `raw_input`,
  `raw_output`, `content`, `is_error` ([`event/acp_tool_call.py:46-65`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/acp_tool_call.py#L46-L65)).
- `HookExecutionEvent` (`hook_event_type`, `hook_command`, `exit_code`,
  `stdout`, `stderr`, `blocked`; [`event/hook_execution.py:22-80`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/hook_execution.py#L22-L80)),
  `Condensation` and `CondensationSummaryEvent` (`summary`;
  [`event/condenser.py:11-37`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/condenser.py#L11-L37), [`120-126`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/condenser.py#L120-L126)),
  `ConversationStateUpdateEvent` (`key`, `value`;
  [`event/conversation_state.py:18-35`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/conversation_state.py#L18-L35)), `PauseEvent`, `InterruptEvent`
  ([`event/user_action.py:7-32`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/event/user_action.py#L7-L32)).

`meta.json`: `id`, `title`, `created_at`, `updated_at`,
`forked_from_conversation_id`, `workspace` (`kind`, `working_dir`),
`parent_conversation_id`, `secrets`, `initial_message`
([`agent_server/models.py:102-143`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/models.py#L102-L143);
[`conversation/request.py:93-156`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/request.py#L93-L156)). `base_state.json`: `id`,
`agent.llm.model` ([`llm/llm.py:272`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/llm.py#L272); [`agent/base.py:117`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/agent/base.py#L117)),
`workspace.working_dir` ([`workspace/base.py:43`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/workspace/base.py#L43)), `execution_status`,
`stats.usage_to_metrics`.

Bash events (`bash_events/<YYYYMMDDHHMMSSffffff>_<kind>_[<command id>_]<event id>`,
no extension, indented JSON;
[`agent_server/bash_service.py:61-85`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/bash_service.py#L61-L85)): `BashCommand` (`id`,
`timestamp` UTC, `command`, `cwd`), `BashOutput` (`command_id`, `order`,
`exit_code`, `stdout`, `stderr`), `BashError`
([`agent_server/models.py:616-660`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-agent-server/openhands/agent_server/models.py#L616-L660)).

## 4. Joins

Session to project: `meta.json` or `base_state.json`
`workspace.working_dir` (a container path under Canvas-in-Docker).
Tool call to result: `ActionEvent.tool_call_id` = `ObservationEvent.tool_call_id`;
also `ObservationEvent.action_id` = `ActionEvent.id`. Parent to child
conversation: `meta.json` `parent_conversation_id`,
`forked_from_conversation_id`. Event order: the `idx` in the file name;
`parent_id` forms a tree when the user navigated back and branched.

## 5. SQLite or binary stores

None for current transcripts. Legacy 1.x kept conversation metadata in
`.openhands/openhands.db`
([`openhands/app_server/services/db_session_injector.py:192`](https://github.com/OpenHands/OpenHands/blob/11ca68ab2e15dcd85c21e4d7d3409e7a259369ac/openhands/app_server/services/db_session_injector.py#L192)). Legacy 0.x
wrote `agent_state.pkl` and `conversation_stats.pkl` (Python pickle; never
unpickle evidence) ([`openhands/storage/locations.py:29-38`](https://github.com/OpenHands/OpenHands/blob/7fbb48c40679afd674970966b96185657d92a487/openhands/storage/locations.py#L29-L38)).
`.openhands/automation/automations.db` is SQLite (automation schedules and
runs), outside this parser's scope.

## 6. Format versions

- Current SDK: as above. The 5-digit index is a minimum
  ([`persistence_const.py:6-10`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/persistence_const.py#L6-L10)).
- Legacy 1.x app: `.openhands/[<user_id>/]v1_conversations/<hex>/<event hex>.json`
  ([`openhands/app_server/conversation_paths.py:12`](https://github.com/OpenHands/OpenHands/blob/11ca68ab2e15dcd85c21e4d7d3409e7a259369ac/openhands/app_server/conversation_paths.py#L12); [`event/event_service_base.py:89`](https://github.com/OpenHands/OpenHands/blob/11ca68ab2e15dcd85c21e4d7d3409e7a259369ac/openhands/app_server/event/event_service_base.py#L89)),
  SDK events stored by id rather than index (inferred: the app server
  relays SDK events; field shapes not re-read).
- Legacy 0.x: `.openhands/sessions/<sid>/events/<n>.json` with top-level
  `id`, `timestamp`, `source`, `message`, `cause`, `action` or
  `observation`, `tool_call_metadata`, `llm_metrics`, and `args`/`extras`
  ([`openhands/events/serialization/event.py:15-25`](https://github.com/OpenHands/OpenHands/blob/7fbb48c40679afd674970966b96185657d92a487/openhands/events/serialization/event.py#L15-L25);
  [`openhands/storage/locations.py:1-18`](https://github.com/OpenHands/OpenHands/blob/7fbb48c40679afd674970966b96185657d92a487/openhands/storage/locations.py#L1-L18)). A different parser.

## 7. Secrets

`base_state.json` `agent.llm.api_key`, `aws_secret_access_key`
([`llm/llm.py:277`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/llm.py#L277), [`327`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/llm/llm.py#L327)) and `secret_registry`, and
`meta.json` `secrets`, are Fernet ciphertext when the server has
`OH_SECRET_KEY` (in `.openhands/agent-canvas/secret-key.txt`), else
redacted as `**********` ([`conversation/state.py:435-447`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/conversation/state.py#L435-L447);
[`utils/pydantic_secrets.py:48-78`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/utils/pydantic_secrets.py#L48-L78)). `thinking_blocks[].signature`,
`responses_reasoning_item.encrypted_content` are opaque blobs. Terminal
output in observations and bash events can contain pasted tokens.

## 8. Parser plan

Globs: `.openhands/agent-canvas/dev_conversations/*/events/event-*.json`,
`.openhands/agent-canvas/conversations/*/events/event-*.json`,
`.openhands/conversations/*/events/event-*.json`; read the sibling
`meta.json` and `base_state.json` once per conversation. Optional:
`bash_events/*`. One row per event; an `ActionEvent` also yields a
`thinking` row for `thought`/`reasoning_content`. Detect and report legacy
`sessions/*/events/*.json` without parsing.

| Column | Source |
| --- | --- |
| timestamp_utc | event `timestamp` (naive local; convert with the host zone, else mark) |
| session_id | conversation directory name (hex) or `meta.json` `id` |
| project_path | `workspace.working_dir` |
| git_branch | empty |
| turn_type | `MessageEvent` by `llm_message.role`; `ActionEvent`, `ACPToolCallEvent` → tool_use; `ObservationEvent`, `UserRejectObservation` → tool_result; others → system |
| model | `base_state.json` `agent.llm.model` |
| tool_name, tool_use_id | `tool_name`, `tool_call_id` |
| text | message text; `action.command` or `tool_call.arguments`; observation `content[].text`; `error`; `summary` |

Fixture (`.openhands/conversations/0f0e0d0c111140008000000000000001/`):

`meta.json`:
`{"id":"0f0e0d0c-1111-4000-8000-000000000001","title":"List files","created_at":"2026-10-01T10:00:00Z","updated_at":"2026-10-01T10:00:05Z","workspace":{"kind":"LocalWorkspace","working_dir":"/home/alice/proj"}}`

```json
{"kind":"MessageEvent","id":"6b1d5c2e-0000-4000-8000-000000000001","timestamp":"2026-10-01T12:00:01.000000","source":"user","llm_message":{"role":"user","content":[{"type":"text","text":"list the files"}]},"activated_skills":[],"extended_content":[]}
{"kind":"ActionEvent","id":"6b1d5c2e-0000-4000-8000-000000000002","timestamp":"2026-10-01T12:00:03.000000","source":"agent","thought":[{"type":"text","text":"I will run ls."}],"action":{"kind":"TerminalAction","command":"ls"},"tool_name":"terminal","tool_call_id":"call_1","tool_call":{"id":"call_1","name":"terminal","arguments":"{\"command\":\"ls\"}","origin":"completion"},"llm_response_id":"resp_1","security_risk":"LOW"}
{"kind":"ObservationEvent","id":"6b1d5c2e-0000-4000-8000-000000000003","timestamp":"2026-10-01T12:00:04.000000","source":"environment","tool_name":"terminal","tool_call_id":"call_1","action_id":"6b1d5c2e-0000-4000-8000-000000000002","observation":{"kind":"TerminalObservation","content":[{"type":"text","text":"README.md"}],"is_error":false,"command":"ls","exit_code":0}}
```

(files `events/event-00000-6b1d5c2e-...0001.json` and so on, one object
each).

Confidence. High: directory layout, file naming, `kind` discriminator,
event field names, the naive local `timestamp`, Fernet secrets. Also high: `security_risk` values `UNKNOWN`, `LOW`, ...
([`security/risk.py:13-21`](https://github.com/OpenHands/software-agent-sdk/blob/b347047e2dcdd8f4b2be810aa8bc6632bc756d41/openhands-sdk/openhands/sdk/security/risk.py#L13-L21)). Medium: the 1.x `v1_conversations` event shape. Not determined: whether
any surface writes a zone-aware event timestamp, and the full set of
action and observation `kind` values, which grows with each tool.
