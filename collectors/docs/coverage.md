# What gets collected

Which files the collectors take, from which homes and projects, and which
they exclude or flag as credentials. Back to the
[collectors README](../README.md).

Run `--list` for the full catalog. Every catalog entry is tried against every
home directory, so macOS, Linux and Windows paths coexist and a Windows image
mounted on a Linux workstation is collected correctly. The evidence for every
catalog entry, with citations and the level each claim rests on, is one
document per agent under [research/](../research/README.md).

## Editors, extensions and shared directories

VS Code, VSCodium and their forks are collected through their `User`
directories, which hold Copilot Chat sessions and extension state. The
globalStorage of the Cline, Roo Code, Kilo Code, Continue, Sourcegraph Cody
and Twinny extensions is claimed by nested catalog entries, so those files
are attributed to the extension's agent rather than to the editor, whichever
editor they sit in.

Shared directories read by several agents, such as `~/.agents`, are
collected under the `shared` agent name.

Shell histories and general-purpose `.env` files in the home or a project
are not collected: like process lists and logons, they are the EDR's job. An
agent's own `.env` inside its state directory, such as `~/.codex/.env` or
`~/.hermes/.env`, is collected and flagged `secret: true`.

## Nested entries

When one tool keeps its state inside another tool's directory, as
Antigravity CLI does under `~/.gemini/antigravity-cli`, the nested catalog
entry wins: those files are collected once, attributed to the nested agent,
and left out of the enclosing agent's walk.

## Case variants

Some tools use paths that differ only by case on Linux, where both can exist:
`.config/goose` and `.config/Goose`, `.config/PearAI/User` and
`.config/pearai/User`, and `.config/Cursor/User` inside `.config/cursor`. On
a case-insensitive filesystem (macOS by default, Windows, a directory under
`/mnt/c` in WSL) such entries name one directory, which is collected once:
the catalog line listed first keeps it, and the later line collects nothing
and leaves one log line ending `(case-insensitive filesystem), collected
there`, with no manifest row. A case variant of a path inside another match
(`.config/Cursor/User` inside `.config/cursor`) is treated as the nested
entry it is. On a case-sensitive filesystem every variant that exists is
collected as before. How the two collectors decide that two spellings are
one directory, and how the path is spelled in the manifest, differs:

| | `collect-agent-artifacts.sh` | `Collect-AgentArtifacts.ps1` |
| --- | --- | --- |
| Which matches are compared | Matches whose paths are equal once ASCII-lowercased, or where one lowercased path lies inside another. | Every match, after each literal path segment is replaced by its on-disk name. |
| Test for one directory | Same device and inode (`lstat`): `stat -c '%d:%i'` (GNU), `stat -f '%d:%i'` (BSD), or the inode from `ls -di` when neither `stat` works. | Same path string after the on-disk names are taken. The on-disk name of a segment is the single entry that `Directory.GetFileSystemEntries(parent, segment)` returns; when it returns none or several (two names that differ by case on a case-sensitive filesystem), the segment is kept as written. |
| Spelling in `path` and the archive | The first catalog line's spelling (`.config/PearAI/User/...` even when the directory on disk is `pearai`); a nested variant takes the enclosing match's spelling for the shared part (`.config/cursor/User/...`). | The on-disk spelling. |
| Log line for the dropped entry | `[agent] <path>: same file as <kept path> (case-insensitive filesystem), collected there` | `[agent] <path>: catalog line <glob> names the same path as an earlier line (case-insensitive filesystem), collected there` |

Claimed paths of nested entries are compared case-insensitively by the
PowerShell collector on Windows and case-sensitively elsewhere, so pwsh on
Linux keeps `.config/cursor/User` and `.config/Cursor/User` apart. With
`--inventory` (`-Inventory`) the same folding applies, and the dropped line's
glob is left out of the agent's `evidence`.

## Claude Code config homes

Claude Code reads its whole config home from `CLAUDE_CONFIG_DIR` when that
variable is set, and a second account in `~/.claude-work` or a similar
`~/.claude-<name>` directory is common. Such a directory is collected as
`claude-code` only by the Claude-specific names inside it: `projects/`,
`file-history/`, `history.jsonl`, `.claude.json*`, `.credentials.json`,
`hfi-auth.json`, `.session_ingress_token`, `remote/.oauth_token` and
`remote/.api_key`. The credential files and `.claude.json` are flagged
`secret: true`. A bare `.claude-*` entry would also take other tools'
directories such as `~/.claude-code-router` and `~/.claude-mem`, so the
rest of a relocated home (`settings.json`, `todos/`, `plans/`,
`shell-snapshots/` and the other subdirectories) is not collected. A config
home outside the home directory, or one not named `.claude-<name>`, is not
found; collect it by hand.

## Home directories

Home directories are gathered from several sources, merged, and
de-duplicated by path:

- The sh collector in live mode reads `getent passwd`, or `/etc/passwd`
  where there is no `getent`, and on macOS also
  `dscl . -list /Users NFSHomeDirectory`. In image mode it reads
  `<root>/etc/passwd` and prefixes every home with the root. In both modes
  it also globs `home/*`, `Users/*`, `root`, `var/root`, `usr/home/*` and
  `export/home/*` under the root, taking the directory name as the user.
  Homes that do not exist are dropped, as are system paths that are not
  real homes (`/`, `/bin`, `/sbin`, `/usr`, `/usr/bin`, `/usr/sbin`, `/dev`,
  `/dev/null`, `/proc`, `/sys`, `/nonexistent`, `/var/empty`) and `Shared`,
  `Public`, `Default`, `Default User` and `All Users` under `/Users`.
- The PowerShell collector in live mode reads the registry `ProfileList`
  and globs `Users\*` and `home\*` on the system drive. In image mode it
  only globs, using the same six patterns as the sh collector. It does not
  read `etc/passwd`, so in a Linux image it misses any home outside those
  directories. Profiles named `Public`, `Default`, `Default User`,
  `All Users`, `Shared`, `defaultuser0`, `UMFD-<n>`, `DWM-<n>` or `TEMP` are
  skipped. A profile path that cannot be seen is logged as
  `profile not accessible (skipped)`. When its parent directory still
  lists it (access denied rather than a deleted profile), it also gets an
  `error_read` row, but it is not added to `users` and `homes`.

Service accounts with real homes are included because agents run as them
too, for example the `ollama` system user.

## Project discovery

Project-level artifacts (`CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`,
`.cursorrules`, `.aider.chat.history.md`, Crush's per-project
`.crush/crush.db`, ...) are collected from every directory referenced in
agent state that can be read with grep: Claude Code history and project list
(in `~/.claude` and `~/.claude-<name>` config homes), Codex session
rollouts, Qwen Code chats, Cline sessions and task history, Roo and Kilo
task indexes, Continue sessions, Gemini CLI's project registry, trusted
folders and project root markers, Antigravity's history, trusted workspaces
and project cache, Crush's project list, Goose legacy session files and the
desktop app's recent directories, OpenCode's legacy project store, Cursor
CLI chat and ACP session metadata, Copilot CLI session workspaces, Amp
history, Factory Droid sessions, Muse Code's trusted projects
(`.config/muse/trust.json`) and session logs (`workspace_root`), Kiro CLI
sessions and workspace roots, VS Code family workspace storage including the
remote server data directories, Hermes checkpoint project records, Letta
session index and local-backend transcripts, pi session headers, trusted
folders, crash log and experimental session metadata (which also cover
little-coder), Open Interpreter rollouts, OpenHands workspaces and
conversation metadata, PearAI sessions, OpenClaw workspace and agent
directories from its JSON5 config, nanobot workspace markers and config,
Tabby `file://` repositories, and the common directory of the files in each
Twinny embeddings manifest.

A referenced path is used only if it is absolute and names an existing
directory that is not itself a home. In image mode it is looked up under the
root. The sh collector reads POSIX paths only, so it skips drive-letter
references in a Windows image. The PowerShell collector maps `C:\...` and
`file:///c:/...` references to the same path under `-Root`, dropping the
drive letter. On a live Windows host it ignores POSIX paths.

From each project only the `PROJECT_CATALOG` entries are collected. Their
rows have agent `project`, `home` set to the project directory, and the user
whose state referenced it (the first one, when several did). `-p`
directories join the same list. Each gets as its user the owner of the home
it sits under, or none.

Agents that only record the project path inside SQLite (Zed, Goose,
OpenCode, Kilo Code, Kiro CLI, Hermes `state.db` and `projects.db`, OpenClaw
`openclaw.sqlite`, Tabby `ee/db.sqlite`, the PearAI Roo fork in
`state.vscdb`) are left to the analyst-side parser, as are Codex and Open
Interpreter rollouts compressed with zstd.

## Agents outside dot directories

Most agents keep their state in a dot directory, but a few do not: Agent
Zero lives in its install directory (`~/agent-zero`, `~/Desktop/agent-zero`),
and Local Deep Research writes reports under `~/Documents/LocalDeepResearch`.
Both are also commonly deployed in containers; see [docker.md](docker.md).

ShellGPT keeps its chat history in the system temp directory (`/tmp` on
Linux, `/var/folders/.../T` on macOS), which no home-relative catalog entry
can reach, so on Linux and macOS it is not collected and must be copied by
hand; the Windows locations under `AppData/Local/Temp` are collected.

Muse Code keeps its launcher state beside the launcher. On Linux and macOS
that is `~/.local/bin`, which other tools share, so only Muse's own dot files
there (`.local/bin/.muse-*`: `.muse-version`, `.muse-release-info.json`,
`.muse-update-checked-at` and the like) are catalog entries; the
`muse-bin-<version>` binary next to them is not collected and leaves no
manifest row. On Windows the install directory
`AppData/Local/Programs/muse` is collected whole, and its
`muse-bin-<version>.exe` and staged `.muse-update.<pid>.exe` binaries are
excluded, so their `skipped_excluded` rows record the installed version and
size. A launcher installed anywhere else (`MUSE_INSTALL_DIR`) is not
collected. Two Muse Code locations are system-wide rather than per home and
must be copied by hand: the enterprise policy (the registry key
`HKLM\SOFTWARE\Policies\Muse` on Windows, and
`.enterprise-defaults.json` and `enterprise-policy.json`, read as
`/Library/Application Support/muse/` on macOS; the Linux location is not
known), and on Windows the elevated shell-sandbox setup root under
`%ProgramData%`.

## Remote development servers

Remote development state is collected too: `~/.vscode-server`,
`~/.cursor-server`, `~/.windsurf-server`, `~/.devin-server` and
`~/.kiro-server` keep the same `User` layout as the desktop editor, on the
WSL or SSH host rather than the workstation.

## Host state is not collected

The collectors take files from disk only. Running processes, process
environments, logged-in users, network connections, services and scheduled
tasks are not captured: the collectors supplement an EDR, which already
records that host state. Collectors before 1.6.0 wrote a `live/` snapshot of
it; see [CHANGELOG.md](../CHANGELOG.md). The host name is in the `hostname`
field of `collection.json`.

## Default exclusions

Model weights, Electron and editor caches, extension and daemon binaries,
embedding indexes, shadow git checkpoints, agent worktrees, and git clones of
plugin marketplaces are skipped by default. Each skipped path is still
recorded in the manifest with status `skipped_excluded` and its on-disk
size, so the investigator knows what was there. Pass `--full` to collect
them.

## Credentials

OAuth tokens and keys (`~/.claude/.credentials.json`, `~/.codex/auth.json`,
`~/.gemini/gemini-credentials.json`, `~/.cursor/auth.json`,
`~/.copilot/config.json`, `~/.cline/data/settings/providers.json`,
`~/.local/share/opencode/auth.json`, `~/.config/goose/secrets.yaml`,
`~/.factory/auth.v2.*`, ...) show which account an agent acted as, so they
are collected by default and flagged `secret: true`. Config files that
commonly embed API keys or MCP server environments (Continue's
`config.yaml`, Zed's `settings.json`, Crush's `crush.json`, Claude Code's
`.claude.json`, Claude Desktop's `claude_desktop_config.json`, Kiro powers'
`mcp.json`) are flagged the same way, as are the Electron `Local State`
files that hold the key for encrypted token caches. Run `--list` for the
full pattern list.

Cursor and Windsurf keep their auth tokens inside the same `state.vscdb`
that holds the chat history, so that file is collected unflagged; the keys
to redact are `cursorAuth/*` and `windsurfAuthStatus`. Kilo Code's
`kilo.db` and OpenCode's `opencode.db` embed tokens in their `account` and
`credential` tables and are flagged whole.

Use `--no-secrets` to leave credential files out. They are then recorded
with status `skipped_secret`.

## Pattern matching

Exclusion and credential patterns are matched relative to the directory
being collected, a home, a discovered project or a Docker volume's `_data`,
and `*` in them crosses `/`. The same `.claude/worktrees` pattern therefore
prunes both `~/.claude/worktrees` and a project's `.claude/worktrees`. The
sh collector matches with `case` and `find -path`, which are
case-sensitive. The PowerShell collector converts the patterns to regular
expressions and matches them, and the catalog globs, without regard to
case.

An exclusion wins over a credential pattern. An excluded directory is pruned
from the walk before any file in it is looked at, so a credential file
inside it is never collected or flagged; it is covered only by the
directory's `skipped_excluded` row. Exclusions are therefore written so that
they do not cover credential files: Hermes' installer checkout is excluded
entry by entry (`.hermes/hermes-agent/[!.]*` and
`.hermes/hermes-agent/.[!e]*`) so that `hermes-agent/.env` is still
collected. `[!...]` negated classes work in both collectors.
