# Options

Every option of both collectors in full, the exit codes, and the environment
variables each one reads. The short table is in the
[collectors README](../README.md#options).

## Option reference

| Option | Meaning |
| --- | --- |
| `-o, --output DIR` | Where to write the archive, manifest, summary and log. Created if missing. Default: current directory. |
| `-r, --root DIR` | Alternate root such as a mounted disk image. Switches to image mode. `-r /` is live mode. |
| `-u, --users LIST` | Comma-separated usernames to collect. Default: every home directory found. Names are compared with the user name from the password database, or with the directory name for a home found by globbing. The sh collector compares case-sensitively and the PowerShell collector does not. Also limits the rootless Docker directories. |
| `-p, --project DIR` | Extra project directory whose project-level artifacts (`PROJECT_CATALOG`) are collected, as for a discovered project. Repeatable. It is a path on the machine running the collector and is never prefixed with the root, so in image mode give it including the mount point. A relative path is resolved against the current directory, in image mode too (sh: `cd` and `pwd` for an existing directory, otherwise joined to `pwd` as given; PowerShell: against the current location). A value given twice is collected once. A value that is not a directory (missing, a file, or not visible) is logged as `WARNING: project given with -p is not a directory: <path>: <error>` (`-Project` in the PowerShell message) and gets one `error_read` row; it is not listed in `collection.json` `projects`, only in `options.projects`. Has no effect with `--no-projects`. |
| `--full` | Disable the default size exclusions (model blobs, caches, extension and daemon binaries, marketplace clones). |
| `--no-secrets` | Skip credential files. By default they are collected and flagged `secret: true` in the manifest. |
| `--no-projects` | Skip project-level artifact discovery and `-p`. |
| `--no-docker` | Skip Docker and Podman named volume enumeration (see [docker.md](docker.md)). |
| `--max-file-size MB` | Skip individual files larger than this whole number of MiB. Default 256, `0` disables. |
| `-k, --keep-staging` | Keep the staging directory, `.stage-<archive name>` in the output directory, which holds the unpacked archive contents. |
| `--inventory` | Write nothing: walk the catalog with `lstat` only and print JSON Lines to stdout, one host line and one line per user and agent found. `-o` is ignored, and `-k`, `--no-secrets` and `--max-file-size` have no effect. See [inventory.md](inventory.md). PowerShell: `-Inventory`. |
| `--list` | Print the five tables (home catalog, project catalog, exclusions, credential patterns, Docker volume names), then exit. |
| `-q, --quiet` | Print only the final summary. Progress lines still go to the log file. |
| `-V, --version` | Print `collect-agent-artifacts <version>` and exit. PowerShell: `-Version`. |
| `-h, --help` | Print the usage text and exit. sh only. |

## PowerShell parameters

The PowerShell parameters mirror the sh options: `-OutputDir`, `-Root`,
`-Users`, `-Project`, `-Full`, `-NoSecrets`, `-NoProjects`, `-NoDocker`,
`-MaxFileSizeMB`, `-KeepStaging`, `-Inventory`, `-List`, `-Quiet`,
`-Version`. `-o`, `-r`, `-u`, `-p`, `-k` and `-q` are accepted as aliases.
`-Users` takes one comma-separated string. `-Project` takes a PowerShell
array (`-Project C:\src\a,C:\src\b`) rather than a repeated parameter. There
is no `-h`. `Get-Help .\Collect-AgentArtifacts.ps1 -Detailed` prints the
parameter help.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | An archive was written, even if individual files failed to copy (manifest status `error_copy`) or directories could not be read (`error_read`). With `--inventory`, the walk ran, even if homes or Docker data roots were unreadable. Also `--list`, `--version` and `--help`. |
| `1` | Usage error: unknown option, missing option value, or a `--max-file-size` that is not a whole number. PowerShell: a negative `-MaxFileSizeMB` or a parameter binding error. |
| `2` | Fatal: the root is not a directory, the output directory cannot be created or written, `tar` or `find` is missing (sh), the staging directory cannot be created (sh), or no archive could be written. With `--inventory` only the root and `find` checks apply. |
| `130` | sh only: interrupted by `INT` or `TERM`. The staging directory is removed unless `-k` is given. |

## Environment

The sh collector reads `COLLECTOR_SH`, the shell used to run the per-file
workers that `find -exec` starts (default `sh`, recorded as
`capabilities.worker_shell`). It sets `LC_ALL=C` and puts
`/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin` ahead of the inherited
`PATH`.

The PowerShell collector reads `COMPUTERNAME` for the host name (falling
back to the DNS host name), `SystemDrive` for the drive whose `Users` and
`home` directories are globbed and whose Docker paths are tried in live mode
(default `C:`), `ProgramData` for the live Docker volume and Docker Desktop
paths, and `OS` (it uses `tar.exe` only when that is `Windows_NT`).
