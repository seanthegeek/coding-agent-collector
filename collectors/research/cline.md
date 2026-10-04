# Cline: on-disk paths

## 1. Source and evidence level

Open source. cline/cline at [`39ff2359f7e08231281539696e48a166ce49270c`](https://github.com/cline/cline/commit/39ff2359f7e08231281539696e48a166ce49270c)
(clone `scratchpad/repos/cline`). Everything below is from source; the JetBrains
plugin is closed ([`README.md:131`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/README.md#L131)) and only its shared data dir is known.
Transcript record schemas: [`analyzer/research/cline.md`](../../analyzer/research/cline.md).

## 2. Per-user storage

One layout on every OS; home is `$HOME`, else `%USERPROFILE%`, else
`%HOMEDRIVE%%HOMEPATH%`, else `os.homedir()`
([`sdk/packages/shared/src/storage/paths.ts:84-103`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L84-L103)).

`~/.cline` ([`paths.ts:151-160`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L151-L160), env `CLINE_DIR`):

- `data/` ([`paths.ts:179-185`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L179-L185), env `CLINE_DATA_DIR`), shared by CLI, VS Code
  and JetBrains ([`.clinerules/storage.md:3`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/.clinerules/storage.md#L3)):
  - `globalState.json`, `secrets.json` (mode 0600),
    `workspaces/<hash>/workspaceState.json`
    ([`apps/vscode/src/shared/storage/storage-context.ts:108-143`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/shared/storage/storage-context.ts#L108-L143));
    standalone hosts default the workspace dir to `data/workspace` unless
    `WORKSPACE_STORAGE_DIR` is set ([`apps/vscode/src/standalone/vscode-context.ts:18-21`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/standalone/vscode-context.ts#L18-L21)).
  - `workspaces/chat/`: the real working directory for sessions started
    without a project ([`sdk/packages/shared/src/storage/chat-workspace-paths.ts:10-16`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/chat-workspace-paths.ts#L10-L16)).
  - `sessions/<id>/<id>.json`, `<id>.messages.json`, `<id>.compaction.json`,
    `sessions/sessions.index.json` ([`paths.ts:187-193`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L187-L193), env
    `CLINE_SESSION_DATA_DIR`; [`sdk/packages/core/src/services/session-artifacts.ts:63-94`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/session-artifacts.ts#L63-L94);
    [`session/services/file-session-service.ts:63`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/session/services/file-session-service.ts#L63)).
  - `tasks/<taskId>/` legacy task dirs and `state/taskHistory.json`
    ([`apps/vscode/src/sdk/legacy-state-reader.ts:42-75`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/sdk/legacy-state-reader.ts#L42-L75)).
  - `db/sessions.db`, `db/session-search.db` (FTS copy of transcripts),
    `db/connectors.db`, `db/cron.db`, `db/tasks.db` ([`paths.ts:240-281`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L240-L281),
    env `CLINE_DB_DATA_DIR`; [`services/storage/sqlite-session-store.ts:30-45`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/storage/sqlite-session-store.ts#L30-L45);
    [`session/search/session-history-search.ts:196`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/session/search/session-history-search.ts#L196)).
  - `teams/teams.db` ([`paths.ts:195-201`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L195-L201); [`services/storage/sqlite-team-store.ts:210`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/storage/sqlite-team-store.ts#L210)).
  - `settings/providers.json`, `global-settings.json`,
    `cline_mcp_settings.json`, `remote-environments.json`,
    `composio/<sha256>.json` ([`paths.ts:424-446`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L424-L446);
    [`remote/remote-environments.ts:209`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/remote/remote-environments.ts#L209); [`extensions/composio/composio-tools-extension.ts:63`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/extensions/composio/composio-tools-extension.ts#L63)).
  - `connectors/settings.json`, `connectors/<name>/...`
    ([`paths.ts:203-238`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L203-L238); [`apps/cli/src/connectors/base.ts:221`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/connectors/base.ts#L221)).
  - `logs/hooks.jsonl` (hook audit, env `CLINE_HOOKS_LOG_PATH`),
    `logs/hub-daemon.log`, `logs/<name>.log`, `logs/connectors/<channel>/<key>.log`,
    `logs/code.log` ([`paths.ts:910-920`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L910-L920); [`hooks/hook-file-hooks.ts:647`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/hooks/hook-file-hooks.ts#L647);
    [`hub/daemon/index.ts:120`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/hub/daemon/index.ts#L120); [`apps/cli/src/commands/doctor.ts:206`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/commands/doctor.ts#L206)).
  - `cache/user_input_history.jsonl` (CLI prompt history with `ts`),
    `cache/feature-flags.json` ([`apps/cli/src/utils/input-history.ts:8`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/utils/input-history.ts#L8),[`66`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/utils/input-history.ts#L66);
    [`utils/feature-flags.ts:23`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/utils/feature-flags.ts#L23)).
  - `checkpoint-scratch/<sha>/index`, `pathspec` (git index files, reaped
    after 14 days; [`sdk/packages/core/src/hooks/checkpoint-hooks.ts:19-48`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/hooks/checkpoint-hooks.ts#L19-L48)).
  - `agent-plugins/` ([`extensions/agent-plugin/loader.ts:1067`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/extensions/agent-plugin/loader.ts#L1067)),
    `locks/hub/production.json` ([`hub/discovery/workspace.ts:43`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/hub/discovery/workspace.ts#L43)),
    `diagnostics/` ([`apps/examples/desktop-app/sidecar/diagnostics.ts:134`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/examples/desktop-app/sidecar/diagnostics.ts#L134)).
- `rules/`, `workflows/`, `skills/<name>/SKILL.md`, `plugins/`,
  `schedules/`, `tasks/`, `cron/{reports,events}`, `worktrees/`
  ([`paths.ts:299-305`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L299-L305),[`348-349`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L348-L349),[`563-617`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L563-L617); [`services/marketplace.ts:251`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/marketplace.ts#L251);
  [`apps/cli/src/utils/worktree.ts:20`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/utils/worktree.ts#L20)).

`~/Documents/Cline/{Rules,Workflows,MCP,Hooks,Agents,Plugins}`
([`apps/vscode/src/core/storage/disk.ts:55-97`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/disk.ts#L55-L97); [`paths.ts:162-177`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L162-L177)). Documents
is resolved via PowerShell `MyDocuments` on Windows and `xdg-user-dir
DOCUMENTS` on Linux ([`documents-path.ts:6-40`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/documents-path.ts#L6-L40)), so it may sit under
`%OneDrive%\Documents` or, on headless Linux, at `~/Cline/Rules`
([`paths.ts:538-575`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L538-L575)).

`~/.agents/skills`, `~/.agents/plugins`, `~/.agents/AGENTS.md`
([`paths.ts:509-513`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L509-L513),[`517-518`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L517-L518),[`630-632`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L630-L632)) are shared cross-agent.

VS Code extension `saoudrizwan.claude-dev` globalStorage (still the root for
extension tasks: [`apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts:25-32`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts#L25-L32)):
`tasks/<id>/{api_conversation_history,ui_messages,context_history,task_metadata,settings}.json`,
`state/taskHistory.json`, `checkpoints/`, `cache/remote_config_<org>.json`,
`cache/cline_recommended_models.json` ([`disk.ts:17-36`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/disk.ts#L17-L36),[`51-52`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/disk.ts#L51-L52),[`186-194`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/disk.ts#L186-L194);
[`apps/vscode/src/utils/storage.ts:11-12`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/utils/storage.ts#L11-L12)). MCP settings for the extension
now live in `~/.cline/data/settings/` ([`apps/vscode/src/sdk/SdkController.ts:309-312`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/sdk/SdkController.ts#L309-L312)).

CLI binary: `npm install -g cline` platform package, `bin/cline` ([`apps/cli/DISTRIBUTION.md:52`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/DISTRIBUTION.md#L52),[`240`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/DISTRIBUTION.md#L240));
no home-relative binary dir. Hub daemon runs as `cline --cline-hub-daemon`
([`apps/cli/src/commands/doctor.test.ts:218`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/cli/src/commands/doctor.test.ts#L218)).

## 3. Credentials

- `~/.cline/data/settings/providers.json`: `apiKey`, `auth.apiKey`,
  `auth.accessToken`, `auth.refreshToken` per provider
  ([`sdk/packages/core/src/services/storage/provider-settings-manager.ts:78-85`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/storage/provider-settings-manager.ts#L78-L85),[`275`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/services/storage/provider-settings-manager.ts#L275)).
- `~/.cline/data/secrets.json`: 46 keys incl. `clineApiKey`, `awsSecretKey`,
  `openai-codex-oauth-credentials`, `ocaRefreshToken`, `mcpOAuthSecrets`
  ([`apps/vscode/src/shared/storage/state-keys.ts:313-361`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/shared/storage/state-keys.ts#L313-L361)).
- `~/.cline/data/connectors/settings.json`, `db/connectors.db` (connector
  credentials, [`paths.ts:248-258`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L248-L258)).
- `settings/cline_mcp_settings.json` and `settings/composio/*.json` can embed
  `headers`/`env` and connected-account ids ([`apps/vscode/src/services/mcp/schemas.ts:42-143`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/services/mcp/schemas.ts#L42-L143)).
- VS Code extension: secrets migrated out of `context.secrets` into
  `secrets.json` ([`vscode-to-file-migration.ts:4-15`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts#L4-L15)). No keychain use.

## 4. Exclude

`.cline/data/checkpoint-scratch`, `.cline/worktrees`, `.cline/data/workspaces/chat`
(agent working tree), `.cline/data/agent-plugins`, `.cline/plugins`,
`*/User/globalStorage/saoudrizwan.claude-dev/checkpoints`, `.../cache`. Keep
`.cline/data/db/session-search.db*`: a searchable copy of every transcript, not a cache.

## 5. Project-local

`.clinerules` (file or dir) with `workflows/`, `hooks/`, `skills/`;
`.cline/{rules,skills,workflows,plugins,tasks,cron,<remote-config plugin>}`;
`.clineignore`; `AGENTS.md`; also reads `.cursorrules`, `.cursor/rules`,
`.windsurfrules`, `.claude/skills`, `.agents/skills`
([`disk.ts:17-36`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/storage/disk.ts#L17-L36); [`paths.ts:309-314`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L309-L314),[`357`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L357),[`461-470`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L461-L470),[`528-535`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L528-L535),[`595-617`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/storage/paths.ts#L595-L617);
[`sdk/packages/shared/src/remote-config/paths.ts:11-19`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/remote-config/paths.ts#L11-L19);
[`apps/vscode/src/core/ignore/ClineIgnoreController.ts:41`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/core/ignore/ClineIgnoreController.ts#L41)). No per-project database.

## 6. Project path

- Legacy: `state/taskHistory.json[].cwdOnTaskInitialization`
  ([`apps/vscode/src/shared/HistoryItem.ts:13`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/shared/HistoryItem.ts#L13)), both under globalStorage and
  `~/.cline/data`.
- SDK: `sessions/<id>/<id>.json` keys `cwd`, `workspace_root`
  ([`sdk/packages/core/src/session/models/session-manifest.ts:6-28`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/core/src/session/models/session-manifest.ts#L6-L28));
  `db/sessions.db` table `sessions` columns `cwd`, `workspace_root`
  ([`sdk/packages/shared/src/db/sqlite-db.ts:188-273`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/sdk/packages/shared/src/db/sqlite-db.ts#L188-L273)).

## 7. Confidence

High: every `~/.cline/data` path, secrets key list, globalStorage layout,
discovery keys. Medium: whether `Documents/Cline/Agents|Plugins` is written
by the extension (the SDK only reads them). Low: JetBrains plugin's own
storage beyond `~/.cline/data` and `WORKSPACE_STORAGE_DIR`
([`storage-context.ts:58-63`](https://github.com/cline/cline/blob/39ff2359f7e08231281539696e48a166ce49270c/apps/vscode/src/shared/storage/storage-context.ts#L58-L63)); not determinable without the closed plugin.
