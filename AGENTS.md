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
collect-agent-artifacts.sh   the macOS/Linux/BSD collector, single POSIX sh file
Collect-AgentArtifacts.ps1   the Windows collector, single PowerShell 5.1 file
tests/smoke.sh               end-to-end test of the sh collector (fake disk image)
tests/smoke.ps1              end-to-end test of the PowerShell collector
tests/catalog-sync.sh        fails if the four catalog tables differ between scripts
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

**Windows PowerShell 5.1, not PowerShell 7.** `Collect-AgentArtifacts.ps1`
must run under the PowerShell that ships with Windows 10, 11 and Server 2016+,
and also under PowerShell 7 on any OS so the test can run in Linux CI.
Concretely:

- No ternary operator, no `??`, no `-AsHashtable`, no three-argument
  `Join-Path`, no `[System.IO.Path]::GetRelativePath`, no `.NET Core`-only
  APIs. `Get-FileHash`, `ConvertTo-Json -Compress`, `[DateTimeOffset]` and
  `System.IO.Compression.FileSystem` are fine.
- Never name a variable after an automatic variable: `$home`, `$host`,
  `$args`, `$input`, `$error`, `$pid`, `$profile` are read-only or special
  and fail silently or loudly. Use `$homeDir`, `$HostName`, `$cargs`.
- Under `Set-StrictMode -Version 2` on 5.1 a scalar has no `.Count` and a
  missing property throws. Wrap anything that may be a single item in `@()`.
- Array splatting to a script file binds positionally; use a hashtable splat
  to pass named parameters.
- Hidden items (every dotfile under PowerShell 7 on Linux, `AppData` on
  Windows) need `-Force` on `Get-Item` and `Get-ChildItem`.
- Use `tar.exe` only when `$env:OS` is `Windows_NT`; under WSL, PowerShell 7
  on Linux can find the Windows `tar.exe` through interop and produce a
  broken archive. Fall back to `ZipFile` elsewhere.
- Write files through `StreamWriter` with UTF-8 and no BOM; `Add-Content` on
  5.1 defaults to ASCII and mangles non-ASCII paths.
- Open source files with `FileShare.ReadWrite | Delete` so stores locked by a
  running editor still copy.

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
`PROJECT_CATALOG`, `EXCLUDES` and `SECRET_GLOBS` tables at the top of both
scripts. Adding a tool means adding the same lines to both, never new code
paths. Every entry is tried against every home directory so one table covers
macOS, Linux, Windows and disk images of each. The tables are byte-identical
between the sh single-quoted strings and the PowerShell `@'...'@`
here-strings; `tests/catalog-sync.sh` fails on any drift, and `--list` and
`-List` must print identical output. Glob semantics are shared: catalog
globs do not cross `/`, exclusion and secret globs do, and `[...]` classes
work in both (the PowerShell side converts globs to regexes).

**Manifest schema is an interface.** The v2 parser and analysts depend on
`manifest.jsonl` and `collection.json`. Fields, status values
(`collected`, `symlink`, `skipped_excluded`, `skipped_size`, `skipped_secret`,
`error_copy`) and the `fs/<original path>` archive layout are documented in the
README. Add fields if needed, but do not rename or remove them without
updating the README and noting it in the commit message.

## Adding an agent to the catalog

Prefer reading the tool's source over installing it. Most agents are open
source even when their models are not, and the path constants are easy to
find. The validation for every current entry is recorded in the README table.

1. Shallow-clone the repository into the scratchpad and grep for `homedir`,
   `XDG`, `APPDATA`, `Application Support`, `.config/`, `.local/share`,
   `sessions`, `history`, `sqlite`, `auth`, `token`, `secrets`, `cache`,
   `cwd`, `workspace`. Read the paths module (`paths.ts`, `paths.rs`,
   `global.ts`, `storage.ts`, `home.go`) and cite file and line in the issue.
   For closed-source tools, grep the shipped npm bundle or binary for literal
   path strings (`npm pack`, `strings`), then fall back to official docs,
   vendor forums and published DFIR write-ups, and say which was used.
2. From that, identify transcripts, history, config, credentials, and
   anything large (binaries, model weights, caches, indexes, shadow git
   checkpoints, worktrees, git clones of marketplaces). Note which OSes share
   a layout: many tools use `~/.config` and `~/.local/share` on macOS and
   Windows too, and several keep credentials in the OS keychain with a file
   fallback that only appears on headless hosts.
3. Add `agent|path` lines to `CATALOG` in both scripts for every platform
   path the tool uses, including the Windows `AppData` location so images are
   covered. Run `tests/catalog-sync.sh`.
4. Add large or irrelevant subtrees to `EXCLUDES` and credential files to
   `SECRET_GLOBS`.
5. If the tool records project paths, add extraction to `discover_projects`
   and any per-project files to `PROJECT_CATALOG`.
6. Add a fixture and assertions to `tests/smoke.sh` and `tests/smoke.ps1` if
   the layout has anything unusual (symlinks, SQLite sidecars, spaces in
   paths, drive-letter or `file:///` project references).
7. Update the README's tool list and close the matching GitHub issue.

Every catalog entry has been validated against source, a shipped bundle, or
official documentation; see the README table for which. Real-install checks
exist for Claude Code, Antigravity CLI, Codex CLI, Copilot CLI and Ollama.
Agents whose project paths live only in SQLite (Zed, Goose, OpenCode, Kilo
Code, Kiro CLI) are not covered by `discover_projects`; that is v2 work.

## Validating catalog entries from source

This is the process used for the v1.1 catalog, and the one to repeat when a
tool is added or a tool's layout is suspected to have changed. It replaces
installing the tool: source is authoritative, faster, and keeps the
workstation clean.

**1. Group the tools and fan out.** One researcher per platform group, run in
parallel. Group forks of the same codebase together (Gemini CLI with Qwen
Code; Cline with Roo Code and Kilo Code; OpenCode with Crush) because the
differences are what matter. Put closed-source tools in their own groups since
the evidence gathering is different.

**2. Give each researcher the same brief.** It should contain: the current
catalog lines for that tool (from `--list`), the repository to shallow-clone
into the scratchpad, the grep terms to start with, and the instruction to
cite file and line for every claim and never rely on memory. Grep terms that
find the paths module quickly:

```
homedir  XDG  APPDATA  LOCALAPPDATA  "Application Support"  .config/  .local/share
.local/state  .cache  sessions  history  checkpoint  snapshot  worktree  sqlite  .db
auth  token  credential  secrets  keyring  keychain  cache  bin  node_modules
cwd  workspace  project  worktree  mcp  rules  AGENTS.md
```

Likely file names: `paths.ts`, `paths.rs`, `global.ts`, `storage.ts`,
`home.go`, `config/load.go`, `env.ts`, `directories.rs`.

**3. Require a fixed report structure.** Eight numbered sections, under
about a thousand words:

1. Repo, commit checked, open source or not.
2. Per-user storage for Linux, macOS and Windows: every directory and file
   under the home, what each holds, and whether the layout is shared across
   OSes. Flag tools that use XDG paths on macOS and Windows.
3. Credentials on disk, by exact file name, and whether the OS keychain is
   used with a file fallback. Note config files that can embed API keys.
4. Large or low-value subtrees to exclude, as exact path patterns: binaries,
   model weights, caches, embedding indexes, shadow git checkpoints,
   worktrees, marketplace clones, Electron caches.
5. Project-local files written or read inside repositories. Call out any
   per-project database, since those are easy to miss.
6. Where the project or workspace path is recorded, with file and JSON key or
   table and column, so `discover_projects` or the v2 parser can use it.
7. Proposed lines in the collector's own formats: `agent|glob` for
   `CATALOG`, globs for `EXCLUDES` and `SECRET_GLOBS`, `project|glob` for
   `PROJECT_CATALOG`.
8. Confidence per item and what could not be determined.

**4. Evidence hierarchy for closed-source tools.** In order: the shipped npm
tarball or binary (`npm pack`, then grep or `strings`; minified bundles keep
literal path strings), official docs, vendor forums and issue trackers, then
published DFIR or reverse-engineering write-ups. The report must say which
level each claim came from, and the README validation table records it.

**5. Integrate in one commit.** Save each report to the scratchpad as it
arrives and do not touch the script until all are in, so the tables change
once. Then: rewrite the four tables, extend `discover_projects` with every
new grep-able source, add a fixture and checks to `tests/smoke.sh` for each
new secret pattern, exclusion and discovery source, run the full shell
matrix, run a live collection and read the `skipped_excluded` and
`secret: true` rows, update the README tool table, bump `VERSION`.

**6. Close the loop on GitHub.** Close each tool's issue with a comment that
names the evidence source and commit, the key findings, and the catalog
changes. Comment on the v2 parser issue with any SQLite-only sources found.
File new issues for anything out of scope that the research surfaced, such
as sandboxed install paths or tokens stored inside chat databases.

Things the first run taught us, to check for explicitly next time:

- A library with no platform branching (`xdg-basedir`, `etcetera`,
  `home.Config()`) means `~/.config` and `~/.local/share` on macOS and
  Windows too. Do not assume Library or AppData.
- Exclusions must not swallow credential files. Continue's
  `index/globalContext.json` sits next to the embedding index it shares a
  directory with.
- Some tools store sessions inside the repository (Crush) or gitignore
  their own state directory, so the project list, not git, is the index.
- Auth tokens and chat history can share one SQLite file (Cursor, Windsurf);
  collect it unflagged and document the keys to redact.
- Forks drift: Kilo Code moved from the Roo layout to an OpenCode fork;
  Windsurf is rebranding to Devin. Check the current commit, not the name.

## Validation and testing

Run all of this before committing a change to the collector:

```sh
shellcheck -s sh collect-agent-artifacts.sh
tests/smoke.sh            # /bin/sh
tests/smoke.sh dash
tests/smoke.sh bash
tests/smoke.sh ash        # busybox
printf '#!/bin/sh\nexec zsh --emulate sh "$@"\n' > /tmp/zsh-sh && chmod +x /tmp/zsh-sh && tests/smoke.sh /tmp/zsh-sh
tests/catalog-sync.sh
pwsh -NoProfile -File tests/smoke.ps1
```

For a change to the PowerShell collector, also run the test under real
Windows PowerShell 5.1. From this WSL checkout that is:

```sh
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File '\\wsl.localhost\Ubuntu\home\sean\dev\coding-agent-collector\tests\smoke.ps1' \
  -Collector '\\wsl.localhost\Ubuntu\home\sean\dev\coding-agent-collector\Collect-AgentArtifacts.ps1'
```

Symlink creation needs a privilege the test may not have on Windows; it
skips the symlink checks and says so. A pass under PowerShell 7 alone is not
enough: 5.1 is stricter about `.Count` on scalars and lacks several APIs.

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
powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -OutputDir $env:TEMP\live -Quiet
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
