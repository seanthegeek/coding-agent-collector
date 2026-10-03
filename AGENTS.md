# AGENTS.md

Guidance for AI coding agents and humans working in this repository.

## Purpose

`coding-agent-collector` is a forensic collection tool for incident responders.
It gathers the on-disk artifacts of AI coding agents (Claude Code, Gemini CLI,
Antigravity, Codex CLI, Copilot CLI, Cursor, VS Code chat extensions, Windsurf,
Aider, Ollama, and others) for every user on a host, plus shell histories and a
live system snapshot, into one archive with a hashed manifest.

It must work in three situations:

1. Remotely through an EDR remote shell (CrowdStrike RTR, SentinelOne
   RemoteOps, Defender Live Response).
2. Locally on the host by a responder.
3. Against a mounted disk image on an analyst workstation, including Windows
   images mounted on Linux or macOS.

Roadmap: v1 (done) collects. A PowerShell 5.1 collector for live Windows hosts
is planned. v2 is an analyst-side Python tool that parses collected transcripts
into a CSV timeline. Parsing never happens on the host.

## Repository layout

```
collect-agent-artifacts.sh   the collector, single POSIX sh file
tests/smoke.sh               end-to-end test against a fake disk image
README.md                    user documentation, keep in sync with behaviour
AGENTS.md                    this file
CLAUDE.md                    imports this file for Claude Code
LICENSE                      Apache 2.0
```

## Non-negotiable standards

**No dependencies on the host.** The collector uses only the base system: sh,
find, cp, tar, gzip, du, awk, grep, sed, sort, cut, tr, readlink, mkdir, rm,
and one of `sha256sum`, `shasum`, `sha256` or `openssl`. Never add Python,
Perl, jq, or anything that may be absent on a minimal host. macOS does not ship
Python 3; Alpine containers and BSD base systems do not ship bash. The Windows
collector, when written, is PowerShell 5.1 with no modules.

**POSIX sh, not bash.** The shebang is `#!/bin/sh` and the script must run
unchanged under bash 3.2 (macOS `/bin/sh`), dash, busybox ash, FreeBSD and
OpenBSD sh, and `zsh --emulate sh`. Concretely:

- No arrays, no `local`, no `[[ ]]`, no `read -d`, no `mapfile`, no
  `${var,,}`, no `${var:0:3}`, no `$'...'`, no `function` keyword, no
  `-print0 | read -d ''`, no process substitution.
- No GNU-only flags: no `sed -i`, `date -d`, `cp --parents`, `find -false`,
  `stat -c` without a BSD fallback, `xargs -0` without a fallback.
- Platform differences (`stat`, hashing, `ps`, user enumeration) go behind a
  small wrapper function with capability detection done once at startup.
- Shell functions cannot be inherited by `find -exec sh -c`, so shared helpers
  live in the `COMMON` string, which is `eval`'d in the main script and
  prepended to the worker programs.
- Globs with spaces are expanded with `IFS` set to newline only; see
  `expand_glob`. Pattern matching uses `case`.
- `shellcheck -s sh` must be clean apart from info-level notices.

**Single file, non-interactive.** No prompts, nothing read from stdin, all
output under `-o`, concise stdout, exit `0` when an archive was written even if
individual files failed. EDR consoles upload one file and run it once.

**Forensic soundness.**

- Never modify, move or delete anything outside the output directory.
- `lstat` every file before copying it so the manifest holds pre-copy times.
- Hash the staged copy, not the source, so the hash matches the archived bytes
  even when a running agent appends to the source mid-collection.
- Never follow symlinks; record them with their target and recreate them.
- Everything that is skipped (size exclusions, oversized files, secrets) is
  still recorded in the manifest with a status and size. Silence is a bug.
- Credential files are evidence of which account acted. Collect them by
  default, flag them `secret: true`, and honour `--no-secrets`.
- Never print secrets or file contents to stdout or the log.

**Catalog is data, not code.** Agent paths live in the `CATALOG`,
`PROJECT_CATALOG`, `EXCLUDES` and `SECRET_GLOBS` tables at the top of the
script. Adding a tool means adding lines there, never new code paths. Every
entry is tried against every home directory so one table covers macOS, Linux,
Windows and disk images of each. When the PowerShell collector exists, both
scripts' tables must be generated from one source with a test that fails on
drift.

**Manifest schema is an interface.** The v2 parser and analysts depend on
`manifest.jsonl` and `collection.json`. Fields, status values
(`collected`, `symlink`, `skipped_excluded`, `skipped_size`, `skipped_secret`,
`error_copy`) and the `fs/<original path>` archive layout are documented in the
README. Add fields if needed, but do not rename or remove them without
updating the README and noting it in the commit message.

## Adding an agent to the catalog

1. Install the tool and run a short session that uses its agent or chat
   feature, so real transcripts exist.
2. Inspect the home directory: `find ~/.tool -maxdepth 3`, `du -sk ~/.tool/*`.
   Identify transcripts, history, config, credentials, and anything large
   (binaries, model weights, caches, indexes, git clones of marketplaces).
3. Add `agent|path` lines to `CATALOG` for every platform path the tool uses,
   including the Windows `AppData` location so images are covered.
4. Add large or irrelevant subtrees to `EXCLUDES` and credential files to
   `SECRET_GLOBS`.
5. If the tool records project paths, add extraction to `discover_projects`
   and any per-project files to `PROJECT_CATALOG`.
6. Add a fixture and assertions to `tests/smoke.sh` if the layout has anything
   unusual (symlinks, SQLite sidecars, spaces in paths).
7. Update the README's tool list and close the matching GitHub issue.

Verified against real installs so far: Claude Code, Gemini CLI, Antigravity
CLI, Codex CLI, Copilot CLI, Ollama. Everything else has an open issue.

## Validation and testing

Run all of this before committing a change to the collector:

```sh
shellcheck -s sh collect-agent-artifacts.sh
tests/smoke.sh            # /bin/sh
tests/smoke.sh dash
tests/smoke.sh bash
tests/smoke.sh ash        # busybox
printf '#!/bin/sh\nexec zsh --emulate sh "$@"\n' > /tmp/zsh-sh && chmod +x /tmp/zsh-sh && tests/smoke.sh /tmp/zsh-sh
```

The smoke test builds a fake disk image under `$TMPDIR` with two users, a
service account, a `nobody` account to skip, awkward filenames (quotes,
spaces, backslashes), a symlink, credential files, excluded directories, an
oversized file and projects referenced from agent state. It runs the collector
in image mode with the given shell for both the script and the `find -exec`
workers (`COLLECTOR_SH`), then checks statuses, hashes, JSON validity,
archive contents, `--no-secrets`, `--full` and `-u`. All checks must pass under
every shell; a failure under one shell is a portability bug, not a test
problem.

Then run a live collection against your own host and read the summary:

```sh
./collect-agent-artifacts.sh -o /tmp/live -q
```

Check the error count, look at the `skipped_excluded` rows for anything new
and large, and confirm the manifest parses as JSONL. Delete the output
afterwards; it contains your own credentials.

The test uses `python3` only for JSON validation and the hash cross-check, and
skips those checks when it is absent. Never add a `python3` requirement to the
collector itself.

## Conventions

- Commit messages: imperative subject under 70 characters, body explaining
  why, ending with the `Co-Authored-By` line when an AI agent wrote the code.
- Work on `main` directly for now; branch when a change spans several commits.
- Outstanding work is tracked as GitHub issues labelled `enhancement`. File
  one when you find something out of scope rather than widening a change.
- Keep the README's option table, output layout and status list accurate.
  Behaviour changes without a README update are incomplete.
- Bump `VERSION` in the script for any change to output format or options.

## Things to avoid

- Adding Python, jq or any interpreter to the on-host collector.
- Parsing transcripts on the host. That is v2 and runs on the analyst side.
- Collecting model weights, editor caches or extension binaries by default.
- Reading files through symlinks or descending into symlinked directories.
- Writing to `/tmp` by default or anywhere other than `-o`.
- Interactive prompts, `sudo` calls, or anything that reads stdin.
- Bash-isms that happen to work on the developer's machine. Test under dash
  and busybox ash before assuming something is portable.
