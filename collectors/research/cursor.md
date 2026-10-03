# cursor: Cursor IDE and Cursor Agent CLI

## 1. Source and evidence level

Closed source. Evidence, strongest first:
- L1 shipped bundle: Cursor Agent CLI `2026.10.01-e373342`, `agent-cli-package.tar.gz` from `downloads.cursor.com/lab/.../linux/x64/` (URL from `https://cursor.com/install`, saved as `scratchpad/npm/cursor-install.sh:78-131`), extracted to `scratchpad/npm/cursor-agent/dist-package/`. Minified webpack chunks keep module names, so citations are `<chunk>.js` plus the original module path.
- L2 official docs: cursor.com/docs `cli/reference/configuration`, `context/rules`, `context/mcp`, `agent/hooks`, `context/ignore-files`.
- L3 forum.cursor.com threads 2825, 167641, 169582, 172127.
- L4 write-ups and tools: Callum-Ward/cursaves `docs/how-cursor-stores-chats.md`, extracurricular.ai (2026-09-09), getagentseal/codeburn issue 986, Cosmos-0118/AgentSweep `rules/rules.toml`, ShayGus/quota PR 20.
- The npm packages `cursor-agent` and `cursor-cli` are unrelated third-party projects (`npm view`), not Cursor's CLI.

## 2. Per-user storage

IDE (VS Code fork, see vscode.md for the generic layout): `~/Library/Application Support/Cursor/User`, `%APPDATA%\Cursor\User`, `~/.config/Cursor/User` (forum 2825, 169582; cursaves; extracurricular). Chats and agent runs live in `User/globalStorage/state.vscdb` table `cursorDiskKV` (`composerData:<id>`, `bubbleId:<composer>:<bubble>`, `checkpointId:*`, `messageRequestContext:*`, `composer.content.<hash>`, `agentKv:blob:*`) and `ItemTable` (`composer.composerData` on <=2.6, `composer.composerHeaders` on 3.0+, legacy `workbench.panel.aichat.view.aichat.chatdata`, `aiService.prompts`) (cursaves; forum 2825, 167641). The file is never vacuumed and reaches 30-125 GB (forum 167641, 169582, 172127); `state.vscdb.backup` sits beside it. `User/workspaceStorage/<md5>/workspace.json` and `state.vscdb` as in VS Code.

CLI data root `~/.cursor` (`CURSOR_DATA_DIR` override; `index.js` module `../cursor-config/dist/paths.js`, function `c`). Config root for `cli-config.json` is `CURSOR_CONFIG_DIR`, else `$XDG_CONFIG_HOME/cursor`, else `~/.cursor` (same module, function `a`; docs cli/reference/configuration). Contents found in the bundle:
- `projects/<sanitized cwd>/` where the name is the path with every non-alphanumeric run replaced by `-` (`../utils/dist/workspace-paths.js` function `s`; `paths.js` function `d` truncates to 84 chars plus a 7-hex sha256 suffix, falling back to `/tmp/.cursor` when the home path is too long). Inside: `agent-transcripts/` (`*.jsonl`, older `*.txt`), `terminals/` (terminal captures), `agent-tools/` (tool outputs over 51,380,224 bytes), `agent-notes/shared` and `agent-notes/<agent>`, `mcps/`, `mcp-auth.json`, `mcp-approvals.json`, `mcp-cache.json`, `.workspace-trusted` (`index.js` ignore list `!projects/*/...`; `./src/mcp/project-paths.ts`; `./src/workspace/approval.tsx`).
- `chats/<md5(resolved cwd)>/<sessionId>/store.db` plus `meta.json` (`7000.index.js` `./src/state/index.ts` functions `a`,`i`; `./src/state/chat-session-meta.ts` schema v1 with `createdAtMs`, `updatedAtMs`, `cwd`, `hasConversation`, `isSubagent`). `store.db` tables `meta(key,value)` and `blobs(id,data)` (codeburn 986).
- `acp-sessions/<id>/store.db` and `meta.json` (`6136.index.js`).
- `worktrees/<repo>/<name>` (`CURSOR_WORKTREES_ROOT`; `index.js` `./src/project/worktree.ts`), `plans/` (`1623.index.js`), `commands/`, `skills/`, `skills-cursor/`, `cloud-skills/`, `plugins/{local,marketplaces,local-marketplaces.json}` (`index.js` `../cursor-plugins/dist/index.js`), `sandbox-policies/` (`CURSOR_SANDBOX_POLICY_DIR`), `ide_state.json` (recently viewed files), `hooks.json`, `hooks/`, `managed/active-team-hooks/hooks.json` (`190.index.js`), `mcp.json` (docs), `ai-tracking/ai-code-tracking.db` (`2734.index.js`), `extensions/` and `argv.json` (dataFolderName convention; AgentSweep 859-872).
- Enterprise hooks: `/Library/Application Support/Cursor/hooks.json`, `/etc/cursor/hooks.json`, `C:\ProgramData\Cursor\hooks.json` (`190.index.js`; docs agent/hooks).
- CLI binaries: `~/.local/share/cursor-agent/versions/<ver>/`, symlinks `~/.local/bin/{agent,cursor-agent,cursor}` (`cursor-install.sh:78-131`; `2761.index.js`). Worker mode uses `/opt/cursor` or `~/.local/share/cursor-agent` as `--data-dir`.
- Remote SSH server `~/.cursor-server/` (serverDataFolderName convention; `2721.index.js` mentions downloading `cursor-server`).
Layout is identical on all OSes except the IDE app-data parent and the CLI `auth.json` location below.

## 3. Credentials

- IDE: `User/globalStorage/state.vscdb` `ItemTable` keys `cursorAuth/accessToken`, `cursorAuth/refreshToken` (JWTs), plus user id (ShayGus/quota PR 20, L4). Same file as the chats, so collect unflagged and redact by key.
- CLI (`index.js` `../cli-credentials/dist/index.js`, factory `d`): macOS uses the login keychain via `/usr/bin/security` (services `cursor-access-token`, `cursor-refresh-token`, `cursor-api-key`, `cursor-bedrock-*`, account `cursor-user`); every other OS, and macOS with `AGENT_CLI_CREDENTIAL_STORE=file`, writes `auth.json` (`accessToken`, `refreshToken`, `apiKey`, `bedrockCredentials`) at `$XDG_CONFIG_HOME/cursor/auth.json` or `~/.config/cursor/auth.json` on Linux, `~/.cursor/auth.json` on macOS, `%APPDATA%\Cursor\auth.json` on Windows (mode 0600).
- MCP OAuth tokens per project: `~/.cursor/projects/<p>/mcp-auth.json` (`6136.index.js`, `8192.index.js`).
- `~/.cursor/mcp.json` and project `.cursor/mcp.json` carry server env blocks that often hold literal keys (docs recommend `${env:...}`).
- `~/.cursor_info` "holds a Cursor authentication token" (AgentSweep 904-910, L4 only, unverified).

## 4. Exclusions

`.cursor/extensions` (extension payloads), `.cursor/worktrees` (git checkouts), `.cursor/plugins/marketplaces` (cloned marketplaces), `*/Cursor/User/globalStorage/state.vscdb.backup` (stale copy, up to 12 GB per forum 167641), `.cursor-server/bin` and `.cursor-server/extensions` if the server dir is added. `~/.local/share/cursor-agent` (557 MB per version) is not in the catalog. `projects/*/agent-tools` holds only outputs over 49 MB; leave it to the size cap rather than exclude.

## 5. Project-local files

`.cursor/rules/**/*.mdc`, `.cursorrules`, `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` (`index.js` `LocalCursorRulesService`; docs context/rules), `.cursor/mcp.json`, `.cursor/hooks.json`, `.cursor/hooks/`, `.cursor/cli.json`, `.cursor/worktrees.json`, `.cursor/commands/`, `.cursor/skills/`, `.cursor/skills-cursor/`, `.cursor/*.json` generally, `.cursorignore` (docs; bundle). `.cursorindexingignore` appears in neither the bundle nor current docs. `.cursor-plugin/marketplace.json` marks a plugin marketplace repo (docs). No per-project database.

## 6. Project path

- `~/.cursor/chats/*/*/meta.json` key `cwd` (bundle `chat-session-meta.ts`); `~/.cursor/acp-sessions/*/meta.json` likewise.
- `~/.cursor/projects/<name>` is the sanitized cwd (lossy: `/home/u/a-b` and `/home/u/a_b` collide).
- IDE: `User/workspaceStorage/<id>/workspace.json` `folder`; `composerData` JSON has no reliable cwd.

## 7. Catalog review

- `cursor|.cursor` confirmed (bundle). `cursor|Library/Application Support/Cursor/User|logs`, `.config/Cursor/User|logs`, `AppData/Roaming/Cursor/User|logs` confirmed (L2-L4).
- `project|.cursor`, `.cursorrules`, `.cursorignore` confirmed; `project|.cursorindexingignore` doubtful (legacy, no current evidence), harmless to keep.
- Excludes `.cursor/extensions`, `.cursor/worktrees`, `*/Cursor/User/globalStorage/state.vscdb.backup` confirmed.
- No cursor secret globs exist today: wrong by omission.

Add:
```
cursor|.config/cursor
cursor|AppData/Roaming/Cursor/auth.json
cursor|.cursor-server/data/User
cursor|.cursor_info
```
Excludes: `.cursor/plugins/marketplaces`, `.cursor-server/bin`, `.cursor-server/extensions`. Secret globs: `.cursor/auth.json`, `.config/cursor/auth.json`, `AppData/Roaming/Cursor/auth.json`, `.cursor/projects/*/mcp-auth.json`, `.cursor/mcp.json`, `.cursor_info`. Discovery: `.cursor/chats/*/*/meta.json` and `.cursor/acp-sessions/*/meta.json` key `cwd` (the former is already read).

## 8. Confidence

High: `~/.cursor` layout, chats/acp-sessions/store.db, projects sanitization, worktrees, hooks, ai-tracking, CLI `auth.json` and keychain logic (all L1 bundle); IDE app-data paths and `state.vscdb` keys (L3/L4, consistent across sources). Medium: `cursorAuth/*` keys (L4 only), `.cursor/extensions` and `.cursor-server` (convention plus L4). Low: `~/.cursor_info` (single L4 claim). Not determined: `store.db` blob encryption (`blobEncryptionKey` in `meta`, codeburn 986), whether Windows CLI uses `%APPDATA%\Cursor\auth.json` or the IDE's dir with the same name, and `.cursorindexingignore` status.
