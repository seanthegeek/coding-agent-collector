# vscode: VS Code, Insiders, VSCodium and the fork family as hosts for AI extensions

## 1. Source and evidence level

- L1 source: microsoft/vscode at `d7622a529314a4abcefd7ca9e3d7344bc9ccba9e` (`scratchpad/repos/vscode`); microsoft/vscode-copilot-chat at `5863f5a7088958050792b5dccbe8b46c6e13eccc` (`scratchpad/repos/vscode-copilot-chat`); posit-dev/positron `product.json` (raw.githubusercontent); VSCodium `prepare_vscode.sh`.
- L4 community: Kiro IDE `product.json` copy (github.com/Bad3r/dotfiles `opt/kiro/resources/app/product.json`), AgentsView docs for Trae, wookat/DevCleaner `conversation.rs` for Trae keys.
- L5 this workstation (read-only `du`/`ls`): `~/.vscode-server`, `/mnt/c/Users/Sean/AppData/Roaming/Code`, `~/.vscode`.

## 2. Per-user storage

User data dir resolution (`src/vs/platform/environment/node/userDataPath.ts:51-68, 80-99`): `$VSCODE_PORTABLE/user-data`, then `$VSCODE_APPDATA/<nameShort>`, then `--user-data-dir`, else Windows `%APPDATA%\<nameShort>` (fallback `%USERPROFILE%\AppData\Roaming`), macOS `~/Library/Application Support/<nameShort>`, Linux `$XDG_CONFIG_HOME/<nameShort>` or `~/.config/<nameShort>`. Layout is identical on all three OSes; only the parent differs.

`nameShort` / `dataFolderName` / `serverDataFolderName`: Code-OSS `Code - OSS`/`.vscode-oss`/`.vscode-server-oss` (`product.json:2-15`); shipped builds `Code`, `Code - Insiders` with `.vscode`, `.vscode-insiders`, `.vscode-server`; VSCodium `VSCodium`/`.vscode-oss`/`.vscodium-server`, Insiders `VSCodium - Insiders`/`.vscodium-insiders`/`.vscodium-server-insiders` (`prepare_vscode.sh:68-76, 96-103`); Positron `Positron`/`.positron`/`.positron-server` (product.json L1); Kiro `Kiro`/`.kiro`/`.kiro-server` (L4); Cursor `Cursor`/`.cursor`/`.cursor-server`, Windsurf→Devin `Windsurf`,`Devin`/`.windsurf`,`.devin`, Antigravity `Antigravity`/`.antigravity`, Trae `Trae`, `Trae CN`, `TRAE SOLO CN` (L4 AgentsView) follow the same convention; see the per-agent documents.

Inside the user data dir (`src/vs/platform/environment/common/environmentService.ts`):
- `User/` = appSettingsHome (`:56`); `User/globalStorage/storage.json` (`:65`); `User/globalStorage/state.vscdb` (`platform/storage/electron-main/storageMain.ts:285,353`), SQLite `ItemTable(key TEXT UNIQUE, value BLOB)` (`base/parts/storage/node/storage.ts:343`).
- `User/globalStorage/<extension id lowercased>/` per extension (`workbench/api/common/extHostStoragePaths.ts:21`). `User/workspaceStorage/<id>/<extension id, case as published>/` (`:15`), e.g. `GitHub.copilot-chat`.
- `User/workspaceStorage/<id>/state.vscdb` and `workspace.json` (`storageMain.ts:415-416, 472-474`). `<id>` = md5 of the folder URI plus inode (Linux) or birthtime (macOS/Windows) (`platform/workspaces/node/workspaces.ts:53-73`); `.code-workspace` ids are md5 of the config path (`:32`).
- Chat sessions (`workbench/contrib/chat/common/model/chatSessionStore.ts:72-79, 152, 738-749`): `User/workspaceStorage/<id>/chatSessions/<sessionId>.jsonl` (append log, `chat.useLogSessionStorage`) or `.json`; empty-window chats in `User/globalStorage/emptyWindowChatSessions/`; `User/globalStorage/transferredChatSessions/`; legacy `User/workspaceStorage/no-workspace/chatSessions/`.
- `User/History/` local file history with `entries.json` (`environmentService.ts:89`; `workingCopyHistoryService.ts:59`); `User/sync/` (`:71`); `User/profiles/<id>/` (`platform/userDataProfile/common/userDataProfile.ts:273`) each with `settings.json`, `keybindings.json`, `tasks.json`, `snippets/`, `prompts/`, `mcp.json`, `extensions.json`, `globalStorage/`, `agent-plugins/` (`:196-205`); `User/agent-sessions.code-workspace` (`environmentService.ts:281`).
- `logs/<yyyymmddThhmmss>/window<N>/exthost/<ext id>/` (`environmentService.ts:73-78`; `workbench/services/environment/electron-browser/environmentService.ts:109`); `Backups/` hot-exit unsaved buffers (`platform/environment/electron-main/environmentMainService.ts:49`); `Workspaces/` untitled (`environmentService.ts:108`).

Dot folder `~/<dataFolderName>/`: `extensions/` and `extensions/extensions.json` (`environmentService.ts:131-147`; `platform/userDataProfile/node/userDataProfile.ts:43`), `extensions/.obsolete` (`extensionManagementService.ts:558`), `argv.json` (`:95-101`), `policy.json` (`:274`), `cli/` tunnel-CLI state migrated from `~/.vscode-cli` (`cli/src/state.rs:150-152`). Observed on this host: `~/.vscode/{agent-plugins,argv.json,cli,extensions}` (L5).

Remote server `~/<serverDataFolderName>/` (`src/vs/server/node/server.main.ts:41-47`, env `VSCODE_AGENT_FOLDER`, flag `--server-data-dir`): `data/User/...` same layout as above, `data/Machine/settings.json`, `data/logs/`, `extensions/`, `bin/<commit>/`. On WSL and SSH targets this is where Copilot Chat sessions live; this host has `~/.vscode-server/data/User/globalStorage/github.copilot-chat` at 54 MB (L5).

Portable mode (`src/bootstrap-node.ts:225-246`): `<app>/data` on Windows/Linux, `<app dir>/<applicationName>-portable-data` on macOS, containing `user-data/`, `extensions/`, `tmp/`. Env: `VSCODE_PORTABLE`, `VSCODE_APPDATA`, `VSCODE_EXTENSIONS`, `XDG_CONFIG_HOME`.

## 3. Credentials

- Extension secrets are `ItemTable` rows keyed `secret://<key>` in `User/globalStorage/state.vscdb`, encrypted with the OS keyring/safeStorage when available (`platform/secrets/common/secrets.ts:19, 148, 227`). Collect the DB unflagged; the values are not recoverable offline without the keyring. Forks that patched this store plaintext tokens (Cursor `cursorAuth/*`, Windsurf `windsurfAuthStatus`).
- Tunnel CLI: keyring first, file fallback `~/<dataFolder>/cli/token.json` or `token-<namespace>.json` (`cli/src/auth.rs:178-189, 386, 416`).
- Files that can embed API keys: `User/settings.json`, `User/mcp.json`, `User/profiles/*/mcp.json`, project `.vscode/mcp.json`.
- Copilot's own token store `~/.config/github-copilot` is covered by the `copilot` entries.

## 4. Exclusions (observed sizes L5; code L1)

- `*/User/globalStorage/ms-dotnettools.vscode-dotnet-runtime` 463 MB (WSL) / 834 MB (Windows): bundled .NET runtimes.
- `*/User/globalStorage/yzane.markdown-pdf` 371 MB (bundled Chromium); `*/User/globalStorage/ms-edgedevtools.vscode-edge-devtools` 113 MB.
- Copilot Chat recorders: `*/User/globalStorage/github.copilot-chat/logContextRecordings` and `workspaceRecordings` (`src/extension/inlineEdits/vscode-node/inlineEditProviderFeature.ts:130`; `workspaceRecorder/vscode-node/workspaceRecorderFeature.ts:57`); keep `editRecordings` (`platform/multiFileEdit/common/editLogService.ts:68`, an AI edit log).
- Copilot Chat indexes under workspaceStorage: `GitHub.copilot-chat/codebase-external.sqlite` (`codeSearch/externalIngestIndex.ts:172`) and chunk-embedding caches (`workspaceChunkEmbeddingsIndex.ts:70`, `embeddingsIndex.ts:76-77`).
- Other `ms-*`, `redhat.*`, `eamodio.*`, `golang.*`, `rust-lang.*` globalStorage dirs were 1-20 MB here; their binaries live in `extensions/`, which is not collected. `User/History` is evidence; leave it to the size cap.

## 5. Project-local files

`.vscode/mcp.json` (already catalogued), `.vscode/settings.json` (holds `chat.*`/`github.copilot.*` settings), `.github/copilot-instructions.md` (catalogued). Copilot prompt/instruction/agent files under `.github/` were not re-verified in this pass.

## 6. Project path

`User/workspaceStorage/<id>/workspace.json`: `{"folder": "<file URI>"}` or `{"workspace": "<path to .code-workspace>"}` (`storageMain.ts:472-474`). Decode `file:///c%3A/...` on Windows. Chat `.jsonl` records carry no cwd.

## 7. Catalog review

Current lines:
- `vscode|.vscode*/extensions/extensions.json` confirmed (`environmentService.ts:147`; `node/userDataProfile.ts:43`); the glob also matches `.vscode-server` and `.vscode-insiders`.
- `vscode|Library/Application Support/Code*/User`, `.../logs`, `.config/Code*/User|logs`, `AppData/Roaming/Code*/User|logs` confirmed (`userDataPath.ts:85-99`; nameShort `Code`, `Code - Insiders`, `Code - OSS`).
- `vscode|Library/Application Support/VSCodium/User`, `.config/VSCodium/User`, `AppData/Roaming/VSCodium/User` confirmed (`prepare_vscode.sh:96`); misses `VSCodium - Insiders` and `logs`.

Add:
```
vscode|.vscode-server*/data/User
vscode|.vscode-server*/data/logs
vscode|.vscodium-server*/data/User
vscode|.positron-server/data/User
vscode|Library/Application Support/VSCodium*/User
vscode|Library/Application Support/VSCodium*/logs
vscode|.config/VSCodium*/User
vscode|.config/VSCodium*/logs
vscode|AppData/Roaming/VSCodium*/User
vscode|AppData/Roaming/VSCodium*/logs
vscode|Library/Application Support/Positron/User
vscode|.config/Positron/User
vscode|AppData/Roaming/Positron/User
vscode|Library/Application Support/Trae*/User
vscode|.config/Trae*/User
vscode|AppData/Roaming/Trae*/User
vscode|Library/Application Support/TRAE*/User
vscode|.config/TRAE*/User
vscode|AppData/Roaming/TRAE*/User
vscode|.vscode*/argv.json
vscode|.vscode*/cli/token*.json
```
Replace the three `VSCodium/User` lines with the `VSCodium*` lines above. Exclusions:
```
*/User/globalStorage/ms-dotnettools.vscode-dotnet-runtime
*/User/globalStorage/yzane.markdown-pdf
*/User/globalStorage/ms-edgedevtools.vscode-edge-devtools
*/User/globalStorage/github.copilot-chat/logContextRecordings
*/User/globalStorage/github.copilot-chat/workspaceRecordings
*/User/workspaceStorage/*/GitHub.copilot-chat/codebase-external.sqlite*
```
Secret globs: `.vscode*/cli/token*.json`, `*/User/mcp.json`, `*/User/profiles/*/mcp.json`. Discovery: read `*/User/workspaceStorage/*/workspace.json` keys `folder` and `workspace` (also for Cursor, Windsurf, Kiro, Antigravity, Trae data dirs). Optional, generic rather than AI: `Code*/Backups`.

## 8. Confidence

High: user data path order, `User/` layout, `state.vscdb` schema, chat session paths, workspace.json keys, server `data/User`, Positron and VSCodium names, this host's sizes. Medium: Trae names (L4 docs only), `agent-plugins` location (source puts it under the profile, host shows `~/.vscode/agent-plugins`), Copilot index exclusions (file names from source, sizes not observed). Not determined: whether forks lowercase extension ids the same way (Kiro's `kiro.kiroagent` suggests yes), Copilot `.github/` customization file names, and which `secret://` keys each AI extension writes.
