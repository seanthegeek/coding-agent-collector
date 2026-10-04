# Roo Code: on-disk paths

## 1. Source and evidence level

Open source. RooCodeInc/Roo-Code at [`b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`](https://github.com/RooCodeInc/Roo-Code/commit/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16)
(clone `scratchpad/repos/roo`). All claims from source. Extension id
`RooVeterinaryInc.roo-cline` ([`src/package.json:2`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/package.json#L2),[`5`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/package.json#L5)); the CLI is
`apps/cli` on top of `packages/vscode-shim`. Record schemas:
`analyzer/research/roo-code.md`.

## 2. Per-user storage

VS Code extension, globalStorage `rooveterinaryinc.roo-cline/` (same layout on
every OS; root is redirectable by the setting `roo-cline.customStoragePath`,
[`src/utils/storage.ts:14-48`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/utils/storage.ts#L14-L48), [`src/package.json:334`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/package.json#L334)):

- `tasks/<taskId>/api_conversation_history.json`, `ui_messages.json`,
  `task_metadata.json`, `history_item.json`; `tasks/_index.json`
  ([`src/shared/globalFileNames.ts:1-9`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/shared/globalFileNames.ts#L1-L9);
  [`src/core/task-persistence/TaskHistoryStore.ts:24-25`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/TaskHistoryStore.ts#L24-L25),[`561-570`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/TaskHistoryStore.ts#L561-L570)).
- `tasks/<taskId>/checkpoints/.git` shadow repo per task, or
  `checkpoints/<sha256[:8] of workspace>/` per workspace
  ([`src/services/checkpoints/ShadowCheckpointService.ts:125`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/checkpoints/ShadowCheckpointService.ts#L125),[`432-447`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/checkpoints/ShadowCheckpointService.ts#L432-L447);
  [`RepoPerTaskCheckpointService.ts:10`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/checkpoints/RepoPerTaskCheckpointService.ts#L10)).
- `settings/mcp_settings.json`, `settings/custom_modes.yaml`
  ([`src/utils/storage.ts:63-68`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/utils/storage.ts#L63-L68); [`src/services/mcp/McpHub.ts:494`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/mcp/McpHub.ts#L494);
  [`src/core/config/CustomModesManager.ts:251`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/config/CustomModesManager.ts#L251); the old name
  `cline_mcp_settings.json` is migrated, [`src/utils/migrateSettings.ts:26`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/utils/migrateSettings.ts#L26)).
- `cache/<provider>_models.json` ([`src/api/providers/fetchers/modelCache.ts:39-46`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/api/providers/fetchers/modelCache.ts#L39-L46)).
- `roo-index-cache-<sha256>.json` per workspace, codebase-index file hashes
  ([`src/services/code-index/cache-manager.ts:24-26`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/code-index/cache-manager.ts#L24-L26)). Vectors go to Qdrant,
  not disk.

CLI (`roo`), `~/.vscode-mock/` from `$HOME` or `%USERPROFILE%`
([`packages/vscode-shim/src/utils/paths.ts:8-16`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/utils/paths.ts#L8-L16),[`65-82`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/utils/paths.ts#L65-L82)):

- `global-storage/`: same `tasks/` tree as above, plus `global-state.json`,
  `configuration.json`, `secrets.json`
  ([`packages/vscode-shim/src/context/ExtensionContext.ts:102-111`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/context/ExtensionContext.ts#L102-L111);
  [`api/WorkspaceConfiguration.ts:87-88`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/api/WorkspaceConfiguration.ts#L87-L88); [`storage/SecretStorage.ts:47`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/storage/SecretStorage.ts#L47)).
- `workspace-storage/<hash>/workspace-state.json`, `configuration.json`;
  hash is a 32-bit string hash of the workspace path, not reversible
  ([`paths.ts:24-32`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/utils/paths.ts#L24-L32),[`72-75`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/utils/paths.ts#L72-L75)).
- `logs/` ([`paths.ts:80-82`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/utils/paths.ts#L80-L82)).

`~/.roo/` ([`src/services/roo-config/index.ts:26-28`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/roo-config/index.ts#L26-L28);
[`apps/cli/src/lib/storage/config-dir.ts:5`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/apps/cli/src/lib/storage/config-dir.ts#L5)): `rules/`, `rules-<mode>/`
([`src/core/webview/webviewMessageHandler.ts:1908`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/webview/webviewMessageHandler.ts#L1908)), `commands/`
([`src/services/command/commands.ts:137`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/command/commands.ts#L137)), `skills/`
([`src/services/skills/SkillsManager.ts:608`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/skills/SkillsManager.ts#L608)), `worktrees/<project>-<suffix>`
([`src/core/webview/worktree/handlers.ts:229-230`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/webview/worktree/handlers.ts#L229-L230)), `cli-history.json`
([`apps/cli/src/lib/storage/history.ts:21`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/apps/cli/src/lib/storage/history.ts#L21), entries are raw prompts),
`cli-settings.json` ([`settings.ts:9`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/apps/cli/src/lib/storage/settings.ts#L9); mode, provider, model only,
[`apps/cli/src/types/types.ts:55-67`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/apps/cli/src/types/types.ts#L55-L67)). `~/.agents/skills` is also read
([`roo-config/index.ts:53-55`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/roo-config/index.ts#L53-L55); [`SkillsManager.ts:594`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/skills/SkillsManager.ts#L594)).

Global MCP server install dir is platform-branched: Windows
`AppData/Roaming/Roo-Code/MCP`, macOS `Documents/Cline/MCP` (sic), Linux
`.local/share/Roo-Code/MCP`, fallback `~/.roo-code/mcp`
([`src/core/webview/ClineProvider.ts:1547-1562`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/webview/ClineProvider.ts#L1547-L1562)). It holds cloned server
code, not evidence of use. No XDG use elsewhere; no environment variable
relocates storage.

## 3. Credentials

- Extension: provider profiles with API keys are stored in VS Code
  `context.secrets` under `roo_cline_config_api_config`
  ([`src/core/config/ProviderSettingsManager.ts:45`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/config/ProviderSettingsManager.ts#L45),[`657`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/config/ProviderSettingsManager.ts#L657)); Codex OAuth
  credentials likewise ([`src/integrations/openai-codex/oauth.ts:451`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/integrations/openai-codex/oauth.ts#L451)). Those
  land in the editor's `state.vscdb`, collected by the vscode entries.
- CLI: the same keys serialised to `~/.vscode-mock/global-storage/secrets.json`
  (mode 0600, [`packages/vscode-shim/src/storage/SecretStorage.ts:10-47`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/packages/vscode-shim/src/storage/SecretStorage.ts#L10-L47)).
- `settings/mcp_settings.json` and project `.roo/mcp.json` can embed `env`
  and headers. No keychain use.

## 4. Exclude

`*/rooveterinaryinc.roo-cline/tasks/*/checkpoints`,
`*/rooveterinaryinc.roo-cline/checkpoints`, `*/rooveterinaryinc.roo-cline/cache`,
`.vscode-mock/global-storage/tasks/*/checkpoints`,
`.vscode-mock/global-storage/checkpoints`, `.roo/worktrees`,
`.local/share/Roo-Code/MCP`, `AppData/Roaming/Roo-Code/MCP`, `.roo-code/mcp`.

## 5. Project-local

`.roo/rules/`, `.roo/rules-<mode>/`, `.roo/commands/`, `.roo/mcp.json`,
`.roo/skills/` ([`roo-config/index.ts:68-80`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/roo-config/index.ts#L68-L80); [`webviewMessageHandler.ts:1901`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/webview/webviewMessageHandler.ts#L1901);
[`commands.ts:141`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/command/commands.ts#L141); [`McpHub.ts:379`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/mcp/McpHub.ts#L379); [`SkillsManager.ts:379`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/services/skills/SkillsManager.ts#L379)); `.roomodes`,
`.roorules*`, `.rooignore`, `.rooprotected`, legacy `.clinerules*`
([`src/core/protect/RooProtectedController.ts:17-23`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/protect/RooProtectedController.ts#L17-L23);
[`src/core/ignore/RooIgnoreController.ts:41`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/ignore/RooIgnoreController.ts#L41);
[`src/core/prompts/sections/custom-instructions.ts:229`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/prompts/sections/custom-instructions.ts#L229)); `.agents/skills`;
`AGENTS.md`. No per-project database.

## 6. Project path

`tasks/_index.json[].workspace` and `tasks/<id>/history_item.json.workspace`
([`src/core/task-persistence/taskMetadata.ts:22`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/taskMetadata.ts#L22),[`37`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/taskMetadata.ts#L37),[`111`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/taskMetadata.ts#L111);
[`TaskHistoryStore.ts:146-149`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/task-persistence/TaskHistoryStore.ts#L146-L149)), in both globalStorage and
`~/.vscode-mock/global-storage`. `checkpoints/<hash>` is a truncated sha256
and not reversible.

## 7. Confidence

High: all globalStorage and `~/.vscode-mock` paths, `_index.json.workspace`,
secrets locations. Medium: `.roo/worktrees` is only the suggested default
offered to the user ([`handlers.ts:230`](https://github.com/RooCodeInc/Roo-Code/blob/b867ec9145750d0ae1ff7f02d35406e9bf2a0b16/src/core/webview/worktree/handlers.ts#L230)), so it may be elsewhere. Not
determined: where the CLI stores cloud (Roo account) tokens beyond
`secrets.json`; `@roo-code/cloud` is an external package not in this clone.
