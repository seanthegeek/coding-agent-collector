# Cline: on-disk paths

## 1. Source and evidence level

Open source. cline/cline at `39ff2359f7e08231281539696e48a166ce49270c`
(clone `scratchpad/repos/cline`). Everything below is from source; the JetBrains
plugin is closed (`README.md:131`) and only its shared data dir is known.
Transcript record schemas: `analyzer/research/cline.md`.

## 2. Per-user storage

One layout on every OS; home is `$HOME`, else `%USERPROFILE%`, else
`%HOMEDRIVE%%HOMEPATH%`, else `os.homedir()`
(`sdk/packages/shared/src/storage/paths.ts:84-103`).

`~/.cline` (`paths.ts:151-160`, env `CLINE_DIR`):

- `data/` (`paths.ts:179-185`, env `CLINE_DATA_DIR`), shared by CLI, VS Code
  and JetBrains (`.clinerules/storage.md:3`):
  - `globalState.json`, `secrets.json` (mode 0600),
    `workspaces/<hash>/workspaceState.json`
    (`apps/vscode/src/shared/storage/storage-context.ts:108-143`);
    standalone hosts default the workspace dir to `data/workspace` unless
    `WORKSPACE_STORAGE_DIR` is set (`apps/vscode/src/standalone/vscode-context.ts:18-21`).
  - `workspaces/chat/`: the real working directory for sessions started
    without a project (`sdk/packages/shared/src/storage/chat-workspace-paths.ts:10-16`).
  - `sessions/<id>/<id>.json`, `<id>.messages.json`, `<id>.compaction.json`,
    `sessions/sessions.index.json` (`paths.ts:187-193`, env
    `CLINE_SESSION_DATA_DIR`; `sdk/packages/core/src/services/session-artifacts.ts:38-55`;
    `session/services/file-session-service.ts:63`).
  - `tasks/<taskId>/` legacy task dirs and `state/taskHistory.json`
    (`apps/vscode/src/sdk/legacy-state-reader.ts:42-75`).
  - `db/sessions.db`, `db/session-search.db` (FTS copy of transcripts),
    `db/connectors.db`, `db/cron.db`, `db/tasks.db` (`paths.ts:240-281`,
    env `CLINE_DB_DATA_DIR`; `services/storage/sqlite-session-store.ts:30-45`;
    `session/search/session-history-search.ts:196`).
  - `teams/teams.db` (`paths.ts:195-201`; `services/storage/sqlite-team-store.ts:210`).
  - `settings/providers.json`, `global-settings.json`,
    `cline_mcp_settings.json`, `remote-environments.json`,
    `composio/<sha256>.json` (`paths.ts:424-446`;
    `remote/remote-environments.ts:209`; `extensions/composio/composio-tools-extension.ts:63`).
  - `connectors/settings.json`, `connectors/<name>/...`
    (`paths.ts:203-238`; `apps/cli/src/connectors/base.ts:221`).
  - `logs/hooks.jsonl` (hook audit, env `CLINE_HOOKS_LOG_PATH`),
    `logs/hub-daemon.log`, `logs/<name>.log`, `logs/connectors/<channel>/<key>.log`,
    `logs/code.log` (`paths.ts:910-920`; `hooks/hook-file-hooks.ts:647`;
    `hub/daemon/index.ts:120`; `apps/cli/src/commands/doctor.ts:206`).
  - `cache/user_input_history.jsonl` (CLI prompt history with `ts`),
    `cache/feature-flags.json` (`apps/cli/src/utils/input-history.ts:8,66`;
    `utils/feature-flags.ts:23`).
  - `checkpoint-scratch/<sha>/index`, `pathspec` (git index files, reaped
    after 14 days; `sdk/packages/core/src/hooks/checkpoint-hooks.ts:19-48`).
  - `agent-plugins/` (`extensions/agent-plugin/loader.ts:1067`),
    `locks/hub/production.json` (`hub/discovery/workspace.ts:43`),
    `diagnostics/` (`apps/examples/desktop-app/sidecar/diagnostics.ts:134`).
- `rules/`, `workflows/`, `skills/<name>/SKILL.md`, `plugins/`,
  `schedules/`, `tasks/`, `cron/{reports,events}`, `worktrees/`
  (`paths.ts:299-305,348-349,563-617`; `services/marketplace.ts:251`;
  `apps/cli/src/utils/worktree.ts:20`).

`~/Documents/Cline/{Rules,Workflows,MCP,Hooks,Agents,Plugins}`
(`apps/vscode/src/core/storage/disk.ts:55-97`; `paths.ts:162-177`). Documents
is resolved via PowerShell `MyDocuments` on Windows and `xdg-user-dir
DOCUMENTS` on Linux (`documents-path.ts:6-40`), so it may sit under
`%OneDrive%\Documents` or, on headless Linux, at `~/Cline/Rules`
(`paths.ts:538-575`).

`~/.agents/skills`, `~/.agents/plugins`, `~/.agents/AGENTS.md`
(`paths.ts:106-107,517-518,630-632`) are shared cross-agent.

VS Code extension `saoudrizwan.claude-dev` globalStorage (still the root for
extension tasks: `apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts:25-32`):
`tasks/<id>/{api_conversation_history,ui_messages,context_history,task_metadata,settings}.json`,
`state/taskHistory.json`, `checkpoints/`, `cache/remote_config_<org>.json`,
`cache/cline_recommended_models.json` (`disk.ts:17-36,51-52,186-194`;
`apps/vscode/src/utils/storage.ts:11-12`). MCP settings for the extension
now live in `~/.cline/data/settings/` (`apps/vscode/src/sdk/SdkController.ts:309-312`).

CLI binary: `npm install -g cline` platform package, `bin/cline` (`apps/cli/DISTRIBUTION.md:52,240`);
no home-relative binary dir. Hub daemon runs as `cline --cline-hub-daemon`
(`apps/cli/src/commands/doctor.test.ts:218`).

## 3. Credentials

- `~/.cline/data/settings/providers.json`: `apiKey`, `auth.apiKey`,
  `auth.accessToken`, `auth.refreshToken` per provider
  (`sdk/packages/core/src/services/storage/provider-settings-manager.ts:78-85,275`).
- `~/.cline/data/secrets.json`: 46 keys incl. `clineApiKey`, `awsSecretKey`,
  `openai-codex-oauth-credentials`, `ocaRefreshToken`, `mcpOAuthSecrets`
  (`apps/vscode/src/shared/storage/state-keys.ts:313-361`).
- `~/.cline/data/connectors/settings.json`, `db/connectors.db` (connector
  credentials, `paths.ts:248-258`).
- `settings/cline_mcp_settings.json` and `settings/composio/*.json` can embed
  `headers`/`env` and connected-account ids (`apps/vscode/src/services/mcp/schemas.ts:42-143`).
- VS Code extension: secrets migrated out of `context.secrets` into
  `secrets.json` (`vscode-to-file-migration.ts:4-15`). No keychain use.

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
(`disk.ts:17-36`; `paths.ts:309-314,357,461-470,528-535,595-617`;
`sdk/packages/shared/src/remote-config/paths.ts:11-19`;
`apps/vscode/src/core/ignore/ClineIgnoreController.ts:41`). No per-project database.

## 6. Project path

- Legacy: `state/taskHistory.json[].cwdOnTaskInitialization`
  (`apps/vscode/src/shared/HistoryItem.ts:13`), both under globalStorage and
  `~/.cline/data`.
- SDK: `sessions/<id>/<id>.json` keys `cwd`, `workspace_root`
  (`sdk/packages/core/src/session/models/session-manifest.ts:6-28`);
  `db/sessions.db` table `sessions` columns `cwd`, `workspace_root`
  (`sdk/packages/shared/src/db/sqlite-db.ts:188-273`).

## 7. Catalog review

Home: `.config/*/User/globalStorage/saoudrizwan.claude-dev` and the Library /
AppData twins: confirmed. `.cline`: confirmed (`paths.ts:159`).
`Documents/Cline`: confirmed. `Cline/Rules`: confirmed (`paths.ts:570`).

Project: `.clinerules`, `.cline`: confirmed. Missing: `.clineignore`.

Excluded: `*/saoudrizwan.claude-dev/checkpoints`, `/cache`: confirmed.
`.cline/data/checkpoint-scratch`: confirmed.

Credential: `settings/providers.json`, `secrets.json`,
`connectors/settings.json`, `db/connectors.db*`: all confirmed.

Add:

```
project|.clineignore
.cline/worktrees
.cline/data/workspaces/chat
.cline/data/agent-plugins
.cline/plugins
.cline/data/settings/cline_mcp_settings.json
.cline/data/settings/composio/*.json
```

Doubtful: `Documents/Cline` misses OneDrive-redirected Documents on Windows
images (`paths.ts:547-556`); a `OneDrive*/Documents/Cline` entry would need a
glob the catalog cannot express across `/`.

## 8. Confidence

High: every `~/.cline/data` path, secrets key list, globalStorage layout,
discovery keys. Medium: whether `Documents/Cline/Agents|Plugins` is written
by the extension (the SDK only reads them). Low: JetBrains plugin's own
storage beyond `~/.cline/data` and `WORKSPACE_STORAGE_DIR`
(`storage-context.ts:58-63`); not determinable without the closed plugin.
