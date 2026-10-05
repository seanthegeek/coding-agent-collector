# Collectors

The on-host half of coding-agent-collector: two single-file scripts that walk
every user's home directory, copy the on-disk artifacts of AI coding agents
into a staging area, hash them, and produce one `tar.gz` with a JSONL manifest.
Nothing is parsed on the host; that is the job of the analyst-side tool
described in the [project README](../README.md).

The evidence for every catalog entry, with citations and the level each
claim rests on, is one document per agent under
[research/](research/README.md).

VS Code, VSCodium and their forks are collected through their `User`
directories, which hold Copilot Chat sessions and extension state. The
globalStorage of the Cline, Roo Code, Kilo Code, Continue, Sourcegraph Cody
and Twinny extensions is claimed by nested catalog entries, so those files are attributed to the
extension's agent rather than to the editor, whichever editor they sit in. Shared cross-agent
directories such as `~/.agents` are collected too. Shell histories and
general-purpose `.env` files in the home or a project are not: like process
lists and logons, they are the EDR's job. An agent's own `.env` inside its
state directory, such as `~/.codex/.env` or `~/.hermes/.env`, is collected
and flagged `secret: true`.

There are two collectors with the same catalog, manifest schema and archive
layout:

- `collect-agent-artifacts.sh` is a single POSIX `sh` script with no
  dependencies beyond the base system. It runs under bash 3.2 (macOS
  `/bin/sh`), dash, ash and busybox, FreeBSD and OpenBSD `sh`, and zsh in sh
  emulation.
- `Collect-AgentArtifacts.ps1` is a single Windows PowerShell 5.1 script with
  no modules, for live Windows hosts. It also runs under PowerShell 7 on any OS.

Either script can collect a mounted disk image of any of the three platforms,
because every catalog entry is tried against every home directory.

The two scripts share one version; [CHANGELOG.md](CHANGELOG.md) lists what
changed in each, including manifest schema changes.

## Quick start

The paths below are relative to this `collectors/` directory. Both scripts are
self-contained, so copy whichever one you need to the host on its own.

```sh
# Live host, all users (run as root to read other users' homes)
sudo ./collect-agent-artifacts.sh -o /var/tmp/ir

# Mounted disk image (Linux, macOS or Windows volume)
sudo ./collect-agent-artifacts.sh -r /mnt/evidence -o /cases/host01

# Only two users, without credential files
sudo ./collect-agent-artifacts.sh -u alice,bob --no-secrets -o /var/tmp/ir
```

When the run finishes, the collector prints a summary on stdout:

```text
archive:    /var/tmp/ir/host01_20261003T165531Z_agent-artifacts.tar.gz
size:       55959669 (53.4 MiB)
sha256:     19c47a0e...
manifest:   /var/tmp/ir/host01_20261003T165531Z_agent-artifacts.manifest.jsonl
summary:    /var/tmp/ir/host01_20261003T165531Z_agent-artifacts.collection.json
log:        /var/tmp/ir/host01_20261003T165531Z_agent-artifacts.log
users:      4
projects:   12
collected:  5985 files, 110669230 bytes (105.5 MiB)
skipped:    7 excluded, 0 too large, 0 secret
errors:     2 (2 error_copy, 0 error_read)
docker:     4 volumes found, 1 collected, 0 unreadable
```

`size` and `sha256` are the archive's; `size` is in bytes, followed by
the same size in binary units (`B`, `KiB`, `MiB`, `GiB`, `TiB`, one
decimal). `users` counts the homes that produced at least one manifest
row, the `users_with_artifacts` list in `collection.json`; homes that were
scanned and held nothing are left out of the count but stay in `users`
there. `projects` counts the project directories collected from.
`collected` counts the manifest rows with status `collected` and their
bytes, followed by the same total in binary units. `skipped` counts the
`skipped_excluded`, `skipped_size` and `skipped_secret` rows, and `errors`
is the number of `error_copy` and `error_read` rows together, followed by
each of the two counts in parentheses. The `docker:` line appears only when a Docker
or Podman volume directory or Docker Desktop data was found; see
[Docker volumes](#docker-volumes). Progress lines (each user, catalog match
and project) go to stderr unless `-q` is given. They always go to the log.
A `User` line is written only for a home with at least one catalog match,
just before that match. The last progress line is `done`; the log file's
`done:` line also records the archive path, size in bytes and sha256.

### Windows

```powershell
# Live host, all profiles (run elevated to read other users' profiles)
powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -OutputDir C:\ir

# Mounted image or offline volume
powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -Root E:\ -OutputDir C:\cases\host01
```

`-ExecutionPolicy Bypass` is needed because fresh Windows installs default to
`Restricted`; it affects only that process and does not change machine policy.
The parameters mirror the sh options: `-OutputDir`, `-Root`, `-Users`,
`-Project`, `-Full`, `-NoSecrets`, `-NoProjects`, `-NoDocker`,
`-MaxFileSizeMB`, `-KeepStaging`, `-Inventory`, `-List`, `-Quiet`, `-Version`. `-o`, `-r`,
`-u`, `-p`, `-k` and `-q` are accepted as aliases. `-Users` takes one
comma-separated string. `-Project` takes a PowerShell array
(`-Project C:\src\a,C:\src\b`) rather than a repeated parameter. There is no
`-h`. `Get-Help .\Collect-AgentArtifacts.ps1 -Detailed` prints the parameter
help.

On Windows 10 1803 and later, Windows 11, and Server 2019 and later the script
writes a `tar.gz` through the built-in `tar.exe`, so the archive is identical in
form to the sh collector's. When `tar.exe` is not on the `PATH` (older hosts)
or fails, the script falls back to `System.IO.Compression` and produces a
`.zip`. The summary's `capabilities.archiver` records which archiver was chosen
at startup. It still says `tar.exe` after a `tar.exe` failure, so check the
archive's extension.

## Options

| Option | Meaning |
| --- | --- |
| `-o, --output DIR` | Where to write the archive, manifest, summary and log. Created if missing. Default: current directory. |
| `-r, --root DIR` | Alternate root such as a mounted disk image. Switches to image mode. `-r /` is live mode. |
| `-u, --users LIST` | Comma-separated usernames to collect. Default: every home directory found. Names are compared with the user name from the password database, or with the directory name for a home found by globbing. The sh collector compares case-sensitively and the PowerShell collector does not. Also limits the rootless Docker directories. |
| `-p, --project DIR` | Extra project directory whose project-level artifacts (`PROJECT_CATALOG`) are collected, as for a discovered project. Repeatable. It is a path on the machine running the collector and is never prefixed with the root, so in image mode give it including the mount point. A relative path is resolved against the current directory, in image mode too (sh: `cd` and `pwd` for an existing directory, otherwise joined to `pwd` as given; PowerShell: against the current location). A value given twice is collected once. A value that is not a directory (missing, a file, or not visible) is logged as `WARNING: project given with -p is not a directory: <path>: <error>` (`-Project` in the PowerShell message) and gets one `error_read` row; it is not listed in `collection.json` `projects`. Has no effect with `--no-projects`. |
| `--full` | Disable the default size exclusions (model blobs, caches, extension and daemon binaries, marketplace clones). |
| `--no-secrets` | Skip credential files. By default they are collected and flagged `secret: true` in the manifest. |
| `--no-projects` | Skip project-level artifact discovery and `-p`. |
| `--no-docker` | Skip Docker and Podman named volume enumeration (see [Docker volumes](#docker-volumes)). |
| `--max-file-size MB` | Skip individual files larger than this whole number of MiB. Default 256, `0` disables. |
| `-k, --keep-staging` | Keep the staging directory, `.stage-<archive name>` in the output directory, which holds the unpacked archive contents. |
| `--inventory` | Write nothing: walk the catalog with `lstat` only and print JSON Lines to stdout, one host line and one line per user and agent found. `-o` is ignored, and `-k`, `--no-secrets` and `--max-file-size` have no effect. See [Inventory mode](#inventory-mode). PowerShell: `-Inventory`. |
| `--list` | Print the five tables (home catalog, project catalog, exclusions, credential patterns, Docker volume names), then exit. |
| `-q, --quiet` | Print only the final summary. Progress lines still go to the log file. |
| `-V, --version` | Print `collect-agent-artifacts <version>` and exit. PowerShell: `-Version`. |
| `-h, --help` | Print the usage text and exit. sh only. |

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | An archive was written, even if individual files failed to copy (manifest status `error_copy`) or directories could not be read (`error_read`). With `--inventory`, the walk ran, even if homes or Docker data roots were unreadable. Also `--list`, `--version` and `--help`. |
| `1` | Usage error: unknown option, missing option value, or a `--max-file-size` that is not a whole number. PowerShell: a negative `-MaxFileSizeMB` or a parameter binding error. |
| `2` | Fatal: the root is not a directory, the output directory cannot be created or written, `tar` or `find` is missing (sh), the staging directory cannot be created (sh), or no archive could be written. With `--inventory` only the root and `find` checks apply. |
| `130` | sh only: interrupted by `INT` or `TERM`. The staging directory is removed unless `-k` is given. |

Environment: the sh collector reads `COLLECTOR_SH`, the shell used to run
the per-file workers that `find -exec` starts (default `sh`, recorded as
`capabilities.worker_shell`). It sets `LC_ALL=C` and puts `/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin`
ahead of the inherited `PATH`. The PowerShell collector reads
`COMPUTERNAME` for the host name (falling back to the DNS host name),
`SystemDrive` for the drive whose `Users` and `home` directories are globbed
and whose Docker paths are tried in live mode (default `C:`), `ProgramData`
for the live Docker volume and Docker Desktop paths, and `OS` (it uses
`tar.exe` only when that is `Windows_NT`).

## What gets collected

Run `--list` for the full catalog. Every catalog entry is tried against every
home directory, so macOS, Linux and Windows paths coexist and a Windows image
mounted on a Linux workstation is collected correctly.

Shared directories read by several agents are collected under the `shared`
agent name. When one tool keeps its state inside another tool's directory, as
Antigravity CLI does under `~/.gemini/antigravity-cli`, the nested catalog
entry wins: those files are collected once, attributed to the nested agent,
and left out of the enclosing agent's walk.

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

Project-level artifacts (`CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`,
`.cursorrules`, `.aider.chat.history.md`, Crush's per-project `.crush/crush.db`,
...) are collected from every directory referenced in agent state that can be
read with grep: Claude Code history and project list (in `~/.claude` and
`~/.claude-<name>` config homes), Codex session rollouts,
Qwen Code chats, Cline sessions and task history, Roo and Kilo task indexes,
Continue sessions, Gemini CLI's project registry, trusted folders and project
root markers, Antigravity's history, trusted workspaces and project cache,
Crush's project list, Goose legacy session files and the desktop app's recent
directories, OpenCode's legacy project store, Cursor CLI chat and ACP session
metadata, Copilot CLI session workspaces, Amp history, Factory Droid sessions,
Muse Code's trusted projects (`.config/muse/trust.json`) and session logs
(`workspace_root`),
Kiro CLI sessions and workspace roots, VS Code family workspace storage
including the remote server data directories, Hermes checkpoint project
records, Letta session index and local-backend transcripts, pi session
headers, trusted folders, crash log and experimental session metadata (which
also cover little-coder), Open Interpreter rollouts, OpenHands workspaces and
conversation metadata, PearAI sessions, OpenClaw workspace and agent
directories from its JSON5 config, nanobot workspace markers and config,
Tabby `file://` repositories, and the common directory of the files in each
Twinny embeddings manifest. A referenced path is used only if it is
absolute and names an existing directory that is not itself a home. In
image mode it is looked up under the root. The sh collector reads POSIX
paths only, so it skips drive-letter references in a Windows image. The
PowerShell collector maps `C:\...` and `file:///c:/...` references to the
same path under `-Root`, dropping the drive letter. On a live Windows host
it ignores POSIX paths. From each project only the `PROJECT_CATALOG`
entries are collected. Their rows have agent `project`, `home` set to the
project directory, and the user whose state referenced it (the first one,
when several did). `-p` directories join the same list. Each gets as its
user the owner of the home it sits under, or none. Agents that only record the project path inside SQLite
(Zed, Goose, OpenCode, Kilo Code, Kiro CLI, Hermes `state.db` and
`projects.db`, OpenClaw `openclaw.sqlite`, Tabby `ee/db.sqlite`, the PearAI
Roo fork in `state.vscdb`) are left to the analyst-side parser, as are Codex
and Open Interpreter rollouts compressed with zstd.

Most agents keep their state in a dot directory, but a few do not: Agent
Zero lives in its install directory (`~/agent-zero`, `~/Desktop/agent-zero`),
and Local Deep Research writes reports under `~/Documents/LocalDeepResearch`.
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

Remote development state is collected too: `~/.vscode-server`,
`~/.cursor-server`, `~/.windsurf-server`, `~/.devin-server` and
`~/.kiro-server` keep the same `User` layout as the desktop editor, on the
WSL or SSH host rather than the workstation.

### Host state is not collected

The collectors take files from disk only. Running processes, process
environments, logged-in users, network connections, services and scheduled
tasks are not captured: the collectors supplement an EDR, which already
records that host state. Collectors before 1.6.0 wrote a `live/` snapshot of
it; see [CHANGELOG.md](CHANGELOG.md). The host name is in the `hostname`
field of `collection.json`.

### Docker volumes

Several agents are commonly deployed in containers with their state in a
named volume rather than a home directory: Agent Zero's README runs it with
`-v a0_usr:/a0/usr`, Local Deep Research's compose file keeps its data in
`ldr_data`, and Ollama's Docker instructions use a volume named `ollama`.
The collectors enumerate volumes themselves, from the filesystem and never
through the `docker` binary, so the same code works live and on a disk
image. The volume directories tried, relative to the root (`/` live, `-r`
in image mode), are `var/lib/docker/volumes` (root Docker),
`var/lib/containers/storage/volumes` (root Podman) and
`ProgramData/Docker/volumes` (Windows containers), and under every
selected home `.local/share/docker/volumes` (rootless Docker) and
`.local/share/containers/storage/volumes` (rootless Podman). `-u` limits
the rootless directories to the named users; the system directories are
always tried. A volumes directory that is a symlink, or has a symlink on
the way to it, is noted in `collection.json` and not followed. A volume
whose own directory is a symlink is skipped without a row. A volume whose
`_data` is missing or a symlink is counted in `volumes_found`, logged, and
skipped without a row.

Each volume is `<volumes dir>/<name>/_data`. Its name is matched case-sensitively against the
`DOCKER_VOLUMES` table (`--list` prints it last, under
`# docker volumes (agent|volume name glob)`), and the first match wins. A matched
volume is collected whole: its rows have `user` `docker`, `home` the
volume's `_data` path and `agent` from the table, and its files are
archived under `fs/<original path>` like everything else. Exclusion and
credential patterns apply relative to `_data`, so the tables carry
volume-relative forms such as `tmp/playwright` and `secrets.env` beside the
home-relative ones. A volume that matches nothing is not collected. It gets
one `dir` row with status `skipped_unmatched_volume`, an empty `agent` and
its size, so a database volume or an agent with an unexpected volume name is
still visible.

`/var/lib/docker` is readable only by root. Run as root to collect system
volumes. When a volume directory exists but cannot be read, or a matched
volume cannot be walked completely, the collection carries on with
everything else, the stdout summary says so
(`docker:     3 volumes found, 1 collected, 1 unreadable (run as root to collect)`)
and `collection.json` gets a note naming the path. The exit code is still
`0` when an archive was written. `--no-docker` skips the enumeration.

Docker Desktop on Windows and macOS keeps Linux volumes inside its virtual
machine disk (the WSL `docker_data.vhdx` on Windows, `Docker.raw` on macOS),
which neither collector can reach. When Docker Desktop data is found
(`%ProgramData%\DockerDesktop`, a profile's `AppData\Local\Docker`, or
`~/Library/Containers/com.docker.docker`) the collectors only record a note
and append `; Docker Desktop VM disk not collected` to the summary line.
Collect those volumes from inside the VM, for example with
`docker run --rm -v VOLUME:/v -v "$PWD":/out alpine tar -czf /out/VOLUME.tgz -C /v .`.

### Default exclusions

Model weights, Electron and editor caches, extension and daemon binaries,
embedding indexes, shadow git checkpoints, agent worktrees, and git clones of
plugin marketplaces are skipped by default. Each skipped path is
still recorded in the manifest with status `skipped_excluded` and its on-disk
size, so the investigator knows what was there. Pass `--full` to collect them.

### Credentials

OAuth tokens and keys (`~/.claude/.credentials.json`, `~/.codex/auth.json`,
`~/.gemini/gemini-credentials.json`, `~/.cursor/auth.json`,
`~/.copilot/config.json`, `~/.cline/data/settings/providers.json`,
`~/.local/share/opencode/auth.json`, `~/.config/goose/secrets.yaml`,
`~/.factory/auth.v2.*`, ...) show which account an agent acted as, so they
are collected by default and flagged `secret: true`. Config files that
commonly embed API keys or MCP server environments (Continue's `config.yaml`,
Zed's `settings.json`, Crush's `crush.json`, Claude Code's `.claude.json`,
Claude Desktop's `claude_desktop_config.json`, Kiro powers' `mcp.json`) are
flagged the same way, as are the Electron `Local State` files that hold the
key for encrypted token caches. Run `--list` for the full pattern list.
Cursor and Windsurf keep their auth tokens inside the same `state.vscdb` that
holds the chat history, so that file is collected unflagged; the keys to
redact are `cursorAuth/*` and `windsurfAuthStatus`. Kilo Code's `kilo.db` and
OpenCode's `opencode.db` embed tokens in their `account` and `credential`
tables and are flagged whole. Use `--no-secrets` to leave credential
files out. They are then recorded with status `skipped_secret`.

Exclusion and credential patterns are matched relative to the directory being
collected, a home, a discovered project or a Docker volume's `_data`, and
`*` in them crosses `/`. The
same `.claude/worktrees` pattern therefore prunes both `~/.claude/worktrees`
and a project's `.claude/worktrees`. The sh collector matches with `case`
and `find -path`, which are case-sensitive. The PowerShell collector
converts the patterns to regular expressions and matches them, and the
catalog globs, without regard to case.

An exclusion wins over a credential pattern. An excluded directory is pruned
from the walk before any file in it is looked at, so a credential file inside
it is never collected or flagged; it is covered only by the directory's
`skipped_excluded` row. Exclusions are therefore written so that they do not
cover credential files: Hermes' installer checkout is excluded entry by entry
(`.hermes/hermes-agent/[!.]*` and `.hermes/hermes-agent/.[!e]*`) so that
`hermes-agent/.env` is still collected. `[!...]` negated classes work in both
collectors.

### Privileges

Run as root (sh) or from an elevated PowerShell (Windows) to collect every
user. Without that privilege, a live run still finishes and exits `0`. The
log gets a `WARNING: not running as root` (or `as Administrator`) line,
and:

- A home the responder cannot list or enter is still listed in `users`,
  gets one `error_read` row (`agent` empty, `path` and `home` the home
  directory), and is logged as `read failed: <home>: <error>`. The
  catalog is still tried against it, so a home that can be entered but
  not listed (mode `711`) still yields the entries that are not globs.
  Its `error_read` row does not put the user in `users_with_artifacts`.
  A discovered project directory or a `-p` directory that cannot be read
  gets the same row.
- Inside a walk, a directory that cannot be listed or entered gets one
  `error_read` row under the agent being walked, and a `read failed:` log
  line. sh: every directory `find` reaches is tested with `test -r` and
  `test -x` in the worker, and `error` is the first line `ls` printed for
  the same access, so the decision never depends on `find`'s localised
  message; `find` still logs its own `find:` line for the directory. The
  PowerShell collector writes the row when `Get-ChildItem` fails on the
  directory, with the exception message as `error`. On Linux and macOS a
  directory that can be listed but not entered fails that call only when
  it has entries, so an empty one gets a row from the sh collector alone.
  A catalog path whose parent cannot be entered is not seen by either
  collector and gets no row; the PowerShell collector logs a
  `stat failed:` line, with no row, for a matched path whose metadata it
  cannot read. A file
  that can be listed but not read is an `error_copy` row.
- The root-owned Docker and Podman data roots are reported as unreadable
  (see [Docker volumes](#docker-volumes)).

## Inventory mode

`--inventory` (sh) and `-Inventory` (PowerShell) answer a fleet question,
which users have used which agents on which hosts, without collecting
anything. Run the script on every host through the EDR console and keep
what it prints: stdout is the whole result. Nothing is created, copied,
hashed or written, not even a log, and `-o` is ignored. When `-o` or
`-OutputDir` is given, a `NOTE: --inventory writes nothing; -o <dir>
ignored` line (PowerShell: `-OutputDir <dir>`) goes to stderr, unless `-q`
is given.

The walk is the collection walk with the copy step removed. Homes are
enumerated as for a collection and honour `-u` and `-r`. Every `CATALOG`
entry is expanded against every home, nested entries claim their subtree
from the enclosing entry, and the `EXCLUDES` patterns prune their subtrees
(not with `--full`), so the counts cover what a collection would take.
Regular files are counted with their `lstat` size and modification time
(PowerShell: `Length` and `LastWriteTimeUtc`); symlinks and reparse points
are neither followed nor counted. Docker and Podman volumes are enumerated
as in [Docker volumes](#docker-volumes) unless `--no-docker` is given, and a
volume that matches a `DOCKER_VOLUMES` line is walked like a home. Project
discovery runs, so the project count is available, but `PROJECT_CATALOG`
files are not walked. Credential files are never opened: discovery sources
that match `SECRET_GLOBS` (`.claude.json`, `.openclaw*/openclaw.json`,
`.clawdbot/clawdbot.json`, `.nanobot*/config.json`, `.tabby/config.toml`)
are skipped in this mode, so the project count can be lower than the
number of projects a collection takes from. The other discovery sources
are read as in a collection, which updates their access time on
filesystems that track it.

stdout carries JSON Lines and nothing else: first one `host` line, then one
`agent` line per user and agent, users in enumeration order and each user's
agents in order of their first catalog match, then the Docker volume agents
under user `docker`. Progress lines go to stderr unless `-q` is given. The
exit code is `0` once the walk has run, including when homes or Docker data
roots were unreadable.

```jsonl
{"type":"host","host":"host01","collector":"1.6.0","mode":"live","at":"2026-10-04T16:31:54Z","users_scanned":3,"users_unreadable":0,"docker_volumes":3}
{"type":"agent","host":"host01","user":"alice","agent":"claude-code","files":6,"bytes":318,"first":"2026-09-15T01:02:03Z","last":"2026-10-04T16:31:11Z","projects":29,"evidence":".claude,.claude.json*"}
{"type":"agent","host":"host01","user":"docker","agent":"agent-zero","files":2,"bytes":63,"first":"2026-10-04T16:31:11Z","last":"2026-10-04T16:31:11Z","projects":0,"evidence":"*a0_usr"}
```

The `host` line, one per run, keys in this order:

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | string | `host`. |
| `host` | string | The host name, as in `collection.json` `hostname`: sh `hostname`, else `uname -n`; PowerShell `COMPUTERNAME`, else the DNS host name. Read from the machine running the collector, so with `-r` it is the analyst workstation's name. |
| `collector` | string | The collector version, as printed by `--version`. |
| `mode` | string | `live`, or `image` with `-r`. |
| `at` | string | UTC start time to the second, `2026-10-04T16:31:54Z`. |
| `users_scanned` | number | Home directories walked after `-u`. sh: every enumerated home that exists as a directory, readable or not. PowerShell: the same, plus enumerated profiles that .NET reports as missing although their parent directory lists them (access denied). A `ProfileList` entry whose directory is gone is not counted. |
| `users_unreadable` | number | Of those, the homes that cannot be read. sh: a home for which `test -r` or `test -x` fails, so it cannot be listed or entered; its globs match nothing. PowerShell: a profile .NET reports as missing although its parent lists it, or one whose entries cannot be listed. Each is also logged to stderr as `WARNING: home of <user> is not readable: <home>` (sh, and PowerShell for listable-but-unreadable profiles; the PowerShell `profile not accessible (skipped)` line covers the rest). As root, or as Administrator with access, this is `0`; without, other users' homes are counted here. A directory that cannot be listed inside a readable home is not counted anywhere: its files are simply missing from the totals. |
| `docker_volumes` | number | Volume directories found under the Docker and Podman volume roots, matched or not, as `collection.json` `docker.volumes_found`. `0` with `--no-docker`. Without root the root-owned data roots cannot be entered, so their volumes are not found; a `NOTE: docker:` line on stderr says so unless `-q` is given. |

One `agent` line per user and agent with at least one regular file under
its matched `CATALOG` paths after exclusions and nested claims, keys in this
order. A match that holds no files of its own gives no line: an empty
directory, a symlink, an excluded-only tree, or a `~/.gemini` that holds
only the `antigravity-cli` directory claimed by the nested `antigravity`
entry. The same rule applies to Docker volumes. `files` is therefore never
`0`.
The `shared` entries are not inventoried, and `project` never appears.

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | string | `agent`. |
| `host` | string | As on the host line. |
| `user` | string | The home's user, as in the manifest, or `docker` for a matched Docker or Podman volume. |
| `agent` | string | The catalog agent name, or for a volume the `DOCKER_VOLUMES` agent. |
| `files` | number | Regular files under the agent's matched paths after exclusions, with nested entries' subtrees left to their own agent. |
| `bytes` | number | Their total size in bytes. |
| `first`, `last` | string | The earliest and latest modification time of those files, UTC to the second. Empty when no modification time was available (sh on a host with neither GNU nor BSD `stat`). |
| `projects` | number | Project directories discovered for this user, the same number on each of the user's lines: discovery does not record which agent's state named a project. A project named by several users counts for the first of them in enumeration order, as in a collection, and a `-p` directory counts for the user whose home contains it. `0` for `docker` lines and with `--no-projects`. |
| `evidence` | string | The `CATALOG` globs (the part after `agent\|`) that matched, in catalog order, joined by commas, so no path below the home is printed. For a volume, the `DOCKER_VOLUMES` globs that matched. |

Strings are JSON-escaped: the sh collector escapes backslash, double
quote, tab, carriage return and newline; PowerShell's `ConvertTo-Json`
also escapes other control characters, and Windows PowerShell 5.1 escapes
`<`, `>`, `&` and `'` as `\u` sequences. The analyzer's
`inventory` command reads these lines from saved stdout files and builds a
fleet CSV; see [the analyzer README](../analyzer/README.md#inventory).

## Output

The output directory receives five files named
`<host>_<UTC time>_agent-artifacts`. In the host name, characters other
than `A-Za-z0-9._-` become `-`:

```text
host_20261003T165531Z_agent-artifacts.tar.gz          the archive
host_20261003T165531Z_agent-artifacts.tar.gz.sha256   its hash, as "<hex>  <file name>" (sha256sum format)
host_20261003T165531Z_agent-artifacts.manifest.jsonl  the manifest (the archive holds a copy)
host_20261003T165531Z_agent-artifacts.collection.json the run summary (the archive holds a copy)
host_20261003T165531Z_agent-artifacts.log             the log (the archive holds a copy)
.stage-host_20261003T165531Z_agent-artifacts/         the staging directory, only with -k
```

The sh collector writes the archive with `tar -czf`. If that fails, it pipes
`tar` through `gzip`. If that fails too, it writes an uncompressed `.tar`.
The PowerShell collector writes a `.tar.gz` with `tar.exe`, or a `.zip`
(see [Windows](#windows)). The log is copied into the archive before
archiving starts, so only the copy outside has the final `done` line with
the archive's size and hash.

Inside the archive (the sh collector's tar members start with `./`):

```text
fs/<original path>          collected files, mirroring the source filesystem
manifest.jsonl
collection.json
collector.log
```

Each manifest row is one JSON object:

```json
{"user":"alice","home":"/home/alice","agent":"claude-code",
 "path":"/home/alice/.claude/projects/-srv-proj/s1.jsonl",
 "archive_path":"fs/home/alice/.claude/projects/-srv-proj/s1.jsonl",
 "type":"file","size":97,"mtime":1791046385,"atime":1791046385,"ctime":1791046385,
 "btime":1791046385,"uid":1000,"gid":1000,"mode":"644","sha256":"...",
 "secret":false,"status":"collected","target":"","error":""}
```

| Field | Meaning |
| --- | --- |
| `user` | Owner of the home the path was found under. For a project file, the user whose agent state referenced the project (empty for a `-p` directory outside every home). `docker` for volume rows. |
| `home` | The base the path was collected relative to: the home directory, the project directory, or a volume's `_data`, including the `-r` root. |
| `agent` | Catalog agent name. `project` for files found through the project catalog, the `DOCKER_VOLUMES` agent for a matched volume, and empty for `skipped_unmatched_volume` and for the `error_read` row of a home, project or `-p` directory. |
| `path` | The original full path, including the `-r` root in image mode. |
| `archive_path` | Where the file is in the archive: `fs/<original path>`. Set for `collected` rows, and for `symlink` rows from the sh collector. Empty otherwise. |
| `type` | `file`, `symlink`, or `dir` (an excluded directory, an unmatched volume, or an `error_read` directory). |
| `size` | Bytes. `0` for an `error_read` row. For any other `dir` row, the size of everything under it: `du -sk` × 1024 from the sh collector, the sum of file lengths from the PowerShell collector. |
| `mtime`, `atime`, `ctime`, `btime` | Epoch seconds, read before the copy. `btime` (creation) is `0` where the platform cannot report it, and `ctime` is `0` from the PowerShell collector. All four are `0` for an excluded directory from the sh collector, for an unmatched volume, for an `error_read` row of a `-p` value that does not exist, and on a host with neither GNU nor BSD `stat` (where `uid`, `gid` and `mode` are `0` too). |
| `uid`, `gid`, `mode` | Numeric owner and group, and the permission bits as an octal string (`"644"`), from `lstat`. `0`, `0` and `""` from the PowerShell collector. |
| `owner`, `attributes` | PowerShell collector only: the owning account name (or SID when the name cannot be resolved) and the attribute list, such as `Archive, ReparsePoint`. |
| `sha256` | SHA-256 of the staged copy, set only for `collected` rows. The sh collector leaves it empty when it found no hash tool (`capabilities.hash_tool` is `none`). |
| `secret` | `true` when the path, relative to `home`, matched a credential pattern. |
| `status` | See below. |
| `target` | For a symlink, its target as stored. The PowerShell collector joins several reparse point targets with `;`. |
| `error` | For `error_copy`, why the copy failed: `cp`'s message or the .NET exception. For `error_read`, why the directory could not be read: the first line of `ls`'s message (sh, for example `ls: cannot open directory '/home/carol': Permission denied`) or the .NET exception message. |

| Status | Meaning |
| --- | --- |
| `collected` | Copied, hashed and archived. |
| `symlink` | A symbolic link (on Windows any reparse point, including junctions), recorded with its target and never followed. The sh collector recreates the link in the archive. The PowerShell collector records it in the manifest only. |
| `skipped_excluded` | Matched an `EXCLUDES` pattern. An excluded directory is one `dir` row with its total size. |
| `skipped_size` | Larger than `--max-file-size`. |
| `skipped_secret` | A credential file left out by `--no-secrets`. |
| `error_copy` | Could not be read or copied; see `error`. |
| `skipped_unmatched_volume` | A Docker or Podman volume that matched no `DOCKER_VOLUMES` line: one `dir` row with its size, `user` `docker`, an empty `agent`, and `home` and `path` both the volume's `_data`. |
| `error_read` | A directory that could not be listed or entered: a home, a project directory, a `-p` value that is not a directory, or a directory inside a walk (see [Privileges](#privileges)). One `dir` row with size `0`, no `archive_path` and the reason in `error`; nothing under it is collected. |

A path that was not excluded is checked first for being a symlink, then
for `--no-secrets`, then for size. A symlink is therefore never skipped for
size, and a credential file is `skipped_secret` under `--no-secrets`
whatever its size.
Timestamps come from `lstat` on the original file (sh), or from the item's
times before the copy (PowerShell). On a live Windows host the archive
path is `fs/<drive letter>/<path>`, for example
`fs/C/Users/alice/.claude/history.jsonl`. In image mode it is relative to
the root, as on other platforms.

`collection.json` records the run:

| Field | Meaning |
| --- | --- |
| `tool`, `version` | `collect-agent-artifacts` and the collector version. |
| `hostname` | The host name, the only record of it in the output. sh: `hostname`, else `uname -n`. PowerShell: `COMPUTERNAME`, else the DNS host name. Always read from the machine running the collector, so in image mode (`-r`) it is the analyst workstation's name, not the imaged host's. |
| `mode` | `live` or `image`. |
| `root` | The `-r` root. In live mode, `/` (sh) or `\` (PowerShell). |
| `platform` | sh: `uname -s`, `-r` and `-m`. PowerShell: `Windows <OS version> <PROCESSOR_ARCHITECTURE> PowerShell <version>`. |
| `run_as_uid` | sh only: the numeric uid the collector ran as, as a string. |
| `run_as`, `run_as_admin` | PowerShell only: the account the collector ran as, and whether it was elevated. |
| `started`, `finished` | UTC to the second, `2026-10-03T16:55:31Z`. `finished` is taken before archiving. |
| `options` | `full`, `no_secrets`, `max_file_size_bytes` (`0` means no limit), `users_filter` (the `-u` string), `no_docker`. `--no-projects` and `-p` are not recorded. |
| `capabilities` | sh: `hash_tool` (`sha256sum`, `shasum`, `sha256`, `openssl` or `none`), `stat_mode` (`gnu`, `gnu0` for GNU `stat` without birth time, `bsd` or `none`) and `worker_shell`. PowerShell: `hash_tool` (`Get-FileHash`) and `archiver` (`tar.exe` or `ZipFile`, as chosen at startup). |
| `users`, `homes` | Parallel lists of every user and home scanned, including homes with no agent state. |
| `users_with_artifacts` | The users whose home produced at least one manifest row, in the order of `users`. Rows from discovered projects and Docker volumes do not count. The stdout `users:` line is its length. |
| `projects` | The project directories collected from, discovered or given with `-p`. A `-p` value that is not a directory is left out and has an `error_read` row instead. |
| `counts` | Rows per status (`collected`, `symlink`, `skipped_excluded`, `skipped_size`, `skipped_secret`, `error_copy`, `skipped_unmatched_volume`, `error_read`) and `collected_bytes`. |
| `docker` | `volumes_found`, `volumes_collected`, `unreadable` and `docker_desktop`; see [Docker volumes](#docker-volumes). |
| `notes` | Messages about what could not be collected, such as an unreadable or symlinked Docker volume directory, or Docker Desktop data. |
| `archive` | The archive file name as chosen at startup: `.tar.gz`, or `.zip` from the PowerShell collector without `tar.exe`. It does not reflect a later fallback to `.tar` or `.zip`. |

The copy of each file is hashed after staging, so the hash matches the bytes
in the archive even if a running agent appended to the source afterwards.

## Deployment through an EDR

The script is a single file with no interactive prompts, reads nothing from
stdin, and writes everything under `-o`. From CrowdStrike RTR, SentinelOne
RemoteOps, Defender Live Response or Palo Alto Networks Cortex XDR Live
Terminal, upload the script, run it with `-o` pointing at a directory you can
retrieve from, then pull the `tar.gz`. Use `-q` to keep the console output to
the final summary. Runtime on a developer workstation with several agents
installed is well under a minute.

For a fleet inventory, run the script with `--inventory` (`-Inventory`) and
no `-o`: nothing is uploaded back or left on the host, and the console
output of the run is the result. Save each host's stdout as its own file
(the EDR console's output export or a copy and paste of the response) and
pass the files to the analyzer's `inventory` command. Add `-q` so stderr
stays empty; stderr never mixes into stdout, but some consoles show both
together.

On Windows, files held open by a running editor (Cursor's `state.vscdb`,
Electron LevelDB stores) are read with shared access so they still copy.
Reparse points (symlinks and junctions) are recorded with their target and
never followed. Paths longer than 260 characters fail to copy under Windows
PowerShell 5.1 unless long paths are enabled on the host; the failure is
recorded as `error_copy`.

Note on access times: copying a file updates its `atime` on filesystems that
track it. The manifest records the pre-copy `atime` from `lstat`, taken before
the copy. On a disk image, mount it read-only with `noatime`.

## Testing

```sh
tests/smoke.sh          # under sh
tests/smoke.sh dash
tests/smoke.sh bash
printf '#!/bin/sh\nexec busybox ash "$@"\n' > /tmp/ash && chmod +x /tmp/ash && tests/smoke.sh /tmp/ash
printf '#!/bin/sh\nexec zsh --emulate sh "$@"\n' > /tmp/zsh-sh && chmod +x /tmp/zsh-sh && tests/smoke.sh /tmp/zsh-sh
tests/smoke.sh posh
shellcheck -s sh -S warning collect-agent-artifacts.sh
tests/catalog-sync.sh   # the five tables, --list output and the analyzer copy agree
pwsh -File tests/smoke.ps1
powershell.exe -ExecutionPolicy Bypass -File tests\smoke.ps1   # on Windows
```

`tests/smoke.sh [SHELL]` runs the collector script under `SHELL` (default
`sh`, a name on the `PATH` or a path), and passes the same shell to the
`find -exec` workers through `COLLECTOR_SH`. Every collection run but one is
in image mode with `--max-file-size 1`; the exception is a live run limited
to a user that does not exist (`-u no-such-user-cac --no-docker
--no-projects`), which checks that no `live/` directory or `live` row
appears. It works in a `cac-smoke.*` directory under `TMPDIR`
(default `/tmp`). The directory is removed when every check passes and kept,
with its path printed, when one fails. The exit status is `0` or `1`.
`tests/smoke.ps1` takes `-Collector PATH` to test a copy of the script other
than the one beside it, which is how the test runs under Windows PowerShell
5.1 from a WSL checkout. It works under the system temp directory, keeps it
on failure in the same way, and skips the symlink checks, saying so, where
creating symlinks is not permitted.

Each smoke test builds a fake disk image with two users, a service account,
awkward filenames, a symlink, credential files, excluded directories, an
oversized file and projects referenced from agent state, then checks the
manifest, hashes and archive contents. The sh test also has a `nobody`
account to skip. It is POSIX sh too, and its JSON validity and hash
cross-check steps run only when `python3` is available. The PowerShell test
uses a Windows profile tree with drive-letter and `file:///` project
references and runs under both PowerShell 5.1 and 7. Both smoke tests also
build root and rootless Docker volumes, one matched and one unmatched, check
`--no-docker` and the Docker Desktop note, and run `--no-secrets`, `--full`
and `-u`. The sh test adds an unreadable volume and data root when it is not
run as root. Both run `--inventory` / `-Inventory` against the same image
and check the key order of both line types, one known line's `files`,
`bytes`, `first`, `last` and `evidence`, that an excluded subtree is not
counted (and is with `--full`), the Docker volume lines, `-u`,
`--no-docker`, that nothing is written in the current directory or under
`-o`, that stdout stays pure JSON Lines with and without `-q`, and, on a
POSIX host not run as root, that an unreadable home is counted in
`users_unreadable`.

`tests/catalog-sync.sh` extracts the five tables from both scripts and fails
if they differ. When `pwsh` is on the `PATH` it also compares `--list` with
`-List`. It also fails when `analyzer/agent_analyzer/catalog.txt` is not
identical to `--list`. The repository's pre-commit hook in `.githooks/`
(enable it once per clone with `git config core.hooksPath .githooks`)
refuses a commit that stages either collector or the analyzer copy while the
copy is stale or the tables differ; the linters run in CI only. CI (`.github/workflows/ci.yml`) runs the
drift test and shellcheck, the sh smoke test under sh, dash, bash, busybox
ash, zsh and posh, a lint job, the PowerShell smoke test under PowerShell 7 on Linux and
Windows PowerShell 5.1 on Windows, and the analyzer tests, on every push to
`main` and every pull request.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
