# Collectors

The on-host half of doubleagent: two single-file scripts that walk
every user's home directory, copy the on-disk artifacts of AI coding agents
into a staging area, hash them, and produce one `tar.gz` with a JSONL manifest.
Nothing is parsed on the host; that is the job of the analyst-side tool
described in the [project README](../README.md).

The two collectors share one catalog, manifest schema, archive layout and
version:

- `collect-agent-artifacts.sh` is a single POSIX `sh` script with no
  dependencies beyond the base system. It runs under bash 3.2 (macOS
  `/bin/sh`), dash, ash and busybox, FreeBSD and OpenBSD `sh`, and zsh in sh
  emulation.
- `Collect-AgentArtifacts.ps1` is a single Windows PowerShell 5.1 script with
  no modules, for live Windows hosts. It also runs under PowerShell 7 on any OS.

Either script can collect a mounted disk image of any of the three platforms,
because every catalog entry is tried against every home directory.
[CHANGELOG.md](CHANGELOG.md) lists what changed in each version, including
manifest schema changes.

## Quick start

The paths below are relative to this `collectors/` directory. Both scripts are
self-contained, so copy whichever one you need to the host on its own.

macOS, Linux and BSD:

```sh
# Live host, all users (run as root to read other users' homes)
sudo ./collect-agent-artifacts.sh -o /var/tmp/ir

# Mounted disk image (Linux, macOS or Windows volume)
sudo ./collect-agent-artifacts.sh -r /mnt/evidence -o /cases/host01

# Only two users, without credential files
sudo ./collect-agent-artifacts.sh -u alice,bob --no-secrets -o /var/tmp/ir
```

Windows:

```powershell
# Live host, all profiles (run elevated to read other users' profiles)
powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -OutputDir C:\ir

# Mounted image or offline volume
powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -Root E:\ -OutputDir C:\cases\host01
```

`-ExecutionPolicy Bypass` is needed because fresh Windows installs default to
`Restricted`; it affects only that process and does not change machine policy.

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

[docs/output.md](docs/output.md) explains each line and every file written.

## Options

| sh | PowerShell | Meaning |
| --- | --- | --- |
| `-o, --output DIR` | `-OutputDir`, `-o` | Where to write the archive, manifest, summary and log. Default: current directory. |
| `-r, --root DIR` | `-Root`, `-r` | Alternate root such as a mounted disk image (image mode). `-r /` is live mode. |
| `-u, --users LIST` | `-Users`, `-u` | Comma-separated usernames to collect. Default: every home found. |
| `-p, --project DIR` | `-Project`, `-p` | Extra project directory to collect project-level artifacts from. Repeatable (PowerShell: an array). |
| `--full` | `-Full` | Disable the default size exclusions. |
| `--no-secrets` | `-NoSecrets` | Skip credential files (recorded as `skipped_secret`). |
| `--no-projects` | `-NoProjects` | Skip project-level artifact discovery and `-p`. |
| `--no-docker` | `-NoDocker` | Skip Docker and Podman named volume enumeration. |
| `--max-file-size MB` | `-MaxFileSizeMB` | Skip files larger than this many MiB. Default 256, `0` disables. |
| `-k, --keep-staging` | `-KeepStaging`, `-k` | Keep the staging directory. |
| `--inventory` | `-Inventory` | Write nothing; print one JSON line per user and agent found. See [docs/inventory.md](docs/inventory.md). |
| `--list` | `-List` | Print the five catalog tables and exit. |
| `-q, --quiet` | `-Quiet`, `-q` | Print only the final summary. |
| `-V, --version` | `-Version` | Print `collect-agent-artifacts <version>` and exit. |
| `-h, --help` | none | Print the usage text and exit. |

[docs/options.md](docs/options.md) has the full semantics of each option,
the environment variables each collector reads, and the PowerShell
parameter details.

| Exit code | Meaning |
| --- | --- |
| `0` | An archive was written, even if individual files failed; also `--inventory`, `--list`, `--version`, `--help`. |
| `1` | Usage error. |
| `2` | Fatal: bad root, unwritable output, missing tool, or no archive written. |
| `130` | sh only: interrupted by `INT` or `TERM`. |

## What gets collected

Every catalog entry is tried against every home directory, so macOS, Linux
and Windows paths coexist and a Windows image mounted on a Linux workstation
is collected correctly. Run `--list` for the full catalog. Credential files
are collected by default and flagged `secret: true`; model weights, caches
and binaries are excluded but still recorded in the manifest. Processes,
network connections and other host state are left to the EDR.

Details are in [docs/coverage.md](docs/coverage.md), and the evidence for
every catalog entry, with citations and the level each claim rests on, is
one document per agent under [research/](research/README.md).

## Documentation

| Page | Covers |
| --- | --- |
| [docs/options.md](docs/options.md) | Full option semantics, exit codes, environment variables, PowerShell parameter details |
| [docs/output.md](docs/output.md) | The stdout summary, output files, archive layout, manifest fields and statuses, `collection.json` |
| [docs/coverage.md](docs/coverage.md) | What is collected and from where: homes, projects, nested and case-variant entries, exclusions, credentials |
| [docs/docker.md](docs/docker.md) | Docker and Podman named volumes, Docker Desktop |
| [docs/privileges.md](docs/privileges.md) | What a run without root or Administrator still collects and records |
| [docs/inventory.md](docs/inventory.md) | Inventory mode and its JSON Lines fields |
| [docs/windows.md](docs/windows.md) | Windows specifics: `tar.exe` and zip, symlinks and reparse points, locked files, long paths |
| [docs/deployment.md](docs/deployment.md) | Running through an EDR remote shell, fleet inventory, access times |
| [docs/testing.md](docs/testing.md) | The smoke tests, the catalog drift check and CI |

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
