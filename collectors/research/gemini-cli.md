# gemini-cli: on-disk paths

## 1. Source and evidence level

google-gemini/gemini-cli, commit `fb972b2f87fe7d5b06d37eac711490162d98de2c`
(2026-10-02, package version `0.64.0-nightly.20260929`). Open source. Every
claim below is source-level (`packages/...` file:line in that checkout) unless
marked `docs/` (repo documentation) or `live` (names only from this
workstation's `~/.gemini`, which holds just `config/` and `antigravity-cli/`,
so it contributed nothing for Gemini CLI itself).

## 2. Per-user storage

Home resolution: `homedir()` returns `$GEMINI_CLI_HOME` if set, else
`os.homedir()` (`core/src/utils/paths.ts:22-27`). `GEMINI_DIR = '.gemini'`
(`paths.ts:13`). No `win32`/`darwin` branch exists for user paths; the only
platform split is the system settings dir (`/etc/gemini-cli`,
`/Library/Application Support/GeminiCli`, `C:\ProgramData\gemini-cli`,
`core/src/config/storage.ts:174-182`). So the layout is `~/.gemini` on
Linux, macOS and `%USERPROFILE%\.gemini` on Windows. No XDG use.

Runtime dir (`storage.ts:92-108`): `~/.gemini`, except under
`SANDBOX=sandbox-exec` (macOS seatbelt) where it is `~/.cache/.gemini`
(created in `cli/src/utils/sandbox.ts:208`). Runtime-dir files therefore
exist in either location on macOS: `mcp-oauth-tokens.json`,
`a2a-oauth-tokens.json` (`storage.ts:70-76`), `installation_id` (123),
`google_accounts.json` (127), `trustedFolders.json` (131-136, overridable by
`GEMINI_CLI_TRUSTED_FOLDERS_PATH`), `policy_integrity.json` (170), `tmp/`
(195), `projects.json` (289-292), `history/` (320).

Always under `~/.gemini`: `settings.json` (78), `commands/` (138), `skills/`
(142), `policies/` with `auto-saved.toml` (28, 150, 247), `keybindings.json`
(154), `agents/` (158), `acknowledgments/agents.json` (162-168),
`oauth_creds.json` (255), `extensions/` (472-478 with `homedir()` target;
`cli/src/config/extensions/variables.ts:21`), `GEMINI.md`
(`core/src/tools/memoryTool.ts:90-91`), `gemini-credentials.json`
(`core/src/services/fileKeychain.ts:19-20`), `trusted_hooks.json`
(`core/src/hooks/trustedHooks.ts:27-30`), `state.json`
(`cli/src/utils/persistentState.ts:11,35`), `mcp-server-enablement.json`
(`cli/src/config/mcp/mcpServerEnablement.ts:181`), `whisper_models/`
(`core/src/voice/whisperModelManager.ts:39`), `bin/litert/`
(`cli/src/commands/gemma/constants.ts:36`), `cli-browser-profile/`
(`core/src/utils/browserConsent.ts:16`), `.env` (`cli/src/config/settings.ts:585`).
A sibling `~/.agents/skills` is also read (`storage.ts:62-68,146`).

Per-project tree `tmp/<id>/` (`storage.ts:230-234`). `<id>` is now a slug
from `projects.json`: basename lowercased, non-alphanumerics to `-`,
`-N` suffix on collision (`core/src/config/projectRegistry.ts:304-316,
414-420`). The old `<sha256(path)>` dir (`paths.ts:318-319`) is copied, not
removed, on migration (`storage.ts:310-324`,
`storageMigration.ts:45`), so both forms coexist. Contents: `chats/`
`session-<ts>-<id>.jsonl` or `<sessionId>.jsonl`, subagent sessions in a
sub-dir (`core/src/services/chatRecordingService.ts:757-799`); `logs.json`
and `checkpoint-<tag>.json` (`core/src/core/logger.ts:15,149,294`);
`checkpoints/` (364); `logs/session-<id>.jsonl` activity log
(`cli/src/utils/activityLogger.ts:696-699`); `plans/`, `tracker/`, `tasks/`,
optionally under `<sessionId>/` (372-411); `memory/` (336);
`shell_history` (480); `tool-outputs/` (`core/src/utils/fileUtils.ts:799`);
`otel/collector*.log` (`docs/local-development.md:63,113`); `.project_root`
(`projectRegistry.ts:24,382-397`). `tmp/bin/` holds downloaded tools (199-201).

`history/<id>/` is the checkpoint shadow repo: `.git`, `.gitconfig`,
`.gitconfig_system_empty`, `.gitignore` (`core/src/services/gitService.ts:
105-106,138-148,170-188`; `docs/cli/checkpointing.md:15`), plus
`.project_root` (registry base dirs, `storage.ts:293-296`).

`extensions/<name>/`: `gemini-extension.json`,
`.gemini-extension-install.json`, `.env` (`variables.ts:22-24`); git sources
are shallow clones (`cli/src/config/extensions/github.ts:57`).

## 3. Credentials

- `oauth_creds.json`: legacy. On load it is migrated into the keychain and
  deleted (`core/src/code_assist/oauth-credential-storage.ts:16,117-153`).
  Still present on hosts that never ran a new build.
- Keychain is `@github/keytar` (`core/src/services/keychainService.ts:176`,
  `core/package.json:97`), services `gemini-cli-oauth` and
  `gemini-cli-api-key` (`oauth-credential-storage.ts:16`,
  `core/src/core/apiKeyCredentialStorage.ts:12`). Fallback `FileKeychain` →
  `~/.gemini/gemini-credentials.json`, AES-256-GCM, key from
  `hostname-username-gemini-cli` (`fileKeychain.ts:19-26`). Used when
  `GEMINI_FORCE_FILE_STORAGE=true`, under WSL, or when the native module
  fails (`keychainService.ts:22,112-136`). Decryptable offline given hostname
  and username.
- MCP/A2A tokens: `HybridTokenStorage` (keychain, else encrypted file,
  `core/src/mcp/token-storage/hybrid-token-storage.ts:28-41`); the plain
  `mcp-oauth-tokens.json` writer still exists (`core/src/mcp/oauth-token-storage.ts:48,114-117`).
- `google_accounts.json`: active Google account email
  (`core/src/utils/userAccountManager.ts:19`); identity, not a token.
- `.env` search order: `<cwd>/.gemini/.env`, `<cwd>/.env`, `~/.gemini/.env`,
  `~/.env` (`settings.ts:561-590`), carrying `GEMINI_API_KEY`/`GOOGLE_API_KEY`
  (`cli/src/config/auth.ts:22,36`).
- `settings.json` `mcpServers.*.env` and `.headers` embed secrets
  (`cli/src/config/settingsSchema.ts:3053,3071`). Extension `.env` holds
  non-sensitive settings; `sensitive` ones go to keychain
  (`docs/extensions/reference.md:204`).

## 4. Exclude

`.gemini/whisper_models`, `.gemini/bin` (litert models), `.gemini/tmp/bin`,
`.gemini/extensions/*/node_modules`, `.gemini/extensions/*/.git`,
`.gemini/cli-browser-profile` (Chromium profile). `history/*/.git` is a
shadow copy of the project at each checkpoint: large but evidentiary; keep,
rely on the size cap.

## 5. Project-local files

`GEMINI.md` (any configured context name), `.geminiignore`
(`core/src/config/constants.ts:37`), `.gemini/settings.json` (344),
`.gemini/.env` (`settings.ts:570`), `.gemini/commands`, `skills`, `agents`,
`policies` (236-237, 348-362), `.gemini/extensions/gemini-extension.json`
(472-478 on `targetDir`), `.gemini/worktrees/<name>`
(`core/src/services/worktreeService.ts:118,143`), `.gemini/hooks/`,
`.gemini/sandbox.Dockerfile`, `.gemini/sandbox-macos-custom.sb` (docs),
`.agents/skills` (356-358). No per-project database.

## 6. Where the project path is recorded

- `~/.gemini/tmp/<slug>/.project_root` and
  `~/.gemini/history/<slug>/.project_root`: plain absolute path, trimmed
  (`projectRegistry.ts:247-250,382-397`); lowercased on Windows (95-100).
- `~/.gemini/projects.json`: `{"projects": {"<abs path>": "<slug>"}}`
  (`projectRegistry.ts:16-21`).
- `~/.gemini/trustedFolders.json`: keys are folder paths (`storage.ts:131`).
- Chat records carry `projectHash` = sha256(path) only (`chatRecordingService.ts:580,812`); not reversible, but matches legacy `tmp/<sha256>` dirs.

## 7. Catalog review

Current lines, all confirmed:
`gemini-cli|.gemini` (storage.ts:54-60); `gemini-cli|.cache/.gemini`
(storage.ts:97-101, macOS sandbox-exec only); `project|GEMINI.md`,
`project|.gemini`, `project|.geminiignore`; excludes
`.gemini/whisper_models`, `.gemini/bin`, `.gemini/tmp/bin`,
`.gemini/extensions/*/node_modules`; secrets `*.gemini/oauth_creds.json`
(legacy, now auto-deleted), `*.gemini/gemini-credentials.json`,
`*.gemini/mcp-oauth-tokens.json`, `*.gemini/a2a-oauth-tokens.json`,
`*.gemini/.env`, `*.gemini/extensions/*/.env`.

Add:
```
# excluded
.gemini/cli-browser-profile
.gemini/extensions/*/.git
# project (if not already in the shared section)
project|.agents
# discovery sources
.gemini/tmp/*/.project_root        (whole file is the path)
.gemini/history/*/.project_root
.gemini/projects.json              (object keys of "projects")
.gemini/trustedFolders.json        (object keys)
```
Consider flagging `*.gemini/settings.json` secret only if the collector
starts flagging MCP configs generally; `google_accounts.json` should stay
unflagged (account identity, no token).

## 8. Confidence

High: every path in sections 2-6 is read from constants in the cited files.
Medium: `.cache/.gemini` contents (runtime-dir files only exist there if the
user runs the macOS sandbox); `history/*/.git` size. Not determined: whether
a `GEMINI_CLI_HOME` relocation is common in the field; which keychain entry
names appear on macOS Keychain dumps (service names given, account names
not checked); the `tmp/<slug>/<sessionId>/` sub-layout beyond
`plans/tracker/tasks`.
