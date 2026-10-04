# qwen-code: on-disk paths

## 1. Source and evidence level

QwenLM/qwen-code, commit [`2c591ecc08a6fa080342f9b1b9f7f43215178cbb`](https://github.com/QwenLM/qwen-code/commit/2c591ecc08a6fa080342f9b1b9f7f43215178cbb)
(2026-10-03, version `0.24.7`). Open source. All claims are source-level
(`packages/...` file:line) unless marked `docs/` (repo documentation, used
for directories whose writer lives in code not grepped here). `~/.qwen`
does not exist on this workstation, so no live check. The layout has grown
far beyond the v1.1 catalog (channels, boards, arena, workflows, audits).

## 2. Per-user storage

`QWEN_DIR = '.qwen'` ([`core/src/utils/paths.ts:14`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/paths.ts#L14)). `getGlobalQwenDir()`
returns `$QWEN_HOME` (with `~` expansion) else `os.homedir()/.qwen`
([`core/src/config/storage.ts:193-203`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L193-L203)). No platform branch for user paths;
`platformFoldsCase()` only affects comparisons ([30-32](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L30-L32)). Same layout on
Linux, macOS, `%USERPROFILE%\.qwen` on Windows; no XDG.

A second root, the runtime base dir, defaults to the global dir but is
relocated by `$QWEN_RUNTIME_DIR` ([`storage.ts:172-191`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L172-L191)). It holds `tmp/`,
`projects/`, `debug/` ([229-238](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L229-L238)) and `resources/<sessionId>`
([`core/src/utils/sessionStorageUtils.ts:813`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/sessionStorageUtils.ts#L813)).

Global dir files (all `storage.ts` unless noted): `settings.json` ([209](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L209)),
`installation_id` ([213](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L213)), `google_accounts.json` ([217](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L217), defined, no writer
found), `commands/` ([221](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L221)), `memory.md` ([225](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L225), no callers found; docs use
`~/.qwen/QWEN.md`, [`docs/users/features/memory.md:30`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/docs/users/features/memory.md#L30)), `ide/` ([241-245](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L241-L245)),
`plans/` ([325](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L325)), `bin/` ([340](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L340)), `arena/` ([344](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L344); [`core/src/agents/arena/ArenaManager.ts:136`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/agents/arena/ArenaManager.ts#L136)),
`audits/<sha256>/` ([371](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L371)), `workflows/` ([670](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L670)), `extensions/` ([768](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L768)),
`skills/` plus `~/.agents/skills` ([17](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L17), [758](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L758)), `rules/`
([`core/src/config/rulesDiscovery.ts:331`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/rulesDiscovery.ts#L331)), `sessions/<pid>.json` live
session registry ([`core/src/services/session-registry.ts:322`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/session-registry.ts#L322),[`332`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/session-registry.ts#L332)),
`usage_record.jsonl` ([`core/src/services/usageHistoryService.ts:140`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/usageHistoryService.ts#L140)),
`model-registry.json` ([`core/src/models/model-catalog.ts:64`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/models/model-catalog.ts#L64)), `artifacts/`
([`core/src/tools/artifact/local-publisher.ts:30`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/tools/artifact/local-publisher.ts#L30)), `file-history/` edit
backups ([`core/src/services/sessionService.ts:3317`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L3317),[`4274`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L4274)), `boards/`
([`core/src/agents/team/board-lock.ts:32-35`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/agents/team/board-lock.ts#L32-L35)), `batch/`
([`cli/src/commands/batch-task.ts:283`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/commands/batch-task.ts#L283)), `tip_history.json`
([`cli/src/services/tips/tipHistory.ts:132`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/services/tips/tipHistory.ts#L132)), `startup-perf/`
([`cli/src/utils/startupProfiler.ts:339`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/utils/startupProfiler.ts#L339)), `source.json`
([`core/src/telemetry/qwen-logger/qwen-logger.ts:372-376`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/telemetry/qwen-logger/qwen-logger.ts#L372-L376)),
`channels/{service.pid,sessions.json,cron.json}`
([`cli/src/commands/channel/pidfile.ts:55`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/commands/channel/pidfile.ts#L55), [`runtime.ts:44`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/commands/channel/runtime.ts#L44),[`89`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/commands/channel/runtime.ts#L89)),
`updates/npm/` ([`cli/src/utils/managed-npm-update.ts:257`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/utils/managed-npm-update.ts#L257)),
`scratch-workspaces/` ([`cli/src/serve/run-qwen-serve.ts:5231`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/serve/run-qwen-serve.ts#L5231)),
`extension-store/` ([`core/src/extension/extension-store.ts:523`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/extension/extension-store.ts#L523)),
`debug/<sessionId>.txt` ([233-238](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L233-L238)), `trustedFolders.json`
([`cli/src/config/trustedFolders.ts:33-41`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/config/trustedFolders.ts#L33-L41), override
`QWEN_CODE_TRUSTED_FOLDERS_PATH`), `.env` ([`cli/src/config/environment.ts:192-195`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/config/environment.ts#L192-L195)).
Docs-only: `desktop-relay/`, `computer-use/`, `browser-use/`, `todos/`,
`paste-cache/`, `output-styles/`, `output-language.md`, `memories/`,
`log/otel-*`, `locales/` (user locale overrides; the bundled `locales` is in
the install dir, [`cli/src/i18n/index.ts:47`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/i18n/index.ts#L47)).

`projects/<sanitizeCwd(cwd)>/` ([619-623](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L619-L623); non-alphanumerics replaced by
`-`, [`paths.ts:388-391`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/paths.ts#L388-L391)): `chats/<uuid>.jsonl`
([`sessionService.ts:459`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L459),[`948`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L948); [`chatRecordingService.ts:1305`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/chatRecordingService.ts#L1305)),
`chats/<id>.worktree.json` ([`cli/src/serve/routes/session-pr-backfill.ts:314`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/serve/routes/session-pr-backfill.ts#L314)),
`workflows/` run snapshots and `generated/` scripts ([679-723](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L679-L723)), `memory/`
(docs).

`tmp/<sha256(cwd)>/` ([625-629](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L625-L629); [`paths.ts:368-372`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/paths.ts#L368-L372)): `logs.json`,
`checkpoint-<tag>.json` ([`core/src/core/logger.ts:14`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/core/logger.ts#L14),[`204`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/core/logger.ts#L204),[`693`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/core/logger.ts#L693)),
`checkpoints/`, `tool-results/` ([633](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L633)), `shell_history` ([773](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L773)),
`attachments/`, `scheduled_tasks.json`, `otel/` (docs). No shadow git
repository exists in this fork (`gitService.ts` absent).

## 3. Credentials

- `oauth_creds.json` plaintext, mode 0600, plus `oauth_creds.lock`
  ([`core/src/qwen/sharedTokenManager.ts:26-27`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/qwen/sharedTokenManager.ts#L26-L27),[`643`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/qwen/sharedTokenManager.ts#L643); [`qwenOAuth2.ts:41`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/qwen/qwenOAuth2.ts#L41),[`1094`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/qwen/qwenOAuth2.ts#L1094)).
  No OS keychain for the main login.
- `mcp-oauth-tokens-v2.json` and `extension-secrets-v1.json`: AES-GCM with
  `scryptSync('qwen-code-oauth', '<hostname>-<username>-qwen-code')`
  ([`core/src/mcp/token-storage/file-token-storage.ts:30-38`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/mcp/token-storage/file-token-storage.ts#L30-L38)); decryptable
  given hostname and username. Legacy `mcp-oauth-tokens.json` path still
  defined ([`storage.ts:205-206`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L205-L206)).
- `extensions/<name>/.qwen-extension-git-credentials.json` is a selector
  file; the secret goes to the keyring service `Qwen Code Extension Git
  Credentials` ([`core/src/extension/extension-git-credentials.ts:19-22`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/extension/extension-git-credentials.ts#L19-L22),[`66-67`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/extension/extension-git-credentials.ts#L66-L67),[`152`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/extension/extension-git-credentials.ts#L152)).
- `settings.json` `modelProviders[].apiKey` and `envKey`
  ([`core/src/models/modelsConfig.ts:725`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/models/modelsConfig.ts#L725),[`926`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/models/modelsConfig.ts#L926)); `.env` in `~/.qwen/.env`
  or `~/.env` ([`environment.ts:192-195`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/config/environment.ts#L192-L195),[`224-239`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/config/environment.ts#L224-L239)). `channels/*.json` hold
  messaging-platform tokens (docs `~/.qwen/channels/dingtalk-groups.json`).

## 4. Exclude

`.qwen/updates`, `.qwen/extension-store`, `.qwen/bin`,
`.qwen/scratch-workspaces`, `.qwen/extensions/*/node_modules`, `.qwen/arena`
(parallel agent working copies), `.qwen/artifacts` (published build
outputs), `.qwen/resources`, `.qwen/startup-perf`. Keep `file-history/`
(pre-edit file copies: evidence), `audits/`, `debug/`, `boards/`.

## 5. Project-local files

`QWEN.md` ([`core/src/utils/memory-constants.ts:7`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/memory-constants.ts#L7)), `.qwenignore`
([`core/src/utils/qwenIgnoreParser.ts:13`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/utils/qwenIgnoreParser.ts#L13)), `.qwen/settings.json` ([648](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L648)),
`.qwen/commands` ([652](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L652)), `.qwen/workflows` ([661](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L661)), `.qwen/extensions/qwen-extension.json`
([746-750](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L746-L750)), `.qwen/skills` and `.agents/skills` ([17](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/config/storage.ts#L17)), `.qwen/batch`
([`cli/src/commands/batch-workflow.ts:486`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/cli/src/commands/batch-workflow.ts#L486)). No per-project database.

## 6. Where the project path is recorded

- `projects/<sanitized>/chats/*.jsonl`: first record has `cwd`
  ([`sessionService.ts:154`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L154),[`2757`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L2757),[`2835`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L2835),[`3975`](https://github.com/QwenLM/qwen-code/blob/2c591ecc08a6fa080342f9b1b9f7f43215178cbb/packages/core/src/services/sessionService.ts#L3975)). The directory name is lossy
  (`/` and `.` both become `-`), so the record is the source.
- `trustedFolders.json`: keys are folder paths.
- `tmp/<sha256>` is one-way; match it by hashing discovered paths.
- `sessions/<pid>.json` and `usage_record.jsonl` likely carry a cwd but the
  keys were not verified.

## 7. Confidence

High: all `storage.ts`, session, token and settings paths. Medium:
docs-only directories (`memories/`, `channels/<scope>/...`, `log/otel-*`,
`paste-cache`), and that `~/.qwen/QWEN.md` rather than `memory.md` is the
live global memory file (code defines `memory.md`, docs and the memory
tool's users point at `QWEN.md`; collect both). Not determined: the JSON
keys in `sessions/<pid>.json` and `usage_record.jsonl`; whether
`.qwen/sandbox` ever existed; whether `extension-secrets-v1.json` is used
by anything other than MCP extension secrets.
