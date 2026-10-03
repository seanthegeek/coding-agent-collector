# coding-agent-collector

Forensic collector for the on-disk artifacts of AI coding agents and
assistants. It walks every user's home directory, copies the artifacts into a
staging area, hashes them, and produces one `tar.gz` with a JSONL manifest.

Covered tools, with how each one's catalog entries were validated:

| Tool | Validation |
| --- | --- |
| Claude Code, Antigravity CLI, Codex CLI, Copilot CLI, Ollama | Real install plus source |
| Gemini CLI, Qwen Code, Aider, Continue, Goose, Zed, OpenCode, Crush, Cline, Roo Code, Kilo Code | Source code of the project |
| Amp, Factory Droid, Augment | Shipped npm bundle strings plus official docs |
| Kiro | Amazon Q CLI source, Kiro CLI binary strings, official docs |
| Cursor, Windsurf, Claude Desktop, ChatGPT Desktop | Official docs, vendor forums, published DFIR write-ups |

VS Code, VSCodium and their forks are collected through their `User`
directories, which hold the state of Copilot Chat, Cline, Roo Code, Kilo Code,
Continue and Augment extensions. Shell histories and shared cross-agent
directories such as `~/.agents` and `~/.env` are collected too.

The collector is a single POSIX `sh` script with no dependencies beyond the base
system. It runs under bash 3.2 (macOS `/bin/sh`), dash, ash and busybox,
FreeBSD and OpenBSD `sh`, and zsh in sh emulation. A PowerShell equivalent for
Windows hosts is planned; Windows disk images are already handled by the sh
script (see below).

## Quick start

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
```

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
agent name. Project `.env` files are collected from discovered project
directories because Aider, Gemini CLI, Qwen Code and Continue read them; they
are flagged `secret: true` like every other credential file.

Home directories come from `getent passwd` or `/etc/passwd` (prefixed with the
root in image mode), `dscl` on macOS, and globbing `home/*`, `Users/*`, `root`,
`var/root`, `usr/home/*` and `export/home/*` under the root. Service accounts
with real homes are included because agents run as them too, for example the
`ollama` system user.

Project-level artifacts (`CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`,
`.cursorrules`, `.aider.chat.history.md`, Crush's per-project `.crush/crush.db`,
...) are collected from every directory referenced in agent state that can be
read with grep: Claude Code history and project list, Codex session rollouts,
Qwen Code chats, Cline sessions and task history, Roo and Kilo task indexes,
Continue sessions, Gemini CLI's project registry, Crush's project list,
Goose legacy session files, OpenCode's legacy project store, Cursor CLI chat
metadata, and VS Code family workspace storage. Each project is attributed to
the user whose state referenced it. Agents that only record the project path
inside SQLite (Zed, Goose, OpenCode, Kilo Code, Kiro CLI) are left to the
analyst-side parser.

In live mode the collector also writes a `live/` directory with the process
list, agent processes, their environment and working directory from `/proc`
on Linux, users, logins, mounts, network sockets and services.

### Default exclusions

Model weights, Electron and editor caches, extension and daemon binaries,
embedding indexes, shadow git checkpoints, agent worktrees, and git clones of
plugin marketplaces are skipped by default. Each skipped path is
still recorded in the manifest with status `skipped_excluded` and its on-disk
size, so the investigator knows what was there. Pass `--full` to collect them.

### Credentials

OAuth tokens and keys (`~/.claude/.credentials.json`, `~/.codex/auth.json`,
`~/.gemini/gemini-credentials.json`, `~/.cline/data/settings/providers.json`,
`~/.local/share/opencode/auth.json`, `~/.config/goose/secrets.yaml`, ...) show
which account an agent acted as, so they are collected by default and flagged
`secret: true`. Config files that commonly embed API keys (Continue's
`config.yaml`, Zed's `settings.json`, Crush's `crush.json`) are flagged the
same way. Run `--list` for the full pattern list. Cursor and Windsurf keep
their auth tokens inside the same `state.vscdb` that holds the chat history,
so that file is collected unflagged; the keys to redact are `cursorAuth/*` and
`windsurfAuthStatus`. Process environments captured
under `live/environ/` are flagged the same way. Use `--no-secrets` to leave
them out; they are then recorded with status `skipped_secret`.

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
`skipped_secret` or `error_copy`. Timestamps are epoch seconds from `lstat` on
the original file; `btime` is `0` where the platform cannot report it.
Symlinks are recreated in the archive and their target recorded, never
followed. The copy of each file is hashed after staging, so the hash matches
the bytes in the archive even if a running agent appended to the source
afterwards.

## Deployment through an EDR

The script is a single file with no interactive prompts, reads nothing from
stdin, and writes everything under `-o`. From CrowdStrike RTR, SentinelOne
RemoteOps or Defender Live Response, upload the script, run it with `-o`
pointing at a directory you can retrieve from, then pull the `tar.gz`. Use `-q`
to keep the console output to the final summary. Runtime on a developer
workstation with several agents installed is well under a minute.

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
```

The smoke test builds a fake disk image with two users, a service account,
awkward filenames, a symlink, credential files, excluded directories, an
oversized file and projects referenced from agent state, then checks the
manifest, hashes and archive contents. It is POSIX sh too; the JSON validity
and hash cross-check steps use `python3` when available.

## Roadmap

- v1 (this): collection.
- Windows: a PowerShell 5.1 collector generated from the same catalog.
- v2: an analyst-side Python tool that parses the collected transcripts
  (Claude Code JSONL, Codex rollouts, Gemini and Antigravity SQLite, Cursor
  `state.vscdb`) into a normalised CSV timeline of turns and tool calls.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](LICENSE).
