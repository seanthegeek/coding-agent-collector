# little-coder transcript schema

Catalog agent: `little-coder`. little-coder is a launcher and extension set
for the pi coding agent, so its transcripts are pi session files written by
pi itself. This document covers what little-coder adds and how to tell its
sessions from plain pi sessions; the full pi record schema belongs to pi's
own research. Paths are in [`collectors/research/little-coder.md`](../../collectors/research/little-coder.md).

## 1. Source

itayinbarr/little-coder at [`89d4fa0af864230527ab75d12604ed0eb320e6df`](https://github.com/itayinbarr/little-coder/commit/89d4fa0af864230527ab75d12604ed0eb320e6df),
Apache-2.0. It depends on `@earendil-works/pi-coding-agent` `^0.83.0`
([package.json:41](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/package.json#L41)), read at earendil-works/pi `v0.83.0`,
[`845d6ff1f6643aba440341cce877ce1c43ebbc39`](https://github.com/earendil-works/pi/commit/845d6ff1f6643aba440341cce877ce1c43ebbc39).

## 2. Transcript files

- `.pi/agent/sessions/--<encoded cwd>--/<ISO timestamp with - for : and .>_<uuid>.jsonl`,
  one file per session, appended per entry
  ([packages/coding-agent/src/core/session-manager.ts:476-481](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L476-L481), [950-953](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L950-L953)).
  Shared with plain pi.
- `.pi/agent/little-coder-prompt-history.json`: JSON array of up to 100
  prompt strings, oldest first, no timestamps or session ids
  ([.pi/extensions/prompt-history/index.ts:26](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L26), [38-40](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L38-L40), [52-57](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L52-L57)).
- `.little-coder/checkpoints/<session file name>/<mangled path>`: pre-edit
  file copies, not transcripts, but they join to a session by name
  ([.pi/extensions/checkpoint/index.ts:25-29](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L25-L29), [63-65](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L63-L65)).

Sub-agents run pi with `--no-session`, so they leave no file
([.pi/extensions/subagent/spawn.ts:14](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/subagent/spawn.ts#L14), [318-322](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/subagent/spawn.ts#L318-L322)).

## 3. Record schema

pi session format version 3
([session-manager.ts:30](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L30)). Line 1 is the header
`{type:"session", version, id, timestamp (ISO), cwd, parentSession?}`
([:32-39](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L32-L39)). Every other line has `type`, `id`, `parentId`, `timestamp`
(ISO) ([:46-51](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L46-L51)) and is one of `message`, `thinking_level_change`,
`model_change` (`provider`, `modelId`), `compaction`, `branch_summary`,
`custom`, `custom_message`, `label`, `session_info` ([:53-153](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L53-L153)).

`message.message` ([packages/ai/src/types.ts:393-431](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L393-L431)):

- `user`: `content` string or `text`/`image` parts, `timestamp` (Unix ms).
- `assistant`: `content[]` of `text`, `thinking` (`thinking`), `toolCall`
  (`id`, `name`, `arguments` object) ([:338-366](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L338-L366)); `provider`, `model`,
  `usage`, `stopReason` (`stop|length|toolUse|error|aborted`, [:391](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L391)),
  `errorMessage`, `timestamp` (ms).
- `toolResult`: `toolCallId`, `toolName`, `content[]`, `isError`, `timestamp`.
- pi's own roles `bashExecution` (`command`, `output`, `exitCode`),
  `custom`, `branchSummary`, `compactionSummary`
  ([packages/coding-agent/src/core/messages.ts:29-67](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/messages.ts#L29-L67)).

Extension messages become `custom_message` entries with `customType`,
`content`, `display`, `details` ([session-manager.ts:135-141](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L135-L141);
[packages/coding-agent/src/core/agent-session.ts:624-633](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/agent-session.ts#L624-L633)).

**little-coder markers.** Its extensions tag what they inject:
`lc-skills`, `lc-knowledge`, `lc-project-context`
([.pi/extensions/_shared/inject.ts:49-64](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/_shared/inject.ts#L49-L64); [skill-inject/index.ts:393](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/skill-inject/index.ts#L393);
[knowledge-inject/index.ts:169](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/knowledge-inject/index.ts#L169); [project-context/index.ts:96](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/project-context/index.ts#L96)),
`lc-bg-shell` with `details.id` ([bg-shell/index.ts:134-135](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/bg-shell/index.ts#L134-L135)), `lc-plan`,
`lc-approved-plan` ([plan-mode/index.ts:394](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/plan-mode/index.ts#L394), [817](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/plan-mode/index.ts#L817)), `lc-research`
([deep-research/index.ts:334](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/deep-research/index.ts#L334)). Injection can instead go into the
system prompt (`injectMode` `system`), which leaves no entry
([inject.ts:60-62](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/_shared/inject.ts#L60-L62)). Assistant `provider` is commonly `llamacpp`,
little-coder's local provider ([.pi/extensions/llama-cpp-provider/index.ts:172](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/llama-cpp-provider/index.ts#L172);
[models.json:2-4](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/models.json#L2-L4)).

## 4. Joins

Session id: header `id`, also in the file name. Tree: `parentId` → `id`.
Tool use to result: `toolCall.id` = `toolResult.toolCallId`. Project path:
header `cwd`. Forked sessions: header `parentSession`. Checkpoint directory
name = session file basename.

## 5. SQLite or binary stores

None. Images are base64 inside `image` parts ([types.ts:354-358](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L354-L358)).

## 6. Format versions

pi header `version` (absent in v1 files, 3 now,
[session-manager.ts:30-35](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L30-L35)). little-coder pins pi 0.83.x; a release that moves
to pi 1.x should be re-checked against pi's research.

## 7. Secrets

Session files store tool inputs and outputs verbatim; `thinkingSignature`
and `thoughtSignature` are opaque provider blobs ([types.ts:344-366](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L344-L366)).
Credentials are in `auth.json`, not in sessions.

## 8. Parser plan

Use the pi parser for `.pi/agent/sessions/*/*.jsonl` and label a session
`little-coder` when it contains any `custom_message` whose `customType`
starts with `lc-`; otherwise leave it `pi`. Parse
`little-coder-prompt-history.json` as `user` rows with no timestamp and no
session.

| Column | Source |
| --- | --- |
| timestamp_utc | entry `timestamp` (ISO); `message.timestamp` (ms) as fallback |
| session_id | header `id` |
| project_path | header `cwd` |
| git_branch | empty |
| turn_type | `user`, `assistant`; `toolCall` → tool_use; `toolResult` → tool_result; `thinking` → thinking; `custom_message`, `model_change`, `compaction`, `bashExecution` → system |
| model | assistant `provider`/`model` |
| tool_name, tool_use_id | `toolCall.name`/`id`; `toolResult.toolName`/`toolCallId` |
| text | text parts; tool_use: `arguments.command` or `path`, else JSON; tool_result: text parts |

Fixture:

```json
{"type":"session","version":3,"id":"0b9e2f4c-1111-4000-8000-000000000001","timestamp":"2026-10-01T09:00:00.000Z","cwd":"/home/alice/proj"}
{"type":"custom_message","id":"a1","parentId":null,"timestamp":"2026-10-01T09:00:01.000Z","customType":"lc-skills","content":"## Skill: edit\nUse the edit tool.","display":false}
{"type":"message","id":"a2","parentId":"a1","timestamp":"2026-10-01T09:00:02.000Z","message":{"role":"user","content":"fix the failing test","timestamp":1759309202000}}
{"type":"message","id":"a3","parentId":"a2","timestamp":"2026-10-01T09:00:05.000Z","message":{"role":"assistant","content":[{"type":"thinking","thinking":"run tests first"},{"type":"toolCall","id":"call_1","name":"bash","arguments":{"command":"npm test"}}],"api":"openai-completions","provider":"llamacpp","model":"qwen3.6-35b-a3b","usage":{"input":900,"output":40,"cacheRead":0,"cacheWrite":0},"stopReason":"toolUse","timestamp":1759309205000}}
{"type":"message","id":"a4","parentId":"a3","timestamp":"2026-10-01T09:00:09.000Z","message":{"role":"toolResult","toolCallId":"call_1","toolName":"bash","content":[{"type":"text","text":"1 failing"}],"isError":false,"timestamp":1759309209000}}
```

`little-coder-prompt-history.json`: `["fix the failing test","now run lint"]`

Confidence. High: file locations, header and entry fields, message roles,
`lc-*` custom types, sub-agents unsaved (source). Medium: that every
little-coder session contains an `lc-` entry; with injection set to
`system` mode and no plan, bg-shell or research use, a session may carry
none, and then only `provider: "llamacpp"` hints at it. Not determined:
the exact `usage` sub-fields beyond those shown ([types.ts:368-380](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/ai/src/types.ts#L368-L380)).
