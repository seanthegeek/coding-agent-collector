# PearAI: on-disk paths

Catalog agent: `pearai`. PearAI is a VS Code fork that ships two AI
extensions of its own: `pearai.pearai`, a fork of Continue (chat,
autocomplete, memory), and `PearAI.pearai-roo-cline`, a fork of Roo Code
(the "Agent" view). Editor state follows the VS Code layout in
[vscode.md](vscode.md); the extension forks follow
[continue.md](continue.md) and [roo-code.md](roo-code.md) with renamed
directories. The single most important fact: **`~/.pearai` is both the
editor's `dataFolderName` (extensions) and the Continue fork's global
directory (chat sessions, config, API keys).** Transcript schema is in
`analyzer/research/pearai.md`.

## 1. Source and evidence level

All claims from source, three repositories:

- Editor: trypear/pearai-app, MIT
  ([`LICENSE.txt`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/LICENSE.txt)), commit
  [`d930f0233c14668df9f85c6a78a81828f4251194`](https://github.com/trypear/pearai-app/commit/d930f0233c14668df9f85c6a78a81828f4251194)
  (2025-05-15), the last push. Its tree records the two extensions only in
  [`.gitmodules:1-8`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/.gitmodules#L1-L8), with no pinned gitlink,
  so the extension commits below are their current heads, not the ones a
  given PearAI build shipped.
- Continue fork: trypear/pearai-submodule, Apache-2.0, commit
  [`51eceef62a90c29f712b3a9607ea70a9dca657e9`](https://github.com/trypear/pearai-submodule/commit/51eceef62a90c29f712b3a9607ea70a9dca657e9)
  (2026-06-19), extension `pearai.pearai` 2.0.0
  ([`extensions/vscode/package.json:3-6`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/package.json#L3-L6)).
- Roo Code fork: trypear/PearAI-Roo-Code, Apache-2.0, commit
  [`0b6df736c9b2799c38b9ee629668407521a7bdda`](https://github.com/trypear/PearAI-Roo-Code/commit/0b6df736c9b2799c38b9ee629668407521a7bdda)
  (2026-06-19), extension `PearAI.pearai-roo-cline` 3.15.3
  ([`package.json:2-7`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/package.json#L2-L7)).

## 2. Per-user storage

**Editor.** `product.json` sets `nameShort` `PearAI`, `dataFolderName`
`.pearai` and `serverDataFolderName` `.pearai-server`
([`product.json:2-6`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/product.json#L2-L6),
[`15`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/product.json#L15)). The user data directory is
`getUserDataPath(args, product.nameShort)`
([`src/main.ts:60`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/main.ts#L60)), which resolves to
`VSCODE_APPDATA`, else `%APPDATA%`, `~/Library/Application Support`
or `$XDG_CONFIG_HOME`/`~/.config`, joined with the product name
([`src/vs/platform/environment/node/userDataPath.js:63-101`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/environment/node/userDataPath.js#L63-L101)):

- `~/.config/PearAI`, `~/Library/Application Support/PearAI`,
  `%APPDATA%\PearAI`, each with the standard `User/` (settings,
  `globalStorage/state.vscdb`, `workspaceStorage/`, `History/`) and
  `logs/`.
- `~/.pearai/extensions/` (installed extensions), `~/.pearai/argv.json`
  and `~/.pearai/policy.json`
  ([`environmentService.ts:104`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/environment/common/environmentService.ts#L104),
  [`149`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/environment/common/environmentService.ts#L149),
  [`250`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/environment/common/environmentService.ts#L250)).
- Remote server: `~/.pearai-server/`
  ([`src/vs/server/node/server.main.ts:39`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/server/node/server.main.ts#L39)),
  with `data/User` as in VS Code.
- Extension `globalStorage` folders are the lowercased extension id
  ([`extHostStoragePaths.ts:90`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/workbench/api/common/extHostStoragePaths.ts#L90)):
  `User/globalStorage/pearai.pearai` and
  `User/globalStorage/pearai.pearai-roo-cline`.

**Continue fork (`pearai.pearai`).** Global directory is
`$CONTINUE_GLOBAL_DIR` or `os.homedir()/.pearai` on every OS
([`core/util/paths.ts:11-21`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L11-L21)). Layout is
Continue's: `sessions/<id>.json` and `sessions/sessions.json`
([`23-53`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L23-L53)), `config.json`,
`config.ts`, `package.json`, `types/`, `tsconfig.json`, `out/config.js`
([`55-144`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L55-L144)), `.continuerc.json`
([`146-162`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L146-L162)), `dev_data/devdata.sqlite`
and `dev_data/<table>.jsonl` ([`164-178`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L164-L178)),
`.migrations/` ([`203-209`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L203-L209)),
`index/index.sqlite`, `index/lancedb/`, `index/autocompleteCache.sqlite`,
`index/docs.sqlite`, `index/globalContext.json`
([`31-41`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L31-L41),
[`233-247`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L233-L247)), `.configs/<host>/`
([`249-287`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L249-L287)), `.env`
([`289-295`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L289-L295)), `logs/core.log`,
`logs/prompt.log` ([`297-311`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L297-L311)) and
`.prompts/` ([`313-315`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L313-L315)). PearAI
additions in the same directory:

- `pearai_memories.json`: local "memories" the assistant keeps about the
  user, written by both extensions
  ([`extensions/vscode/src/integrations/mem0/localMemoryService.ts:33-35`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/integrations/mem0/localMemoryService.ts#L33-L35),
  [`util/pearai/pearaiMemory.ts:1`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/util/pearai/pearaiMemory.ts#L1);
  [`PearAI-Roo-Code src/utils/memory.ts:23`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/utils/memory.ts#L23),
  [`39-42`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/utils/memory.ts#L39-L42)).
- `pearai.log` ([`commands.ts:603-604`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/commands.ts#L603-L604)),
  `.diffs/` ([`diff/horizontal.ts:30-32`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/diff/horizontal.ts#L30-L32)),
  `firstLaunch.flag`, `firstLaunchCreator.flag`
  ([`copySettings.ts:8-12`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/copySettings.ts#L8-L12)).

**Import from VS Code.** The welcome flow's "import settings" copies VS
Code's `settings.json`, `keybindings.json`, `snippets`, `sync` and
`globalStorage/state.vscdb` into a PearAI `User` directory, and every
VS Code extension except AI ones into `~/.pearai/extensions`
([`copySettings.ts:40-102`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/copySettings.ts#L40-L102),
[`141-145`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/copySettings.ts#L141-L145)). The
target is built with a lowercase `pearai`
([`copySettings.ts:24-33`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/copySettings.ts#L24-L33)),
so on Linux it is `~/.config/pearai/User`, a different directory from the
`~/.config/PearAI/User` the editor uses. A `state.vscdb` there is a copy
of the user's VS Code state, not PearAI activity.

**Roo Code fork (`pearai.pearai-roo-cline`).** Storage is the extension's
`globalStorage` unless the `roo-cline.customStoragePath` setting moves it
([`src/shared/storagePathManager.ts:11-27`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/storagePathManager.ts#L11-L27)):
`tasks/<taskId>/` ([`52-57`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/storagePathManager.ts#L52-L57))
with `api_conversation_history.json`, `ui_messages.json`,
`task_metadata.json`; `settings/custom_modes.json` and
`settings/pearai_agent_mcp_settings.json`
([`src/shared/globalFileNames.ts:1-7`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/globalFileNames.ts#L1-L7);
[`storagePathManager.ts:62-67`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/storagePathManager.ts#L62-L67));
`cache/` ([`74`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/storagePathManager.ts#L74)); shadow-git
checkpoints in `tasks/<id>/checkpoints` or `checkpoints/<hash>`
([`ShadowCheckpointService.ts:348`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/services/checkpoints/ShadowCheckpointService.ts#L348),
[`358`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/services/checkpoints/ShadowCheckpointService.ts#L358)). The
task list is the `taskHistory` key in the editor's global state
(`state.vscdb`; [`ClineProvider.ts:1091`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/webview/ClineProvider.ts#L1091)).
MCP server checkouts go to Roo Code's own directories,
`AppData/Roaming/Roo-Code/MCP`, `Documents/Cline/MCP` (macOS),
`.local/share/Roo-Code/MCP`, fallback `~/.roo-code/mcp`
([`ClineProvider.ts:952-973`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/webview/ClineProvider.ts#L952-L973)),
which the catalog already collects as `roo-code` and `cline`.

## 3. Credentials

- PearAI account: the Continue fork stores `pearai-token` and
  `pearai-refresh` in VS Code SecretStorage
  ([`commands.ts:1004-1005`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/commands.ts#L1004-L1005));
  the Roo fork stores `pearaiApiKey` and `pearaiRefreshKey`
  ([`src/extension.ts:112-113`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/extension.ts#L112-L113)). Both
  land as encrypted `secret://` rows in `User/globalStorage/state.vscdb`
  (see [vscode.md](vscode.md)); not recoverable offline without the OS
  keyring. Roo's other provider keys go to the same store.
- `~/.pearai/config.json` and `config.ts` model entries carry `apiKey`
  ([`core/index.d.ts:810-814`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/index.d.ts#L810-L814), `ModelDescription`); `~/.pearai/.env` is
  loaded as environment ([`paths.ts:289-295`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/paths.ts#L289-L295));
  `.configs/<host>/config.json` is a remote config.
- `settings/pearai_agent_mcp_settings.json` in the Roo fork's storage and
  project `.pearai-agent/mcp.json`
  ([`src/services/mcp/McpHub.ts:502-503`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/services/mcp/McpHub.ts#L502-L503))
  can hold MCP server `env` secrets.
- `index/globalContext.json` holds only UI state in this fork
  ([`core/util/GlobalContext.ts:5-16`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/GlobalContext.ts#L5-L16)),
  unlike upstream Continue; it need not be flagged.

## 4. Exclusions

- `.pearai/extensions`: extension binaries, the equivalent of the
  `.cursor/extensions` exclusion, and after a VS Code import a full copy of
  the user's VS Code extensions.
- `.pearai-server/bin`, `.pearai-server/extensions` (only `data/User` is
  proposed, so these are never reached).
- Continue fork: `.pearai/index/lancedb`, `.pearai/index/*.sqlite`,
  `.pearai/types`, `.pearai/out`, `.pearai/node_modules`, `.pearai/.diffs`,
  `.pearai/.migrations`, `.pearai/dev_data/devdata.sqlite`, mirroring the
  Continue exclusions. Keep `index/globalContext.json`.
- Roo fork: `*/User/globalStorage/pearai.pearai-roo-cline/checkpoints`,
  `.../tasks/*/checkpoints` and `.../cache`, mirroring Roo Code.

## 5. Project-local files

- Continue fork: `.pearairc.json` at each workspace root
  ([`extensions/vscode/src/ideProtocol.ts:310-322`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/extensions/vscode/src/ideProtocol.ts#L310-L322)),
  `.pearaiignore` ([`core/indexing/walkDir.ts:209`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/indexing/walkDir.ts#L209)),
  and `.prompts/*.prompt` slash commands
  ([`core/config/load.ts:185-200`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/config/load.ts#L185-L200);
  [`core/config/promptFile.ts:10`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/config/promptFile.ts#L10)).
- Roo fork renames Roo's `.roo` to `.pearai-agent/` (`rules/`,
  `rules-<mode>/`, `system-prompt-<mode>`, `mcp.json`), `.rooignore` to
  `.pearai-agent-ignore` and `.roomodes` to `.pearai-agent-modes`
  ([`src/shared/constants.ts:1-5`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/shared/constants.ts#L1-L5);
  [`custom-instructions.ts:161`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/prompts/sections/custom-instructions.ts#L161),
  [`197`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/prompts/sections/custom-instructions.ts#L197);
  [`custom-system-prompt.ts:50`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/prompts/sections/custom-system-prompt.ts#L50)),
  and still reads `.roorules`, `.clinerules` and `.clinerules-<mode>`
  ([`custom-instructions.ts:170`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/prompts/sections/custom-instructions.ts#L170),
  [`213`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/core/prompts/sections/custom-instructions.ts#L213)).
- No per-project database.

## 6. Where the project path is recorded

- `~/.pearai/sessions/sessions.json` `[].workspaceDirectory` and
  `sessions/<id>.json` `workspaceDirectory`
  ([`core/util/history.ts:118-135`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/util/history.ts#L118-L135);
  [`gui/src/hooks/useHistory.tsx:79-85`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/gui/src/hooks/useHistory.tsx#L79-L85)),
  the first workspace folder as a plain path or empty.
- Roo fork: `taskHistory[].workspace` inside `state.vscdb`
  ([`src/schemas/index.ts:339-352`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/schemas/index.ts#L339-L352)),
  SQLite only.
- Editor: `User/workspaceStorage/*/workspace.json` as in VS Code.

## 7. Catalog proposal

```
# PearAI (VS Code fork; ~/.pearai is both the editor's extension dir and the Continue fork's home)
pearai|.pearai
pearai|.config/PearAI/User
pearai|.config/PearAI/logs
pearai|.config/pearai/User
pearai|Library/Application Support/PearAI/User
pearai|Library/Application Support/PearAI/logs
pearai|AppData/Roaming/PearAI/User
pearai|AppData/Roaming/PearAI/logs
pearai|.pearai-server/data/User
```

```
project|.pearairc.json
project|.pearaiignore
project|.pearai-agent
project|.pearai-agent-ignore
project|.pearai-agent-modes
```

```
.pearai/extensions
.pearai/index/lancedb
.pearai/index/*.sqlite
.pearai/types
.pearai/out
.pearai/node_modules
.pearai/.diffs
.pearai/.migrations
.pearai/dev_data/devdata.sqlite
*/User/globalStorage/pearai.pearai-roo-cline/checkpoints
*/User/globalStorage/pearai.pearai-roo-cline/tasks/*/checkpoints
*/User/globalStorage/pearai.pearai-roo-cline/cache
```

```
.pearai/config.json
.pearai/config.ts
.pearai/.env
.pearai/.configs/*/config.js*
*/globalStorage/pearai.pearai-roo-cline/settings/pearai_agent_mcp_settings.json
.pearai-agent/mcp.json
```

Discovery sources:

```
.pearai/sessions/sessions.json  workspaceDirectory
```

No nested entries are needed: the `User` lines above are PearAI's own, and
the globalStorage folders of real Continue, Cline or Roo Code installed into
PearAI are already claimed by the existing `*/User/globalStorage/...`
nested entries.

## 8. Confidence

High: editor directory names and remote server directory (product.json and
the path resolver); `~/.pearai` layout of the Continue fork; Roo fork
storage, file names and renamed project files; SecretStorage key names.
Medium: that shipped builds use these commits; the app tree pins no
submodule revision, and the extension repositories took commits after the
app's last push. Medium: Linux `~/.config/pearai/User` from the import
flow; it follows from the lowercase path in source but whether a Linux
build renames the product was not checked. Not determined: whether
`console.log` of access tokens in `PearAICredentials`
([`core/pearaiServer/PearAICredentials.ts:18-21`](https://github.com/trypear/pearai-submodule/blob/51eceef62a90c29f712b3a9607ea70a9dca657e9/core/pearaiServer/PearAICredentials.ts#L18-L21))
or `console.dir(data)` at login
([`src/extension.ts:110-111`](https://github.com/trypear/PearAI-Roo-Code/blob/0b6df736c9b2799c38b9ee629668407521a7bdda/src/extension.ts#L110-L111)) reaches a
file under `logs/`; if it does, extension host logs contain live tokens.
