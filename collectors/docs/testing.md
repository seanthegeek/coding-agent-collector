# Testing

The collectors' smoke tests, the catalog drift check and what CI runs; for
developers changing the collectors. Back to the
[collectors README](../README.md).

Run from the `collectors/` directory:

```sh
tests/smoke.sh          # under sh
tests/smoke.sh dash
tests/smoke.sh bash
printf '#!/bin/sh\nexec busybox ash "$@"\n' > /tmp/ash && chmod +x /tmp/ash && tests/smoke.sh /tmp/ash
printf '#!/bin/sh\nexec zsh --emulate sh "$@"\n' > /tmp/zsh-sh && chmod +x /tmp/zsh-sh && tests/smoke.sh /tmp/zsh-sh
tests/smoke.sh posh
shellcheck -s sh -S warning collect-agent-artifacts.sh
tests/catalog-sync.sh   # the five tables, --list output and the analyzer copy agree
pwsh -NoProfile -File tests/smoke.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests\smoke.ps1   # on Windows
```

The linters CI runs on every file (shfmt, shellcheck with `.shellcheckrc`,
checkbashisms, PSScriptAnalyzer, markdownlint) are listed under "Quality
gates" in [AGENTS.md](../../AGENTS.md#quality-gates).

## Smoke tests

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
creating symlinks is not permitted. Its symlink-in-archive checks use a
separate small image with a relative, a dangling and a directory symlink
(and, on Windows, a junction) and run it three times: with `tar`, with no
`tar` on the `PATH` (zip from the start), and, off Windows, with a `tar`
that fails (the late fall back to zip).

Each smoke test builds a fake disk image with two users, a service account,
awkward filenames, a symlink, credential files, excluded directories, an
oversized file and projects referenced from agent state, then checks the
manifest, hashes and archive contents. The sh test also has a `nobody`
account to skip. It is POSIX sh too, and its JSON validity and hash
cross-check steps run only when `python3` is available. The PowerShell test
uses a Windows profile tree with drive-letter and `file:///` project
references and runs under both PowerShell 5.1 and 7.

Both smoke tests also build root and rootless Docker volumes, one matched
and one unmatched, check `--no-docker` and the Docker Desktop note, and run
`--no-secrets`, `--full` and `-u`. The sh test adds an unreadable volume and
data root when it is not run as root. Both run `--inventory` / `-Inventory`
against the same image and check the key order of both line types, one
known line's `files`, `bytes`, `first`, `last` and `evidence`, that an
excluded subtree is not counted (and is with `--full`), the Docker volume
lines, `-u`, `--no-docker`, that nothing is written in the current directory
or under `-o`, that stdout stays pure JSON Lines with and without `-q`, and,
on a POSIX host not run as root, that an unreadable home is counted in
`users_unreadable`.

The sh test also runs a small separate image through the batched stage
worker, which lstats, copies and hashes up to 256 files at a time: names
with a newline, a backslash and a carriage return, an unreadable file
between readable ones (not when run as root), and 300 files, more than one
chunk. It checks the hashes against the archived bytes, the `error_copy`
row and log line, that a run with `CAC_NO_BATCH=1` (the per-file path)
writes the same manifest in the same order apart from `atime`, and that a
copy of the collector forced onto `shasum` writes the same manifest.

## Catalog drift check and CI

`tests/catalog-sync.sh` extracts the five tables from both scripts and fails
if they differ. When `pwsh` is on the `PATH` it also compares `--list` with
`-List`. It also fails when `analyzer/doubleagent/catalog.txt` is not
identical to `--list`. The repository's pre-commit hook in `.githooks/`
(enable it once per clone with `git config core.hooksPath .githooks`)
refuses a commit that stages either collector or the analyzer copy while the
copy is stale or the tables differ; the linters run in CI only.

CI (`.github/workflows/ci.yml`) runs the drift test and shellcheck, the sh
smoke test under sh, dash, bash, busybox ash, zsh and posh, a lint job, the
PowerShell smoke test under PowerShell 7 on Linux and Windows PowerShell 5.1
on Windows, and the analyzer tests, on every push to `main` and every pull
request.
