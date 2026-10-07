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

Editors are collected through their `User` directories; extension state
inside them goes to the extension's agent.

- **VS Code, VSCodium and their forks:** the `User` directories, which hold
  Copilot Chat sessions and extension state.
- **Cline, Roo Code, Kilo Code, Continue, Sourcegraph Cody and Twinny:**
  their globalStorage is claimed by nested catalog entries, so those files
  are attributed to the extension's agent rather than to the editor,
  whichever editor they sit in.
- **Skills and configuration files** that several agents read are
  collected too, with agent `shared` in the manifest.
- **`.env` files:** an agent's own `.env` inside its state directory, such
  as `~/.codex/.env` or `~/.hermes/.env`, is collected and flagged
  `secret: true`. General-purpose `.env` files in the home or a project are
  not collected.
- **Shell histories** are not collected: like process lists and logons,
  they are the EDR's job.

## Nested entries

A nested catalog entry wins over the entry that encloses it. When one tool
keeps its state inside another tool's directory, as Antigravity CLI does
under `~/.gemini/antigravity-cli`, those files are collected once,
attributed to the nested agent, and left out of the enclosing agent's walk.

## Case variants

On a case-insensitive filesystem, catalog lines that differ only by case
name one directory, which is collected once by the line listed first. On a
case-sensitive filesystem every variant that exists is collected as before.

The variants in the catalog, where both can exist on Linux:

- `.config/goose` and `.config/Goose`
- `.config/PearAI/User` and `.config/pearai/User`
- `.config/Cursor/User` inside `.config/cursor`

Case-insensitive filesystems are macOS by default, Windows, and a directory
under `/mnt/c` in WSL. The later line collects nothing and leaves one log
line ending `(case-insensitive filesystem), collected there`, with no
manifest row. A case variant of a path inside another match
(`.config/Cursor/User` inside `.config/cursor`) is treated as the nested
entry it is.

How the two collectors decide that two spellings are one directory, and how
the path is spelled in the manifest, differs:

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

A second Claude Code config home named `~/.claude-<name>` (such as
`~/.claude-work`) is collected as `claude-code`, but only by the
Claude-specific names inside it. One outside the home directory, or not
named `.claude-<name>`, is not found; collect it by hand.

Claude Code reads its whole config home from `CLAUDE_CONFIG_DIR` when that
variable is set, and a second account in such a directory is common. The
names collected there:

| Name | Flagged `secret: true` |
| --- | --- |
| `projects/` | no |
| `file-history/` | no |
| `history.jsonl` | no |
| `.claude.json*` | `.claude.json` only |
| `.credentials.json` | yes |
| `hfi-auth.json` | yes |
| `.session_ingress_token` | yes |
| `remote/.oauth_token` | yes |
| `remote/.api_key` | yes |

The rest of a relocated home (`settings.json`, `todos/`, `plans/`,
`shell-snapshots/` and the other subdirectories) is not collected, because
a bare `.claude-*` entry would also take other tools' directories such as
`~/.claude-code-router` and `~/.claude-mem`.

## Home directories

Home directories are gathered from several sources, merged, and
de-duplicated by path. Service accounts with real homes are included,
because agents run as them too, for example the `ollama` system user.

| | sh collector | PowerShell collector |
| --- | --- | --- |
| Live mode | `getent passwd`, or `/etc/passwd` where there is no `getent`; on macOS also `dscl . -list /Users NFSHomeDirectory`. | The registry `ProfileList`, and the globs below. |
| Image mode | `<root>/etc/passwd`, with every home prefixed with the root. | Globs only, the same six patterns as the sh collector. It does not read `etc/passwd`, so in a Linux image it misses any home outside those directories. |
| Globs | In both modes, `home/*`, `Users/*`, `root`, `var/root`, `usr/home/*` and `export/home/*` under the root, taking the directory name as the user. | In image mode, the same six patterns; in live mode, `Users\*` and `home\*` on the system drive. |
| Dropped | Homes that do not exist; system paths that are not real homes (`/`, `/bin`, `/sbin`, `/usr`, `/usr/bin`, `/usr/sbin`, `/dev`, `/dev/null`, `/proc`, `/sys`, `/nonexistent`, `/var/empty`); `Shared`, `Public`, `Default`, `Default User` and `All Users` under `/Users`. | Profiles named `Public`, `Default`, `Default User`, `All Users`, `Shared`, `defaultuser0`, `UMFD-<n>`, `DWM-<n>` or `TEMP`. |

The PowerShell collector logs a profile path that cannot be seen as
`profile not accessible (skipped)`. When its parent directory still lists
it (access denied rather than a deleted profile), it also gets an
`error_read` row, but it is not added to `users` and `homes`.

## Project discovery

Project-level artifacts (`CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`,
`.cursorrules`, `.aider.chat.history.md`, Crush's per-project
`.crush/crush.db`, ...) are collected from every directory referenced in
agent state that can be read with grep, and from every `-p` directory.

### Sources read

| Agent | Where the project path is read from |
| --- | --- |
| Amp | History. |
| Antigravity | History, trusted workspaces and project cache. |
| Claude Code | History and project list, in `~/.claude` and `~/.claude-<name>` config homes. |
| Cline | Sessions and task history. |
| Codex | Session rollouts. |
| Continue | Sessions. |
| Copilot CLI | Session workspaces. |
| Crush | Project list. |
| Cursor CLI | Chat and ACP session metadata. |
| Factory Droid | Sessions. |
| Gemini CLI | Project registry, trusted folders and project root markers. |
| Goose | Legacy session files and the desktop app's recent directories. |
| Hermes | Checkpoint project records. |
| Kilo Code | Task indexes. |
| Kiro CLI | Sessions and workspace roots. |
| Letta | Session index and local-backend transcripts. |
| Muse Code | Trusted projects (`.config/muse/trust.json`) and session logs (`workspace_root`). |
| nanobot | Workspace markers and config. |
| Open Interpreter | Rollouts. |
| OpenClaw | Workspace and agent directories from its JSON5 config. |
| OpenCode | Legacy project store. |
| OpenHands | Workspaces and conversation metadata. |
| PearAI | Sessions. |
| pi | Session headers, trusted folders, crash log and experimental session metadata (which also cover little-coder). |
| Qwen Code | Chats. |
| Roo Code | Task indexes. |
| Tabby | `file://` repositories. |
| Twinny | The common directory of the files in each embeddings manifest. |
| VS Code family | Workspace storage, including the remote server data directories. |

### Which paths are used

- A referenced path is used only if it is absolute and names an existing
  directory that is not itself a home.
- In image mode it is looked up under the root.
- The sh collector reads POSIX paths only, so it skips drive-letter
  references in a Windows image.
- The PowerShell collector maps `C:\...` and `file:///c:/...` references to
  the same path under `-Root`, dropping the drive letter. On a live Windows
  host it ignores POSIX paths.

### What is taken from each project

From each project only the `PROJECT_CATALOG` entries are collected. Their
rows have agent `project`, `home` set to the project directory, and the user
whose state referenced it (the first one, when several did). `-p`
directories join the same list. Each gets as its user the owner of the home
it sits under, or none.

### Left to the analyzer

Project paths recorded only inside SQLite, and in zstd-compressed rollouts,
are not discovered; they are left to the analyst-side parser:

- Zed
- Goose
- OpenCode
- Kilo Code
- Kiro CLI
- Hermes `state.db` and `projects.db`
- OpenClaw `openclaw.sqlite`
- Tabby `ee/db.sqlite`
- the PearAI Roo fork in `state.vscdb`
- Codex and Open Interpreter rollouts compressed with zstd
- CLAI 2.0 `sessions.db` (`conversations.metadata` key `workspace`), whose
  projects' `.clai` directories are collected only when another source or
  `-p` names the project

## Agents outside dot directories

Most agents keep their state in a dot directory; a few do not, and some of
their state must be copied by hand.

- **Agent Zero** lives in its install directory (`~/agent-zero`,
  `~/Desktop/agent-zero`). It is also commonly deployed in containers; see
  [docker.md](docker.md).
- **Local Deep Research** writes reports under
  `~/Documents/LocalDeepResearch`. It is also commonly deployed in
  containers; see [docker.md](docker.md).
- **ShellGPT** keeps its chat history in the system temp directory (`/tmp`
  on Linux, `/var/folders/.../T` on macOS), which no home-relative catalog
  entry can reach, so on Linux and macOS it is not collected and must be
  copied by hand. The Windows locations under `AppData/Local/Temp` are
  collected.
- **Muse Code** keeps its launcher state beside the launcher; see below.

### Muse Code

| Location | Collected |
| --- | --- |
| Linux and macOS, `~/.local/bin` | Only Muse's own dot files (`.local/bin/.muse-*`: `.muse-version`, `.muse-release-info.json`, `.muse-update-checked-at` and the like), since other tools share the directory. The `muse-bin-<version>` binary next to them is not collected and leaves no manifest row. |
| Windows, `AppData/Local/Programs/muse` | The install directory whole. Its `muse-bin-<version>.exe` and staged `.muse-update.<pid>.exe` binaries are excluded, so their `skipped_excluded` rows record the installed version and size. |
| Anywhere else (`MUSE_INSTALL_DIR`) | Not collected. |

Two Muse Code locations are system-wide rather than per home and must be
copied by hand:

- The enterprise policy: the registry key `HKLM\SOFTWARE\Policies\Muse` on
  Windows, and `.enterprise-defaults.json` and `enterprise-policy.json`,
  read as `/Library/Application Support/muse/` on macOS; the Linux location
  is not known.
- On Windows, the elevated shell-sandbox setup root under `%ProgramData%`.

## Agent frameworks and self-hosted platforms

Agent frameworks are libraries inside someone else's application, so most
write nothing to a fixed place in the home; the catalog covers the ones
that do (AutoGen Studio, CrewAI, CAMEL, MetaGPT, the Pydantic AI CLIs, the
legacy Open Interpreter Python tool) and the self-hosted platforms Dify,
Flowise, Langflow and n8n, in the home and in their Docker volumes (see
[docker.md](docker.md)). The sweep behind this, with the reason each
framework got a catalog line or not, is
[research/frameworks.md](../research/frameworks.md).

Some of their state has no fixed home-relative name and is not collected.
Copy it by hand when the framework was in use:

| Framework | State not collected | Where to look |
| --- | --- | --- |
| TaskWeaver | Session transcripts and prompt logs (`workspace/sessions/<id>/`), logs, and `taskweaver_config.json`, which holds the LLM API key. | The project directory: the directory holding `taskweaver_config.json`, which TaskWeaver finds by walking up from where it was started. Nothing under the home records it. |
| LangGraph | `langgraph dev` runs, threads and checkpoints, as Python pickles in `.langgraph_api/`; `langgraph up` keeps them in PostgreSQL. | `.langgraph_api/` in the project directory; the Docker volume `<project dir name>_langgraph-data`, a PostgreSQL data directory, which is recorded as `skipped_unmatched_volume`. Never unpickle the files to read them. |
| Dify | The PostgreSQL database with conversations, messages and agent tool calls, uploaded files, tenant RSA keys and `docker/.env` (`SECRET_KEY`). | The bind mounts under `docker/volumes/` beside Dify's compose file, in wherever Dify was cloned. Only its two agent sandbox named volumes and the `difyctl` config are collected. |
| Langflow (pip or uv install) | `langflow.db` (`langflow-pre.db` for a pre-release), with messages, run history and encrypted credentials. | The installed package directory, `site-packages/langflow/`, inside the virtual environment Langflow runs from, unless the `database_url` or `save_db_in_config_dir` setting moved it (the second puts it in the collected config directory). Langflow Desktop's database is under `.langflow/data` or `AppData/Roaming/com.LangflowDesktop` and is collected. |
| CrewAI (Linux and macOS) | Opt-in agent memory (`memory/`) and knowledge stores (Chroma, `qdrant/`). | The directory that holds a collected `latest_kickoff_task_outputs.db`, which is named after the project folder (`~/.local/share/<project>`, `~/Library/Application Support/<project>`). Only CrewAI's own files in it are collected, because the directory name is not fixed. On Windows the whole `AppData/Local/CrewAI` directory is collected. |
| IntentKit | Agent state in PostgreSQL, Redis and RustFS. It is not in the catalog, because it runs no tools on the host. | Its Compose named volumes, such as `intentkit_postgres_data`, recorded as `skipped_unmatched_volume`, and `.env` in its checkout. |

## Remote development servers

Remote development state is collected: `~/.vscode-server`,
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

Large, low-value subtrees are skipped by default but still recorded in the
manifest with status `skipped_excluded` and their on-disk size, so the
investigator knows what was there. Pass `--full` to collect them. Skipped
by default:

- model weights
- Electron and editor caches
- extension and daemon binaries
- embedding indexes
- shadow git checkpoints
- agent worktrees
- git clones of plugin marketplaces

Ollama's model weights are excluded as `.ollama/models/blobs` only, so the
rest of `.ollama/models` is collected: the small JSON manifests under
`models/manifests/<registry>/<namespace>/<model>/<tag>`, whose names and
pre-copy times record which models were pulled and when, and the per-blob
metadata files under `models/metadata`. In a Docker volume the exclusion
is the volume-relative `models`, which also covers Tabby, Hermes and
Local Deep Research volumes, where `models` holds model weights. It stays
whole, so a Docker Ollama volume's `models/manifests` is not collected;
when the pulled models matter, copy `models/manifests` from the volume's
`_data` by hand, or pass `--full` (`-Full`), which also takes the weights.

## Credentials

Credential files are collected by default and flagged `secret: true`, since
they show which account an agent acted as. Use `--no-secrets` to leave them
out; they are then recorded with status `skipped_secret`. Run `--list` for
the full pattern list.

- **OAuth tokens and keys:** `~/.claude/.credentials.json`,
  `~/.codex/auth.json`, `~/.gemini/gemini-credentials.json`,
  `~/.cursor/auth.json`, `~/.copilot/config.json`,
  `~/.cline/data/settings/providers.json`,
  `~/.local/share/opencode/auth.json`, `~/.config/goose/secrets.yaml`,
  `~/.factory/auth.v2.*`, ...
- **Config files that commonly embed API keys or MCP server environments:**
  Continue's `config.yaml`, Zed's `settings.json`, Crush's `crush.json`,
  Claude Code's `.claude.json`, Claude Desktop's
  `claude_desktop_config.json`, Kiro powers' `mcp.json`.
- **Electron `Local State` files** that hold the key for encrypted token
  caches.
- **Databases flagged whole:** Kilo Code's `kilo.db` and OpenCode's
  `opencode.db`, which embed tokens in their `account` and `credential`
  tables.

Cursor and Windsurf keep their auth tokens inside the same `state.vscdb`
that holds the chat history, so that file is collected unflagged; the keys
to redact are `cursorAuth/*` and `windsurfAuthStatus`.

## Pattern matching

Exclusion and credential patterns are matched relative to the directory
being collected, and `*` in them crosses `/`. An exclusion wins over a
credential pattern.

- **Base:** a home, a discovered project or a Docker volume's `_data`. The
  same `.claude/worktrees` pattern therefore prunes both
  `~/.claude/worktrees` and a project's `.claude/worktrees`.
- **Case:** the sh collector matches with `case` and `find -path`, which are
  case-sensitive. The PowerShell collector converts the patterns to regular
  expressions and matches them, and the catalog globs, without regard to
  case.
- **Classes:** `[...]` classes and `[!...]` negated classes work in both
  collectors, in catalog globs too: CrewAI's Windows directory is the
  single line `AppData/Local/[Cc]rew[Aa][Ii]`, which matches `CrewAI` and
  `crewai` on a case-sensitive filesystem without two lines that differ
  only by case.

An excluded directory is pruned from the walk before any file in it is
looked at, so a credential file inside it is never collected or flagged; it
is covered only by the directory's `skipped_excluded` row. Exclusions are
therefore written so that they do not cover credential files: Hermes'
installer checkout is excluded entry by entry (`.hermes/hermes-agent/[!.]*`
and `.hermes/hermes-agent/.[!e]*`) so that `hermes-agent/.env` is still
collected.
