# muse-code (Meta Muse Code CLI)

How the transcripts are encoded and how the parser reads them is in
[`analyzer/research/muse-code.md`](../../analyzer/research/muse-code.md).

## 1. Source and evidence level

- Closed source, no public repository, so there are no commit links. Muse
  Code is Meta's coding agent CLI (models `muse-spark-*`), shipped as a
  launcher script (bash on Linux and macOS, PowerShell on Windows) plus a
  native binary that the launcher downloads from Meta's lookaside host and
  keeps up to date.
- Evidence level **B** = `strings -n 6` of the shipped binary
  `muse-bin-1.4.2-R4684.1` (344,369,368 bytes, x86-64 ELF, statically
  linked, stripped; sha256
  `dfb3096c91f4767c4d98006460800b7ba906a0b1a408280a926a8dc19a1af64f`).
  It is a Rust build: panic paths name
  `fbcode/musecode/build/src/crates/<crate>/src/...` for the crates `agent`,
  `tui`, `session-server`, `config`, `session-view`, `local-store`,
  `plugins`, `agent-session-storage`, `local-tracing` and others. Literal
  strings are concatenated without separators in the string table, so a
  claim cites the literal string, not a function.
- Evidence level **L** = the launcher `~/.local/bin/muse` (32,737 bytes,
  bash, sha256
  `c6db294799a190ca380da274beb3b9c0e160e0da9681a3d364ce8b0e5fa3a4bc`),
  cited by line.
- Evidence level **K** = vendor-written skill text that the binary embeds
  and materialises on first run into
  `~/.local/share/muse/plugins/cache/builtin/muse-core/<skill>/<sha256>/`
  and `~/.local/share/muse/skills/bundled/muse-core/skills/<skill>/`
  (version 1.4.2-R4684.1). Cited as `<skill>/SKILL.md:<line>`; the
  directories used are `read-session/0782fa625e56…`,
  `resume-claude/9df9d8756818…`, `resume-codex/30ddd55a24fd…`,
  `import/5bc46b7edb9f…`, `migrate/1dda33263863…`,
  `manage-settings/4381b5a6a995…`, `doctor/362cd5a3ba33…`, and under
  `skills/bundled/muse-core/skills/`, `agents/` and `fleet-manager/`.
- Evidence level **I** = the real install on the research host (Linux,
  WSL2), two interactive sessions on 2026-10-03 and 2026-10-04, one of which
  started two subagents. Only names, sizes, JSON key names and SQLite
  schemas were read; SQLite files were copied with their sidecars before
  opening.
- Evidence level **W** = shipped binary strings (Windows build):
  `muse-x86-windows.exe` 1.4.2-R4684.1 (443,192,056 bytes, sha256
  `39a97806d315ece0fc5cdbb88c903ef5bc77655f32e66dc22d267a212c5030ba`,
  matching the release manifest), ASCII and UTF-16LE strings
  (`strings -n 6` and `-e l`) in one file, cited as `W:<line>` of that
  strings file.
- Evidence level **S** = installer/launcher script (Windows):
  `install.ps1` from `https://dev.meta.ai/install.ps1` (sha256
  `45be8be39acf500982e816a09eb55b886ef65a986895741b10498c50bbb93776`),
  cited `S-inst:<line>`, and `muse-launcher.ps1` from
  `https://api.meta.ai/muse-launcher.ps1` (sha256
  `4c6913af8d611bf41a72c17337a6c9e57a733943fb890dbaf3d8f9f06f27fde8`,
  launcher version 3), cited `S-ps:<line>`. Neither was run.
- Evidence level **M** = the public channel and release manifests
  (`channel.json`, `manifest.json` for 1.4.2-R4684.1), which list
  artifacts `x86_macos`, `aarch64_macos`, `x86_linux`, `aarch64_linux`,
  `x86_windows`, `aarch64_windows` and `universal_macos_pkg` (`muse.pkg`).
  The Linux artifact checksum equals the binary above.
- No official documentation was consulted.

## 2. Per-user storage

Platforms: Linux, macOS and Windows, each on x86-64 and arm64 (M). The
bash launcher covers Linux and macOS (`detect_platform`, L:91-99); a
separate PowerShell installer and launcher cover Windows (S-inst:200-203
refuses non-Windows hosts and names `installer.sh` for macOS and Linux; `Get-PlatformKey` returns `x86_windows` or
`aarch64_windows`, S-ps:70-73). macOS also ships as `muse.pkg` (M); its
install location was not read.

Path resolution is the same on every OS: XDG base directories with a home
fallback, never `AppData` or `Library/Application Support` for per-user
state.

- Linux and macOS: the Rust `xdg` crate table (B: `XDG_DATA_HOME
  .local/share XDG_CACHE_HOME .cache XDG_STATE_HOME .local/state
  XDG_CONFIG_HOME .config`); K `doctor/SKILL.md:87-88`; L:20-25. The
  Linux binary names no `AppData`, `USERPROFILE` or `Application Support`
  path (the only `APPDATA`/`LOCALAPPDATA` hits are inside an NSIS
  syntax-highlighting grammar).
- Windows: "no usable config directory from XDG_CONFIG_HOME, HOME, or
  USERPROFILE" and "no usable data directory from XDG_DATA_HOME, HOME, or
  USERPROFILE" (W:351696), and the PowerShell launcher builds the
  credential path as `MUSE_AUTH_PATH`, else `XDG_CONFIG_HOME`, else
  `%USERPROFILE%\.config`, then `muse\auth.json` (S-ps:23-33). So Windows
  uses `%USERPROFILE%\.config\muse` and `%USERPROFILE%\.local\share\muse`
  (or `%HOME%\...` when `HOME` is set). The existing home-relative lines
  `.config/muse` and `.local/share/muse` therefore cover Windows homes as
  well.

Two roots:

- Config root `${XDG_CONFIG_HOME:-$HOME/.config}/muse` (L:20-23;
  K `manage-settings/SKILL.md:97-98`, `doctor/SKILL.md:87`; Windows
  W:351696, S-ps:23-33).
- Data root `${XDG_DATA_HOME:-$HOME/.local/share}/muse` (K
  `read-session/SKILL.md:82`, `doctor/SKILL.md:88`; B
  `.local/share/muse/runtime/muse`,
  `.local/share/muse/session-name-authority`; Windows W:351696).

No `~/.local/state/muse` or `~/.cache/muse` exists on the host and the
binary names neither (I, B); the XDG state and cache keys appear only in
the crate's generic table.

Config root `~/.config/muse/` (I unless stated):

- `settings.json`: `schema_version`, `provider`, `model`; also `mcpServers`
  (K `migrate/SKILL.md:144-152`). Lock file `.settings.json.lock`.
- `auth.json`: credentials (section 3). Lock file `.auth.json.lock`.
- `trust.json`: `{"schema_version": int, "projects": {"<absolute project
  path>": {"decision": "trusted"}}}` (I, two entries). Lock file
  `.trust.json.lock`.
- `skills/<skill-id>/SKILL.md`: user-installed skills, with a store lock
  `skills/.muse/lock.json` (keys `package`, `source_path`, `trust`,
  `package_hash`, `repository`, `requested_ref`, `resolved_revision`,
  `manifest_hash`, `content_sha256`), `quarantine/`, `audit.log` and
  `.skills.lock` (B `$CONFIG_DIR/skills/<skill-id>`,
  `$CONFIG_DIR/skills/.muse/lock.json`,
  `lock.jsonquarantineaudit.log.skills.lock`). Not present on the host.
- `machines.toml`: remote machines for the bundled `fleet-manager` skill
  (B `~/.config/muse/machines.toml`; K
  `fleet-manager/references/getting-started.md:69-72`). Not present.

Data root `~/.local/share/muse/` (I, 6.1 MB in total after two sessions):

- `sessions/YYYY/MM/DD/<session-id>/` (2.1 MB), session ids are UUIDv7 and
  the shard is the local date (K `read-session/SKILL.md:18-28`). Each holds
  `session.jsonl` (the event log, one JSON record per line),
  `subagent/<child-session-id>/session.jsonl` (one log per subagent),
  `tool-outputs/<id>/call_<id>-<tool>[-page].txt` (full tool outputs kept
  out of line; 208 KB here) with a `.spool/` of in-flight `.tmp` files,
  `approval-review/<uuid>.jsonl` (approval decisions, same envelope keys as
  `session.jsonl`), `cron.db` (SQLite, table `cron_jobs` with `prompt`,
  `cron_expr`, `session_id`, `next_fire_at_ms`; journal mode DELETE, so a
  `cron.db-journal` can appear, B), `session.peer-history.sqlite3` with
  `-wal`, `-shm` and `.rebuild.lock` (an index of retained records by line
  offset and sha256, tables `source_snapshot`, `retained_records`,
  `stable_ids`), `cli-<uuid>.log` (tracing log of the process that ran the
  session), `.session.lock` and `.session.jsonl.permission-init`. The
  binary also names `goals.db` (with `-wal`, `-shm`) and `input-assets/`
  (attached images and video, mode 0600) in the same directory (B
  `cron.dbinput-assetscron.db-journalcron.db-walcron.db-shmgoals.db-wal`);
  neither was created here. A directory that holds only lock files is
  left by a session that never started a turn (I).
- `sessions/.msp-view-v1/<session-id>/`: a materialised view of each
  session for the TUI: `HEAD.json`, `index-00000000.bin`,
  `journal-00000000.bin`, `snapshot-<uuid>.json` (I; 264 KB for the larger
  session). Derived from `session.jsonl`.
- `sessions/.prior-crash-telemetry-markers-v1`: empty marker file (I).
- `session-index.db`: SQLite in WAL mode, table `sessions`, one row per
  session (I; schema in section 6).
- `session-name-authority/`: `authority.json` (`schema_version`,
  `authority_id`) and `session-names.db` (tables `session_name_claims_v2`,
  `session_name_operations_v2`, `session_name_counters_v2`) (I).
- `tui-history.jsonl`: prompt history, one JSON string per line holding the
  prompt text, no cwd and no timestamp (I). `MUSE_SKIP_PROMPT_HISTORY`
  disables it (B). Lock file `tui-history.jsonl.lock`.
- `local-tracing/bootstrap/cli-<uuid>.log`: process tracing logs written
  before a session directory exists, plain text lines
  `<RFC 3339 time> <LEVEL> tbh.local.host <source path>:<line> ...`
  (I, 288 KB; B `local tracing bootstrap path must be
  <data-root>/local-tracing/bootstrap`).
- `memory/`: Muse's own memory notes (`MEMORY.md` index plus `<name>.md`
  notes) for the `personal` and `personal_project` scopes (K
  `doctor/SKILL.md:51,91`, `migrate/SKILL.md:67-70`). Not created here; the
  layout below `memory/` is not determined.
- `crashes/`: crash reports (K `doctor/SKILL.md:91-92`). Not present.
- `model-catalog/<hex>__<hex>.json`: cached provider model list (12 KB;
  keys `profile_id`, `provider_id`, `rows`, `schema_version`, `source`) (I;
  K agents skill `MODEL_CATALOG_SUBDIR = "model-catalog"`).
- `feature-config/<hex>.json`: remote feature gates (keys `gates`,
  `killed_slash_commands`, `schema_version`, `ttl_seconds`) (I).
- `plugins/cache/builtin/<plugin>/<skill>/<sha256>/`: the bundled plugins
  `muse-core` (1.6 MB) and `threejs` (172 KB), extracted from the binary
  (I). User plugins land in `plugins/cache/local/`, and marketplaces in
  `plugins/marketplaces.json` and `plugins/marketplaces/` (B
  `plugins/cache/local/`, `plugins/marketplaces.json`,
  `plugins/marketplaces/`). Not present.
- `skills/bundled/muse-core/skills/<skill>/`: a second copy of the bundled
  skills with their scripts (1.5 MB) (I).
- `runtime/muse/`: local session registry and Unix sockets,
  `.session-registry.mutation.lock`, `sessions/` (I; B
  `.local/share/muse/runtime/muse`, `directory must be same-user mode
  0700`, `endpoint path exceeds the Unix socket bound`).
- `session-admission-locks/session-v1-<session-id>.lock` (I).
- `fleet-manager/state.json` and `fleet-manager/home/<machine>/` (files
  fetched from remote machines by the `fleet-manager` skill) (K
  `fleet-manager/references/getting-started.md:69-71`). Not present.

Other per-user locations:

- `~/.muse/projects/<slug>/` with `tracking.json`, and
  `~/.muse/projects/.archive/<slug>-<stamp>/`: coordinator projects of the
  experimental `agents` skill (gated by `MUSE_EXPERIMENTAL_AGENTS`);
  relocated by `MUSE_PROJECTS_HOME` (K
  `agents/references/verbs.md:36-37`; B). Not present.
- Install directory on Linux and macOS, the directory holding the bash
  launcher (`~/.local/bin` on this host; the shell installer was not
  read): `muse` (launcher), `muse-bin-<version>` (binary),
  `.muse-version` (active version, L:951,1017), `.muse-release-info.json`
  (keys `channel`, `version`, `manifest_url`, `urgency`,
  `notification_text`, `state`, `min_version`; L:922,1026),
  `.muse-update-checked-at` (epoch seconds of the last update check,
  L:1078), `.muse-update-notice` (L:898,1038), `.muse-launcher.previous`
  (the prior launcher, L:866), and transient `.muse-update.XXXXXX/` (holds
  a downloaded candidate binary, L:952), `.muse-launcher.XXXXXX` (L:843)
  and `.muse-update-lock/` (L:803). The bash launcher writes no
  `.muse-channel` (it reads `MUSE_CHANNEL` each run, L:4).
- Install directory on Windows: `MUSE_INSTALL_DIR`, else
  `%LOCALAPPDATA%\Programs\muse` (S-inst:188-196). It holds
  `.muse-launcher.ps1` and the `muse.cmd` shim that runs it
  (S-inst:211-212, 106-120), `muse-bin-<version>.exe` (S-ps:535,566),
  `.muse-version` (S-ps:531,542,558), `.muse-release-info.json`
  (S-ps:543,572,614), `.muse-channel` (S-ps:524,574,617),
  `.muse-update-checked-at` (S-ps:707), `.muse-update-notice`
  (S-ps:488,503), `.muse-update-lock/pid` (S-ps:446),
  `.muse-launcher.previous` (S-ps:656), and transient
  `.muse-update.<pid>.exe` (a staged binary, S-ps:597) and
  `.muse-launcher.<pid>` (S-ps:646). The installer removes stale
  `.muse-updater` and `.muse-install-lock` from earlier versions
  (S-inst:242-246).
- Windows shell sandbox scratch: a per-session private temp root named
  `muse-shell-sandbox-<session id>`, required to be a direct child of
  `FOLDERID_LocalAppDataLow`, that is
  `%USERPROFILE%\AppData\LocalLow\muse-shell-sandbox-<session id>`
  (W:364189-364200). It holds the temp files of sandboxed shell commands
  for one session; whether it is removed when the session ends is not
  determined.
- Remote-machine forwards `/tmp/fleet-manager-<uid>/` (K): outside the
  home, not collectable by a catalog line.

System-wide (not per home, outside the catalog's scope):

- Windows elevated sandbox setup root under `%ProgramData%` ("setup root
  has no ProgramData ancestor", W:364301; `MuseSandboxUsers` group, W:364118,364240, and
  the `TBH_WINDOWS_ELEVATED_SETUP_ROOT` override, W:364306), with
  sandbox accounts `muse-sbx-r1`/`muse-sbx-u1` whose passwords are
  protected with DPAPI `CryptProtectData` (W:364322-364330).
- Enterprise policy: Windows registry `SOFTWARE\Policies\Muse`
  (W:352349); on macOS `Library/Application Support/muse` beside the
  keys `EnterpriseDefaultsJson` and `EnterprisePolicyJson` (W:352353-352354),
  with file names `.enterprise-defaults.json` and `enterprise-policy.json`
  (W:352592; Linux binary B has the same two file names). Read as the
  system-wide `/Library/Application Support/muse/` (medium confidence).
  The Linux location of these files is not determined: the Linux strings
  name no `/etc/muse` or other system path for them. A responder collects
  these by hand; a catalog line cannot reach them.

Environment relocation: `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
`XDG_RUNTIME_DIR` (B), `MUSE_AUTH_PATH` (launchers' view of `auth.json`
only, L:25, S-ps:23; the string does not occur in the Linux binary),
`MUSE_PROJECTS_HOME`, `MUSE_CHANNEL` (`muse-stable` or `muse-canary`,
L:4), `MUSE_INSTALL_DIR` (Windows installer, S-inst:189),
`MUSE_SKIP_PROMPT_HISTORY` (B).

## 3. Credentials

- `~/.config/muse/auth.json` (mode 0600, I). Shape:
  `{"schema_version", "providers": {"meta": {"mechanism", "obtained_via",
  "access_token", "api_key", "api_base_url", "user_email",
  "user_full_name", "user_avatar_url"}}}`; here `mechanism` is `oauth`
  and `obtained_via` is `device_code` (I). The launcher reads
  `providers.meta.access_token` and optional `providers.meta.expires_at`
  and never writes the file (L:472-494). It holds the account's email and
  name as well as tokens. The binary also stores MCP OAuth state through
  the same store under keys prefixed `mcp_oauth:` and
  `mcp_oauth_client:` (B `auth.jsonstoragemcp_oauthmcp_oauth_client:
  mcp-oauth-v1mcp_oauth:`; medium confidence on the exact layout).
- macOS: Meta credentials are kept in the macOS Keychain, with a file
  fallback (B: Keychain error texts, `credential_backend`,
  `keychain_fallback_file`). Each session's `session.opened.observed`
  record carries `credential_backend` and `keychain_fallback_reason`; on
  Linux the value is `file` (I). On a Mac `auth.json` may therefore be
  absent or hold only the fallback.
- Windows: `%USERPROFILE%\.config\muse\auth.json`, the same file, which
  the PowerShell launcher reads for its download token (S-ps:23-33). No
  Windows Credential Manager use was found in the Windows strings; the
  only DPAPI use protects the sandbox accounts' passwords (W:364322-364330),
  which live under the system-wide setup root, not in the home.
- `settings.json` can hold literal secrets: `mcpServers.<name>.env` and
  `.headers` values, which the `migrate` skill writes as literal values
  such as a GitHub token or an `Authorization: Bearer` header (K
  `migrate/SKILL.md:144-176`).
- Environment variables named in the binary: `META_API_KEY`,
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` and their
  `*_BASE_URL`, `MUSE_CUSTOM_HEADERS`, `TBH_CREDENTIAL_BACKEND` (B). No
  other key file is named.
- Session logs can contain the tool outputs of anything the agent read,
  as in every agent's transcript; nothing Muse-specific there.

## 4. Exclusions

Sizes from the host after two sessions (I):

| Path | Size | Content |
| --- | --- | --- |
| `.local/share/muse/plugins/cache/builtin` | 1.8 MB | bundled plugins extracted from the binary, identical for every user of a version |
| `.local/share/muse/skills/bundled` | 1.5 MB | a second copy of the same bundled skills |
| `.local/share/muse/sessions/.msp-view-v1` | 0.3 MB | derived view of `session.jsonl` |
| `.local/share/muse/local-tracing` | 0.3 MB | process logs; evidence, keep |
| `.local/share/muse/model-catalog` | 12 KB | provider model list; keep |

- Exclude the two bundled copies: they are vendor content rebuilt from the
  binary, and they grow with every skill Meta ships. Do not exclude all of
  `plugins/cache`: `plugins/cache/local/` holds user-installed plugins,
  which can be evidence of what ran.
- `plugins/marketplaces/` is named in the binary (B) and, by the pattern of
  other agents, likely holds marketplace clones; its contents are not
  determined, so it is proposed as an exclusion only with low confidence.
- `.msp-view-v1` is small and derived; keeping it is harmless.
- `<repo>/.muse/worktrees/`: git worktrees that Muse creates inside a
  project for subagents and isolated sessions (B
  `/.muse/worktrees`, `exclude/.muse/worktrees/`, `subagent worktree
  retained at`). Each is a checkout of the repository, so exclude it
  relative to the collection base, which covers discovered projects.
- Linux and macOS install directory: `~/.local/bin` holds other tools'
  binaries, so it cannot be a catalog entry. The proposal is one glob,
  `.local/bin/.muse-*`, which matches the state files and
  `.muse-launcher.previous` but not `muse-bin-*` (344 MB, no leading
  dot). It also matches the transient `.muse-update.XXXXXX/` directory,
  which holds a full candidate binary during an update, so that directory
  is excluded (`.local/bin/.muse-update.*`; the lock directory is
  `.muse-update-lock`, a dash, and stays collected).
- Windows install directory `AppData/Local/Programs/muse` holds only
  Muse's files, so the whole directory is an entry, and the two binary
  names are excluded: `muse-bin-*.exe` (443 MB for 1.4.2) and the staged
  `.muse-update.*.exe`. Both collectors apply `EXCLUDES` to files as well
  as directories: the sh collector prunes any `find -path` match and
  records a file with its `stat` size (`SKIP_PROG`), and the PowerShell
  collector's `Add-Excluded` records a file's `Length`; the existing
  `.continue/index/*.sqlite` exclusion is a file pattern. The excluded
  binary still leaves a `skipped_excluded` row whose name and size
  record the installed version.
- Windows sandbox scratch `AppData/LocalLow/muse-shell-sandbox-*` is
  per-session temp; its size is not known. It is proposed as a catalog
  entry (it can hold files a sandboxed command wrote) and not excluded;
  revisit if a real install shows it large.

## 5. Project-local files

- `AGENTS.md`, with `CLAUDE.md` as the fallback when `AGENTS.md` is absent
  (B: "Directly probe the active workspace's `AGENTS.md`; only when it is
  absent, directly probe its `CLAUDE.md` fallback"). Muse also writes
  `AGENTS.md` (B: compact shape `# AGENTS.md`, `## Commands`,
  `## Code Map`), and `muse init` generates one headed "Muse Code reads
  this file as project rules when it runs in this directory" (W:351576-351578).
  `MUSE.md` occurs nowhere in either binary.
- `.muse/worktrees/` (section 4), added to `.git/info/exclude` (B).
- `.muse/hooks.json`: the strings `.muse` and `hooks.json` are adjacent
  constants in both binaries (B and W:352591 `.musehooks.json`, the line
  before the enterprise file names), read as the project hooks file
  (medium confidence).
- `.agents/memory/` (the shared `project` memory scope, K
  `migrate/SKILL.md:69`), `.agents/skills/`, `.agents/skill-drafts/<id>/`
  (personal skill staging), `.agents/plans/YYYY-MM-DD-<slug>.md`,
  `.agents/workflows/` (B).
- Skills read from `.claude/skills`, `.codex/skills` and `.agents/skills`;
  plugin manifests `.muse-plugin/plugin.json`, also `.codex-plugin` and
  `.claude-plugin`; `.mcp.json` and `.claude/settings*.json` read by the
  migrate skill (B; K `migrate/SKILL.md:42,119`).
- No per-project database. Sessions are always under the data root
  (K `read-session/SKILL.md:30-33`).

## 6. Project path records

- `session.jsonl`: the `runtime.session.metadata` record carries
  `payload.record.workspace_root` (absolute path), and
  `runtime.session.route_facts` carries `payload.record.cwd` (K
  `read-session/SKILL.md:87-88`; I). Both appear in the raw file as
  `"workspace_root":"/..."` and `"cwd":"/..."`, so a grep works. Subagent
  logs under `subagent/<id>/` carry neither key (I).
- `session-index.db`, table `sessions`: `workspace_root` and
  `workspace_key` (absolute paths), plus `session_dir`,
  `session_log_path`, `git_branch`, `title`, `first_user_prompt`,
  `created_at_us`, `updated_at_us`, `model_id`, `provider_id` (I). WAL
  mode; the `-wal` sidecar is present while Muse runs.
- `~/.config/muse/trust.json`: keys of `projects` are absolute project
  paths (I). This is the simplest file for `discover_projects` to read,
  but it lists only projects the user trusted, which is a subset of those
  used.
- `tui-history.jsonl` records no path (I).
- `~/.muse/projects/<slug>/tracking.json` names coordinator threads and
  worktrees (K); shape not determined.

## 7. Confidence

High: the two XDG roots under the home on Linux, macOS and Windows
(`%USERPROFILE%\.config\muse`, `%USERPROFILE%\.local\share\muse`); the
three platforms and architectures in the release manifest; the session
directory layout and file names; `session-index.db` and `cron.db`
schemas; `auth.json` key names; the install-directory files of both
launchers and the Windows default `%LOCALAPPDATA%\Programs\muse`;
`workspace_root` and `cwd` in `session.jsonl`; `trust.json` shape; the
bundled-copy directories and sizes.

Medium: macOS Keychain with `auth.json` as fallback (strings only, no Mac
install); MCP OAuth entries in the credential store; `memory/` and
`crashes/` under the data root (vendor skill text, not created here);
`.muse/worktrees` and `.muse/hooks.json` inside projects;
`~/.config/muse/skills/` layout; `goals.db` and `input-assets/` per
session; the Windows sandbox scratch `AppData/LocalLow/muse-shell-sandbox-*`
(strings only, no Windows install); macOS enterprise policy under
`/Library/Application Support/muse/`.

Low: `plugins/marketplaces/` holding clones; `~/.local/share/metacode`
as a former data root (it appears only in the `import` skill's helper
lookup, `import/SKILL.md:156-157`, and not as a path either binary
builds).

Not determined: the layout under `memory/` (how `personal_project` is
keyed); where the Linux and macOS shell installer and `muse.pkg` place
the launcher (the bash launcher uses its own directory; `~/.local/bin`
is observed only); the shape of `tracking.json`; whether the Windows
sandbox scratch directory is removed at session end and how large it
gets; the Linux location of the enterprise policy files; whether any
state is written outside the two roots on macOS (for example a
`Library/Logs` path; none is named).

Other agents whose state Muse reads (K `resume-claude`, `resume-codex`,
`import`, `migrate`; B): Claude Code (`${CLAUDE_CONFIG_DIR:-~/.claude}/projects/*/*.jsonl`,
`projects/*/memory/`, `~/.claude.json` `mcpServers`, `.claude/settings*.json`,
`.claude/skills`), Codex CLI (`${CODEX_HOME:-~/.codex}/sessions`,
`memories/`, `memories_1.sqlite`, `config.toml`, `skills/`), and Grok
Build (`${GROK_HOME:-~/.grok}/sessions/<percent-encoded cwd>/<uuid>/`
with `summary.json`, `events.jsonl`, `chat_history.jsonl`,
`updates.jsonl`; `import/SKILL.md:122-129`). All are read-only; Muse
writes only into its own roots (`migrate/SKILL.md:12-14`). Grok Build is
not in the catalog. Goose has a `muse_code` provider directory
(`.config/goose/muse_code/`, already a secret glob), so Goose can drive
Muse as a provider.
