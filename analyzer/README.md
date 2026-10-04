# Analyzer

The analyst-side half of coding-agent-collector. It takes a collector archive,
an extracted collection, or any loose directory tree, detects which AI coding
agents left state in it, and parses the transcripts it knows how to read into
one normalised CSV timeline. It never runs on the host under investigation, so
unlike the collectors it may carry dependencies. It needs Python 3.10 or
later and the packages in `requirements.txt` (`pip install -r
requirements.txt`): today only `zstandard`, for Zed threads, Codex and Open
Interpreter `.jsonl.zst` rollouts and OpenClaw's compressed transcript rows.
Without it each such thread, rollout or row is reported as an undecodable
`system` row and everything else still runs.

[CHANGELOG.md](CHANGELOG.md) lists what changed in each version, including
changes to the `timeline.csv` and `sessions.csv` columns.

## Quick start

```sh
cd analyzer

# What is in this collection?
python3 -m agent_analyzer detect /cases/host01/host01_20261003T165531Z_agent-artifacts.tar.gz

# Build the timeline
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/analysis

# Shorter rows for a spreadsheet
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/short --max-text-length 200

# A home directory copied off a host by other means, or a mounted image
python3 -m agent_analyzer timeline /mnt/evidence -o /cases/host02/analysis --host host02

# A single agent directory copied on its own, under its original name
python3 -m agent_analyzer detect /cases/host03/alice/.claude --user alice

# Fleet inventory: one saved collector --inventory stdout per host in a directory
python3 -m agent_analyzer inventory /cases/fleet/inventory -o /cases/fleet/fleet-inventory.csv
```

`pip install .` in this directory installs the package
`coding-agent-analyzer`, which provides the same tool as the
`analyze-agent-artifacts` command. `--version` prints
`analyze-agent-artifacts <version>`.

## Inputs

| Input | How it is read |
| --- | --- |
| Any file, normally `*_agent-artifacts.tar.gz` or `.zip` from either collector | Recognised as zip or tar by its content (any compression `tarfile` reads), extracted to a temporary directory (or `--work-dir`), then read as an extracted collection. If it does not unpack to `manifest.jsonl` and `fs/`, it is read as a loose tree. A `.sha256` sidecar next to the archive is verified and the result reported as a note. Symlinks, hard links and device files inside the archive are not materialised (their targets are in the manifest), and members with absolute paths, `..` or a drive letter are skipped. A file that is neither tar nor zip is an error. |
| Extracted collection: a directory holding `manifest.jsonl` and `fs/` | Host name from `collection.json` `hostname` unless `--host` is given. User, home and agent for every file come from the manifest. Only rows with status `collected` and type `file` are read. |
| Anything else | Treated as a loose tree: a copied home directory, a mounted disk image, another collector's output, or one agent directory such as `.claude`. Homes and agents are discovered from the catalog, and the user is inferred from the path. A directory with `fs/` but no `manifest.jsonl` is read from `fs/`. |

In loose mode the analyzer walks the tree and treats a directory as a home
when at least one catalog entry for a real agent matches under it. A
directory that holds only shared files such as `AGENTS.md` or `.env` is a
project, not a home. A home is never nested inside another, so project-level
`.claude` directories inside a home are not mistaken for a second user. The
user is taken from `home/<user>`, `Users/<user>`, `usr/home/<user>`,
`export/home/<user>`, `root` or `var/root` in the path, falling back to the
directory name, and left empty when the input root itself is the home. When
the input is itself an agent directory, its name must match a one-segment
catalog entry such as `.claude` or `.codex`. Its parent is then the only
home, the user comes from the parent's path by the same conventions (with no
directory-name fallback), and `source_file` is relative to that parent.
Pass `--user` and `--host` to fill in what the path cannot say. Loose-mode
output is marked `inferred` in `detect --json` because none of this comes
from a manifest. Exclusions do not apply in loose mode: every file under a
matched catalog path is attributed and offered to the parsers.

## Detection

Detection uses the collectors' own catalog. `agent_analyzer/catalog.txt` is a
verbatim copy of `collect-agent-artifacts.sh --list`; the catalog drift test
in `collectors/tests/catalog-sync.sh` and the analyzer's own test suite both
fail when it is stale. Regenerate it with:

```sh
collectors/collect-agent-artifacts.sh --list > analyzer/agent_analyzer/catalog.txt
```

Every agent the collectors know is therefore detected, whether or not a
parser exists for it. When two entries match the same file, the more specific
one wins, so Antigravity CLI state under `.gemini/antigravity-cli` is
attributed to `antigravity`, not to the enclosing `gemini-cli` entry, in both
loose mode and the collectors' manifests. `python3 -m agent_analyzer catalog --agents` lists the
agents and which have parsers.

## Parsers

| Agent | Files | Validated against |
| --- | --- | --- |
| `claude-code` | `.claude/projects/<slug>/<session>.jsonl`, subagent transcripts under the session directory, `.claude/history.jsonl` | Real install, Claude Code 2.x, October 2026 |
| `codex-cli` | `.codex/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst` (needs `zstandard`), `.codex/history.jsonl` | Real install, Codex CLI, October 2026; archived and `.zst` rollouts from source at 3e23877, synthetic fixture |
| `antigravity` | `.gemini/antigravity-cli/conversations/*.db` (SQLite of protobuf steps, with WAL sidecars), `conversation_summaries.db`, `history.jsonl` | Protobuf descriptors extracted from the shipped `agy` binary plus a real install, October 2026; see `research/antigravity.md` |
| `qwen-code` | `.qwen/projects/<slug>/chats/<session>.jsonl` and `chats/archive/`, `.qwen/tmp/<hash>/logs.json` | Source at 2c591ec, synthetic fixture |
| `kiro` | Amazon Q CLI `data.sqlite3` (`conversations` and legacy `history` tables) under `amazon-q/` or `kiro-cli/` in `.local/share`, `Library/Application Support` or `AppData/Local`; `/save` exports (`.json` with `conversation_id` and `history`). Kiro CLI `.kiro/sessions/` files are not parsed until their format is confirmed | Source at 15cc8f3, synthetic fixture |
| `gemini-cli` | `.gemini/tmp/<slug>/chats/**/*.jsonl` (with `$set`, `$patch` and `$rewindTo` replayed), legacy `chats/**/*.json`, `tmp/<slug>/logs.json`, also under `.cache/.gemini`; project path from `.project_root` or `projects.json` | Source at fb972b2, synthetic fixture |
| `crush` | `<project>/.crush/crush.db` (SQLite with WAL sidecars; reached as a project artifact, or under a home when Crush ran in `~`), `.local/share/crush/projects.json`, `AppData/Local/crush/projects.json` | Source at ca6ae26, synthetic fixture |
| `goose` | `.local/share/goose/sessions/sessions.db` (SQLite with WAL sidecars), legacy `sessions/*.jsonl`, `.local/state/goose/logs/llm_request.*.jsonl`, `history.txt`, and the `AppData/Roaming/Block/goose/data` equivalents | Source at 591edd4, synthetic fixture |
| `continue` | `.continue/sessions/<sessionId>.json` (timestamped from `sessions/sessions.json` `dateCreated`; messages have no time of their own), `.continue/dev_data/<schema>/chatInteraction.jsonl` and `toolUsage.jsonl` | Source at 5522c6f, synthetic fixture |
| `aider` | `.aider.chat.history.md`, `.aider.input.history`, `.aider.llm.history`, in a home or (as agent `project` in the manifest) a repository; times are host local time, emitted as if UTC | Source at 5dc9490, synthetic fixture |
| `zed` | `threads/threads.db` (zstd-compressed JSON threads; needs `zstandard`) and `db/0-<channel>/db.sqlite` `sidebar_threads` (external-agent threads as `system` rows) under `.local/share/zed`, `Library/Application Support/Zed`, `AppData/Local/Zed` or the Flatpak data dir. No per-message timestamps: messages carry the thread's `updated_at` | Source at a846890, synthetic fixture |
| `vscode` | `User/workspaceStorage/<hash>/chatSessions/*.jsonl` and `.json` (with the sibling `workspace.json` for the project), `User/globalStorage/emptyWindowChatSessions/*`, `User/globalStorage/transferredChatSessions/*.json`, for Code, Code - Insiders, VSCodium, Positron, Trae and the `.vscode-server*/data` remote layout. Covers Copilot Chat; its model and participant ids are opaque strings | Source at d7622a5, synthetic fixture |
| `opencode` | `.local/share/opencode/opencode*.db` (SQLite with JSON columns, WAL sidecars; V1 `message`/`part`, V2 `session_message` for sessions without V1 rows), legacy JSON `storage/session/*/*.json` and `storage/message/*/*.json` with their `part/` files, and the older `project/<slug>/storage/session/` tree | Source at 907b3bc, synthetic fixture |
| `kilo-code` | `.local/share/kilo/kilo*.db` and `opencode-*.db` plus the same JSON trees under `.local/share/kilo` (OpenCode parser, Kilo paths), and pre-migration VS Code tasks `<globalStorage>/kilocode.kilo-code/tasks/<id>/api_conversation_history.json` | Source at 76bcfd4, synthetic fixture |
| `cline` | `<editor>/User/globalStorage/saoudrizwan.claude-dev/` and `.cline/data/`: `tasks/<id>/ui_messages.json` (preferred), `api_conversation_history.json` (only when `ui_messages.json` is absent; inherits the task start time), `task_metadata.json`, `state/taskHistory.json`; SDK `.cline/data/sessions/<id>/<id>.json` and `*.messages.json`, `.cline/data/db/sessions.db` | Source at 39ff2359, synthetic fixture; see `research/cline.md` |
| `roo-code` | `<editor>/User/globalStorage/rooveterinaryinc.roo-cline/` and `.vscode-mock/global-storage/`: the Cline task files plus `tasks/<id>/history_item.json` and `tasks/_index.json` | Source at b867ec91, synthetic fixture; see `research/roo-code.md` |
| `tabby` | Server-side: `.tabby/ee/db.sqlite` or `dev-db.sqlite` (SQLite with WAL sidecars; `threads`, `thread_messages`, `user_events`, thread owner from `users.email`; secret columns never read), the pre-migration backups `ee/db.backup-YYYYMMDD.sqlite` (may hold threads since deleted), and the completion event log `.tabby/events/YYYY-MM-DD.json` (full prompt and generated text). Project is the attached repository URL; no local path is recorded | Source at 21b2904, synthetic fixture; see `research/tabby.md` |
| `openhands` | `.openhands/agent-canvas/dev_conversations/<hex>/`, `.openhands/agent-canvas/conversations/<hex>/` and `.openhands/conversations/<hex>/`: one `events/event-<idx>-<id>.json` per event, with the sibling `meta.json` (title, `created_at`, working dir) and `base_state.json` (model). Event times are naive local time, corrected by the offset `meta.json` `created_at` implies, else emitted as if UTC. Legacy 0.x `sessions/<sid>/events/<n>.json` is reported as one `system` row per session, not parsed | Source at b347047 (SDK), synthetic fixture; see `research/openhands.md` |
| `shellgpt` | Files directly under a `chat_cache/` directory: `AppData/Local/Temp/chat_cache/<id>` and `AppData/Local/Temp/shell_gpt/chat_cache/<id>`, or a copied Linux or macOS temp directory given as loose input. One JSON array of OpenAI messages per chat, `tool_calls` and the pre-1.5.0 `function_call` shape; no timestamp, model or working directory is recorded, so those columns stay empty | Source at a082bd5, synthetic fixture; see `research/shellgpt.md` |
| `pi` | `.pi/agent/sessions/<cwd>/<time>_<id>.jsonl` and legacy `.pi/agent/*.jsonl` (session tree; fork entries copied from a collected parent file are dropped; a session that looks driven by little-coder gets a `system` row saying so), `.pi/agent/experimental/sessions/<id>/meta.json` (the durable `session.sqlite` beside it is not parsed) | Source at 2003871, synthetic fixture; see `research/pi.md` |
| `little-coder` | `.pi/agent/little-coder-prompt-history.json` (prompts without timestamps or sessions) and `.little-coder/checkpoints/<session file>/` (one `system` row per session's pre-edit copies); its transcripts are pi sessions, parsed as `pi` | Source at 89d4fa0, synthetic fixture; see `research/little-coder.md` |
| `letta` | Letta Code `.letta/lc-local-backend/conversations/<key>/messages.jsonl` (pi session format), `.letta/transcripts/<agent>/<conversation>/transcript.jsonl` (project path from `sessions.jsonl` by time, a heuristic; skipped when the conversation's `messages.jsonl` is present), `.letta/sessions.jsonl` | Source at 77faf36, synthetic fixture; see `research/letta.md` |
| `hermes` | `state.db` (SQLite with WAL sidecars; `sessions` and `messages`, rewound or compacted `active = 0` rows kept with a `[rewound]` prefix) and the fallback `sessions/<id>.jsonl` under `.hermes`, `.hermes_<suffix>`, `AppData/Local/hermes` and their `profiles/<name>/` homes | Source at 8b66a51, synthetic fixture |
| `agent-zero` | `usr/chats/<ctxid>/chat.json` (UI log for timestamps, each agent's history for full text and model, `messages/<n>.txt` for long tool results; history-only turns without timestamps when the log was trimmed at 1000 items) under `agent-zero`, `agent-zero/<instance>` or `Desktop/agent-zero`, also the legacy `chats/<ctxid>.json` and `tmp/chats`; project path is the container path `/a0/usr/projects/<name>` | Source at e3051fb, synthetic fixture |
| `open-interpreter` | Codex rollouts (Codex parser, Open Interpreter paths): `.openinterpreter/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst`, `.openinterpreter/history.jsonl`, and `external_agent_session_imports.json` (one `system` row per `/import`ed thread, naming the Claude Code or Cursor source file; that thread's record times are import time) | Source at 2767e5f, synthetic fixture |
| `openclaw` | `agents/<id>/agent/openclaw-agent.sqlite` (SQLite with WAL sidecars: `transcript_events`, zstd `event_zstd` rows need `zstandard`; unpublished reset/deleted archives and SQLite cold archives), legacy `agents/<id>/sessions/<id>.jsonl` and `sessions/*.jsonl`, reset and deleted archives `*.jsonl.reset.*` / `*.jsonl.deleted.*` (optionally `.zst`) and `sessions/cold/*.jsonl.zst`, under `.openclaw`, `.openclaw-<profile>`, `.clawdbot` or `.moltbot`. The session key (channel and sender) is in each session's start row; `auth_profile_store` is never read | Source at 3b16db7, synthetic fixture |
| `nanobot` | `.nanobot*/sessions/<workspace-id>/<key>.jsonl` (project path from the sibling `.workspace`), legacy `sessions/*.jsonl` and `.migration-conflicts/`, and `memory/history.jsonl`; times are host local time, emitted as if UTC | Source at acdae3d, synthetic fixture |
| `cody` | The `sourcegraph.cody-ai` row of a VS Code or fork `User/globalStorage/state.vscdb` (its `cody-local-chatHistory-v2` member) and the JetBrains file `Cody-nodejs/[Data/]JetBrains-globalState/cody-local-chatHistory-v2`. Every row of a chat carries the chat's creation time (its id); no project path is recorded | Source at 8e20ac6c, synthetic fixture |
| `twinny` | The `rjmacarthy.twinny` row of a VS Code or fork `User/globalStorage/state.vscdb` (`twinny.conversations`). Messages have no time of their own: every row carries the conversation's `updatedAt`. Provider `apiKey`s in the same value are never emitted | Source at 9339bd10, synthetic fixture |
| `pearai` | `.pearai/sessions/<sessionId>.json` (Continue fork, `history` and `perplexityHistory`, timestamped from `sessions.json` `dateCreated`) and `<editor>/User/globalStorage/pearai.pearai-roo-cline/tasks/<id>/` (Roo Code 3.15 fork through the Cline task mapping; XML tool calls in `api_conversation_history.json`; project from `taskHistory` in the sibling `state.vscdb`) | Source at 51eceef6 and 0b6df736, synthetic fixture |

The field names each parser relies on are listed in its module docstring
under `agent_analyzer/parsers/`. Thinking and reasoning blocks are left out
unless `--include-thinking` is passed. The `text` column carries the full
text of each event by default, so the timeline is a complete transcript, one
event per row; `--max-text-length` shortens it for a spreadsheet view. History files are parsed even when the
matching session transcript exists, because they survive session deletion;
filter on `source_file` to drop them.

Files the collector finds inside a discovered repository through its project
catalog are recorded with agent `project`; the analyzer offers each of them to
every parser and keeps the rows of any parser that accepts it, under that
parser's agent, so `--agent aider` also includes a repository's
`.aider.chat.history.md` and `--agent crush` its `.crush/crush.db`.

Every other file goes to the parsers of the agent the manifest (or, for loose
input, the catalog) attributes it to, plus any parser that names that agent
in its `reads_agents` attribute. Cody and Twinny keep their chats as rows of
the editor's own `state.vscdb`, which the catalog attributes to `vscode` or
to the fork whose `User/` directory holds it (`cursor`, `windsurf`, `pearai`,
`kiro`, `antigravity`); both parsers list all six editors in `reads_agents`,
so that file is offered to them too and the rows come out under `cody` or
`twinny`, and `--agent cody` selects them. `secret://` rows are never read.

Agents detected but not yet parsed: `claude-desktop`, `chatgpt-desktop`,
`copilot-cli`, `copilot`, `cursor`, `windsurf`, `amp`, `factory-droid`,
`augment`, `ollama` and `local-deep-research`, plus the `shared` and
`shell-history` entries, which are not agents.
Windsurf and Cursor need format work first.

Protobuf stores are decoded by `agent_analyzer/protobuf.py`, a small
schema-driven wire decoder, from field tables written into each parser. For
a closed-source agent the field names come from the descriptors embedded in
its binary. `tools/proto_descriptors.py extract BINARY OUT.json` extracts
them, and `show OUT.json MESSAGE...` and `find OUT.json TEXT` query them. SQLite
stores are copied together with their `-wal` and `-shm` sidecars into a
scratch directory before being opened, so the evidence copy is never touched
and rows still in the write-ahead log are not lost.

## Output

`detect` prints the input, its kind (`archive`, `collected` for an extracted
collection, or `loose`), the host, any notes, and one line per user, home
and agent with the number of files, their bytes (from the manifest `size`,
or from disk in loose mode), and whether a parser exists. The notes cover the
archive hash check, unreadable `collection.json`, manifest rows that do not
parse, and how a loose root was interpreted. `--files` adds one
`user<TAB>agent<TAB>path` line per attributed file. With `--json` the same
data is printed as one object with the keys `input`, `kind`, `host`,
`notes`, `homes` (`user`, `home`, `inferred`), `agents` (`user`, `home`,
`agent`, `files`, `bytes`, `parser`, `inferred`), and with `--files` also
`files` (`user`, `agent`, `path`). Collections made by collectors before
1.6.0 also hold a `live/` system snapshot, which appears as agent `live`
with no user, and `detect only`.

`timeline` writes three files into `-o`, creating the directory if needed,
and writes them even when no rows were produced:

```
timeline.csv    one row per turn, tool call, tool result or system event
sessions.csv    one row per session with first and last timestamp and counts
detect.json     the detect --json object without its homes and files keys
```

On stdout it prints the input, host and notes, one `problem:` line per file a
parser could not read, the agents parsed and the agents only detected, the
row count with a breakdown by agent and `turn_type`, and the session count.

Both CSV files are UTF-8 without a byte order mark, quoted where needed as
in RFC 4180, with CRLF line ends, and start with a header row.

`timeline.csv` columns, in order:

| Column | Meaning |
| --- | --- |
| `timestamp_utc` | ISO 8601 UTC with milliseconds, `2026-10-03T16:55:31.123Z`. Times recorded without a zone are taken as UTC. Epoch numbers above 10^11 are read as milliseconds, smaller ones as seconds. Empty when the record has none. |
| `host` | From `collection.json`, or `--host`. Empty for loose input without `--host`. |
| `user` | From the manifest, inferred from the path, or `--user`. |
| `agent` | Catalog agent name of the parser that produced the row. |
| `session_id` | The agent's own session or thread identifier. |
| `project_path` | Working directory recorded for the turn. |
| `git_branch` | Branch recorded for the turn, where the agent logs one. |
| `turn_type` | `user`, `assistant`, `tool_use`, `tool_result`, `system`, or `thinking` with `--include-thinking`. |
| `model` | Model that produced the turn, where recorded. |
| `tool_name` | For `tool_use` rows: the tool. Codex shell calls are `shell`. |
| `tool_use_id` | Links a `tool_use` row to its `tool_result`. |
| `text` | The event's text with whitespace runs collapsed: the prompt, the response, the tool output, or for a tool call its most identifying argument (the Bash command, the edited file, the search pattern, the fetched URL), else the arguments as JSON. Full length by default; `--max-text-length` cuts it. |
| `source_file` | Path of the record on the source host, as in the manifest. In loose mode it is the path relative to the input root with a leading `/`, or relative to the home when the input root is the home or an agent directory. |
| `source_line` | Where the record is in that file, so the full record can be read. For line-oriented files (JSONL, Markdown, text) the 1-based line number. For SQLite stores it is the record's `rowid` (Tabby events: the event id), and for JSON documents an array index or `1`. Each parser's module docstring says which. `0` when no position applies. |

Rows are sorted by timestamp, then by source file and line. Rows without a
timestamp sort last. Injected context (`isMeta` user records in Claude Code,
`developer` messages in Codex) is typed `system`, not `user`, so the `user`
rows are what the person typed. A line a parser cannot decode, such as a
transcript's last line cut off mid-write, is reported as a `system` row,
and the rest of the file is still read.

`sessions.csv` has one row per `host`, `user`, `agent` and `session_id`,
built from the timeline rows that have a session id. Its columns: `host`,
`user`, `agent`, `session_id`, `project_path` (the first non-empty one),
`first_timestamp_utc`, `last_timestamp_utc`, `models` (space separated, in
order of first use), `user_turns` and `assistant_turns` (rows of those
types), `tool_calls` (`tool_use` rows), and `source_file` (the file that
contributed the most rows). It is sorted by first timestamp, so sessions
with no timestamp come first.

The two CSV layouts are a compatibility contract with the analysts and
tooling that consume them. A future version may append new columns after the
existing ones, but existing columns keep their names, order and meaning.

## Inventory

`inventory` merges the output of collector runs made with `--inventory`
(sh) or `-Inventory` (PowerShell), described in the
[collectors README](../collectors/README.md#inventory-mode), into one CSV
for the fleet. Each `INPUT` is a file holding one host's captured stdout,
or a directory whose regular files are all read (not recursively, sorted
by name, symlinks skipped). A symlink given as `INPUT` is an error.

Each file is read line by line as UTF-8 (a byte order mark is dropped,
undecodable bytes are replaced). A line that is not a JSON object with
`type` `host` or `agent`, such as a console banner, a prompt or a record
cut off mid-line, is skipped, and the number skipped is printed on stderr
as `skipped N non-inventory lines in <file>`. Blank lines are skipped
without being counted. A `host` line opens a run, and each later `agent`
line in the same file is a row of that run until the next `host` line, so
one file may hold several runs. An `agent` line before any `host` line
gives a row with its own `host` and empty `collector`, `mode` and `at`.
Rows are written in input order; nothing is deduplicated, so two captures
of the same host give two sets of rows.

The CSV, `fleet-inventory.csv` in the current directory unless `-o` names
another path (missing parent directories are created), is UTF-8 without a
byte order mark, quoted where needed, with CRLF line ends and a header row.
Columns, in order:

| Column | Meaning |
| --- | --- |
| `host` | The run's `host` line `host`: the collector machine's host name. |
| `collector` | The collector version from the `host` line. |
| `mode` | `live` or `image`, from the `host` line. |
| `at` | The run's start time, normalised to ISO 8601 UTC with milliseconds, `2026-10-04T16:31:54.000Z`. |
| `user` | The home's user, or `docker` for a Docker or Podman volume. |
| `agent` | The catalog agent name. |
| `files`, `bytes` | Regular files under the agent's matched paths after exclusions, and their total size. |
| `first`, `last` | Earliest and latest file modification time, normalised like `at`. Empty when the collector reported none. |
| `projects` | The user's discovered project count, the same on each of the user's rows (the collector does not attribute projects to agents). |
| `evidence` | The catalog globs that matched, comma-separated, as the collector printed them. |

A `host` line with no `agent` lines after it gives one row with the four
host columns filled and the eight agent columns empty, so hosts where
nothing was found are still in the sheet. The `host` line's
`users_scanned`, `users_unreadable` and `docker_volumes` are not carried
into the CSV. The columns are an interface like the timeline's: new ones
are appended, existing ones keep their names, order and meaning.

On stdout `inventory` then prints `rows: N from H hosts in <path>` (H
counts distinct `host` values) and, when any row has an agent, a rollup
with one line per agent: `agent`, `hosts` (distinct hosts with a row for
it), `users` (distinct host and user pairs, `docker` included) and
`latest` (the greatest `last`). The rollup is sorted by `hosts`, then
`users`, both descending, then by agent name.

## Options

```
analyze-agent-artifacts detect INPUT [--json] [--files] [common options]
analyze-agent-artifacts timeline INPUT -o DIR [--max-text-length N] [--include-thinking] [--agent NAME]... [common options]
analyze-agent-artifacts inventory [-o FILE] INPUT...
analyze-agent-artifacts catalog [--agents]
analyze-agent-artifacts --version
```

| Option | Subcommand | Meaning |
| --- | --- | --- |
| `--json` | `detect` | Print the machine-readable object described under [Output](#output). |
| `--files` | `detect` | Also list every attributed file. |
| `-o, --output DIR` | `timeline` | Output directory, required. |
| `-o, --output FILE` | `inventory` | CSV to write. Default `fleet-inventory.csv` in the current directory. |
| `--max-text-length N` | `timeline` | Cut the `text` column to N characters, the last of which is an ellipsis. Default `0`, the full text. |
| `--include-thinking` | `timeline` | Emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | `timeline` | Run only the parsers of this agent. Repeatable. An unknown name produces no rows. |
| `--agents` | `catalog` | Print each agent in the catalog with `parser` or `detect only`, instead of the catalog text. |
| `--host NAME` | `detect`, `timeline` | Host name to record. Overrides `collection.json`. |
| `--user NAME` | `detect`, `timeline` | User to record for every home whose user is empty. |
| `--work-dir DIR` | `detect`, `timeline` | Where to extract an archive. A `cac-*` directory is created inside it. Default: a `cac-analyzer-*` directory in the system temp directory. Either is removed afterwards unless `--keep-extracted` is given. |
| `--keep-extracted` | `detect`, `timeline` | Keep the extracted archive and print `extracted to: <path>` on stderr. |

`catalog` prints the bundled `catalog.txt` verbatim.

| Exit code | Meaning |
| --- | --- |
| `0` | `timeline` wrote at least one row; `detect` found agent artifacts, or `--json` was given; `inventory` wrote at least one row; `catalog`, `--version`. |
| `1` | `timeline` produced no rows (the three files are still written), `detect` without `--json` found no agent artifacts, or `inventory` found no `host` or `agent` line (the CSV is written with its header only). |
| `2` | The input does not exist, a file input is neither tar nor zip, an `inventory` input is a symlink or a file or directory that cannot be read, or the command line is invalid. |

## Testing

```sh
cd analyzer
tests/run.sh                 # python3 -m unittest discover -s tests -t tests
tests/run.sh -p 'test_catalog*'   # extra arguments go to unittest discover
```

`tests/run.sh` changes to the `analyzer/` directory itself, so it can be run
from anywhere.

The suite builds a fake image with two Linux users and a Windows profile
tree, each holding synthetic state for every parsed agent in the exact shapes
the parsers were validated against, and checks detection in every input mode,
each parser's rows, the CSV output, and the bundled catalog against the
collector's `--list`. When `sh` and `tar` are available it also runs the sh
collector on the fake image and analyses the resulting archive end to end.
`test_inventory.py` feeds `inventory` captured outputs of three hosts, one
with console junk lines and one with a `host` line only, and checks the
columns, the default file name, `-o`, the rollup and the empty-host row;
with `sh` available it also runs the collector's `--inventory` on the fake
image and reads that.
Tests that need `zstandard`, the collector script, `sh` and `tar`, or
permission to create symlinks are skipped, with the reason, when it is
missing. CI runs the suite on Python 3.10, 3.12 and 3.13 with `requirements.txt`
installed.

## Adding a parser

1. Confirm the record format against source or a real install and write the
   field names into the module docstring, as the existing parsers do.
2. Subclass `Parser` in `agent_analyzer/parsers/<agent>.py`: set `agent` to
   the catalog name, implement `wants` on `artifact.rel` and `parse` yielding
   `Row` objects. Use `iter_jsonl` so a truncated line is reported, not fatal.
   Timestamps go through `to_utc`; text through `compact`, which collapses
   whitespace and applies `--max-text-length`.
3. Register it in `agent_analyzer/parsers/__init__.py`. A parser that must
   read a file the catalog attributes to another agent sets `reads_agents`.
4. Add fixture records to `tests/fixtures.py` and a test class to
   `tests/test_parsers.py`. Then add the row to the table above.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
