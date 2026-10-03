# windsurf: Windsurf / Devin Desktop IDE, Codeium plugins and the Devin CLI

## 1. Source and evidence level

Closed source. docs.windsurf.com now 307-redirects to docs.devin.ai (observed on `/windsurf/cascade/mcp` and `/troubleshooting/windsurf-common-issues`).
- L2 official docs: docs.devin.ai `desktop/devin-desktop-faq`, `desktop/cascade/mcp`, `desktop/cascade/memories`, `desktop/cascade/workflows`, `desktop/cascade/hooks`, `desktop/troubleshooting/windsurf-common-issues`, `cli/reference/commands` (credentials.toml wording from search snippet of that page).
- L3 vendor tracker: Exafunction/codeium issue 295 (`.windsurf\extensions` on Windows).
- L4 community source read locally (`scratchpad/npm/community/`): wookat/DevCleaner `conversation.rs`, Cosmos-0118/AgentSweep `rules.toml`, vinzdg/codenotch `DevinCredentials.swift`, jlcodes99/cockpit-tools `windsurf_account.rs`; Exafunction/windsurf.nvim `lua/codeium/api.lua`.

## 2. Per-user storage

IDE user data (FAQ): macOS `~/Library/Application Support/Windsurf/` legacy and `~/Library/Application Support/Devin/` new; Windows `%APPDATA%\Windsurf\` and `%APPDATA%\Devin\`; Linux `~/.config/Windsurf/` and `~/.config/Devin/`. Each holds the VS Code layout (`User/settings.json`, `User/globalStorage/`, `Workspaces/`, `argv.json`, `logs/`, `User/History/`). "Migrate from Windsurf" copies the legacy dir and extensions dir and skips `logs/`, `crashpad/`, `User/History/`, so both trees can exist with different content. Devin Desktop reads both and writes to Devin paths.

Extensions: `~/.windsurf/extensions/` legacy (read-only after migration), `~/.devin/extensions/` new (FAQ; issue 295).

Cascade transcripts for hooks: `~/.windsurf/transcripts/{trajectory_id}.jsonl` (docs cascade/hooks, `transcript_path`). Post-rename `~/.devin/transcripts` is unverified.

Central Codeium dir `~/.codeium/` on every OS (FAQ: "not changing in this release"; Windows `C:\Users\<u>\.codeium\windsurf\cascade` per troubleshooting page):
- `windsurf/cascade/` conversation history as `<uuid>.pb` protobuf files; deleting the dir clears chat history (troubleshooting page; DevCleaner `conversation.rs:1199-1229`). `ItemTable` keys `cascade.chatdata`, `cascade.conversations`, `cascade.*`, `windsurf.cascadeViewContainerId.*` in `state.vscdb` hold view state (DevCleaner `:41-85`).
- `windsurf/memories/` auto memories plus `windsurf/memories/global_rules.md` (docs memories); `windsurf/global_workflows/*.md` (docs workflows); `windsurf/skills/`; `windsurf/hooks.json` (IDE) and `hooks.json` (JetBrains plugin) (docs hooks); `windsurf/mcp_config.json` and `mcp_config.json`, `user_settings.pb`, `windsurf/user_settings.pb`, `installation_id` (FAQ; AgentSweep 1107-1113).
- `windsurf/database/`, `database/` "local Cascade/Windsurf database", `windsurf/code_tracker/`, `windsurf/codemaps/`, `brain/`, `recipes/`, `context_state/`, `windsurf/implicit/`, `implicit/`, `windsurf/native_storage_migrations.lock`, `ws-browser/`, `ws-browser-profile/` (AgentSweep 1078-1149, labels only).
- `windsurf/bin/` language-server and CLI binaries (FAQ); `~/.local/bin/devin` (macOS/Linux), `%LOCALAPPDATA%\devin\bin\` (Windows).
- Plugins (JetBrains, Eclipse, nvim) share `~/.codeium/`: `codeium.log` (plugin logs search snippet), language server under a configured manager dir (windsurf.nvim `api.lua:147-167`).

Devin CLI / local agent: `~/.config/devin/mcp_config.json` (`$XDG_CONFIG_HOME/devin/`), `%APPDATA%\devin\mcp_config.json` (docs cascade/mcp); `~/.local/share/devin/credentials.toml` (`$XDG_DATA_HOME/devin/`), `%APPDATA%\devin\credentials.toml` (cli/reference/commands; codenotch `:23-26`). Its session store was not found in docs.

System-level, outside home: `/Library/Application Support/{Devin,Windsurf}/{rules,workflows,skills,hooks.json}`, `/etc/{devin,windsurf}/...`, `C:\ProgramData\{Devin,Windsurf}\...` (docs memories, workflows, hooks).

Env: `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `WINDSURF_API_KEY` (docs).

## 3. Credentials

- IDE: `User/globalStorage/state.vscdb` `ItemTable` key `windsurfAuthStatus` with JSON `apiKey`, `email` (codenotch `:16-20, 73-83`; cockpit-tools `:1133-1148`); multi-account keys `codeium.windsurf-windsurf_auth` and `windsurf_auth-%` (cockpit-tools `:1167-1185`). Same file as chat view state: collect unflagged, redact by key.
- `~/.codeium/config.json` `{"api_key": ...}` written by the nvim/emacs plugins (windsurf.nvim `api.lua:60-90`, config_path default).
- Devin CLI `credentials.toml` field `windsurf_api_key`, persistent and non-expiring (docs; codenotch `:86-96`).
- `mcp_config.json` files (all three locations) embed server env and support `${file:~/.secrets/...}` indirection (docs cascade/mcp).

## 4. Exclusions

`.codeium/windsurf/bin`, `.codeium/bin`, `.codeium/*/bin` (binaries, FAQ), `.codeium/ws-browser`, `.codeium/ws-browser-profile` (embedded Chromium, AgentSweep 1078-1085), `.codeium/windsurf/implicit` and `.codeium/implicit` (prior finding: multi-GB embedding cache; AgentSweep lists them unclassified), `.windsurf/extensions`, `.devin/extensions`, `AppData/Local/devin/bin`. Keep `database`, `code_tracker`, `codemaps`, `brain`, `memories`, `cascade`.

## 5. Project-local files

`.devin/rules/*.md` preferred, `.windsurf/rules/*.md` fallback, legacy `.windsurfrules`; `.devin/workflows/*.md`, `.windsurf/workflows/*.md`; `.devin/skills/`, `.windsurf/skills/`; `.devin/plans/`, `.windsurf/plans/`; `.devin/hooks.json`, `.windsurf/hooks.json`, `.devin/hooks.v1.json`; ignore files `.devinignore`, `.windsurfignore`, `.codeiumignore` (FAQ workspace table; docs memories, workflows, hooks; cli commands). No per-project database.

## 6. Project path

Not determinable from available evidence. Memories are "associated with the workspace they were created in" (docs memories) but the key is inside the files; `cascade/*.pb` is protobuf without a published schema; `~/.windsurf/transcripts/*.jsonl` content fields are not documented beyond `type`/`status`. Fall back to `User/workspaceStorage/*/workspace.json` in the Windsurf and Devin data dirs.

## 7. Catalog review

- `windsurf|.codeium` confirmed. `windsurf|.windsurf/extensions/extensions.json` confirmed (FAQ, issue 295). `windsurf|.config/devin`, `AppData/Roaming/devin` confirmed (docs mcp; cli credentials). `Windsurf/User` and `Devin/User` on three platforms confirmed (FAQ).
- `project|.windsurf`, `.windsurfrules`, `.devin` confirmed.
- Excludes `.codeium/windsurf/implicit` doubtful-but-reasonable (L4 label only), `.codeium/*/bin`, `.codeium/bin`, `.windsurf/extensions` confirmed.
- Secret `.codeium/config.json` confirmed.
- Missing: `~/.windsurf/transcripts` (Cascade transcripts, the single most valuable new source), `~/.devin`, Devin CLI data dir, IDE `logs`.

Add:
```
windsurf|.windsurf
windsurf|.devin
windsurf|.local/share/devin
windsurf|Library/Application Support/Windsurf/logs
windsurf|.config/Windsurf/logs
windsurf|AppData/Roaming/Windsurf/logs
windsurf|Library/Application Support/Devin/logs
windsurf|.config/Devin/logs
windsurf|AppData/Roaming/Devin/logs
windsurf|.windsurf-server/data/User
windsurf|.devin-server/data/User
```
and drop `windsurf|.windsurf/extensions/extensions.json` in favour of `.windsurf` plus the exclusion. Project: `project|.devinignore`, `project|.windsurfignore`, `project|.codeiumignore`. Excludes: `.devin/extensions`, `.codeium/ws-browser`, `.codeium/ws-browser-profile`, `.codeium/implicit`, `AppData/Local/devin/bin`. Secrets: `.local/share/devin/credentials.toml`, `AppData/Roaming/devin/credentials.toml`, `.codeium/mcp_config.json`, `.codeium/windsurf/mcp_config.json`, `.config/devin/mcp_config.json`, `AppData/Roaming/devin/mcp_config.json`.

## 8. Confidence

High: IDE data dirs old and new, extensions dirs, `~/.codeium/windsurf/{cascade,memories,global_workflows,mcp_config.json,hooks.json,bin}`, `windsurfAuthStatus`, `credentials.toml`, project directories (all L2 or two independent L4 sources). Medium: `.pb` naming (one L4 tool), `~/.windsurf/transcripts` existence post-rename, `implicit` size, `database`/`code_tracker`/`codemaps` content. Not determined: Devin CLI session/log directory, `.pb` schema, whether `~/.devin/transcripts` replaces `~/.windsurf/transcripts`, `windsurf-next` beta paths, Windows `%LOCALAPPDATA%` use beyond `devin\bin`.
