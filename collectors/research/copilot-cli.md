# copilot-cli

## 1. Source and evidence level

Closed source (`github/copilot-cli` repo is issues only). Evidence is the **shipped bundle**: `npm pack @github/copilot` 1.0.91 (5 KB loader, `buildMetadata.gitCommit 216810c5`) → `npm pack @github/copilot-linux-x64@1.0.91`, a 178 MB Node single-executable (`copilot`). Its SEA blob (magic 0x143da20 at 0x67a01b8) holds `sea-loader.js` (122 KB, `scratchpad/npm/cp-sea-loader.js`) and one asset `copilot.tgz` (69.7 MB, `scratchpad/npm/cp-asset-copilot.tgz`), extracted to `scratchpad/npm/cp-pkg/package/`: `app.js` (7.6 MB JS), `prebuilds/linux-x64/cli-native.node` (8 MB) and `runtime.node` (122 MB, Rust). Citations: "app.js" with the surrounding identifiers, "sea-loader" (same code appears in cc-loader), "native"/"runtime" for byte-string hits. **Docs**: docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference. **Local**: names-only listing of `~/.copilot` and `~/.cache/copilot`.

## 2. Per-user storage

Config home: `configDir ?? process.env.COPILOT_HOME ?? join(homedir(), ".copilot")` (app.js `function dot(e)`, `dQe`; native: "Set the configuration directory (default: ~/.copilot). Deprecated: use COPILOT_HOME env var instead"). Same on all OSes; docs confirm `~/.copilot` and `COPILOT_HOME`.

XDG handling: on start the CLI *migrates* state out of XDG dirs into `~/.copilot` (app.js `function CEn(e,t)`): from `$XDG_STATE_HOME/.copilot/` the entries `session-state`, `session-store.db`, `command-history-state`, `command-history-state.json`, `installed-plugins`; from `$XDG_CONFIG_HOME/.copilot/` the entries `config.json`, `config`, `mcp-config`, `lsp-config`, `permissions-config`, `copilot-instructions.md`, `mcp-oauth-config`, `hooks`. So older installs with XDG set may still have `$XDG_STATE_HOME/.copilot` and `$XDG_CONFIG_HOME/.copilot` (default `~/.local/state/.copilot`, `~/.config/.copilot`), and symlinks are left behind (`symlinkSync` in the same function).

Inside `~/.copilot` (docs table plus bundle):
- `session-state/<sessionId>/` session history: `events.jsonl` (runtime: "Computes the absolute path to a session's persisted events.jsonl file"; app.js crash report copies `e.sessionFilePath` as `events.jsonl`), `workspace.yaml` (app.js `loadSessionFsWorkspace`, keys `id`, `created_at`, `updated_at`, `name`, `user_named`, `summary_count`; `workspaceLoadPersistedSessionCwd` reads cwd from it), `plan.md`, `autopilot-objective.json` (app.js `copySessionFsOptionalFile`), checkpoints and files subdirs (`/session checkpoints|files|plan` commands).
- `session-store.db` SQLite "cross-session data such as checkpoint indexing and search" (docs; runtime SQL `FROM checkpoints ... session_id, checkpoint_number`).
- `logs/` process logs (native: "Set log file directory (default: ~/.copilot/logs/)"); local `logs/process-<epoch>-<pid>.log`. `ide/<uuid>.lock` IDE discovery lock files (app.js `QB` scans `Gi(e,"state")/ide` for `.lock`; local `ide/`). `state/` for the session store default path (app.js `sessionStoreDefaultPath(Gi(e,"state"))`).
- `config.json` "automatically managed application state (authentication, installed plugins...)" (docs), `settings.json` user settings (docs; runtime "Settings migration ... between config.json and settings.json"), `mcp-config.json` (native help text), `mcp-oauth-config` (app.js `JDn="mcp-oauth-config"`), `permissions-config.json`, `lsp-config`, `command-history-state/`, `installed-plugins/<marketplace>/<plugin>` (docs; runtime "installed-plugins root"), `copilot-instructions.md`, `instructions/*.instructions.md`, `agents/*.agent.md`, `skills/<name>/SKILL.md`, `hooks/` (docs; app.js help list `$HOME/.copilot/copilot-instructions.md`, `$HOME/.copilot/instructions/**/*.instructions.md`).
- Package cache for auto-update (sea-loader `Xi()`): `$COPILOT_PKG_CACHE_HOME/pkg`, `$COPILOT_CACHE_HOME/pkg`, `~/Library/Caches/copilot/pkg` (macOS), `%LOCALAPPDATA%\copilot\pkg` (Windows), `$XDG_CACHE_HOME/copilot/pkg` or `~/.cache/copilot/pkg` (Linux), `$COPILOT_HOME/pkg`, `~/.copilot/pkg`; extraction marker `.extraction-complete`. Local `~/.cache/copilot/copilot-user-cache.json` (runtime literal `copilot-user-cache`).
- System policy: `/etc/github-copilot/managed-settings.json`, `/etc/github-copilot/policy.d` (runtime).

## 3. Credentials

- GitHub token: OS keyring by default (runtime vendors `keyring-core` and `zbus-secret-service-keyring-store`; env `COPILOT_DISABLE_KEYTAR`), with `storeTokenPlaintext` setting "Store auth token in plaintext (less secure)" (runtime settings schema) which puts it in `config.json` ("authentication" per docs). Treat `config.json` as a secret.
- Env precedence `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`; falls back to `gh auth token` (app.js `Lgo`, runtime "`gh auth token` stdout collection"), so `~/.config/gh/hosts.yml` is a related credential.
- `mcp-oauth-config` MCP OAuth store (`copilot-mcp-oauth-store-key-v1`); `mcp-config.json` can embed headers/tokens; `settings.json` `sandbox.userPolicy.network.proxy.password`.
- The CLI does not use `~/.config/github-copilot/{hosts,apps}.json` (no hit in app.js, native or runtime).

## 4. Exclusions

`.copilot/pkg`, `.cache/copilot/pkg`, `Library/Caches/copilot/pkg`, `AppData/Local/copilot/pkg` (extracted ~180 MB packages per version), `.copilot/installed-plugins` (marketplace copies; keep manifests if desired). Keep `logs/`, `session-state/`, `session-store.db`.

## 5. Project-local files

`.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.github/git-commit-instructions.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/rules/**/*.md` (read; app.js help list), `.github/copilot/settings.json`, `.github/copilot/settings.local.json` (app.js `LO`), `.mcp.json`, `.github/mcp.json` (native help), `.github/lsp.json`, `.github/hooks/`, `.github/skills/`, `.github/agents/` (app.js). No per-project database.

## 6. Where the project path is recorded

`session-state/<id>/workspace.yaml` persisted session cwd (app.js `workspaceLoadPersistedSessionCwd(FP(Wp(e,t),"workspace.yaml"))`); key name not visible in the JS (handled natively), grep for an absolute path. `permissions-config.json` is "organized by project location" (docs). `session-store.db` rows carry `session_id` and checkpoints (v2).

## 7. Catalog review

Current lines:
- `copilot-cli|.copilot` — confirmed.
- `project|.github/copilot-instructions.md` — confirmed.
- No exclusions or secrets exist for copilot-cli.

Add:
```
copilot-cli|.config/.copilot                 (pre-migration XDG config)
copilot-cli|.local/state/.copilot            (pre-migration XDG state)
copilot-cli|.cache/copilot                   (copilot-user-cache.json; pkg excluded)
copilot-cli|Library/Caches/copilot
copilot-cli|AppData/Local/copilot
exclude: .copilot/pkg
exclude: .cache/copilot/pkg
exclude: Library/Caches/copilot/pkg
exclude: AppData/Local/copilot/pkg
exclude: .copilot/installed-plugins
secret: .copilot/config.json
secret: .copilot/mcp-oauth-config*
secret: .copilot/mcp-config.json
project|.github/copilot
project|.github/instructions
project|.github/mcp.json
project|.github/hooks
project|.github/skills
project|.github/agents
project|.github/lsp.json
```

## 8. Confidence

High: config home and `COPILOT_HOME`, directory names (docs plus bundle), XDG migration list, pkg cache locations, log dir, keyring/plaintext token model. Medium: exact `session-state/<id>/` file set (`events.jsonl`, `workspace.yaml`, `plan.md` seen in code; `checkpoints`/`files` inferred from commands); `state/ide` vs `ide/` (local shows `ide/` at top level, code joins through a "state" resolver). Not determined: `workspace.yaml` key for cwd; `session-store.db` schema beyond `checkpoints(session_id, checkpoint_number)`; `config.json` token field name.
