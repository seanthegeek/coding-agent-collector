# qwen-code: on-disk paths

## 1. Source and evidence level

QwenLM/qwen-code, commit `2c591ecc08a6fa080342f9b1b9f7f43215178cbb`
(2026-10-03, version `0.24.7`). Open source. All claims are source-level
(`packages/...` file:line) unless marked `docs/` (repo documentation, used
for directories whose writer lives in code not grepped here). `~/.qwen`
does not exist on this workstation, so no live check. The layout has grown
far beyond the v1.1 catalog (channels, boards, arena, workflows, audits).

## 2. Per-user storage

`QWEN_DIR = '.qwen'` (`core/src/utils/paths.ts:14`). `getGlobalQwenDir()`
returns `$QWEN_HOME` (with `~` expansion) else `os.homedir()/.qwen`
(`core/src/config/storage.ts:193-203`). No platform branch for user paths;
`platformFoldsCase()` only affects comparisons (30-32). Same layout on
Linux, macOS, `%USERPROFILE%\.qwen` on Windows; no XDG.

A second root, the runtime base dir, defaults to the global dir but is
relocated by `$QWEN_RUNTIME_DIR` (`storage.ts:172-191`). It holds `tmp/`,
`projects/`, `debug/` (229-238) and `resources/<sessionId>`
(`core/src/utils/sessionStorageUtils.ts:813`).

Global dir files (all `storage.ts` unless noted): `settings.json` (209),
`installation_id` (213), `google_accounts.json` (217, defined, no writer
found), `commands/` (221), `memory.md` (225, no callers found; docs use
`~/.qwen/QWEN.md`, `docs/users/features/memory.md:30`), `ide/` (241-245),
`plans/` (325), `bin/` (340), `arena/` (344; `core/src/agents/arena/ArenaManager.ts:136`),
`audits/<sha256>/` (371), `workflows/` (670), `extensions/` (768),
`skills/` plus `~/.agents/skills` (17, 758), `rules/`
(`core/src/config/rulesDiscovery.ts:331`), `sessions/<pid>.json` live
session registry (`core/src/services/session-registry.ts:322,332`),
`usage_record.jsonl` (`core/src/services/usageHistoryService.ts:140`),
`model-registry.json` (`core/src/models/model-catalog.ts:64`), `artifacts/`
(`core/src/tools/artifact/local-publisher.ts:30`), `file-history/` edit
backups (`core/src/services/sessionService.ts:3317,4274`), `boards/`
(`core/src/agents/team/board-lock.ts:32-35`), `batch/`
(`cli/src/commands/batch-task.ts:283`), `tip_history.json`
(`cli/src/services/tips/tipHistory.ts:132`), `startup-perf/`
(`cli/src/utils/startupProfiler.ts:339`), `source.json`
(`core/src/telemetry/qwen-logger/qwen-logger.ts:372-376`),
`channels/{service.pid,sessions.json,cron.json}`
(`cli/src/commands/channel/pidfile.ts:55`, `runtime.ts:44,89`),
`updates/npm/` (`cli/src/utils/managed-npm-update.ts:257`),
`scratch-workspaces/` (`cli/src/serve/run-qwen-serve.ts:5231`),
`extension-store/` (`core/src/extension/extension-store.ts:523`),
`debug/<sessionId>.txt` (233-238), `trustedFolders.json`
(`cli/src/config/trustedFolders.ts:33-41`, override
`QWEN_CODE_TRUSTED_FOLDERS_PATH`), `.env` (`cli/src/config/environment.ts:192-195`).
Docs-only: `desktop-relay/`, `computer-use/`, `browser-use/`, `todos/`,
`paste-cache/`, `output-styles/`, `output-language.md`, `memories/`,
`log/otel-*`, `locales/` (user locale overrides; the bundled `locales` is in
the install dir, `cli/src/i18n/index.ts:47`).

`projects/<sanitizeCwd(cwd)>/` (619-623; non-alphanumerics replaced by
`-`, `paths.ts:388-391`): `chats/<uuid>.jsonl`
(`sessionService.ts:459,948`; `chatRecordingService.ts:1305`),
`chats/<id>.worktree.json` (`cli/src/serve/routes/session-pr-backfill.ts:314`),
`workflows/` run snapshots and `generated/` scripts (679-723), `memory/`
(docs).

`tmp/<sha256(cwd)>/` (625-629; `paths.ts:368-372`): `logs.json`,
`checkpoint-<tag>.json` (`core/src/core/logger.ts:14,204,693`),
`checkpoints/`, `tool-results/` (633), `shell_history` (776),
`attachments/`, `scheduled_tasks.json`, `otel/` (docs). No shadow git
repository exists in this fork (`gitService.ts` absent).

## 3. Credentials

- `oauth_creds.json` plaintext, mode 0600, plus `oauth_creds.lock`
  (`core/src/qwen/sharedTokenManager.ts:26-27,643`; `qwenOAuth2.ts:41,1094`).
  No OS keychain for the main login.
- `mcp-oauth-tokens-v2.json` and `extension-secrets-v1.json`: AES-GCM with
  `scryptSync('qwen-code-oauth', '<hostname>-<username>-qwen-code')`
  (`core/src/mcp/token-storage/file-token-storage.ts:30-38`); decryptable
  given hostname and username. Legacy `mcp-oauth-tokens.json` path still
  defined (`storage.ts:205-206`).
- `extensions/<name>/.qwen-extension-git-credentials.json` is a selector
  file; the secret goes to the keyring service `Qwen Code Extension Git
  Credentials` (`core/src/extension/extension-git-credentials.ts:19-22,66-67,152`).
- `settings.json` `modelProviders[].apiKey` and `envKey`
  (`core/src/models/modelsConfig.ts:725,926`); `.env` in `~/.qwen/.env`
  or `~/.env` (`environment.ts:192-195,224-239`). `channels/*.json` hold
  messaging-platform tokens (docs `~/.qwen/channels/dingtalk-groups.json`).

## 4. Exclude

`.qwen/updates`, `.qwen/extension-store`, `.qwen/bin`,
`.qwen/scratch-workspaces`, `.qwen/extensions/*/node_modules`, `.qwen/arena`
(parallel agent working copies), `.qwen/artifacts` (published build
outputs), `.qwen/resources`, `.qwen/startup-perf`. Keep `file-history/`
(pre-edit file copies: evidence), `audits/`, `debug/`, `boards/`.

## 5. Project-local files

`QWEN.md` (`core/src/utils/memory-constants.ts:7`), `.qwenignore`
(`core/src/utils/qwenIgnoreParser.ts:13`), `.qwen/settings.json` (648),
`.qwen/commands` (652), `.qwen/workflows` (661), `.qwen/extensions/qwen-extension.json`
(746-750), `.qwen/skills` and `.agents/skills` (17), `.qwen/batch`
(`cli/src/commands/batch-workflow.ts:486`). No per-project database.

## 6. Where the project path is recorded

- `projects/<sanitized>/chats/*.jsonl`: first record has `cwd`
  (`sessionService.ts:154,2757,2835,3975`). The directory name is lossy
  (`/` and `.` both become `-`), so the record is the source.
- `trustedFolders.json`: keys are folder paths.
- `tmp/<sha256>` is one-way; match it by hashing discovered paths.
- `sessions/<pid>.json` and `usage_record.jsonl` likely carry a cwd but the
  keys were not verified.

## 7. Catalog review

Current: `qwen-code|.qwen` confirmed (storage.ts:193-203). `project|QWEN.md`,
`project|.qwen`, `project|.qwenignore` confirmed. Excludes `.qwen/updates`,
`.qwen/extension-store`, `.qwen/bin`, `.qwen/scratch-workspaces`,
`.qwen/extensions/*/node_modules` confirmed; `.qwen/sandbox` doubtful (no
writer in code or docs); `.qwen/locales` doubtful (only user overrides live
there, small; harmless). Secrets `.qwen/oauth_creds.json`, `.qwen/.env`,
`.qwen/settings.json` confirmed; `.qwen/mcp-oauth-tokens*.json` confirmed
(covers `-v2`); `.qwen/extension-secrets-v1.json` confirmed.

Add:
```
# home (for QWEN_RUNTIME_DIR relocation nothing can be done statically)
# excluded
.qwen/arena
.qwen/artifacts
.qwen/resources
.qwen/startup-perf
# credential
.qwen/oauth_creds.lock          (no secret, but pairs with the file; optional)
.qwen/extensions/*/.qwen-extension-git-credentials.json
.qwen/channels/*.json
# project
project|.agents                 (if not in the shared section)
# discovery
.qwen/projects/*/chats/*.jsonl  first record "cwd" (already used)
.qwen/trustedFolders.json       object keys
```

## 8. Confidence

High: all `storage.ts`, session, token and settings paths. Medium:
docs-only directories (`memories/`, `channels/<scope>/...`, `log/otel-*`,
`paste-cache`), and that `~/.qwen/QWEN.md` rather than `memory.md` is the
live global memory file (code defines `memory.md`, docs and the memory
tool's users point at `QWEN.md`; collect both). Not determined: the JSON
keys in `sessions/<pid>.json` and `usage_record.jsonl`; whether
`.qwen/sandbox` ever existed; whether `extension-secrets-v1.json` is used
by anything other than MCP extension secrets.
