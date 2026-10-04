# gemini-cli: on-disk paths

How the transcripts are encoded and how the parser reads them is in
[`analyzer/research/gemini-cli.md`](../../analyzer/research/gemini-cli.md).

## 1. Source and evidence level

google-gemini/gemini-cli, commit [`fb972b2f87fe7d5b06d37eac711490162d98de2c`](https://github.com/google-gemini/gemini-cli/commit/fb972b2f87fe7d5b06d37eac711490162d98de2c)
(2026-10-02, package version `0.64.0-nightly.20260929`). Open source. Every
claim below is source-level (`packages/...` file:line in that checkout) unless
marked `docs/` (repo documentation) or `live` (names only from this
workstation's `~/.gemini`, which holds just `config/` and `antigravity-cli/`,
so it contributed nothing for Gemini CLI itself).

## 2. Per-user storage

Home resolution: `homedir()` returns `$GEMINI_CLI_HOME` if set, else
`os.homedir()` ([`core/src/utils/paths.ts:22-27`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts#L22-L27)). `GEMINI_DIR = '.gemini'`
([`paths.ts:13`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts#L13)). No `win32`/`darwin` branch exists for user paths; the only
platform split is the system settings dir (`/etc/gemini-cli`,
`/Library/Application Support/GeminiCli`, `C:\ProgramData\gemini-cli`,
[`core/src/config/storage.ts:174-182`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L174-L182)). So the layout is `~/.gemini` on
Linux, macOS and `%USERPROFILE%\.gemini` on Windows. No XDG use.

Runtime dir ([`storage.ts:92-108`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L92-L108)): `~/.gemini`, except under
`SANDBOX=sandbox-exec` (macOS seatbelt) where it is `~/.cache/.gemini`
(created in [`cli/src/utils/sandbox.ts:208`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/utils/sandbox.ts#L208)). Runtime-dir files therefore
exist in either location on macOS: `mcp-oauth-tokens.json`,
`a2a-oauth-tokens.json` ([`storage.ts:70-76`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L70-L76)), `installation_id` ([123](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L123)),
`google_accounts.json` ([127](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L127)), `trustedFolders.json` ([131-136](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L131-L136), overridable by
`GEMINI_CLI_TRUSTED_FOLDERS_PATH`), `policy_integrity.json` ([170](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L170)), `tmp/`
([195](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L195)), `projects.json` ([289-292](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L289-L292)), `history/` ([320](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L320)).

Always under `~/.gemini`: `settings.json` ([78](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L78)), `commands/` ([138](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L138)), `skills/`
([142](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L142)), `policies/` with `auto-saved.toml` ([28](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L28), [150](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L150), [247](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L247)), `keybindings.json`
([154](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L154)), `agents/` ([158](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L158)), `acknowledgments/agents.json` ([162-168](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L162-L168)),
`oauth_creds.json` ([255](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L255)), `extensions/` ([472-478](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L472-L478) with `homedir()` target;
[`cli/src/config/extensions/variables.ts:21`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/extensions/variables.ts#L21)), `GEMINI.md`
([`core/src/tools/memoryTool.ts:90-91`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/tools/memoryTool.ts#L90-L91)), `gemini-credentials.json`
([`core/src/services/fileKeychain.ts:19-20`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/fileKeychain.ts#L19-L20)), `trusted_hooks.json`
([`core/src/hooks/trustedHooks.ts:27-30`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/hooks/trustedHooks.ts#L27-L30)), `state.json`
([`cli/src/utils/persistentState.ts:11`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/utils/persistentState.ts#L11),[`35`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/utils/persistentState.ts#L35)), `mcp-server-enablement.json`
([`cli/src/config/mcp/mcpServerEnablement.ts:181`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/mcp/mcpServerEnablement.ts#L181)), `whisper_models/`
([`core/src/voice/whisperModelManager.ts:39`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/voice/whisperModelManager.ts#L39)), `bin/litert/`
([`cli/src/commands/gemma/constants.ts:36`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/commands/gemma/constants.ts#L36)), `cli-browser-profile/`
([`core/src/utils/browserConsent.ts:16`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/browserConsent.ts#L16)), `.env` ([`cli/src/config/settings.ts:585`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/settings.ts#L585)).
A sibling `~/.agents/skills` is also read ([`storage.ts:62-68`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L62-L68),[`146`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L146)).

Per-project tree `tmp/<id>/` ([`storage.ts:230-234`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L230-L234)). `<id>` is now a slug
from `projects.json`: basename lowercased, non-alphanumerics to `-`,
`-N` suffix on collision ([`core/src/config/projectRegistry.ts:304-316`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L304-L316),
[`414-420`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L414-L420)). The old `<sha256(path)>` dir ([`paths.ts:318-319`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts#L318-L319)) is copied, not
removed, on migration ([`storage.ts:310-324`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L310-L324),
[`storageMigration.ts:45`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storageMigration.ts#L45)), so both forms coexist. Contents: `chats/`
`session-<ts>-<id>.jsonl` or `<sessionId>.jsonl`, subagent sessions in a
sub-dir ([`core/src/services/chatRecordingService.ts:757-799`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L757-L799)); `logs.json`
and `checkpoint-<tag>.json` ([`core/src/core/logger.ts:15`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L15),[`149`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L149),[`294`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/logger.ts#L294));
`checkpoints/` ([364](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L364)); `logs/session-<id>.jsonl` activity log
([`cli/src/utils/activityLogger.ts:696-699`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/utils/activityLogger.ts#L696-L699)); `plans/`, `tracker/`, `tasks/`,
optionally under `<sessionId>/` ([372-411](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L372-L411)); `memory/` ([336](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L336));
`shell_history` ([480](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L480)); `tool-outputs/` ([`core/src/utils/fileUtils.ts:799`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/fileUtils.ts#L799));
`otel/collector*.log` ([`docs/local-development.md:63`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/docs/local-development.md#L63),[`113`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/docs/local-development.md#L113)); `.project_root`
([`projectRegistry.ts:24`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L24),[`382-397`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L382-L397)). `tmp/bin/` holds downloaded tools ([199-201](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L199-L201)).

`history/<id>/` is the checkpoint shadow repo: `.git`, `.gitconfig`,
`.gitconfig_system_empty`, `.gitignore` ([`core/src/services/gitService.ts:
105-106`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/gitService.ts#L105-L106),[`138-148`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/gitService.ts#L138-L148),[`170-188`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/gitService.ts#L170-L188); [`docs/cli/checkpointing.md:15`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/docs/cli/checkpointing.md#L15)), plus
`.project_root` (registry base dirs, [`storage.ts:293-296`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L293-L296)).

`extensions/<name>/`: `gemini-extension.json`,
`.gemini-extension-install.json`, `.env` ([`variables.ts:22-24`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/extensions/variables.ts#L22-L24)); git sources
are shallow clones ([`cli/src/config/extensions/github.ts:57`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/extensions/github.ts#L57)).

## 3. Credentials

- `oauth_creds.json`: legacy. On load it is migrated into the keychain and
  deleted ([`core/src/code_assist/oauth-credential-storage.ts:16`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/code_assist/oauth-credential-storage.ts#L16),[`117-153`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/code_assist/oauth-credential-storage.ts#L117-L153)).
  Still present on hosts that never ran a new build.
- Keychain is `@github/keytar` ([`core/src/services/keychainService.ts:176`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/keychainService.ts#L176),
  [`core/package.json:97`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/package.json#L97)), services `gemini-cli-oauth` and
  `gemini-cli-api-key` ([`oauth-credential-storage.ts:16`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/code_assist/oauth-credential-storage.ts#L16),
  [`core/src/core/apiKeyCredentialStorage.ts:12`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/core/apiKeyCredentialStorage.ts#L12)). Fallback `FileKeychain` →
  `~/.gemini/gemini-credentials.json`, AES-256-GCM, key from
  `hostname-username-gemini-cli` ([`fileKeychain.ts:19-26`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/fileKeychain.ts#L19-L26)). Used when
  `GEMINI_FORCE_FILE_STORAGE=true`, under WSL, or when the native module
  fails ([`keychainService.ts:22`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/keychainService.ts#L22),[`112-136`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/keychainService.ts#L112-L136)). Decryptable offline given hostname
  and username.
- MCP/A2A tokens: `HybridTokenStorage` (keychain, else encrypted file,
  [`core/src/mcp/token-storage/hybrid-token-storage.ts:28-41`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/mcp/token-storage/hybrid-token-storage.ts#L28-L41)); the plain
  `mcp-oauth-tokens.json` writer still exists ([`core/src/mcp/oauth-token-storage.ts:48`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/mcp/oauth-token-storage.ts#L48),[`114-117`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/mcp/oauth-token-storage.ts#L114-L117)).
- `google_accounts.json`: active Google account email
  ([`core/src/utils/userAccountManager.ts:19`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/userAccountManager.ts#L19)); identity, not a token.
- `.env` search order: `<cwd>/.gemini/.env`, `<cwd>/.env`, `~/.gemini/.env`,
  `~/.env` ([`settings.ts:561-590`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/settings.ts#L561-L590)), carrying `GEMINI_API_KEY`/`GOOGLE_API_KEY`
  ([`cli/src/config/auth.ts:22`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/auth.ts#L22),[`36`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/auth.ts#L36)).
- `settings.json` `mcpServers.*.env` and `.headers` embed secrets
  ([`cli/src/config/settingsSchema.ts:3053`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/settingsSchema.ts#L3053),[`3071`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/settingsSchema.ts#L3071)). Extension `.env` holds
  non-sensitive settings; `sensitive` ones go to keychain
  ([`docs/extensions/reference.md:204`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/docs/extensions/reference.md#L204)).

## 4. Exclude

`.gemini/whisper_models`, `.gemini/bin` (litert models), `.gemini/tmp/bin`,
`.gemini/extensions/*/node_modules`, `.gemini/extensions/*/.git`,
`.gemini/cli-browser-profile` (Chromium profile). `history/*/.git` is a
shadow copy of the project at each checkpoint: large but evidentiary; keep,
rely on the size cap.

## 5. Project-local files

`GEMINI.md` (any configured context name), `.geminiignore`
([`core/src/config/constants.ts:37`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/constants.ts#L37)), `.gemini/settings.json` ([344](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L344)),
`.gemini/.env` ([`settings.ts:570`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/config/settings.ts#L570)), `.gemini/commands`, `skills`, `agents`,
`policies` ([236-237](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L236-L237), [348-362](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L348-L362)), `.gemini/extensions/gemini-extension.json`
([472-478](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L472-L478) on `targetDir`), `.gemini/worktrees/<name>`
([`core/src/services/worktreeService.ts:118`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/worktreeService.ts#L118),[`143`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/worktreeService.ts#L143)), `.gemini/hooks/`,
`.gemini/sandbox.Dockerfile`, `.gemini/sandbox-macos-custom.sb` (docs),
`.agents/skills` ([356-358](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L356-L358)). No per-project database.

## 6. Where the project path is recorded

- `~/.gemini/tmp/<slug>/.project_root` and
  `~/.gemini/history/<slug>/.project_root`: plain absolute path, trimmed
  ([`projectRegistry.ts:247-250`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L247-L250),[`382-397`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L382-L397)); lowercased on Windows ([95-100](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L95-L100)).
- `~/.gemini/projects.json`: `{"projects": {"<abs path>": "<slug>"}}`
  ([`projectRegistry.ts:16-21`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/projectRegistry.ts#L16-L21)).
- `~/.gemini/trustedFolders.json`: keys are folder paths ([`storage.ts:131`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts#L131)).
- Chat records carry `projectHash` = sha256(path) only ([`chatRecordingService.ts:580`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L580),[`812`](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/services/chatRecordingService.ts#L812)); not reversible, but matches legacy `tmp/<sha256>` dirs.

## 7. Confidence

High: every path in sections 2-6 is read from constants in the cited files.
Medium: `.cache/.gemini` contents (runtime-dir files only exist there if the
user runs the macOS sandbox); `history/*/.git` size. Not determined: whether
a `GEMINI_CLI_HOME` relocation is common in the field; which keychain entry
names appear on macOS Keychain dumps (service names given, account names
not checked); the `tmp/<slug>/<sessionId>/` sub-layout beyond
`plans/tracker/tasks`.
