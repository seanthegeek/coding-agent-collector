# claude-code

How the transcripts are encoded and how the parser reads them is in
[`analyzer/research/claude-code.md`](../../analyzer/research/claude-code.md).

## 1. Source and evidence level

Closed source. Evidence is the shipped package: `npm pack @anthropic-ai/claude-code` gives 2.1.288, a 28 KB shim whose `package.json` lists `optionalDependencies` on eight platform packages (`scratchpad/npm/cc/package/package.json`). `npm pack @anthropic-ai/claude-code-linux-x64@2.1.288` gives a single 245 MB Bun-compiled binary `claude`; `strings -n 6` of it is `scratchpad/npm/cc.strings` and every "cc:NNN" below is a line in that file. Official docs: code.claude.com/docs/en/settings, /iam, /managed-settings; claude.com/docs/third-party/claude-desktop/data-storage. Layout confirmed names-only against `~/.claude` on this host (2.1.288 native install). Evidence level per claim: **bundle** unless marked **docs** or **local**.

## 2. Per-user storage

Config home = `process.env.CLAUDE_CONFIG_DIR ?? join(homedir(), ".claude")`, NFC-normalised (cc:472945 `o()??u(R(),".claude")`, cc:497291). Same on Linux, macOS and Windows (`%USERPROFILE%\.claude`, docs settings page). No XDG or Library/AppData paths for user state. `CLAUDE_CONFIG_DIR` relocates everything including `.credentials.json` and the keychain entry name (docs /iam "Credential management"); separate account dirs such as `~/.claude-work` are documented practice (docs /iam "multiple accounts").

Known top-level directories inside the config home, from the literal set at cc:482244: `agent-memory`, `agent-memory-local`, `agent-memory-project`, `api-dumps`, `backups`, `cache`, `chrome`, `cowork_plugins`, `daemon`, `debug`, `downloads`, `dump-prompts`, `feedback`, `feedback-bundles`, `file-history`, `file-transfers`, `ide`, `image-cache`, `jobs`, `local`, `local-settings`, `logs`, `mcp-discovery-cache`, `mcp-skill-archives`, `paste-cache`, `plans`, `plugins`, `project-settings`, `projects`, `remote`, `scratch`, `seed-admin`, `session-env`, `sessions`, `shares`, `shell-snapshots`, `startup-perf`, `state`, `statsig`, `storage-v2`, `systemd`, `tasks`, `teams`, `telemetry`, `todos`, `traces`, `uploads`, `usage-data`. User-config subdirs also include `commands`, `agents`, `output-styles`, `skills`, `workflows`, `routines`, `themes`, `rules` (cc:473782). Known top-level files (cc:483303): `.claude.json`, `.claude.json.backup`, `.credentials.json`, `history.jsonl`, `.session_ingress_token`, `policy-limits.json`, `remote-settings.json`, `hfi-auth.json`, `stats-cache.json`, `mcp-needs-auth-cache.json`, `gh-pr-status-cache.json`, `antproto.json`, `active-time.json`, `loop.md`, `server-sessions.json`, `computer-use.lock`, `server.lock`; plus `settings.json`, `settings.local.json` (cc:436317-8), `.device-keys.json` and `.config.json` (cc:477075).

What holds evidence:

- `projects/<key>/<sessionId>.jsonl`: transcripts. `<key>` = cwd with `[^a-zA-Z0-9]` → `-`, truncated to 200 chars plus a base-36 hash (cc:473017, cc:473728). Subagent transcripts: `projects/<key>/<sessionId>/subagents/agent-<id>.jsonl` (cc:476679). Per-project memory: `projects/<key>/memory/*.md` (cc:489631). Local shows `-home-sean-dev-...` dirs holding `<uuid>.jsonl`, `<uuid>/`, `memory/`.
- `history.jsonl`: prompt history, with retention pruning (cc:338013-15, 478233).
- `debug/<sessionId>.txt`: per-session debug logs (cc:472977); `debug/latest` symlink (local).
- `file-history/<sessionId>/`: pre-edit file backups (cc:482923); `session-env/<sessionId>/` (cc:480109); `shell-snapshots/snapshot-<shell>-<epoch>-<rand>.sh` (shell function dumps, cc:480528 region, local name confirms); `todos/`, `tasks/<sessionId>/`, `plans/*.md` (cc:476220), `teams/`, `jobs/<id>/parent-transcript.jsonl` (cc "jobs" ctx), `dump-prompts/*.jsonl` (full outgoing prompts, cc "dump-prompts" ctx), `api-dumps`, `traces/*.json`, `usage-data/{facets,session-meta}/*.json` and `report-*.html` (cc:492127), `feedback-bundles/*.zip`, `shares/*.zip`, `uploads/<sessionId>/`, `ide/<port>.lock` (local `13502.lock`; Windows/WSL also probes `%USERPROFILE%\.claude\ide`, cc "ide" ctx), `backups/` (`.claude.json` snapshots; docs: `~/.claude/backups/.claude.json.corrupted.<ts>`).
- `.claude.json` sits in `$HOME` (variants `.claude${suffix}.json`, cc:477075); docs: "holds your sign-in session, MCP server configurations, per-project state such as trust decisions, and the global config keys" (settings page). Its `projects` object is keyed by project path (cc:474276 `e.projects`).
- `plugins/`: `installed_plugins.json`, `known_marketplaces.json`, `marketplaces/<name>/` git clones, `cache/` zip cache (cc plugins ctx); local also `blocklist.json`, `plugin-directory-cache-v2.json`, `synced/`.
- `statsig/` feature-flag cache, `cache/gateway-models.json`, `cache/model-capabilities.json`, `telemetry/`, `telemetry/runs/`, `chrome/chrome-native-host[.bat]`, `local/` (npm-local install), `remote/` (cloud sessions: `/home/claude/.claude/remote/.oauth_token`, `.api_key`, `.session_ingress_token`, cc `.session_ingress_token` ctx).
- Native installer binaries: `$XDG_DATA_HOME/claude/versions/<ver>` (default `~/.local/share/claude/versions`) and symlink `~/.local/bin/claude` (cc "versions" ctx `o(wje(e),"claude","versions")`, `o(n,".local","bin")`; local confirms three ~245 MB versions). Windows: `winget Anthropic.ClaudeCode` (cc:296086).
- System-wide managed policy (outside home): `/Library/Application Support/ClaudeCode/`, `/etc/claude-code/`, `C:\Program Files\ClaudeCode\` holding `managed-settings.json`, `managed-settings.d/`, `managed-mcp.json` (cc:412717-9; docs /managed-settings). MDM plist domain `com.anthropic.claudecode`; registry `HKLM|HKCU\SOFTWARE\Policies\ClaudeCode\Settings` (docs).

## 3. Credentials

- macOS: Keychain generic password, account = OS user, service = `"Claude Code"` + `"-credentials"` (keyed to the config dir when non-default), read with `security find-generic-password -a <user> -w -s <service>` (cc:473906, cc:494949, `HAn="-credentials"` chunk near cc:473906). Fallback and Linux/Windows: `<config>/.credentials.json` mode 0600 (docs /iam). Local file present.
- `~/.claude/.device-keys.json` (device key store, file fallback to keychain, cc:477075, cc:337890-900).
- `.claude.json` holds the sign-in session / `oauthAccount` and MCP server `env` blocks (docs; cc:406053 "refusing to write to avoid wiping ~/.claude.json" auth).
- `hfi-auth.json`, `.session_ingress_token`, `remote/.oauth_token`, `remote/.api_key` (cloud/host handoff), `CLAUDE_CODE_HOST_CREDS_FILE` path (cc:272494, 276584 region), Claude Desktop `host-creds-*.json` (see claude-desktop).
- Config files that can embed keys: `settings.json` / `settings.local.json` (`apiKeyHelper`, `env.ANTHROPIC_API_KEY`, MCP headers), `.mcp.json`, `managed-mcp.json`. Env: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` (docs /iam precedence list). Anthropic profiles live outside: `~/.config/anthropic` / `%APPDATA%\Anthropic` (docs /iam).

## 4. Exclusions (relative to home)

`.claude/plugins/marketplaces` (git clones), `.claude/plugins/cache`, `.claude/plugins/*/node_modules`, `.claude/local/node_modules`, `.claude/image-cache`, `.claude/paste-cache`, `.claude/chrome`, `.claude/cache`, `.claude/statsig` (flag cache, optional), `.local/share/claude/versions` (~245 MB per version). Project-side: `*/.claude/worktrees`, `*/.claude/checkpoints` (gitignore template cc "claude-code-runtime"). `downloads/`, `uploads/`, `file-transfers/` may be large but are user content; cap by size rather than exclude.

## 5. Project-local files

`.claude/settings.json`, `.claude/settings.local.json`, `.claude/{skills,commands,agents,hooks,rules}/` (cc "agents"/"settings.json" ctx), `.mcp.json` (cc:273219), `CLAUDE.md`, `CLAUDE.local.md` (cc:19360, 299964), `.claude/scheduled_tasks.json`, `.claude/scheduled_tasks.lock`, `.claude/routines/.state/`, `.claude/worktrees/`, `.claude/checkpoints/`, `.claude/mailbox/`, `.claude/agent-registry.json`, `.claude/agent-memory-local`, `.claude/first-run`, `.claude/assistant-daemon-state.json` (gitignore template, cc "claude-code-runtime" ctx). No per-project database.

## 6. Where the project path is recorded

- `~/.claude.json` → `projects` object, keys are absolute cwd paths (cc:474276; docs "per-project state such as trust decisions").
- Transcript records: `projects/<key>/<id>.jsonl` lines carry `"cwd"`, `"sessionId"`, `"parentUuid"`, `"isSidechain"`, `"timestamp"`, `"type"` (cc:482870 parser, key counts in cc.strings). The dir key is lossy (dashes), so read `cwd` from the first record.
- Claude Desktop `claude-code-sessions/` records each Code session's working folder (docs data-storage) and points back to `~/.claude/projects/`.

## 7. Confidence

High: config-dir resolution, directory and file name sets, projects key scheme, transcript naming, keychain service construction, `.credentials.json`, managed paths, native installer paths (all from bundle literals plus docs, layout confirmed locally). Medium: exact keychain service string (built from `"Claude Code"` + `"-credentials"`; not seen as one literal), contents of `storage-v2`, `seed-admin`, `remote`, `systemd`, `daemon` (names only). Not determined: whether `.claude.json` suffix variants (`.claude<suffix>.json`) appear on normal installs; Windows-only paths beyond `%USERPROFILE%\.claude` (none found); size of `dump-prompts` in practice.
