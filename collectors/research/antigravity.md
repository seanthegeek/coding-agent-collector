# antigravity: on-disk paths (CLI `agy` and the IDE)

## 1. Source and evidence level

Closed source. Three evidence levels, tagged per claim:

- **binary**: `~/.local/bin/agy`, ELF x86-64, 209,625,296 bytes, sha256
  `a759ce7c7a235d9b...`, `strings -n 8` saved to `scratchpad/agy_strings.txt`
  (552,251 lines). The embedded changelog's newest heading is `## 1.2.15`
  (`agy_strings.txt:310457`; oldest `## 1.0.0` at 311213). Cited as `str:<line>`
  or by quoted literal.
- **live**: names and sizes only under `~/.gemini/antigravity-cli`,
  `~/.gemini/config`, `~/.cache/antigravity` on this workstation.
- **docs**: antigravity.google/docs/cli/install/, /docs/settings/,
  codelabs.developers.google.com/antigravity-cli-hands-on; **community**:
  jazzyalex.github.io agent-sessions guide, dev.to ndondadaniel2020 restore
  write-up, github.com/Devilaiger/antigravity-chat-history-fix,
  marioalbu08/antigravity-sync, SavFil/antigravity-convo-manager,
  damadorPL/agent-memories (google/antigravity.md),
  discuss.ai.google.dev thread 167445.

## 2. Per-user storage

Everything user-level sits under `~/.gemini/`; the Go binary resolves it via
`os.UserHomeDir` (binary) so Windows is `%USERPROFILE%\.gemini`
(community: Devilaiger, discuss 167445 quote `%USERPROFILE%\.gemini\antigravity-cli\brain`).
`os.UserConfigDir`/`os.UserCacheDir`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`,
`APPDATA`, `LOCALAPPDATA` also appear (binary), consistent with the
`~/.cache/antigravity/staging` dir (live, empty) used as the plugin
"marketplace cache ... staging directories" (str changelog). Windows CLI
install dir is `%LOCALAPPDATA%\agy\bin` (docs/cli/install).

`~/.gemini/antigravity-cli/` (live, with binary literal where noted):
`antigravity-oauth-token` (1,670 B, see 3); `bin/webm_encoder` (17 MB);
`brain/<uuid>/{.system_generated/logs/, .user_uploaded/, scratch/}`
(binary: `.system_generated/logs/transcript.jsonl`, `transcript_full.jsonl`,
`.system_generated/worktrees`, `.system_generated/subagents`);
`builtin/skills/<name>/`, `builtin/.checksum`, `keep.txt` (bundled skills;
binary also names `~/.gemini/<app-name>/builtin/sidecars/<id>/` and
`builtin/plugins/<plugin>/sidecars/`); `cache/{default_project_id.txt,
last_conversations.json, onboarding.json}` plus `cache/projects.json`
(binary: "stores workspace-to-project mappings in a centralized
`~/.gemini/antigravity-cli/cache/projects.json`"); `cli.log` symlink to
`log/cli-<YYYYMMDD_HHMMSS>.log` (binary `cli.log`); `conversation_summaries.db`
(+`-wal`, `-shm`; binary `conversation_summaries.db`, `ALTER TABLE
conversation_summaries ...`); `conversations/<uuid>.db` (+wal/shm);
`crashes/` (empty); `history.jsonl` (binary); `implicit/<uuid>.pb`;
`installation_id` (binary); `jetbox_summaries_proto.pb` (binary
`jetbox_summaries_pb.SummariesState`); `jetski_state.pbtxt` (binary);
`last_check.timestamp`; `presence/<uuid>.lock`; `settings.json` (docs:
`~/.gemini/antigravity-cli/settings.json`; binary `trustedWorkspaces` tag);
`keybindings.json` (docs/settings); `updater/{update.lock,
update_status.json}`; legacy `hooks.json` (binary: "wrote configurations to
`~/.gemini/antigravity-cli/hooks.json` instead of the shared
`~/.gemini/config/hooks.json`").

`~/.gemini/config/` shared by CLI and IDE (binary changelog, live names):
`mcp_config.json`, `hooks.json`, `config.json`, `projects/<uuid>.json`
(live `default-cli-project.json`), `skills/<name>/SKILL.md`,
`plugins/<name>/`, `rules/*.md`, `workflows/`, `global_workflows/`,
`sidecars/`, `GEMINI.md`, `AGENTS.md`, `skills.json`, `rules.json`,
`plugins.json`, `agents.json`, `workflows.json`, `.migrated` (live). The
binary also reads `~/.gemini/GEMINI.md` and `~/.gemini/AGENTS.md`, and
names legacy `~/.gemini/jetski/brain` and per-repo `.antigravitycli`
workspace dirs (both superseded).

IDE (community, consistent across four sources): `~/.gemini/antigravity-ide/`
with `conversations/<uuid>.db`, `brain/<uuid>/` (Markdown artifacts
`task.md`, `implementation_plan.md`, `walkthrough.md`, each with
`.metadata.json`, plus `.system_generated/logs/transcript.jsonl`),
`knowledge/<ki-id>/{metadata.json, artifacts/}`, `knowledge.lock`
(damadorPL); docs/settings calls `~/.gemini/antigravity-ide/` the "local app
data directory". Pre-2.0 editor and current Desktop app: `~/.gemini/antigravity/brain`
(jazzyalex, discuss 167445); upgrade leftover `~/.gemini/antigravity-backup/brain`
(jazzyalex). VS Code-fork app dir is now named `Antigravity IDE`:
`%APPDATA%\Antigravity IDE\User\globalStorage\state.vscdb` (Devilaiger,
marioalbu08), `~/.config/Antigravity IDE/User/globalStorage/state.vscdb`
(dev.to); macOS by convention `~/Library/Application Support/Antigravity IDE`.
The older `Antigravity` app-dir name is the pre-2.0 form. Enterprise
`admin_settings.json` is system-level: `/etc/antigravity/`,
`/Library/Application Support/Antigravity/`, `...\Antigravity\` (binary).

Relocation env vars: none found for the home dir. `ANTIGRAVITY_EXECUTABLE_DATA_DIR`,
`AGY_ACCOUNT`, `AGY_ADC_AUTH`, `ANTIGRAVITY_PROJECT_ID`,
`ANTIGRAVITY_CONVERSATION_ID` exist (binary) but their effect on paths is
unknown.

## 3. Credentials

- Keyring first: `zalando/go-keyring` with Secret Service, service name
  `jetski-standalone-oauth-token` (binary); docs/cli/install: Apple
  Keychain, Linux Secret Service, Windows Credential Manager. File fallback
  when the keyring is "bypassed or unreachable" (binary changelog) is
  `~/.gemini/antigravity-cli/antigravity-oauth-token` (live, 1,670 B; the
  whole literal is not in the strings, so the name is assembled at runtime).
- `GEMINI_API_KEY` with `modelProvider: "gemini"` in `settings.json`
  (binary changelog; docs/cli/install); the key is env-only.
- `~/.gemini/config/mcp_config.json` can embed MCP `env` and `headers`
  (binary `McpStdioTransport.EnvEntry`, `McpHttpTransport.HeadersEntry`).
- IDE `state.vscdb` holds the conversation index
  (`antigravityUnifiedStateSync.trajectorySummaries`, Devilaiger) and, as a
  VS Code fork, probably auth state; collect unflagged.

## 4. Exclude

`.gemini/antigravity-cli/bin` (17 MB encoder), `.gemini/antigravity*/brain/*/.system_generated/worktrees`
(git worktrees of the project, binary), `.gemini/antigravity-cli/builtin`
(176 KB bundled skills, checksummed; optional), `AppData/Local/agy`
(install), `.cache/antigravity` (marketplace staging; currently empty),
`Antigravity IDE` Electron caches (`Cache`, `CachedData`, `GPUCache`,
`Code Cache`, by VS Code convention). Keep `.system_generated/subagents`
(sub-conversation data) and `scratch/`.

## 5. Project-local files

`.agents/` workspace customizations (`.agents/agents/`, binary changelog;
damadorPL `<project-root>\.agents\`), `.antigravityignore` (binary),
`.antigravity-plugin` (binary), legacy `.antigravitycli/` (binary, removed
in favour of `cache/projects.json`). No per-project database.

## 6. Where the workspace path is recorded

- `history.jsonl`: `workspace` per prompt (analyzer/research/antigravity.md:23).
- `settings.json`: `trustedWorkspaces` array (binary json tag; docs/settings).
- `cache/projects.json`: workspace → project map (binary changelog).
- `config/projects/<uuid>.json`: project definitions; JSON tags present in
  the binary: `workspace_uris`, `workspace_paths`, `workspace_uri`,
  `project_id`, `display_name`, `cwd`.
- `conversation_summaries.db` and per-conversation `*.db`: see the analyzer
  schema notes (SQLite-only; v2 parser).

## 7. Catalog review

- `antigravity|.gemini/antigravity-cli`: confirmed (live, binary, docs).
- `antigravity|.antigravity`: doubtful; no source names a `~/.antigravity`
  dir (the VS Code-fork extensions dir is the only candidate). Keep as a
  cheap probe.
- `antigravity|.cache/antigravity`: confirmed to exist (live), low value.
- `.config/Antigravity/User`, `Library/Application Support/Antigravity/User`,
  `AppData/Roaming/Antigravity/User` and the three `/logs` lines: doubtful
  for 2.x; the app dir is `Antigravity IDE` (two community sources). Keep
  for pre-2.0 hosts.
- exclude `.gemini/antigravity-cli/bin`: confirmed. `.antigravity/extensions`: doubtful (depends on the line above).
- secret `*.gemini/antigravity-cli/antigravity-oauth-token`: confirmed (live; keyring fallback).

Add:
```
antigravity|.gemini/antigravity-ide
antigravity|.gemini/antigravity
antigravity|.gemini/antigravity-backup
antigravity|.gemini/config
antigravity|.config/Antigravity IDE/User
antigravity|.config/Antigravity IDE/logs
antigravity|Library/Application Support/Antigravity IDE/User
antigravity|Library/Application Support/Antigravity IDE/logs
antigravity|AppData/Roaming/Antigravity IDE/User
antigravity|AppData/Roaming/Antigravity IDE/logs
project|.antigravityignore
project|.agents
# excluded
.gemini/antigravity*/brain/*/.system_generated/worktrees
AppData/Local/agy
*/Antigravity IDE/User/globalStorage/*/Cache*     (if the VS Code cache rule does not already match)
# discovery
.gemini/antigravity-cli/history.jsonl         "workspace"
.gemini/antigravity-cli/settings.json         "trustedWorkspaces"
.gemini/antigravity-cli/cache/projects.json   object keys
.gemini/config/projects/*.json                "workspace_paths" / "workspace_uris"
```
Note `.gemini/config` is currently swept by `gemini-cli|.gemini` and
attributed to Gemini CLI; the nested entry fixes attribution.

## 8. Confidence

High: the CLI layout (live plus binary literals), keyring service and file
fallback, `~/.gemini/config` contents, `antigravity-ide/conversations` and
`brain` (four independent sources). Medium: `Antigravity IDE` app-dir name
on macOS (inferred from the Windows and Linux names), `knowledge/`
sub-layout (one source), `.cache/antigravity` purpose, exact
`cache/projects.json` and `config/projects/*.json` key names (tags exist in
the binary but were not matched to those files). Not determined: whether
`~/.antigravity` exists at all; the Desktop app's own Electron dir name;
the `implicit/*.pb` and `presence/` semantics; Windows and macOS paths for
`agy` logs and the keyring fallback beyond `%USERPROFILE%\.gemini`.
