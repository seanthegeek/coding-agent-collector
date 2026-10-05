# Analyzer

The analyst-side half of coding-agent-collector. It takes a collector archive,
an extracted collection, or any loose directory tree, detects which AI coding
agents left state in it, and parses the transcripts it knows how to read into
one normalised JSONL timeline. It never runs on the host under investigation, so
unlike the collectors it may carry dependencies. It needs Python 3.10 or
later and the packages in `requirements.txt` (`pip install -r
requirements.txt`): `python-dateutil`, required, which reads the
`--since` and `--until` times, and `zstandard`, optional, for Zed threads,
Codex and Open Interpreter `.jsonl.zst` rollouts and OpenClaw's compressed
transcript rows. Without `zstandard` each such thread, rollout or row is
reported as an undecodable `system` row and everything else still runs.

[CHANGELOG.md](CHANGELOG.md) lists what changed in each version, including
changes to the `timeline.jsonl` and `sessions.jsonl` fields.

## Quick start

```sh
cd analyzer

# What is in this collection?
python3 -m agent_analyzer detect /cases/host01/host01_20261003T165531Z_agent-artifacts.tar.gz

# Build the timeline
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/analysis

# Every Bash command Claude Code ran, from the timeline
jq -r 'select(.agent == "claude-code" and .tool_name == "Bash") | .text' /cases/host01/analysis/timeline.jsonl

# Only 1 October 2026 (UTC), or only the last three days
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/oct1 --since 2026-10-01 --until 2026-10-01
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/recent --since 3d

# Only events whose text mentions curl or wget, with the paired tool calls and results
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/net --match 'curl|wget' -i

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
directory that holds only shared files such as `AGENTS.md` is a
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

### Unreadable inputs

An input that cannot be opened stops `detect`, `timeline` and `inventory`
with exit code `2` and one line on stderr, `error: <path>: <reason>`, where
the reason is the operating system's message in lower case, such as
`no such file or directory` or `permission denied`. The path is the file
the operating system named, so it is the input itself, or `manifest.jsonl`
inside it, or the archive member being extracted. This covers an input that
cannot be stat'ed (including one inside a directory the analyst cannot
traverse), an input directory that cannot be listed, an archive that cannot
be read or written to the work directory while it is extracted, and a
`manifest.jsonl` that cannot be read. An archive whose content is corrupt
gives `error: <path>: cannot extract: <reason>`. An extracted archive is
removed before the command exits.

Anything inside an input that cannot be read is a `problem:` line and the
command carries on:

| Problem line | When |
| --- | --- |
| `<directory>: <reason>` | A directory in a loose tree that cannot be listed, while homes are discovered or files under a catalog match are walked. Reported once per directory; nothing under it is attributed. |
| `<original path>: missing from the collection` | A manifest row with status `collected` and type `file` whose `archive_path` is not a regular file in the extracted collection, for example in a truncated or edited archive. The row is not attributed. Any other reason the file cannot be stat'ed is printed instead. |
| `<original path>: <reason>` | `timeline` only: a parser could not read an attributed file. |

`detect` prints them after the notes, and `timeline` before its `window:`
line. Symlinks are never followed, so a dangling symlink in a loose tree is
skipped like any other symlink rather than reported. An unreadable
`collection.json` is a note, `collection.json unreadable: <reason>`, and an
unreadable `.sha256` sidecar is the note `WARNING archive sha256 not
checked: <path>: <reason>`.

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
| `agent-zero` | `usr/chats/<ctxid>/chat.json` (UI log for timestamps, each agent's history for full text and model, `messages/<n>.txt` for long tool results; history-only turns without timestamps when the log was trimmed at 1000 items) under `agent-zero`, `agent-zero/<instance>` or `Desktop/agent-zero`, also the legacy `chats/<ctxid>.json` and `tmp/chats`; project path is the container path `/a0/usr/projects/<name>` | Source at e3051fb, synthetic fixture; see [`research/agent-zero.md`](research/agent-zero.md) |
| `aider` | `.aider.chat.history.md`, `.aider.input.history`, `.aider.llm.history`, in a home or (as agent `project` in the manifest) a repository; times are host local time, emitted as if UTC | Source at 5dc9490, synthetic fixture; see [`research/aider.md`](research/aider.md) |
| `antigravity` | `.gemini/antigravity-cli/conversations/*.db` (SQLite of protobuf steps, with WAL sidecars), `conversation_summaries.db`, `history.jsonl` | Protobuf descriptors extracted from the shipped `agy` binary plus a real install, October 2026; see [`research/antigravity.md`](research/antigravity.md) |
| `claude-code` | `.claude/projects/<slug>/<session>.jsonl`, subagent transcripts under the session directory (each opens with a `subagent <id> of <session>` row), `tool-results/*.txt` in the session directory when a result's `<persisted-output>` stub names it, `.claude/history.jsonl`; the same files under a `.claude-<name>` config home moved with `CLAUDE_CONFIG_DIR` (such as `.claude-work/projects/...`) | Real install, Claude Code 2.1.286 to 2.1.289, and the shipped 2.1.289 package strings, October 2026; see [`research/claude-code.md`](research/claude-code.md) |
| `cline` | `<editor>/User/globalStorage/saoudrizwan.claude-dev/` and `.cline/data/`: `tasks/<id>/ui_messages.json` (preferred), `api_conversation_history.json` (only when `ui_messages.json` is absent; inherits the task start time), `task_metadata.json`, `state/taskHistory.json`; SDK `.cline/data/sessions/<id>/<id>.json` and `*.messages.json`, `.cline/data/db/sessions.db` | Source at 39ff2359, synthetic fixture; see [`research/cline.md`](research/cline.md) |
| `codex-cli` | `.codex/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst` (needs `zstandard`), `.codex/history.jsonl` | Real install, Codex CLI, October 2026; archived and `.zst` rollouts, subagent and fork records from source at 3e23877, synthetic fixture. User-role context (environment, AGENTS.md, skills) is `system` by its content kind; a subagent row links each spawned thread to its parent; turn items that no response item carries become rows; see [`research/codex-cli.md`](research/codex-cli.md) |
| `cody` | The `sourcegraph.cody-ai` row of a VS Code or fork `User/globalStorage/state.vscdb` (its `cody-local-chatHistory-v2` member) and the JetBrains file `Cody-nodejs/[Data/]JetBrains-globalState/cody-local-chatHistory-v2`. Every row of a chat carries the chat's creation time (its id); no project path is recorded | Source at 8e20ac6c, synthetic fixture; see [`research/cody.md`](research/cody.md) |
| `continue` | `.continue/sessions/<sessionId>.json` (timestamped from `sessions/sessions.json` `dateCreated`; messages have no time of their own), `.continue/dev_data/<schema>/chatInteraction.jsonl` and `toolUsage.jsonl` | Source at 5522c6f, synthetic fixture; see [`research/continue.md`](research/continue.md) |
| `crush` | `<project>/.crush/crush.db` (SQLite with WAL sidecars; reached as a project artifact, or under a home when Crush ran in `~`), `.local/share/crush/projects.json`, `AppData/Local/crush/projects.json` | Source at ca6ae26, synthetic fixture; see [`research/crush.md`](research/crush.md) |
| `gemini-cli` | `.gemini/tmp/<slug>/chats/**/*.jsonl` (with `$set`, `$patch` and `$rewindTo` replayed), legacy `chats/**/*.json`, `tmp/<slug>/logs.json`, also under `.cache/.gemini`; project path from `.project_root` or `projects.json` | Source at fb972b2, synthetic fixture; see [`research/gemini-cli.md`](research/gemini-cli.md) |
| `goose` | `.local/share/goose/sessions/sessions.db` (SQLite with WAL sidecars), legacy `sessions/*.jsonl`, `.local/state/goose/logs/llm_request.*.jsonl`, `history.txt`, and the `AppData/Roaming/Block/goose/data` equivalents | Source at 591edd4, synthetic fixture; see [`research/goose.md`](research/goose.md) |
| `hermes` | `state.db` (SQLite with WAL sidecars; `sessions` and `messages`, rewound or compacted `active = 0` rows kept with a `[rewound]` prefix) and the fallback `sessions/<id>.jsonl` under `.hermes`, `.hermes_<suffix>`, `AppData/Local/hermes` and their `profiles/<name>/` homes | Source at 8b66a51, synthetic fixture; see [`research/hermes.md`](research/hermes.md) |
| `kilo-code` | `.local/share/kilo/kilo*.db` and `opencode-*.db` plus the same JSON trees under `.local/share/kilo` (OpenCode parser, Kilo paths), and pre-migration VS Code tasks `<globalStorage>/kilocode.kilo-code/tasks/<id>/api_conversation_history.json` | Source at 76bcfd4, synthetic fixture; see [`research/kilo-code.md`](research/kilo-code.md) |
| `kiro` | Amazon Q CLI `data.sqlite3` (`conversations` and legacy `history` tables) under `amazon-q/` or `kiro-cli/` in `.local/share`, `Library/Application Support` or `AppData/Local`; `/save` exports (`.json` with `conversation_id` and `history`). Kiro CLI `.kiro/sessions/` files are not parsed until their format is confirmed | Source at 15cc8f3, synthetic fixture; see [`research/kiro.md`](research/kiro.md) |
| `letta` | Letta Code `.letta/lc-local-backend/conversations/<key>/messages.jsonl` (pi session format), `.letta/transcripts/<agent>/<conversation>/transcript.jsonl` (project path from `sessions.jsonl` by time, a heuristic; skipped when the conversation's `messages.jsonl` is present), `.letta/sessions.jsonl` | Source at 77faf36, synthetic fixture; see [`research/letta.md`](research/letta.md) |
| `little-coder` | `.pi/agent/little-coder-prompt-history.json` (prompts without timestamps or sessions) and `.little-coder/checkpoints/<session file>/` (one `system` row per session's pre-edit copies); its transcripts are pi sessions, parsed as `pi` | Source at 89d4fa0, synthetic fixture; see [`research/little-coder.md`](research/little-coder.md) |
| `muse-code` | `.local/share/muse/sessions/YYYY/MM/DD/<id>/session.jsonl` and each subagent's `subagent/<id>/session.jsonl` (event envelopes with microsecond `recorded_at`; tool calls and results joined on `call_id`; approval requests and decisions as `system` rows; a subagent takes its project path and branch from the parent log), `.local/share/muse/tui-history.jsonl` (prompts without timestamps). The approval reviewer's `approval-review/*.jsonl` (synthetic clock), `tool-outputs/` and the SQLite indexes are not read | Shipped binary 1.4.2 strings, vendor skills and a real install (Linux), October 2026, synthetic fixture; see [`research/muse-code.md`](research/muse-code.md) |
| `nanobot` | `.nanobot*/sessions/<workspace-id>/<key>.jsonl` (project path from the sibling `.workspace`), legacy `sessions/*.jsonl` and `.migration-conflicts/`, and `memory/history.jsonl`; times are host local time, emitted as if UTC | Source at acdae3d, synthetic fixture; see [`research/nanobot.md`](research/nanobot.md) |
| `open-interpreter` | Codex rollouts (Codex parser, Open Interpreter paths): `.openinterpreter/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst`, `.openinterpreter/history.jsonl`, and `external_agent_session_imports.json` (one `system` row per `/import`ed thread, naming the Claude Code or Cursor source file; that thread's record times are import time) | Source at 2767e5f, synthetic fixture; see [`research/open-interpreter.md`](research/open-interpreter.md) |
| `openclaw` | `agents/<id>/agent/openclaw-agent.sqlite` (SQLite with WAL sidecars: `transcript_events`, zstd `event_zstd` rows need `zstandard`; unpublished reset/deleted archives and SQLite cold archives), legacy `agents/<id>/sessions/<id>.jsonl` and `sessions/*.jsonl`, reset and deleted archives `*.jsonl.reset.*` / `*.jsonl.deleted.*` (optionally `.zst`) and `sessions/cold/*.jsonl.zst`, under `.openclaw`, `.openclaw-<profile>`, `.clawdbot` or `.moltbot`. The session key (channel and sender) is in each session's start row; `auth_profile_store` is never read | Source at 3b16db7, synthetic fixture; see [`research/openclaw.md`](research/openclaw.md) |
| `opencode` | `.local/share/opencode/opencode*.db` (SQLite with JSON columns, WAL sidecars; V1 `message`/`part`, V2 `session_message` for sessions without V1 rows), legacy JSON `storage/session/*/*.json` and `storage/message/*/*.json` with their `part/` files, and the older `project/<slug>/storage/session/` tree | Source at 907b3bc, synthetic fixture; see [`research/opencode.md`](research/opencode.md) |
| `openhands` | `.openhands/agent-canvas/dev_conversations/<hex>/`, `.openhands/agent-canvas/conversations/<hex>/` and `.openhands/conversations/<hex>/`: one `events/event-<idx>-<id>.json` per event, with the sibling `meta.json` (title, `created_at`, working dir) and `base_state.json` (model). Event times are naive local time, corrected by the offset `meta.json` `created_at` implies, else emitted as if UTC. Legacy 0.x `sessions/<sid>/events/<n>.json` is reported as one `system` row per session, not parsed | Source at b347047 (SDK), synthetic fixture; see [`research/openhands.md`](research/openhands.md) |
| `pearai` | `.pearai/sessions/<sessionId>.json` (Continue fork, `history` and `perplexityHistory`, timestamped from `sessions.json` `dateCreated`) and `<editor>/User/globalStorage/pearai.pearai-roo-cline/tasks/<id>/` (Roo Code 3.15 fork through the Cline task mapping; XML tool calls in `api_conversation_history.json`; project from `taskHistory` in the sibling `state.vscdb`) | Source at 51eceef6 and 0b6df736, synthetic fixture; see [`research/pearai.md`](research/pearai.md) |
| `pi` | `.pi/agent/sessions/<cwd>/<time>_<id>.jsonl` and legacy `.pi/agent/*.jsonl` (session tree; fork entries copied from a collected parent file are dropped; a session that looks driven by little-coder gets a `system` row saying so), `.pi/agent/experimental/sessions/<id>/meta.json` (the durable `session.sqlite` beside it is not parsed) | Source at 2003871, synthetic fixture; see [`research/pi.md`](research/pi.md) |
| `qwen-code` | `.qwen/projects/<slug>/chats/<session>.jsonl` and `chats/archive/`, `.qwen/tmp/<hash>/logs.json` | Source at 2c591ec, synthetic fixture; see [`research/qwen-code.md`](research/qwen-code.md) |
| `roo-code` | `<editor>/User/globalStorage/rooveterinaryinc.roo-cline/` and `.vscode-mock/global-storage/`: the Cline task files plus `tasks/<id>/history_item.json` and `tasks/_index.json` | Source at b867ec91, synthetic fixture; see [`research/roo-code.md`](research/roo-code.md) |
| `shellgpt` | Files directly under a `chat_cache/` directory: `AppData/Local/Temp/chat_cache/<id>` and `AppData/Local/Temp/shell_gpt/chat_cache/<id>`, or a copied Linux or macOS temp directory given as loose input. One JSON array of OpenAI messages per chat, `tool_calls` and the pre-1.5.0 `function_call` shape; no timestamp, model or working directory is recorded, so those columns stay empty | Source at a082bd5, synthetic fixture; see [`research/shellgpt.md`](research/shellgpt.md) |
| `tabby` | Server-side: `.tabby/ee/db.sqlite` or `dev-db.sqlite` (SQLite with WAL sidecars; `threads`, `thread_messages`, `user_events`, thread owner from `users.email`; secret columns never read), the pre-migration backups `ee/db.backup-YYYYMMDD.sqlite` (may hold threads since deleted), and the completion event log `.tabby/events/YYYY-MM-DD.json` (full prompt and generated text). Project is the attached repository URL; no local path is recorded | Source at 21b2904, synthetic fixture; see [`research/tabby.md`](research/tabby.md) |
| `twinny` | The `rjmacarthy.twinny` row of a VS Code or fork `User/globalStorage/state.vscdb` (`twinny.conversations`). Messages have no time of their own: every row carries the conversation's `updatedAt`. Provider `apiKey`s in the same value are never emitted | Source at 9339bd10, synthetic fixture; see [`research/twinny.md`](research/twinny.md) |
| `vscode` | `User/workspaceStorage/<hash>/chatSessions/*.jsonl` and `.json` (with the sibling `workspace.json` for the project), `User/globalStorage/emptyWindowChatSessions/*`, `User/globalStorage/transferredChatSessions/*.json`, for Code, Code - Insiders, VSCodium, Positron, Trae and the `.vscode-server*/data` remote layout. Covers Copilot Chat; its model and participant ids are opaque strings | Source at d7622a5, synthetic fixture; see [`research/vscode.md`](research/vscode.md) |
| `zed` | `threads/threads.db` (zstd-compressed JSON threads; needs `zstandard`) and `db/0-<channel>/db.sqlite` `sidebar_threads` (external-agent threads as `system` rows) under `.local/share/zed`, `Library/Application Support/Zed`, `AppData/Local/Zed` or the Flatpak data dir. No per-message timestamps: messages carry the thread's `updated_at` | Source at a846890, synthetic fixture; see [`research/zed.md`](research/zed.md) |

The field names each parser relies on are listed in its module docstring
under `agent_analyzer/parsers/`. Thinking and reasoning blocks are left out
unless `--include-thinking` is passed. The `text` field carries the full
text of each event, line breaks included, so the timeline is a complete
transcript, one event per line. History files are parsed even when the
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
`augment`, `ollama` and `local-deep-research`, plus the `shared` entries,
which are not agents.
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
parse, and how a loose root was interpreted. One `problem:` line follows the
notes for each directory or file inside the input that could not be read
(see [Unreadable inputs](#unreadable-inputs)). `--files` adds one
`user<TAB>agent<TAB>path` line per attributed file. With `--json` the same
data is printed as one object with the keys `input`, `kind`, `host`,
`notes`, `homes` (`user`, `home`, `inferred`), `agents` (`user`, `home`,
`agent`, `files`, `bytes`, `parser`, `inferred`), `problems` (an array of
the problem line texts, without the `problem:` prefix), and with `--files`
also `files` (`user`, `agent`, `path`). Collections made by collectors before
1.6.0 also hold a `live/` system snapshot, which appears as agent `live`
with no user, and `detect only`.

`timeline` writes three files into `-o`, creating the directory if needed,
and writes them even when no rows were produced:

```text
timeline.jsonl  one record per turn, tool call, tool result or system event
sessions.jsonl  one record per session with first and last timestamp and counts
detect.json     the detect --json object without its homes and files keys; its
                problems also hold the files a parser could not read
```

On stdout it prints the input, host and notes, one `problem:` line per
directory or file that could not be read (see
[Unreadable inputs](#unreadable-inputs)), and, when the timeline is filtered, a `window:` line
with the resolved UTC bounds, a `match:` line with the patterns, and a
`filtered:` line counting the rows dropped outside the window, without a
timestamp, and not matching. Then come the agents parsed and the agents only
detected, the row count with a breakdown by agent and `turn_type`, and the
session count. The agents parsed are those that produced rows before
filtering; the breakdown counts the rows written.

Both JSONL files are UTF-8 without a byte order mark, one JSON object per
line, each line ended by LF, with no header line. Every object has every
field, in the order listed below. Fields with no value hold the empty string
`""`, never `null`, and every field is a string except the integers
`source_line`, `user_turns`, `assistant_turns` and `tool_calls` and the
array `models`. A line holds no literal line break: newlines inside
`text` are written as `\n`, and U+2028 and U+2029 as `\u2028` and
`\u2029`, because some line readers split on them. Other non-ASCII text is
written as UTF-8, not escaped, so a search for it matches as typed; the
exception is a record whose text holds a lone UTF-16 surrogate, which UTF-8
cannot encode, and which is written entirely with `\uXXXX` escapes.
There is no space after `:` or `,`, the same layout `jq -c` prints, so a
`grep` pattern such as `"agent":"codex-cli"` matches the file and jq output
alike. [Reading and searching the output](#reading-and-searching-the-output)
has recipes.

`timeline.jsonl` fields, in order:

| Field | Meaning |
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
| `text` | The event's full text, with leading and trailing whitespace removed and inner line breaks and indentation kept: the prompt, the response, the tool output, or for a tool call its most identifying argument (the Bash command, the edited file, the search pattern, the fetched URL), else the arguments as JSON. |
| `source_file` | Path of the record on the source host, as in the manifest. In loose mode it is the path relative to the input root with a leading `/`, or relative to the home when the input root is the home or an agent directory. |
| `source_line` | Integer. Where the record is in that file, so the full record can be read. For line-oriented files (JSONL, Markdown, text) the 1-based line number. For SQLite stores it is the record's `rowid` (Tabby events: the event id), and for JSON documents an array index or `1`. Each parser's module docstring says which. `0` when no position applies. |

Rows are sorted by timestamp, then by source file and line. Rows without a
timestamp sort last. Injected context is typed `system`, not `user`, so
the `user` rows are what the person typed. In Claude Code that is
`isMeta` records, task notifications, slash commands and their output, a
subagent's task, compaction summaries and messages from other agents. In
Codex it is `developer` messages and user-role blocks whose content kind
names harness context rather than `user.*` input, or, in older rollouts
without content kinds, a block that is wholly a harness wrapper such as
`<environment_context>`. These `system` rows start with a lowercase label
naming the source, such as `subagent task:`, `task notification:`,
`slash command:`, `command output:` or `context: <kind>:`, followed by the
full text. A line a parser cannot decode, such as a
transcript's last line cut off mid-write, is reported as a `system` row,
and the rest of the file is still read.

`sessions.jsonl` has one record per `host`, `user`, `agent` and
`session_id`, built from the timeline records that have a session id. Its
fields, in order: `host`, `user`, `agent`, `session_id`, `project_path`
(the first non-empty one), `first_timestamp_utc`, `last_timestamp_utc`,
`models` (an array of strings, in order of first use, empty when none was
recorded), `user_turns` and `assistant_turns` (integers, timeline records
of those types), `tool_calls` (integer, `tool_use` records), and
`source_file` (the file that contributed the most records). It is sorted by
first timestamp, so sessions with no timestamp come first.

The two JSONL layouts are a compatibility contract with the analysts and
tooling that consume them. A future version may append new fields after the
existing ones, but existing fields keep their names, order, type and
meaning.

## Filtering the timeline

`timeline` can write only part of the timeline, which keeps the output of a
busy host to the incident window:

- `--since WHEN` and `--until WHEN` keep rows with `since <= timestamp_utc
  <= until`. Either may be given alone. Rows without a timestamp are
  dropped once either is given, unless `--keep-undated` is passed. Formats
  without per-message times (Continue, Zed, Cline's legacy history) give
  their rows the session's timestamp, so those rows are kept or dropped by
  the time the session started.
- `--match REGEX` keeps rows whose `text` matches the Python regular
  expression ([`re` syntax](https://docs.python.org/3/library/re.html),
  searched anywhere in the text, so anchor with `^` and `$` for a whole
  match). Repeat it to keep rows that match any of the patterns; `-i`
  makes every pattern case-insensitive. A matched `tool_use` row keeps its
  `tool_result` row, and a matched result its call, when the partner has
  the same `session_id` and `tool_use_id` (the same `source_file` for rows
  without a session id) and is inside the time window. Only `text` is
  searched; filter other fields with jq afterwards.
- `--match` applies after the time window. `sessions.jsonl` is summarised
  from the rows that are kept, so its counts and first and last timestamps
  describe the filtered timeline, not the whole session.

The resolved window is printed as a `window:` line, so a relative value
such as `3d` can be checked and recorded in case notes. A value that is not
one of the forms below, a `--since` later than the `--until`, or a
`--match` that is not a valid regular expression stops the command with
exit code `2` before the input is opened or extracted.

`WHEN` is one of the following, after surrounding whitespace is trimmed;
day words, units, `ago`, `Z` and `UTC` may be in any case. Nothing else is
accepted, and nothing is guessed. A value without an offset is UTC, like the timeline.

| Form | Examples | Meaning |
| --- | --- | --- |
| ISO 8601 date | `2026-10-01`, basic `20261001`, week date `2026-W40-1`, ordinal `2026-274` | That day. |
| Year or month | `2026`, `2026-10` | That year or month. |
| Date and time, `T` or one space between them | `2026-10-01T09`, `2026-10-01T09:30`, `2026-10-01 09:30`, `2026-10-01 09:30:15`, `2026-10-01T09:30:15.250`, basic `20261001T093015` | Seconds are optional and may carry a fraction. |
| Date and time with a UTC offset, directly after the time or after one space | `2026-10-01T09:30Z`, `2026-10-01T09:30+02:00`, `2026-10-01T09:30-0500`, `2026-10-01T09:30+02`, `2026-10-01 09:30 +02:00`, `2026-10-01 09:30 UTC` | Offsets are `Z`, `UTC` (after a space only), `+HH:MM`, `+HHMM` or `+HH`; `-` is west of UTC. The time is converted to UTC. |
| Epoch number | `1759312800`, `1759312800000` | Seconds since 1970; a number above 10^11 is milliseconds. |
| Day word | `today`, `yesterday` | That UTC calendar day. |
| `now` | `now` | The current time. |
| Relative time | `45m`, `45min`, `45 minutes`, `36h`, `36 hours`, `3d`, `3 days ago`, `2w`, `6mo`, `6 months ago`, `1y`, `2 years` | That long before now. The space and a trailing `ago` are optional; units are `m`, `min`, `minute(s)` (minutes), `h`, `hour(s)`, `d`, `day(s)`, `w`, `week(s)`, `mo`, `month(s)`, `y`, `year(s)`. `m` is always minutes and `mo` always months. Months and years move the calendar date and keep the time of day; a day the target month lacks becomes its last day, so 31 March less `1mo` is 28 February (29 in a leap year). |

An absolute value or a day word names a period as long as its last written
unit: a year, a month, a day, an hour (`T09`), a minute (`09:30`) or a
second (`09:30:15`). `--since` takes the period's first millisecond and
`--until` its last, so `--since 2026-10-01 --until 2026-10-01` selects
that whole day, `--until 2026-10` runs to the end of October, and
`--until "2026-10-01 09:30"` keeps an event at 09:30:40. A time with a
fraction of a second, `now`, a relative time and an epoch number are
instants, used as they are. Dates and times are parsed by
`dateutil.parser.isoparse` and months and years counted by
`dateutil.relativedelta`, both from `python-dateutil`; the forms
themselves are defined in `agent_analyzer/filters.py`.

## Reading and searching the output

A timeline from a busy host can run to gigabytes, because `text` holds full
tool output. Each line is one complete record, so the tools below stream
the file line by line and use little memory however large it is. The
examples run in the `-o` directory. A spreadsheet is the wrong viewer for
these files: Excel stops at 1,048,576 rows and 32,767 characters per cell.
Export a filtered, shortened subset to CSV instead, as shown at the end of
the jq examples.

**jq** (<https://jqlang.org>) reads one record at a time. Never pass `-s`
(slurp) on a large file, which loads the whole file into memory.

```sh
# Look at one record, pretty-printed
head -n 1 timeline.jsonl | jq .

# Record counts by agent and turn type
jq -r '[.agent, .turn_type] | @tsv' timeline.jsonl | sort | uniq -c | sort -rn

# Tool calls of one tool, with a few fields
jq -c 'select(.turn_type == "tool_use" and .tool_name == "Bash") | {timestamp_utc, user, text}' timeline.jsonl

# Case-insensitive regular expression over the text
jq -c 'select(.text | test("curl|wget|base64 -d"; "i")) | [.timestamp_utc, .agent, .turn_type, .text[0:120]]' timeline.jsonl

# One session as a readable transcript; line breaks in text are printed as line breaks
jq -r --arg s SESSION_ID 'select(.session_id == $s) | "\(.timestamp_utc)  \(.turn_type)  \(.tool_name)\n\(.text)\n"' timeline.jsonl | less

# A tool call and its result. IDs such as call_1 repeat across agents and
# sessions, so match the session too
jq -c --arg s SESSION_ID --arg id TOOL_USE_ID 'select(.session_id == $s and .tool_use_id == $id)' timeline.jsonl

# Sessions with more than 20 tool calls, and their models
jq -r 'select(.tool_calls > 20) | [.first_timestamp_utc, .user, .agent, .session_id, .tool_calls, (.models | join(" "))] | @tsv' sessions.jsonl

# A CSV for a spreadsheet: filter first, and cut text to 200 characters
jq -r 'select(.agent == "codex-cli") | [.timestamp_utc, .host, .user, .agent, .session_id, .turn_type, .tool_name, .text[0:200]] | @csv' timeline.jsonl > codex.csv
```

**grep first, then jq.** `grep -F` and `rg -F` scan text many times faster
than jq parses JSON, so use them to cut a large file down and jq to check
the field. A grep match can come from any field, so always confirm with a
`select` on the field you meant. Write patterns as the record stores them:
`"turn_type":"tool_use"` without spaces, a quote inside text as `\"`, a
backslash as `\\`, and a line break as the two characters `\n`.

```sh
grep -F '"turn_type":"tool_use"' timeline.jsonl | jq -r .tool_name | sort | uniq -c | sort -rn
rg -F 'aws_secret_access_key' timeline.jsonl | jq -c '{timestamp_utc, user, agent, source_file, source_line}'
```

**Split or compress.** One file per agent keeps each one small enough for an
editor, and gzip shrinks transcripts severalfold; `zcat` feeds jq and
`rg -z` searches the compressed file directly.

```sh
mkdir -p by-agent
jq -r .agent timeline.jsonl | sort -u | while read -r a; do
  jq -c --arg a "$a" 'select(.agent == $a)' timeline.jsonl > "by-agent/$a.jsonl"
done
gzip -k timeline.jsonl && zcat timeline.jsonl.gz | jq -c 'select(.agent == "codex-cli")'
```

**DuckDB** (<https://duckdb.org>) runs SQL over the file without an import
step, and keeps `session_id` a string even when it looks like a number.
`COPY` writes a filtered subset as CSV or Parquet.

```sql
SELECT agent, turn_type, count(*) AS n
FROM read_json_auto('timeline.jsonl') GROUP BY ALL ORDER BY n DESC;

SELECT timestamp_utc, user, agent, left(text, 120)
FROM read_json_auto('timeline.jsonl')
WHERE turn_type = 'tool_use' AND text ILIKE '%rm -rf%'
ORDER BY timestamp_utc;

COPY (SELECT * FROM read_json_auto('timeline.jsonl') WHERE agent = 'codex-cli')
TO 'codex.csv' (HEADER);
```

**Python.** Read line by line for a file of any size, or load it into
pandas when it fits in memory. pandas parses `timestamp_utc` as a datetime
by default; `chunksize` reads a large file in pieces.

```python
import json

with open("timeline.jsonl", encoding="utf-8") as fh:
    for line in fh:
        rec = json.loads(line)
        if rec["turn_type"] == "tool_use" and "curl" in rec["text"]:
            print(rec["timestamp_utc"], rec["agent"], rec["text"])

import pandas as pd

df = pd.read_json("timeline.jsonl", lines=True)
for chunk in pd.read_json("timeline.jsonl", lines=True, chunksize=100_000):
    print(chunk[chunk.turn_type == "tool_use"].tool_name.value_counts())
```

**Filtering by time afterwards.** `timestamp_utc` always has one fixed
form, `2026-10-03T16:55:31.123Z`, so plain string comparison puts times in
the right order and needs no date parsing in any tool. The `--since` and
`--until` options above do this while writing the timeline; these recipes
do it on a timeline already written.

```sh
# Everything on 1 October 2026 (UTC)
jq -c 'select(.timestamp_utc >= "2026-10-01" and .timestamp_utc < "2026-10-02")' timeline.jsonl

# A window to the second
jq -c 'select(.timestamp_utc >= "2026-10-01T10:00:00.000Z" and .timestamp_utc < "2026-10-01T10:05:00.000Z")' timeline.jsonl

# Sessions that overlap a day
jq -c 'select(.last_timestamp_utc >= "2026-10-01" and .first_timestamp_utc < "2026-10-02")' sessions.jsonl
```

```sql
SELECT * FROM read_json_auto('timeline.jsonl')
WHERE timestamp_utc >= '2026-10-01' AND timestamp_utc < '2026-10-02';
```

- Write a bound either as a date alone (`"2026-10-01"`) or in the full
  form with milliseconds and `Z`. `"2026-10-01T10:00:00Z"` without `.000`
  drops the records at exactly 10:00:00, because `.` sorts before `Z`.
- End a range with "before the next day", `< "2026-10-02"`. `<=
  "2026-10-01"` keeps almost nothing from that day, since every time on it
  sorts after the bare date.
- Records without a timestamp hold `""`, which never passes a lower bound,
  so they drop out. Add `or .timestamp_utc == ""` to keep them.
- Convert a local incident window to UTC before writing the bounds.
- In Python compare the strings directly (`"2026-10-01" <=
  rec["timestamp_utc"] < "2026-10-02"`). In Windows PowerShell 5.1 `-ge`
  and `-lt` compare the strings; PowerShell 7 first needs
  `ConvertFrom-Json -DateKind String`, as below.

**PowerShell**, for an analyst on Windows. `Select-String` as the first
filter keeps the slow `ConvertFrom-Json` step to the matching lines.
PowerShell 7 turns `timestamp_utc` into a local `DateTime`; add
`-DateKind String` (PowerShell 7.5 and later) to `ConvertFrom-Json` to keep
the UTC string. Windows PowerShell 5.1 keeps it a string.

```powershell
Select-String -Path timeline.jsonl -SimpleMatch '"agent":"codex-cli"' |
  ForEach-Object { $_.Line | ConvertFrom-Json } |
  Where-Object { $_.turn_type -eq 'tool_use' -and $_.text -match 'rm -rf' } |
  Select-Object timestamp_utc, user, tool_name, text
```

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

```text
analyze-agent-artifacts detect INPUT [--json] [--files] [common options]
analyze-agent-artifacts timeline INPUT -o DIR [--include-thinking] [--agent NAME]...
                         [--since WHEN] [--until WHEN] [--keep-undated] [--match REGEX]... [-i]
                         [common options]
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
| `--include-thinking` | `timeline` | Emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | `timeline` | Run only the parsers of this agent. Repeatable. An unknown name produces no rows. |
| `--since WHEN` | `timeline` | Keep rows at or after `WHEN`, the first millisecond of the period it names. Forms under [Filtering the timeline](#filtering-the-timeline). |
| `--until WHEN` | `timeline` | Keep rows at or before `WHEN`, the last millisecond of the period it names. Same forms. |
| `--keep-undated` | `timeline` | With `--since` or `--until`, also keep rows that have no timestamp. |
| `--match REGEX` | `timeline` | Keep rows whose `text` matches this Python regular expression, with the paired tool call or result. Repeatable; a row matching any pattern is kept. |
| `-i, --ignore-case` | `timeline` | Make every `--match` case-insensitive. |
| `--agents` | `catalog` | Print each agent in the catalog with `parser` or `detect only`, instead of the catalog text. |
| `--host NAME` | `detect`, `timeline` | Host name to record. Overrides `collection.json`. |
| `--user NAME` | `detect`, `timeline` | User to record for every home whose user is empty. |
| `--work-dir DIR` | `detect`, `timeline` | Where to extract an archive. A `cac-*` directory is created inside it. Default: a `cac-analyzer-*` directory in the system temp directory. Either is removed afterwards unless `--keep-extracted` is given. |
| `--keep-extracted` | `detect`, `timeline` | Keep the extracted archive and print `extracted to: <path>` on stderr. |

`catalog` prints the bundled `catalog.txt` verbatim.

| Exit code | Meaning |
| --- | --- |
| `0` | `timeline` wrote at least one row; `detect` found agent artifacts, or `--json` was given; `inventory` wrote at least one row; `catalog`, `--version`. |
| `1` | `timeline` produced no rows, including when every row was filtered out (the three files are still written), `detect` without `--json` found no agent artifacts, or `inventory` found no `host` or `agent` line (the CSV is written with its header only). |
| `2` | The input cannot be opened, printed as `error: <path>: <reason>` (see [Unreadable inputs](#unreadable-inputs)), a file input is neither tar nor zip or cannot be extracted, a `detect` or `timeline` input is neither a regular file nor a directory, a `--since` or `--until` value is not an accepted form or `--since` is later than `--until`, a `--match` pattern is not a valid regular expression, an `inventory` input is a symlink, neither a regular file nor a directory, or cannot be read, or the command line is invalid. |

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
each parser's rows, the JSONL output, and the bundled catalog against the
collector's `--list`. When `sh` and `tar` are available it also runs the sh
collector on the fake image and analyses the resulting archive end to end.
`test_inventory.py` feeds `inventory` captured outputs of three hosts, one
with console junk lines and one with a `host` line only, and checks the
columns, the default file name, `-o`, the rollup and the empty-host row;
with `sh` available it also runs the collector's `--inventory` on the fake
image and reads that.
Tests that need `zstandard`, the collector script, `sh` and `tar`, or
permission to create symlinks are skipped, with the reason, when it is
missing. CI runs the suite on Python 3.10, 3.11, 3.12, 3.13 and 3.14 with `requirements.txt`
installed.

Lint and type checks, from the repository root, at the versions CI pins
(see "Quality gates" in AGENTS.md):

```sh
uvx ruff@0.16.10 check . && uvx ruff@0.16.10 format --check .
uvx --from pyright==1.1.414 --with zstandard --with python-dateutil pyright   # also clean without zstandard
```

## Adding a parser

1. Confirm the record format against source or a real install and write the
   field names into the module docstring, as the existing parsers do.
2. Subclass `Parser` in `agent_analyzer/parsers/<agent>.py`: set `agent` to
   the catalog name, implement `wants` on `artifact.rel` and `parse` yielding
   `Row` objects. Use `iter_jsonl` so a truncated line is reported, not fatal.
   Timestamps go through `to_utc`; text through `compact`, which strips
   leading and trailing whitespace and keeps inner line breaks.
3. Register it in `agent_analyzer/parsers/__init__.py`. A parser that must
   read a file the catalog attributes to another agent sets `reads_agents`.
4. Add fixture records to `tests/fixtures.py` and a test class to
   `tests/test_parsers.py`. Then add the row to the table above.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
