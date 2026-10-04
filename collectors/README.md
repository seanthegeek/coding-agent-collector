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
extension's agent rather than to the editor, whichever editor they sit in. Shell histories and shared cross-agent
directories such as `~/.agents` and `~/.env` are collected too.

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

The final lines on stdout give the archive path, size and SHA-256:

```
archive:    /var/tmp/ir/host01_20261003T165531Z_agent-artifacts.tar.gz
size:       55959669
sha256:     19c47a0e...
collected:  5985 files, 110669230 bytes
skipped:    7 excluded, 0 too large, 0 secret
errors:     2
docker:     4 volumes found, 1 collected, 0 unreadable
```

The `docker:` line appears only when a Docker or Podman volume directory or
Docker Desktop data was found; see [Docker volumes](#docker-volumes).

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
`-Project`, `-Full`, `-NoSecrets`, `-NoLive`, `-NoProjects`, `-NoDocker`,
`-MaxFileSizeMB`, `-KeepStaging`, `-List`, `-Quiet`, `-Version`.

On Windows 10 1803 and later, Windows 11, and Server 2019 and later the script
writes a `tar.gz` through the built-in `tar.exe`, so the archive is identical in
form to the sh collector's. Older hosts fall back to `System.IO.Compression`
and produce a `.zip`; the summary's `capabilities.archiver` says which.

## Options

| Option | Meaning |
| --- | --- |
| `-o, --output DIR` | Where to write the archive, manifest, summary and log. Default: current directory. |
| `-r, --root DIR` | Alternate root such as a mounted disk image. Switches to image mode and disables the live snapshot. |
| `-u, --users LIST` | Comma-separated usernames to collect. Default: every home directory found. |
| `-p, --project DIR` | Extra project directory to collect. Repeatable. |
| `--full` | Disable the default size exclusions (model blobs, caches, extension and daemon binaries, marketplace clones). |
| `--no-secrets` | Skip credential files. By default they are collected and flagged `secret: true` in the manifest. |
| `--no-live` | Skip the live system snapshot. |
| `--no-projects` | Skip project-level artifact discovery. |
| `--no-docker` | Skip Docker and Podman named volume enumeration (see [Docker volumes](#docker-volumes)). |
| `--max-file-size MB` | Skip individual files larger than this. Default 256, `0` disables. |
| `-k, --keep-staging` | Keep the staging directory next to the archive. |
| `--list` | Print the artifact catalog, exclusions and secret patterns, then exit. |
| `-q, --quiet` | Only print the final summary. Everything still goes to the log file. |

Exit code is `0` when an archive was written, even if individual files failed
to copy. Per-file failures are recorded in the manifest with status
`error_copy`. Exit `1` is a usage error and `2` is a fatal error such as an
unwritable output directory.

## What gets collected

Run `--list` for the full catalog. Every catalog entry is tried against every
home directory, so macOS, Linux and Windows paths coexist and a Windows image
mounted on a Linux workstation is collected correctly.

Shared directories read by several agents are collected under the `shared`
agent name. When one tool keeps its state inside another tool's directory, as
Antigravity CLI does under `~/.gemini/antigravity-cli`, the nested catalog
entry wins: those files are collected once, attributed to the nested agent,
and left out of the enclosing agent's walk. Project `.env` files are collected from discovered project
directories because Aider, Gemini CLI, Qwen Code and Continue read them; they
are flagged `secret: true` like every other credential file.

Home directories come from `getent passwd` or `/etc/passwd` (prefixed with the
root in image mode), `dscl` on macOS, the registry `ProfileList` on Windows,
and globbing `home/*`, `Users/*`, `root`, `var/root`, `usr/home/*` and
`export/home/*` under the root. The `Public`, `Default` and `All Users`
profile directories are skipped. Service accounts
with real homes are included because agents run as them too, for example the
`ollama` system user.

Project-level artifacts (`CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`,
`.cursorrules`, `.aider.chat.history.md`, Crush's per-project `.crush/crush.db`,
...) are collected from every directory referenced in agent state that can be
read with grep: Claude Code history and project list, Codex session rollouts,
Qwen Code chats, Cline sessions and task history, Roo and Kilo task indexes,
Continue sessions, Gemini CLI's project registry, trusted folders and project
root markers, Antigravity's history, trusted workspaces and project cache,
Crush's project list, Goose legacy session files and the desktop app's recent
directories, OpenCode's legacy project store, Cursor CLI chat and ACP session
metadata, Copilot CLI session workspaces, Amp history, Factory Droid sessions,
Kiro CLI sessions and workspace roots, VS Code family workspace storage
including the remote server data directories, Hermes checkpoint project
records, Letta session index and local-backend transcripts, pi session
headers, trusted folders, crash log and experimental session metadata (which
also cover little-coder), Open Interpreter rollouts, OpenHands workspaces and
conversation metadata, PearAI sessions, OpenClaw workspace and agent
directories from its JSON5 config, nanobot workspace markers and config,
Tabby `file://` repositories, and the common directory of the files in each
Twinny embeddings manifest. Each project is attributed to the user whose
state referenced it. Agents that only record the project path inside SQLite
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

Remote development state is collected too: `~/.vscode-server`,
`~/.cursor-server`, `~/.windsurf-server`, `~/.devin-server` and
`~/.kiro-server` keep the same `User` layout as the desktop editor, on the
WSL or SSH host rather than the workstation.

### Live system snapshot

The files on disk say what the agents did; the snapshot says what was
running when the collector ran. In live mode (not with `-r`, and skipped by
`--no-live` / `-NoLive`) the collector writes a `live/` directory of plain
text files, each the output of one command or query with a `# command`
header line, and records every file in the manifest under the agent name
`live`. It answers the questions a responder has before opening a transcript:
is an agent or gateway still running, as which user, started when, from which
directory, with which API keys and endpoints in its environment, listening
on which port, and who was logged in.

| File | macOS, Linux, BSD | Windows |
| --- | --- | --- |
| `live/system.txt` | `hostname`, `uname -a`, `date -u`, `uptime`, `id`, `mount`, `df -k`, `/etc/os-release`, `sw_vers` | hostname, UTC time, `Win32_OperatingSystem`, `Win32_ComputerSystem` |
| `live/users.txt` | `getent passwd` or `/etc/passwd`; `dscl . -list /Users NFSHomeDirectory` on macOS | the `ProfileList` registry key and `Win32_UserAccount` |
| `live/logins.txt` | `who`, `last -n 50` | `query user`, `Win32_LoggedOnUser` |
| `live/processes.txt` | `ps` with pid, parent, user, start time, elapsed time and full command line | `Win32_Process` with command line, owner, session and creation time |
| `live/agent-processes.txt` | the lines of the process list whose command line matches an agent name (the `AGENT_PROC_RE` list in the script), with the collector itself removed | the same filter over `Win32_Process` |
| `live/environ/<pid>.txt` | for each agent process on Linux, its environment block from `/proc/<pid>/environ` and its working directory from `/proc/<pid>/cwd`; flagged `secret: true` because environments hold API keys, and omitted with `--no-secrets` | not captured |
| `live/network.txt` | `ss -tunap`, else `netstat -anp` or `netstat -an`: listening sockets and connections with owning process where the platform allows | `Get-NetTCPConnection` with owning process, else `netstat -ano` |
| `live/services.txt` | `launchctl list` on macOS, `systemctl list-units --type=service --all` on systemd hosts | `Win32_Service` with state, start mode, account and path |
| `live/scheduled-tasks.txt` | not written (user units and launch agents are collected as files through the catalog) | scheduled task names, actions and run accounts |

Each command runs once; its error output is written into the same file and
a failure never stops the run, so a hardened host still yields the files it
can. Nothing in the snapshot is parsed on the host, and the analyzer does
not read it yet; it is for the responder to read alongside the timeline.

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
always tried. Symlinked volume directories are noted and not followed.

Each volume is `<volumes dir>/<name>/_data`. Its name is matched against the
`DOCKER_VOLUMES` table (`--list` prints it last, under
`# docker volumes (agent|volume name glob)`), first match wins. A matched
volume is collected whole: its rows have `user` `docker`, `home` the
volume's `_data` path and `agent` from the table, and its files are
archived under `fs/<original path>` like everything else. Exclusion and
credential patterns apply relative to `_data`, so the tables carry
volume-relative forms such as `tmp/playwright` and `secrets.env` beside the
home-relative ones. A volume that matches nothing is not collected; it gets
one `dir` row with status `skipped_unmatched_volume` and its size, so a
database volume or an agent with an unexpected volume name is still visible.

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
tables and are flagged whole. Process environments captured under
`live/environ/` are flagged the same way. Use `--no-secrets` to leave them
out; they are then recorded with status `skipped_secret`.

Exclusion and credential patterns are matched relative to the directory being
collected, a home, a discovered project or a Docker volume's `_data`, and
`*` in them crosses `/`. The
same `.claude/worktrees` pattern therefore prunes both `~/.claude/worktrees`
and a project's `.claude/worktrees`.

An exclusion wins over a credential pattern. An excluded directory is pruned
from the walk before any file in it is looked at, so a credential file inside
it is never collected or flagged; it is covered only by the directory's
`skipped_excluded` row. Exclusions are therefore written so that they do not
cover credential files: Hermes' installer checkout is excluded entry by entry
(`.hermes/hermes-agent/[!.]*` and `.hermes/hermes-agent/.[!e]*`) so that
`hermes-agent/.env` is still collected. `[!...]` negated classes work in both
collectors.

## Output

```
host_20261003T165531Z_agent-artifacts.tar.gz          the archive
host_20261003T165531Z_agent-artifacts.tar.gz.sha256   its hash
host_20261003T165531Z_agent-artifacts.manifest.jsonl  copy of the manifest
host_20261003T165531Z_agent-artifacts.collection.json copy of the run summary
host_20261003T165531Z_agent-artifacts.log             copy of the log
```

Inside the archive:

```
fs/<original path>      collected files, mirroring the source filesystem
live/                   live snapshot (live mode only)
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

`status` is one of `collected`, `symlink`, `skipped_excluded`, `skipped_size`,
`skipped_secret`, `error_copy` or `skipped_unmatched_volume` (a Docker or
Podman volume that matched no `DOCKER_VOLUMES` line; one `dir` row with its
size, `user` `docker` and `home` and `path` both the volume's `_data`). Timestamps are epoch seconds from `lstat` on
the original file; `btime` is `0` where the platform cannot report it. Rows
written by the Windows collector add `owner` (account name or SID) and
`attributes` (NTFS attribute list), set `uid`, `gid` and `mode` to `0` and
`""`, and set `ctime` to `0` because Windows does not expose the change time.
On a live Windows host the archive path is `fs/<drive letter>/<path>`, for
example `fs/C/Users/alice/.claude/history.jsonl`; in image mode it is relative
to the root as on other platforms.
`collection.json` records the run: tool version, mode, root, options
(`full`, `no_secrets`, `no_live`, `max_file_size_bytes`, `users_filter`,
`no_docker`), users, homes, projects, `counts` per status (including
`skipped_unmatched_volume`) and collected bytes, `docker` (`volumes_found`,
`volumes_collected`, `unreadable`, `docker_desktop`), and `notes`, a list of
messages about what could not be collected, such as an unreadable Docker
volume directory.

Symlinks are recreated in the archive and their target recorded, never
followed. The copy of each file is hashed after staging, so the hash matches
the bytes in the archive even if a running agent appended to the source
afterwards.

## Deployment through an EDR

The script is a single file with no interactive prompts, reads nothing from
stdin, and writes everything under `-o`. From CrowdStrike RTR, SentinelOne
RemoteOps, Defender Live Response or Palo Alto Networks Cortex XDR Live
Terminal, upload the script, run it with `-o` pointing at a directory you can
retrieve from, then pull the `tar.gz`. Use `-q` to keep the console output to
the final summary. Runtime on a developer workstation with several agents
installed is well under a minute.

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
tests/smoke.sh          # under /bin/sh
tests/smoke.sh dash
tests/smoke.sh bash
tests/smoke.sh ash      # busybox
shellcheck -s sh collect-agent-artifacts.sh
tests/catalog-sync.sh   # the five tables match between the sh and ps1 scripts
pwsh -File tests/smoke.ps1
powershell.exe -ExecutionPolicy Bypass -File tests\smoke.ps1   # on Windows
```

Each smoke test builds a fake disk image with two users, a service account,
awkward filenames, a symlink, credential files, excluded directories, an
oversized file and projects referenced from agent state, then checks the
manifest, hashes and archive contents. The sh test is POSIX sh too; its JSON
validity and hash cross-check steps use `python3` when available. The
PowerShell test uses a Windows profile tree with drive-letter and `file:///`
project references and runs under both PowerShell 5.1 and 7. The catalog drift
test extracts the five tables from both scripts and fails if they differ.
Both smoke tests also build root and rootless Docker volumes, one matched and
one unmatched, and check `--no-docker`; the sh test adds an unreadable
volume when it is not run as root.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
