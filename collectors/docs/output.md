# Output

What a collection writes: the stdout summary, the files in the output
directory, the archive layout, the manifest and `collection.json`. Back to
the [collectors README](../README.md).

## Stdout summary

When the run finishes, the collector prints a summary on stdout (the sample
is in the [README](../README.md#quick-start)):

- `archive`, `manifest`, `summary`, `log`: the paths of the four main output
  files.
- `size` and `sha256` are the archive's; `size` is in bytes, followed by the
  same size in binary units (`B`, `KiB`, `MiB`, `GiB`, `TiB`, one decimal).
- `users` counts the homes that produced at least one manifest row, the
  `users_with_artifacts` list in `collection.json`; homes that were scanned
  and held nothing are left out of the count but stay in `users` there.
- `projects` counts the project directories collected from.
- `collected` counts the manifest rows with status `collected` and their
  bytes, followed by the same total in binary units.
- `skipped` counts the `skipped_excluded`, `skipped_size` and
  `skipped_secret` rows.
- `errors` is the number of `error_copy` and `error_read` rows together,
  followed by each of the two counts in parentheses.
- The `docker:` line appears only when a Docker or Podman volume directory
  or Docker Desktop data was found; see [docker.md](docker.md).

Progress lines (each user, catalog match and project) go to stderr unless
`-q` is given. They always go to the log. A `User` line is written only for
a home with at least one catalog match, just before that match. The last
progress line is `done`; the log file's `done:` line also records the
archive path, size in bytes and sha256.

## Output files

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

## Archiver fallbacks

The sh collector writes the archive with `tar -czf`. If that fails, it pipes
`tar` through `gzip`. The pipe counts as failed when either `tar` or `gzip`
exits non-zero; `tar`'s exit status is passed through a temporary
`.tar-status-<name>` file in the output directory, outside the staging
directory, which is removed before archiving goes on, and a `tar` failure
there is logged as `tar | gzip: tar exited N`. If the pipe fails, or `gzip`
is not on the `PATH`, it writes an uncompressed `.tar` instead.

The PowerShell collector writes a `.tar.gz` with `tar.exe`, or a `.zip`
(see [windows.md](windows.md)).

Both collectors rewrite `collection.json` and its staged copy before each
fallback, so its `archive` and `capabilities.archiver` fields name the
archive that was written. The log is copied into the archive before
archiving starts, so only the copy outside has the final `done` line with
the archive's size and hash.

## Archive layout

Inside the archive (the sh collector's tar members start with `./`):

```text
fs/<original path>          collected files and recreated symlinks, mirroring
                            the source filesystem
manifest.jsonl
collection.json
collector.log
```

On a live Windows host the archive path is `fs/<drive letter>/<path>`, for
example `fs/C/Users/alice/.claude/history.jsonl`. In image mode it is
relative to the root, as on other platforms.

## Manifest

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
| `archive_path` | Where the file is in the archive: `fs/<original path>`. Set for `collected` rows and for `symlink` rows whose link is in the archive: always from the sh collector, and from the PowerShell collector when the link was recreated and the archive is a tar (see [windows.md](windows.md#symlinks-and-reparse-points)). Empty otherwise. |
| `type` | `file`, `symlink`, or `dir` (an excluded directory, an unmatched volume, or an `error_read` directory). |
| `size` | Bytes. `0` for an `error_read` row. For any other `dir` row, the size of everything under it: `du -sk` × 1024 from the sh collector, the sum of file lengths from the PowerShell collector. |
| `mtime`, `atime`, `ctime`, `btime` | Epoch seconds, read before the copy. `btime` (creation) is `0` where the platform cannot report it, and `ctime` is `0` from the PowerShell collector. All four are `0` for an excluded directory from the sh collector, for an unmatched volume, for an `error_read` row of a `-p` value that does not exist, and on a host with neither GNU nor BSD `stat` (where `uid`, `gid` and `mode` are `0` too). |
| `uid`, `gid`, `mode` | Numeric owner and group, and the permission bits as an octal string (`"644"`), from `lstat`. `0`, `0` and `""` from the PowerShell collector. |
| `owner`, `attributes` | PowerShell collector only: the owning account name (or SID when the name cannot be resolved) and the attribute list, such as `Archive, ReparsePoint`. |
| `sha256` | SHA-256 of the staged copy, set only for `collected` rows. The sh collector leaves it empty when it found no hash tool (`capabilities.hash_tool` is `none`). |
| `secret` | `true` when the path, relative to `home`, matched a credential pattern. |
| `status` | See below. |
| `target` | For a symlink, its target as stored. The PowerShell collector joins several reparse point targets with `;`. |
| `error` | For `error_copy`, why the copy failed: `cp`'s message or the .NET exception. For `error_read`, why the directory could not be read: the first line of `ls`'s message (sh, for example `ls: cannot open directory '/home/carol': Permission denied`) or the .NET exception message. For a PowerShell `symlink` row with no `archive_path`, why the link is not in the archive, starting `not recreated in the archive:` or `not in the archive:`. |

Timestamps come from `lstat` on the original file (sh), or from the item's
times before the copy (PowerShell). The copy of each file is hashed after
staging, so the hash matches the bytes in the archive even if a running
agent appended to the source afterwards.

### Statuses

| Status | Meaning |
| --- | --- |
| `collected` | Copied, hashed and archived. |
| `symlink` | A symbolic link (on Windows any reparse point, including junctions), recorded with its target and never followed. Both collectors recreate the link in the archive with its target as stored. The PowerShell collector cannot where Windows refuses to create it or where the archive is a `.zip`; the row then has no `archive_path` and `error` says why. |
| `skipped_excluded` | Matched an `EXCLUDES` pattern. An excluded directory is one `dir` row with its total size. |
| `skipped_size` | Larger than `--max-file-size`. |
| `skipped_secret` | A credential file left out by `--no-secrets`. |
| `error_copy` | Could not be read or copied; see `error`. |
| `skipped_unmatched_volume` | A Docker or Podman volume that matched no `DOCKER_VOLUMES` line: one `dir` row with its size, `user` `docker`, an empty `agent`, and `home` and `path` both the volume's `_data`. |
| `error_read` | A directory that could not be listed or entered: a home, a project directory, a `-p` value that is not a directory, or a directory inside a walk (see [privileges.md](privileges.md)). One `dir` row with size `0`, no `archive_path` and the reason in `error`; nothing under it is collected. |

### Check order

A path that was not excluded is checked first for being a symlink, then
for `--no-secrets`, then for size. A symlink is therefore never skipped for
size, and a credential file is `skipped_secret` under `--no-secrets`
whatever its size.

## collection.json

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
| `options` | `full`, `no_secrets`, `max_file_size_bytes` (`0` means no limit), `users_filter` (the `-u` string), `no_docker`, `no_projects` (boolean, `--no-projects` or `-NoProjects`) and `projects` (array of the `-p`/`--project` or `-Project` values in the order given, resolved against the current directory to absolute paths and de-duplicated, by both collectors, `[]` when none). A value that is not a directory is still listed here. They are recorded even with `no_projects`, which ignores them. |
| `capabilities` | sh: `hash_tool` (`sha256sum`, `shasum`, `sha256`, `openssl` or `none`), `stat_mode` (`gnu`, `gnu0` for GNU `stat` without birth time, `bsd` or `none`), `worker_shell` and `archiver` (`tar -z` for `tar -czf`, `tar \| gzip` for the pipe, `tar` for the uncompressed `.tar`). PowerShell: `hash_tool` (`Get-FileHash`) and `archiver` (`tar.exe` or `ZipFile`). `archiver` names the one that wrote the archive. |
| `users`, `homes` | Parallel lists of every user and home scanned, including homes with no agent state. |
| `users_with_artifacts` | The users whose home produced at least one manifest row, in the order of `users`. Rows from discovered projects and Docker volumes do not count. The stdout `users:` line is its length. |
| `projects` | The project directories collected from, discovered or given with `-p`. A `-p` value that is not a directory is left out and has an `error_read` row instead. |
| `counts` | Rows per status (`collected`, `symlink`, `skipped_excluded`, `skipped_size`, `skipped_secret`, `error_copy`, `skipped_unmatched_volume`, `error_read`) and `collected_bytes`. |
| `docker` | `volumes_found`, `volumes_collected`, `unreadable` and `docker_desktop`; see [docker.md](docker.md). |
| `notes` | Messages about what could not be collected, such as an unreadable or symlinked Docker volume directory, Docker Desktop data, or (PowerShell) symlinks that are not in the archive and why. |
| `archive` | The file name of the archive written: `.tar.gz`, `.tar` after the sh collector's uncompressed fallback, or `.zip` from the PowerShell collector without `tar.exe` or after it failed. |
