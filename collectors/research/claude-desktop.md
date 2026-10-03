# claude-desktop

## 1. Source and evidence level

Closed Electron app; no package inspected. Evidence: **official docs** claude.com/docs/third-party/claude-desktop/data-storage ("User identity and local data", fetched 2026-10-03), modelcontextprotocol.io/docs/tools/debugging (log and config paths), code.claude.com/docs/en/iam and /settings (relation to `~/.claude`); **community/forum**: github.com/aaddrick/claude-desktop-debian README (Linux path), github.com/CodeZeno/Claude-Code-Usage-Monitor/issues/105 and github.com/yhm138/ai-quota-tray/pull/6 (token cache keys and encryption), github.com/blind0wl/dms-ai-usage/issues/8 (Linux `~/.config/Claude/config.json` keys, unanswered). No DFIR write-up found for this app.

## 2. Per-user storage

Standard build (docs MCP debugging; data-storage note that 3p "is separate from standard Claude Desktop"):
- macOS `~/Library/Application Support/Claude/` (e.g. `developer_settings.json`, `claude_desktop_config.json`), logs `~/Library/Logs/Claude/` (`mcp*.log`).
- Windows `%APPDATA%\Claude\` with logs in `%APPDATA%\Claude\logs\` (MCP debugging doc).
- Linux: official `.deb` exists (claude-desktop-debian 3.0.0 "repackages that official Linux .deb"); config at `~/.config/Claude/claude_desktop_config.json` (README). This is the XDG config dir, no `~/.local/share` use reported.

Enterprise/3p build (data-storage doc table): macOS `~/Library/Application Support/Claude-3p/` + `~/Library/Logs/Claude-3p/`; Windows `%LOCALAPPDATA%\Claude-3p\` (logs inside; earlier releases used `%APPDATA%\Claude-3p\`, migrated on first launch); Linux `~/.config/Claude-3p/` (logs inside).

Contents of the application-data directory (data-storage doc, documented for 3p; the same layout names appear in standard builds per the issues above):
- `ant-did` device id; `configLibrary/_meta.json`, `<id>.json`.
- `local-agent-mode-sessions/`: Cowork and Chat history, one `local_<uuid>.json` plus a working dir per session, scoped by account and org id; `uploads/`, `outputs/`, `audit.jsonl` (HMAC-chained event log) with `.audit-key`; `.../cowork_account_settings.json`; `.../memory/CLAUDE.md` and `memory/memory/*.md`; `.../spaces/<projectId>/memory/`.
- `claude-code-sessions/`: Code session records (working folder, settings, title, summary); transcripts are in `~/.claude/projects/`.
- `claude-code/`, `claude-code-vm/` (bundled Claude Code binary and VM workspace), `vm_bundles/` (VM bundle and data disk), `cowork_plugins/`, `IndexedDB/`, `Local Storage/`, `Session Storage/`.
- Logs: `main.log`, `cowork_vm_node.log`, `claude.ai-web.log`, `mcp.log`, `mcp-server-<name>.log`.
- User outputs outside the app dir: `~/Claude/` (legacy `~/Documents/Claude/`).
- `claude_desktop_config.json` (MCP servers, may hold `env` API keys), `developer_settings.json`, `config.json` (see 3), Electron `Local State`, `Preferences`, `Cookies`, `Cache/`, `Code Cache/`, `GPUCache/`, `DawnGraphiteCache/`, `DawnWebGPUCache/`, `sentry/` (standard Chromium/Electron layout; names from prior catalog, consistent with the OSCrypt `Local State` dependency reported in issue 105).

## 3. Credentials

- `config.json` in the app-data dir, keys `oauth:tokenCacheV2` (live grant, includes `refreshToken`, `expiresAt`, `scopes`) and legacy `oauth:tokenCache`; value is base64 OSCrypt `v10` + nonce + AES-256-GCM ciphertext, key from `Local State` (DPAPI on Windows) (issue 105, PR 6). Docs: "OAuth tokens ... encrypted with the operating system's secure storage (Keychain on macOS, DPAPI on Windows)". So `config.json` + `Local State` together are the credential; on Linux the Chromium safe-storage key comes from the keyring or the fixed "peanuts" key.
- Transient files (docs): `host-creds-<random-id>.json` (resolved inference bearer token or API key, 0600), `ccd-session-secrets/<session-id>/` (GCP ADC / AWS files), and the same cloud credential files inside each Cowork session working directory. Deleted on quit/session end but recoverable on image.
- `claude_desktop_config.json` `mcpServers.*.env` can embed API keys (MCP debugging doc example). `configLibrary/<id>.json` can hold an API key saved from the configuration window (docs: not encrypted).
- `.audit-key` per session: HMAC key, OS-keychain encrypted.
- `Cookies` (Chromium cookie DB) holds claude.ai session cookies.

## 4. Exclusions

`*/Claude*/Cache`, `Code Cache`, `GPUCache`, `DawnGraphiteCache`, `DawnWebGPUCache`, `*/Claude*/claude-code`, `*/Claude*/claude-code-vm`, `*/Claude*/vm_bundles` (docs: binary, VM workspace, VM bundle and data disk, multi-GB), `*/Claude*/sentry`. Keep `IndexedDB/`, `Local Storage/`, `Session Storage/` (UI state, recent folders). `local-agent-mode-sessions/*/uploads` can be large but is evidence.

## 5. Project-local files

None written by the desktop app itself. Code sessions run Claude Code, which writes the `.claude/`, `CLAUDE.md`, `.mcp.json` set (see claude-code). Cowork sessions mount the working folder into the VM; attached files are hard-linked into `uploads/`.

## 6. Where the project path is recorded

- `claude-code-sessions/` records "each session's working folder" (docs). File names and keys are not documented; treat as JSON to grep for absolute paths.
- `local-agent-mode-sessions/.../local_<uuid>.json` session state; `spaces/<projectId>/` for Cowork projects (docs). Exact key names undocumented.
- `Local Storage/` holds "recent folders" (docs) in LevelDB.

## 7. Catalog review

Current lines:
- `claude-desktop|Library/Application Support/Claude` — confirmed (MCP debugging doc).
- `claude-desktop|Library/Application Support/Claude-3p`, `Library/Logs/Claude`, `Library/Logs/Claude-3p` — confirmed (data-storage, MCP docs).
- `claude-desktop|.config/Claude` — confirmed (claude-desktop-debian README; official Linux .deb). `.config/Claude-3p` confirmed (docs).
- `claude-desktop|AppData/Roaming/Claude` — confirmed (MCP docs `%APPDATA%\Claude`).
- `claude-desktop|AppData/Roaming/Claude-3p` — confirmed as legacy location (docs note); `AppData/Local/Claude-3p` confirmed current.
- exclude `*/Claude*/{Cache,Code Cache,GPUCache,DawnGraphiteCache,DawnWebGPUCache,claude-code,claude-code-vm,vm_bundles,sentry}` — confirmed by docs for the three app dirs; the Electron ones are standard names (medium).
- secret `Library/Application Support/Claude*/config.json`, `.config/Claude*/config.json`, `AppData/Roaming/Claude*/config.json`, `AppData/Local/Claude*/config.json` — confirmed (issue 105, PR 6).
- secret `.../Cookies*` — confirmed as a standard Electron artifact (medium).
- secret `Library/Application Support/Claude*/host-creds-*.json`, `.../ccd-session-secrets/*` — confirmed by docs but only listed for macOS.

Add:
```
secret: .config/Claude*/host-creds-*.json
secret: .config/Claude*/ccd-session-secrets/*
secret: AppData/Roaming/Claude*/host-creds-*.json
secret: AppData/Roaming/Claude*/ccd-session-secrets/*
secret: AppData/Local/Claude*/host-creds-*.json
secret: AppData/Local/Claude*/ccd-session-secrets/*
secret: */Claude*/Local State                     (OSCrypt key needed to decrypt config.json)
secret: */Claude*/claude_desktop_config.json      (MCP env API keys)
secret: */Claude*/local-agent-mode-sessions/*/.audit-key
claude-desktop|Claude                             (~/Claude user outputs: artifacts, scheduled-task results)
claude-desktop|Documents/Claude                   (legacy outputs dir)
```
Glob caution: `*/Claude*/...` must not match `ClaudeCode` system dirs or `.claude`; the existing patterns are anchored on the app-dir names so they are fine.

## 8. Confidence

High: app-dir and log locations per OS (docs), 3p layout and file names (docs), `config.json` token keys and OSCrypt scheme (two independent community reports plus docs statement on secure storage). Medium: that every 3p subdirectory name also appears in the standard build (docs say the two share a layout but document only 3p); Linux decryption key source. Not determined: file and key names inside `claude-code-sessions/`; whether standard builds on Windows have moved to `%LOCALAPPDATA%\Claude` as 3p did; IndexedDB schema.
