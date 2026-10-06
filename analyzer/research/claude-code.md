# Claude Code transcript schema

Catalog agent: `claude-code`. Claude Code is Anthropic's closed-source
coding agent CLI. It writes one append-only JSONL transcript per session,
a tree of records linked by `uuid`/`parentUuid`, with each subagent in its
own JSONL file under the session directory, plus a global prompt history.
Paths, credentials and the rest of the per-user state are in
[`collectors/research/claude-code.md`](../../collectors/research/claude-code.md).
No other agent in the catalog shares this format; Claude Desktop's Code
sessions point back at the same `projects/` files (collector document,
section 6).

## 1. Evidence

Closed source; no public repository, so there are no commit links. Each
claim names its evidence level, best first:

- **Bundle**: `npm pack @anthropic-ai/claude-code@2.1.289` (shim, sha256
  `d72b0a94b84e51fbe5686577f322488a89f844c275985e8054e16951c6dd3e64`)
  and `npm pack @anthropic-ai/claude-code-linux-x64@2.1.289` (sha256
  `50a6eb433422febcfa7b7ac1e78ba795cdf79f1fe58f017fb1d9aeb9491b337d`),
  whose single Bun-compiled binary `package/claude` (246,107,320 bytes,
  sha256 `a186b99e4a9c88366cd49df2f7dad56c61fc306ef0140b19ee64b7c42a8d1348`)
  was read with `strings -n 6`. Every `cc:NNN` below is a 1-based line
  in that strings file (531,386 lines); the minified JavaScript keeps
  record type literals and object shapes. The binary was never executed.
  2.1.289 was chosen because it is the newest `version` in the local
  transcripts. The collector document cites 2.1.288, so its `cc:` line
  numbers do not match these.
- **Vendor text in the bundle**: the built-in "Fewer Permission Prompts"
  prompt describes the transcript layout for the model itself
  (cc:489602: "Session transcripts live at
  `~/.claude/projects/<sanitized-cwd>/*.jsonl`. Each line is a JSON
  object. Tool calls appear as `assistant` messages with
  `message.content[]` entries of `type: "tool_use"`").
- **Observed**: the author's Linux (WSL2) install, October 2026, versions
  2.1.286 to 2.1.289: 95 transcript files (15 session files, 80 subagent
  files), 31,116 lines, 0 unparseable, plus 80 subagent `.meta.json`
  files, 37 persisted tool outputs, `history.jsonl` (162 lines) and
  `sessions/*.json` (3). Every line was tabulated by key path and value
  type with throwaway scripts; no value from them is reproduced here.
  Shapes marked observed were seen there; shapes marked bundle rest on
  the binary only.

## 2. Transcript files

The config home is `$CLAUDE_CONFIG_DIR`, else `~/.claude`, on every OS
(collector document, section 2). Relative to the home:

| Path | Content | Parse |
| --- | --- | --- |
| `.claude/projects/<key>/<session id>.jsonl` | the session transcript; `<key>` is the cwd with every `[^a-zA-Z0-9]` replaced by `-`, cut at 200 characters plus `-` and a base-36 hash when longer (cc:473717, cc:474429); the session id is a UUID (cc:477784 `${q()}.jsonl`) | yes |
| `.claude/projects/<key>/<session id>/subagents/agent-<agent id>.jsonl` | one transcript per subagent, same record format; an optional extra directory level sits between `subagents/` and the file when the agent has a transcript subdirectory (cc:477784 `agentTranscriptSubdirs`, cc:484031 parses `subagents/<dirs...>/agent-(.+).jsonl`) | yes |
| `.claude/projects/<key>/<session id>/subagents/agent-<agent id>.meta.json` | one JSON object per subagent: `agentType`, `description`, `toolUseId`, `model`, `spawnDepth`, `requestShape`, `requestNonInteractive`, and for some `isFork`, `parentAgentId`, `spawnedWithWorktree`, `worktreePath`, `worktreeBranch` (observed, 80 of 80; cc:484010 maps `.meta.json` to `.jsonl`) | no, section 6 |
| `.claude/projects/<key>/<session id>/tool-results/<name>.txt` | full output of a tool result too large to keep inline (`tool-results` constant, cc:474483); the inline result holds a `<persisted-output>` stub (cc:382991) | through the stub, section 8 |
| `.claude/projects/<key>/<session id>/remote-agents/remote-agent-<id>.meta.json`, `.../mcp-tasks/mcp-task-<id>.meta.json` | sidecars for remote agents and MCP tasks (cc:484010, cc:488428) | no; not observed |
| `.claude/projects/<key>/memory/*.md` | per-project memory files (observed) | no |
| `.claude/history.jsonl` | prompt history across sessions, section 5 | yes, as history |
| `.claude/sessions/<pid>.json` | live-process registry: `pid`, `sessionId`, `cwd`, `startedAt` (epoch ms), `version`, `kind`, `entrypoint`, optionally `name`, `status` (observed) | no |
| `.claude/jobs/<id>/parent-transcript.jsonl` | a copy of the parent transcript handed to a background job (cc:474968) | no; not observed |
| `.claude/dump-prompts/<session id>.jsonl` | full outgoing prompts, when that debug option is on (cc:487015) | no; not observed |

The parser selects `^\.claude/projects/[^/]+/.*\.jsonl$` and
`.claude/history.jsonl`, so it reads main and subagent transcripts at any
depth, ignores the `.meta.json` sidecars, and reads a `.txt` sidecar
only when a stub names it (section 8). A config home moved with
`CLAUDE_CONFIG_DIR` (for example `~/.claude-work`) is neither in the catalog (`.claude`, `.claude.json*`, `.local/share/claude`) nor
matched by the parser.

Transcripts older than `cleanupPeriodDays` (default 30) are deleted at
startup (cc:474049 setting description, cc:490770 `cleanupPeriodDays??`);
`history.jsonl` is pruned by the same retention (cc:490770). The history
line usually outlives its transcript.

## 3. Record envelope and types

Every line is one JSON object with a `type`. The loader's own type table
(cc:484009, `nxr`) lists every type 2.1.289 reads, with how it merges
repeats; a second table (cc:484010, `rss`) says which survive a session
copy. Counts are observed lines:

| `type` | Loader class | Observed | Holds |
| --- | --- | --- | --- |
| `user` | transcript | 6,008 | a user turn: prompt, tool results, injected text |
| `assistant` | transcript | 9,911 | one content block of a model response |
| `system` | transcript | 318 | runtime notices, by `subtype` |
| `attachment` | transcript | 10,794 | context injected into the next request, by `attachment.type` |
| `progress` | boundary-cleared | 0 | streamed tool, hook and forked-agent progress (bundle: cc:482374, cc:482655, cc:483757, cc:482596) |
| `file-history-snapshot`, `file-history-delta` | boundary-cleared | 172, 25 | which files were backed up before edits, and the backup names |
| `last-prompt` | boundary-cleared | 602 | `lastPrompt` (text of the latest prompt), `leafUuid` |
| `continued-in` | boundary-cleared | 0 | `continuedInSessionId`, `timestamp` (cc:480715) |
| `content-replacement` | accumulate | 0 | `replacements`, optional `agentId` (cc:484029, cc:494705) |
| `api-request-shape`, `api-request-blob`, `api-request` | boundary-cleared | 0 | request capture; shape not determined |
| `fork-context-ref`, `frame-link` | accumulate | 0 | fork reference (cc:484031); artifact link `path`, `frameUrl`, `title`, `artifactCount`, `timestamp` (cc:504346) |
| `summary` | last-wins | 0 | legacy session summary `summary`, `leafUuid` (cc:484055) |
| `custom-title`, `ai-title` | last-wins | 0, 548 | `customTitle` (user-set name), `aiTitle` (generated name) |
| `tag`, `relocated` | last-wins | 0 | `tag`; `relocatedCwd`, written when the session's cwd moves (cc:484038) |
| `ended-by-model` | last-wins | 0 | `timestamp` only (cc:484055) |
| `agent-name`, `agent-color`, `agent-setting` | last-wins | 129, 0, 0 | `agentName`, `agentColor`, `agentSetting` |
| `pr-link` | last-wins | 221 | `prNumber`, `prUrl`, `prRepository`, `timestamp` |
| `mode`, `permission-mode` | last-wins | 608, 410 | `mode` (`normal` observed); `permissionMode` (`auto`, `plan` observed) |
| `bridge-session` | last-wins | 256 | `bridgeSessionId`, `lastSequenceNum`, `ownerAccountUuid`, `ownerOrganizationUuid` |
| `atis-latch`, `cost-state`, `queue-operation` | last-wins | 607, 25, 488 | an opaque token; cumulative cost and per-model token usage; prompt queue changes |
| `isolation-latch`, `dev-mods`, `memory-mode`, `worktree-state`, `history-suppression`, `attribution-snapshot`, `artifact-comment-monitor`, `artifact-autoreact-ledger`, `observer-ref` | various | 0 | session state (cc:484021, cc:484022) |

Session-state records (`last-prompt`, titles, `agent-name`, `mode`,
`permission-mode`, `atis-latch`, `worktree-state`, `pr-link`,
`frame-link`, `bridge-session`) are re-appended as a block whenever the
session's metadata is flushed (cc:484021, cc:484022). They carry
`sessionId` and only `pr-link`, `frame-link` and `queue-operation` carry a
`timestamp`, which for `pr-link` is the time of the flush
(`timestamp:new Date().toISOString()` in the re-append), not of the pull
request. Observed: one file holds 105 `pr-link` lines for a single URL.

**Transcript envelope** (`user`, `assistant`, `system`, `attachment`;
observed on every one unless noted): `type`, `uuid` (UUID), `parentUuid`
(UUID, or null on a chain root: observed on the first transcript record
of every file and on one `system` record), `timestamp` (ISO 8601 UTC, milliseconds, `Z`;
27,061 of 27,061), `sessionId` (UUID), `cwd`, `gitBranch`, `version`
(`2.1.NNN`), `isSidechain` (false in session files, true in subagent
files, 18,429 of 18,429), `userType` (`external`), `entrypoint` (`cli`
observed), optional `slug` (plan name), `agentId` (subagent files only:
equals the file's `agent-<id>`), and on some `user`, `assistant` and
`attachment` records a snake-case `session_id` (section 6).

**`assistant`** adds `message` (the Messages API response object:
`id`, `type:"message"`, `role`, `model`, `content`, `stop_reason`,
`stop_sequence`, `usage`, `container`, `context_management`,
`stop_details`, `diagnostics`, `input_transformations`), `requestId`,
`apiBlockIndex`, `effort`, `perTurnEffort`, `advisorModel`,
`serverClassifierRequest`, optional `thinkingDurationMs`,
`attributionAgent`, `attributionSkill`, and per tool call
`wireToolInputs` and `wireIngestContext` (section 4) (observed; built at
cc:482605). API failures are `assistant` records with
`isApiErrorMessage:true`, `error`, `apiErrorStatus`, `message.model`
`<synthetic>` and one text block holding the error (observed 10;
cc:477488).

**`user`** adds `message` (`role:"user"`, `content` string or block
list), `promptId` (UUID), and as applicable `isMeta`, `origin{kind,
...}`, `promptSource`, `turnOrigin`, `turnPosition`, `permissionMode`,
`toolUseResult`, `sourceToolAssistantUUID`, `serverClassifierContext`,
`isCompactSummary`, `isVisibleInTranscriptOnly`, `summarizeMetadata`,
`interruptedMessageId`, `toolDenialKind`, `userFeedback`,
`queueSkipAttachments`, `queueTranscriptOnly` (the factory at cc:483772
lists them; observed except the compaction fields).

**`system`** adds `subtype`, `isMeta` (false on every builder, cc:483998,
and on 318 of 318 observed), `level`, `content` and subtype fields.
Observed subtypes: `turn_duration` (`durationMs`, `messageCount`,
`pendingBackgroundAgentCount`, no `content`), `away_summary` (`content`,
a model-written recap), `local_command` (`content`, `level:"info"`,
optional `commandRun{command, args}`, `usageReport`), `bridge_status`
(`content`, `url`), `informational` (`content`, `level:"notice"`). The
builders at cc:483998 add `compact_boundary` (`content:"Conversation
compacted"`, `compactMetadata{trigger, preTokens, userContext,
messagesSummarized, ...}`, `logicalParentUuid`), `api_error` (`level:
"error"`, `error`, `retryInMs`, `retryAttempt`, `maxRetries`, no
`content`), `memory_saved` (`writtenPaths`), `agents_killed`,
`stop_hook_summary`, `permission_retry`, `scheduled_task_fire`,
`cloud_session_status`; cc:487124 adds `model_refusal_fallback` and
others. Many `subtype` literals in the bundle (`init`, `status`,
`task_*`, `hook_*`, `ui_*`) belong to the SDK stream, not the transcript.

**`attachment`** adds `attachment{type, ...}` and, on most, `rendered`
and `renderedRole` (the text the model saw). Observed `attachment.type`
values: `total_tokens_reminder`, `batching_reminder_sent`,
`deferred_tools_record`, `deferred_tools_delta`,
`bash_output_audience_note`, `prompt_snapshot` (the system prompt and
tool list), `environment` (`snapshot{workingDirectory, platform, shell,
osVersion, isGitRepo, isWorktree, ...}`), `skill_listing`,
`queued_command`, `remote_session_change`, `date`, `model`
(`identity{modelId, marketingName, knowledgeCutoff}`),
`agent_listing_delta`, `mcp_instructions_delta`, `auto_mode`,
`session_context` (`context{userEmail, gitStatus}`), `credential_org`
(`organizationUuid`), `edited_text_file` (`filename`, `snippet`),
`instructions` (`files`), `silent_turn_reminder`, `command_permissions`,
`plan_mode`, `plan_mode_exit`, `plan_mode_reentry`,
`hook_system_message` (`hookName`, `hookEvent`, `content`),
`thinking_drop`, `read_truncation_notice`. `queued_command` carries
`prompt`, `origin{kind}`, `commandMode`, `source_uuid`, `delivery_id`,
`timestamp`: a prompt that arrived while a turn was running.

**`queue-operation`**: `operation` (`enqueue`, `dequeue`, `remove`),
`timestamp`, `sessionId`, and on `enqueue` and `remove` the queued
`content`; optional `commandUuid`, `deliveryId`, `reason` (observed).

### Completeness and streaming

One API response becomes one `assistant` record per content block: all
9,911 observed `assistant` records hold exactly one block, consecutive
records share `message.id` and `requestId`, and only the last carries a
non-null `stop_reason` (observed; `apiBlockIndex` numbers them). There
are no streaming deltas to reassemble. The transcript is complete except
for persisted tool output (section 4), pasted text in history (section
5), and file backups (`file-history/`).

## 4. Message content, tool calls and results

`message.content` blocks (observed counts):

| Record | Block `type` | Fields |
| --- | --- | --- |
| `assistant` | `text` (886) | `text` |
| `assistant` | `thinking` (3,525) | `thinking`, `signature`; `thinking` is `""` in 3,165, text present in 360 |
| `assistant` | `tool_use` (5,513) | `id` (`toolu_...`), `name`, `input` (object), `caller{type:"direct"}` |
| `assistant` | `redacted_thinking`, `server_tool_use`, others | not observed |
| `user` | string content (474) | the prompt or injected text |
| `user` | `text` (35) | `text` |
| `user` | `tool_result` (5,512) | `tool_use_id`, `content` (string in 5,327; list of `{type:"text", text}` in 167 or `{type:"tool_reference", tool_name}` in 18), `is_error` (true 183, false 4,632, absent 749) |
| `user` | `image` | not observed; `text_of` renders it `[image]` |

**Join.** `tool_use.id` = `tool_result.tool_use_id` (observed). Each
result's `user` record also carries `sourceToolAssistantUUID`, the `uuid`
of the `assistant` record holding the call, and `toolUseResult`, the
tool's structured result: for Bash `stdout`, `stderr`, `interrupted`,
`isImage`, `noOutputExpected`, optional `returnCodeInterpretation`,
`persistedOutputPath`, `persistedOutputSize`, `bashEditDiff`; for file
tools `filePath`, `file{filePath, content, numLines, startLine,
totalLines}`, `oldString`, `newString`, `structuredPatch`,
`originalFile`, `userModified`; for web tools `url`, `code`, `codeText`,
`bytes`, `result`, `durationMs`, `query`, `results`; for Agent `agentId`,
`status`, `prompt`, `resolvedModel`, `outputFile`. On an error it is the
error string (183 observed, all with `is_error:true`). The model-visible
text is the `tool_result.content`; `toolUseResult` repeats or extends it.

**Wire inputs.** `assistant.wireToolInputs` maps each `tool_use.id` to the
input exactly as the model sent it; `tool_use.input` is the normalised
input Claude Code ran (cc:482605 attaches both; cc:481832 and cc:482596
compare and strip them). Observed: 1,607 of 5,513 differ. For 1,498 of
1,501 differing Bash calls the wire `command` is the stored `command`
with a leading `cd <dir> && ` that the stored input lacks, and
`wireIngestContext[<id>].cwd` holds that directory; Edit adds
`replace_all`, ExitPlanMode and SendMessage add fields the model did not
send.

**Persisted output.** When a result is too large, its full text goes to
`<session id>/tool-results/<name>.txt` and the `tool_result.content`
holds a `<persisted-output>` stub with the path and a preview
(cc:382991, cc:474483); `toolUseResult.persistedOutputPath` names the
file (37 observed).

**Tool names observed**: `Bash`, `Read`, `Write`, `Edit`, `WebFetch`,
`WebSearch`, `Agent`, `SendMessage`, `SubagentHandback`, `ToolSearch`,
`EnterPlanMode`, `ExitPlanMode`; MCP tools are `mcp__<server>__<tool>`
(cc:489602). Input keys observed: `command`, `description`, `timeout`,
`run_in_background` (Bash); `file_path`, `offset`, `limit` (Read);
`file_path`, `content` (Write); `file_path`, `old_string`, `new_string`
(Edit); `url`, `prompt` (WebFetch); `query` (WebSearch); `description`,
`prompt`, `subagent_type`, `model`, `isolation` (Agent).

**User-record kinds.** A `user` record is not always typed by the person:

| Signal | Meaning | Observed |
| --- | --- | --- |
| `origin.kind:"human"`, `promptSource` `typed`, `queued` or `suggestion_accepted` | a prompt the person submitted | 165 |
| no `origin`, `parentUuid` null, first line of a subagent file | the task the parent agent gave the subagent | 80 of 80 subagent files |
| `origin.kind:"task-notification"`, content `<task-notification>...` | a background task's completion notice; `isMeta` absent in 62 of 66 | 66 |
| `origin.kind` `peer`, `coordinator`, `auto-continuation` | messages from other sessions or the runtime; `isMeta:true` | 65 |
| `isMeta:true`, `<system-reminder>` or `<local-command-caveat>` | injected context | 87 strings, 27 blocks |
| `<command-name>`, `<command-message>`, `<local-command-stdout>` | a slash command and its output; `isMeta` absent; the 27 `<command-message>` records also carry `origin.kind:"human"` and are counted above | 38 |
| `isCompactSummary:true` | the summary that replaces history after compaction, text starting "This session is being continued from a previous conversation" (cc:482588); built through the user-message factory without `isMeta` (cc:482593, cc:482597, cc:482598) | bundle |
| `tool_result` blocks | tool output | 5,512 |

A prompt typed while a turn runs is first a `queue-operation` `enqueue`
with its `content`, then either a `queued_command` attachment (delivered
inside the running turn) or a later `user` record with
`promptSource:"queued"`. Observed: 11 `queued_command` attachments with
`origin.kind:"human"` whose text is in no `user` record of the file.

## 5. Other files

- `.claude/history.jsonl` (observed 162 of 162): `{display,
  pastedContents, timestamp, project, sessionId}`, `timestamp` epoch
  **milliseconds** (integer), `project` the cwd. Written by `addEntry`
  (cc:479374) and read with the schema at cc:479372. `pastedContents`
  maps a paste number to `{id, type, content, mediaType, filename}` when
  the paste is at most 1,024 characters, else to `{id, type, contentHash,
  mediaType, filename}` with the text stored in `paste-cache/` under its
  hash (cc:479369 `z8=1024`, cc:479374 `registerPastedTextForRecall`,
  cc:479360 `paste-cache`); `display` holds the `[Pasted text #N]`
  placeholder. Every observed `pastedContents` was empty. The collector
  excludes `.claude/paste-cache`, so long pasted text is not collected. History is the only record of a prompt whose transcript
  was deleted by retention.
- `file-history-snapshot` and `file-history-delta` records name the files
  backed up before each edit (`snapshot.trackedFileBackups` keyed by
  path, `backup{backupFileName, backupTime, version, realParentDir}`);
  the bytes are in `.claude/file-history/<session id>/`. The paths in
  `trackedFileBackups` are files the agent edited, which no other record
  lists in one place.
- `sessions/<pid>.json`, `.meta.json`: section 2. No SQLite store holds
  transcript content.
- `.claude.json` `projects` keys are project paths (collector document,
  section 6).

## 6. Timestamps, ids, project, branch, model, subagents

- **Timestamps**: per record `timestamp`, ISO 8601 UTC with milliseconds
  and `Z` (observed 27,061 of 27,061; `new Date().toISOString()` in every
  builder). Not monotonic in file order: in 52 of 95 files a record is
  older than an earlier line, mostly by under a second (assistant blocks
  and attachments written after the fact), 19 by a minute or more.
  Session-state records have no timestamp.
- **Session id**: `sessionId` equals the file name in all session-file
  records (12,526 of 12,526). In a subagent file `sessionId` is the
  **parent** session's id (18,429 of 18,429) and `agentId` names the
  subagent. The snake-case `session_id` on some records equals
  `sessionId` in 12 session files and in 3 names an earlier session whose
  file exists while none of those records' `uuid`s are in it; consistent
  with a resumed or forked session, purpose not determined.
- **Project path**: `cwd` on every transcript record; can change within a
  session (4 of 15 session files had more than one) and `relocated` records it
  (cc:484038). The directory `<key>` is lossy; read `cwd`.
- **Branch**: `gitBranch` on every transcript record (never empty
  observed; `HEAD` when detached is not determined); changes within a
  session (2 files).
- **Model**: `message.model` on `assistant` records (`claude-<family>-N-N`
  observed, `<synthetic>` for local errors); `model` attachment
  `identity.modelId`; `cost-state.modelUsage` keys.
- **Subagents**: the parent's `Agent` `tool_use.id` equals the subagent's
  `.meta.json` `toolUseId`, and the parent's `toolUseResult.agentId`
  equals the file's agent id (76 of 76 non-fork subagents). Forked
  agents (`agentType:"fork"`, 4) have a `toolUseId` that is not in the
  parent transcript.
- **Turn**: `promptId` groups a prompt's records; `turnPosition{
  promptIndex, turnIndex}` on some `user` records.

## 7. Variants and drift

- Versions 2.1.286 to 2.1.289 observed with the same shapes. The parser
  docstring says "Claude Code 2.x"; nothing older was available.
- `summary` (`{type, summary, leafUuid}`) and `progress` records are
  still read by 2.1.289 (cc:484009, cc:484055) and `progress` can still
  be written by forked agents (cc:482596); neither was observed. The
  summary type is the legacy form of session titles, now `ai-title` and
  `custom-title`.
- `thinking` blocks are mostly empty strings with a `signature` (3,165 of
  3,525): the thinking text was not returned, not redacted;
  `redacted_thinking` is a separate block type.
- Compaction (`compact_boundary` plus a `user` record with
  `isCompactSummary`) and `relocated` were not observed.
- No compressed or archived transcript form exists; deletion by
  `cleanupPeriodDays` is the only rotation.

## 8. Parser plan (what the parser does)

`doubleagent/parsers/claude_code.py`, class `ClaudeCodeParser`.
`wants()`:

```text
^\.claude/projects/[^/]+/.*\.jsonl$
.claude/history.jsonl  (exact)
```

Lines are read with `iter_jsonl`; bad lines are counted and reported in
one `system` row at the end with the first bad line's number; earlier
rows are kept. Each session file is read twice: a first pass collects the
prompts that `queued_command` attachments and `user` records deliver
and the lines that deliver them,
whether the file holds a `<fork-boilerplate>` block, and the first `cwd`
and `gitBranch`.

Coverage. A label is the start of a `system` row's text, `<label>: ` and
then the full text:

| Record | `turn_type` |
| --- | --- |
| subagent file, first transcript record | an extra `system` row first, `subagent <agentId> of <sessionId>` (`agentId` from the record, else from the file name) |
| `user`, first one in a subagent file that is not a fork | `system`, label `subagent task` |
| `user`, `isCompactSummary` | `system`, label `compaction summary` |
| `user`, `interruptedMessageId` | `system`, label `interrupted` |
| `user` text starting `<task-notification>` | `system`, label `task notification` |
| `user` text starting `<command-name>` or `<command-message>` | `system`, label `slash command` |
| `user` text starting `<local-command-stdout>` | `system`, label `command output` |
| `user` text starting `<local-command-caveat>` or `<system-reminder>` | `system`, label `context` |
| `user` text starting `<fork-boilerplate>` | `system`, label `subagent task` |
| `user`, `origin.kind` `task-notification`, `peer`, `coordinator`, `auto-continuation` | `system`, label `task notification`, `peer message`, `coordinator message`, `auto-continuation` |
| `user`, other `isMeta` | `system`, label `context` |
| `user`, any other string, `text` or `image` block | `user` (one row per block); the rules above are tried in this order, the record-level ones for every block |
| `user`, `tool_result` block | `tool_result`; `tool_reference` blocks as their `tool_name`; a `<persisted-output>` stub replaced by its `tool-results/` file (below); text prefixed `[error]` when `is_error` |
| `assistant`, `isApiErrorMessage` or model `<synthetic>` | `system`, `api error: <apiErrorStatus> <error>: <text>`, no model |
| `assistant`, `text` block | `assistant` (empty text skipped) |
| `assistant`, `tool_use` block | `tool_use` |
| `assistant`, `thinking` | `thinking` with `include_thinking`; an empty `thinking` (signature only) is skipped |
| `assistant`, `redacted_thinking` | `thinking` with `include_thinking`, text `[redacted]` |
| `assistant`, other block types | skip |
| `system` | `system`, text `<subtype>: <content>`; `turn_duration` as `<durationMs> ms, <messageCount> messages`; without `content`, `<subtype>: ` and the compact JSON of the fields other than the envelope (`api_error`: `level`, `retryInMs`, `retryAttempt`, `maxRetries`, `error`) |
| `attachment` `queued_command`, `origin.kind` `human` | `user`, text `prompt` (a text marker above still makes it `system`) |
| `attachment` `queued_command`, other origin | `system`, the marker or origin label, else `queued command` |
| `attachment` `hook_system_message` | `system`, `hook: <hookName>: <content>` |
| `attachment` `edited_text_file` | `system`, `edited file: <filename>` (the `snippet` is not shown) |
| `attachment`, other types | skip: model context (system prompt, tool lists, reminders, environment and model snapshots, skill and agent listings); `remote_session_change` (the session's PR and commit) is skipped too |
| `ai-title`, `custom-title`, `agent-name` | `system`, `session title: <value>`, once per distinct value per session |
| `relocated` | `system`, `cwd changed: <relocatedCwd>`; every later row of the file takes it as `project_path` |
| `pr-link` | `system`, `pr-link: <prUrl or prNumber>`, once per session and URL (the first record wins) |
| `queue-operation` | `system`, `queue <operation>: <content>`; an `enqueue` whose `content` a `queued_command` attachment or a `user` record of the file delivers is `prompt queued: delivered at line N` at the enqueue's own timestamp, N being the first delivering line after it (else the first), so the typing time is kept and the prompt text appears once, on the delivering row |
| every other type (section 3 table) | skip |
| `history.jsonl` line | `user` |

A forked subagent's file begins with a copy of the forking agent's context
(observed in the 4 fork files: the records before the
`<fork-boilerplate>` one have new `uuid`s, and their tool ids are in no
session file), so no boundary ties those records to their source; their
rows are kept, the first `user` record stays `user`, and the
`<fork-boilerplate>` block is the `subagent task` row.

**Persisted output.** When a `tool_result` text starts with
`<persisted-output>`, the parser takes the path after `Full output saved
to: `, keeps its last component and requires the component before
`tool-results` to equal the transcript's session directory
(`<session id>/` beside a session file, the directory above `subagents/`
for a subagent file). It reads `<session dir>/tool-results/<name>`
when neither the file, `tool-results/` nor the session directory is a
symlink, and otherwise keeps the stub followed by
`[persisted output not found: tool-results/<name>]`. On the observed
install every stub resolved.

Columns:

| Column | Source |
| --- | --- |
| timestamp_utc | record `timestamp`; records without one (titles, `relocated`) take the latest timestamp seen in the file; history: `timestamp` (ms) |
| session_id | latest `sessionId` (or `session_id`) seen in the file; history: `sessionId` |
| project_path | the `relocatedCwd` of an earlier `relocated` record, else the latest `cwd` seen in the file, else the file's first `cwd`; history: `project` |
| git_branch | the latest `gitBranch` seen in the file, else the file's first |
| turn_type | coverage table |
| model | `message.model` on `assistant` and `thinking` rows |
| tool_name | `tool_use.name`; empty on `tool_result` rows |
| tool_use_id | `tool_use.id` / `tool_result.tool_use_id` |
| text | user/assistant/thinking text; `tool_use`: for Bash the `command` of `wireToolInputs[<id>]` when present (it keeps the `cd <dir> &&` prefix), else per-tool key from `input` (`command`, `file_path`, `notebook_path`, `pattern`+`path`, `url`, `query`, `description`+`prompt`, `skill`+`args`, `path`), else the first of `command`, `file_path`, `path`, `pattern`, `url`, `query`, `description`, else compact JSON; `tool_result`: the block text as above |
| source_line | 1-based line number; the subagent header row takes its first record's line |

Not read: `.meta.json` sidecars, `sessions/*.json`, `paste-cache/`, and a
config home moved with `CLAUDE_CONFIG_DIR`.

Sample records, `.claude/projects/-srv-proj/11111111-2222-4333-8444-555555555555.jsonl`
(state record, typed prompt, empty-thinking block, Bash call with a wire
input, its result, a prompt queued mid-turn and its attachment, reply,
turn duration, title, last prompt, PR link, backup snapshot, then a cut
line):

```json
{"type":"mode","mode":"normal","sessionId":"11111111-2222-4333-8444-555555555555"}
{"parentUuid":null,"isSidechain":false,"promptId":"0c0c0c0c-0000-4000-8000-000000000001","type":"user","message":{"role":"user","content":"why does the test fail?"},"uuid":"00000000-0000-4000-8000-000000000001","timestamp":"2026-10-01T10:00:00.000Z","permissionMode":"auto","origin":{"kind":"human"},"promptSource":"typed","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"parentUuid":"00000000-0000-4000-8000-000000000001","isSidechain":false,"message":{"model":"claude-fable-5-1","id":"msg_01","type":"message","role":"assistant","content":[{"type":"thinking","thinking":"","signature":"c2lnbmF0dXJl"}],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":900,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":40}},"requestId":"req_01","apiBlockIndex":0,"type":"assistant","uuid":"00000000-0000-4000-8000-000000000002","timestamp":"2026-10-01T10:00:02.000Z","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"parentUuid":"00000000-0000-4000-8000-000000000002","isSidechain":false,"message":{"model":"claude-fable-5-1","id":"msg_01","type":"message","role":"assistant","content":[{"type":"tool_use","id":"toolu_01","name":"Bash","input":{"command":"npm test","description":"Run the tests"},"caller":{"type":"direct"}}],"stop_reason":"tool_use","stop_sequence":null,"usage":{"input_tokens":900,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":60}},"requestId":"req_01","apiBlockIndex":1,"wireToolInputs":{"toolu_01":{"command":"cd /srv/proj && npm test","description":"Run the tests"}},"wireIngestContext":{"toolu_01":{"cwd":"/srv/proj"}},"type":"assistant","uuid":"00000000-0000-4000-8000-000000000003","timestamp":"2026-10-01T10:00:03.000Z","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"parentUuid":"00000000-0000-4000-8000-000000000003","isSidechain":false,"promptId":"0c0c0c0c-0000-4000-8000-000000000001","type":"user","message":{"role":"user","content":[{"tool_use_id":"toolu_01","type":"tool_result","content":"1 failing","is_error":false}]},"uuid":"00000000-0000-4000-8000-000000000004","timestamp":"2026-10-01T10:00:05.000Z","toolUseResult":{"stdout":"1 failing","stderr":"","interrupted":false,"isImage":false,"noOutputExpected":false},"sourceToolAssistantUUID":"00000000-0000-4000-8000-000000000003","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"type":"queue-operation","operation":"enqueue","timestamp":"2026-10-01T10:00:05.500Z","sessionId":"11111111-2222-4333-8444-555555555555","content":"also check the linter"}
{"parentUuid":"00000000-0000-4000-8000-000000000004","isSidechain":false,"attachment":{"type":"queued_command","prompt":"also check the linter","commandMode":"prompt","origin":{"kind":"human"},"source_uuid":"00000000-0000-4000-8000-0000000000a1","delivery_id":"0d0d0d0d-0000-4000-8000-000000000001","timestamp":"2026-10-01T10:00:05.500Z"},"type":"attachment","uuid":"00000000-0000-4000-8000-000000000005","timestamp":"2026-10-01T10:00:06.000Z","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"parentUuid":"00000000-0000-4000-8000-000000000005","isSidechain":false,"message":{"model":"claude-fable-5-1","id":"msg_02","type":"message","role":"assistant","content":[{"type":"text","text":"The fixture date is stale; the linter is clean."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":950,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":20}},"requestId":"req_02","apiBlockIndex":0,"type":"assistant","uuid":"00000000-0000-4000-8000-000000000006","timestamp":"2026-10-01T10:00:08.000Z","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"parentUuid":"00000000-0000-4000-8000-000000000006","isSidechain":false,"type":"system","subtype":"turn_duration","durationMs":8000,"messageCount":7,"pendingBackgroundAgentCount":0,"timestamp":"2026-10-01T10:00:08.100Z","uuid":"00000000-0000-4000-8000-000000000007","isMeta":false,"userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"type":"ai-title","aiTitle":"Fix stale fixture date","sessionId":"11111111-2222-4333-8444-555555555555"}
{"type":"last-prompt","lastPrompt":"why does the test fail?","leafUuid":"00000000-0000-4000-8000-000000000007","sessionId":"11111111-2222-4333-8444-555555555555"}
{"type":"pr-link","sessionId":"11111111-2222-4333-8444-555555555555","prNumber":7,"prUrl":"https://github.com/example/proj/pull/7","prRepository":"example/proj","timestamp":"2026-10-01T10:00:09.000Z"}
{"type":"file-history-snapshot","messageId":"00000000-0000-4000-8000-000000000001","snapshot":{"messageId":"00000000-0000-4000-8000-000000000001","trackedFileBackups":{},"timestamp":"2026-10-01T10:00:00.000Z"},"isSnapshotUpdate":false}
{"parentUuid":"00000000-0000-4000-8000-000000000007","isSidechain":false,"type":"user","message":{"role":"user","content":"thanks"
```

Subagent `.claude/projects/-srv-proj/11111111-2222-4333-8444-555555555555/subagents/agent-a0b1c2d3e4f5a6b7c.jsonl`
and its sidecar `agent-a0b1c2d3e4f5a6b7c.meta.json`:

```json
{"parentUuid":null,"isSidechain":true,"agentId":"a0b1c2d3e4f5a6b7c","promptId":"0c0c0c0c-0000-4000-8000-000000000001","type":"user","message":{"role":"user","content":"Find where the fixture date is set."},"uuid":"00000000-0000-4000-9000-000000000001","timestamp":"2026-10-01T10:00:04.000Z","userType":"external","entrypoint":"cli","cwd":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555","version":"2.1.289","gitBranch":"main"}
{"agentType":"general-purpose","description":"Find the fixture date","toolUseId":"toolu_02","model":"claude-fable-5-1","spawnDepth":1,"requestShape":"agent","requestNonInteractive":false}
```

History `.claude/history.jsonl`:

```json
{"display":"why does the test fail? [Pasted text #1 +3 lines]","pastedContents":{"1":{"id":1,"type":"text","contentHash":"0123456789abcdef"}},"timestamp":1790848800000,"project":"/srv/proj","sessionId":"11111111-2222-4333-8444-555555555555"}
```

Expected rows from the session sample with the parser: `user` (line 2);
nothing for the empty thinking block (line 3, even with
`include_thinking`); `tool_use` `Bash` `toolu_01` text `cd /srv/proj &&
npm test` (line 4, from `wireToolInputs`); `tool_result` `toolu_01` text
`1 failing` (line 5); `system` `prompt queued: delivered at line 7`
(line 6, at 10:00:05.500); `user` `also check the linter` (line 7);
`assistant` (line 8); `system` `turn_duration: 8000 ms, 7 messages`
(line 9); `system` `session title: Fix stale fixture date` (line 10,
timestamp of line 9); `system` `pr-link: https://...` (line 12); and the
bad-line `system` row (line 14). All have `session_id` `11111111-...`;
all but the bad-line row have `project_path` `/srv/proj` and
`git_branch` `main` (checked by running the parser on this sample). The
subagent sample yields two `system` rows on line 1, `subagent
a0b1c2d3e4f5a6b7c of 11111111-...` and `subagent task: Find where the
fixture date is set.`, with the parent's `session_id`. Noise the parser
must not want: `.claude/settings.json`, the `.meta.json` sidecar,
`tool-results/*.txt` (read only through a stub).

## Confidence

High (observed and consistent with the bundle): file layout and key
scheme, the record type list, the transcript envelope, one block per
`assistant` record, `tool_use`/`tool_result` join, `toolUseResult`,
`sourceToolAssistantUUID`, `wireToolInputs`/`wireIngestContext` and the
stripped `cd` prefix, `user`-record origins and the subagent first-line
prompt, the subagent join through `.meta.json`, millisecond ISO
timestamps, epoch-millisecond history, empty thinking with signature,
`pr-link` re-append, `queued_command` prompts.

Medium (bundle only, not exercised): `compact_boundary` and
`isCompactSummary` shapes, `api_error`, `memory_saved`, `relocated`,
`continued-in`, `ended-by-model`, `content-replacement`, `frame-link`,
`summary`, `progress`, nested subagent subdirectories, `paste-cache`
storage of pasted text.

Not determined: the meaning of a `session_id` that differs from
`sessionId`; the shape of `api-request*`, `fork-context-ref`,
`content-replacement.replacements[]` and `history-suppression`; whether
`redacted_thinking`, `server_tool_use` or `image` blocks still appear in
2.1.x transcripts; `gitBranch` for a detached head or outside a
repository; the layout before 2.1.286; the macOS and Windows transcripts
(the collector document finds the same `~/.claude` layout from the
bundle, but none was inspected).
