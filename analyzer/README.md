# Analyzer

The analyst-side half of coding-agent-collector. It takes a collector archive,
an extracted collection, or any loose directory tree, detects which AI coding
agents left state in it, and parses the transcripts it knows how to read into
one normalised CSV timeline. It never runs on the host under investigation, so
unlike the collectors it may carry dependencies. It needs Python 3.9 or
later and the packages in `requirements.txt` (`pip install -r
requirements.txt`): today only `zstandard`, for Zed threads. Without it the
Zed parser reports each thread as one undecodable `system` row and
everything else still runs.

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

# A single agent directory copied on its own
python3 -m agent_analyzer detect /cases/host03/alice-dot-claude --user alice
```

`pip install .` in this directory installs the same thing as the
`analyze-agent-artifacts` command.

## Inputs

| Input | How it is read |
| --- | --- |
| `*_agent-artifacts.tar.gz` or `.zip` from either collector | Extracted to a temporary directory (or `--work-dir`), then read as an extracted collection. A `.sha256` sidecar next to the archive is verified and the result reported. Symlinks inside the archive are not materialised; their targets are in the manifest. |
| Extracted collection: a directory holding `manifest.jsonl`, `collection.json` and `fs/` | Host name from `collection.json`; user, home and agent for every file from the manifest. Only rows with status `collected` are parsed. |
| Anything else | Treated as a loose tree: a copied home directory, a mounted disk image, another collector's output, or one agent directory such as `.claude`. Homes and agents are discovered from the catalog, and the user is inferred from the path. |

In loose mode the analyzer walks the tree and treats a directory as a home
when at least one catalog entry for a real agent matches under it. A
directory that holds only shared files such as `AGENTS.md` or `.env` is a
project, not a home. A home is never nested inside another, so project-level
`.claude` directories inside a home are not mistaken for a second user. The
user is taken from `home/<user>`, `Users/<user>`, `usr/home/<user>`,
`export/home/<user>`, `root` or `var/root` in the path, falling back to the
directory name, and left empty when the input root itself is the home. Pass
`--user` and `--host` to fill in what the path cannot say. Loose-mode output
is marked `inferred` in `detect --json` because none of this comes from a
manifest.

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
| `codex-cli` | `.codex/sessions/**/rollout-*.jsonl`, `.codex/history.jsonl` | Real install, Codex CLI, October 2026 |
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

Agents detected but not yet parsed: `claude-desktop`, `chatgpt-desktop`,
`copilot-cli`, `copilot`, `cursor`, `windsurf`, `amp`, `factory-droid`,
`augment`, `ollama`, `pearai`, `cody`, `twinny`,
`open-interpreter`, `openhands`, `pi`, `little-coder`, `letta`, `hermes`,
`openclaw`, `nanobot`, `agent-zero`, `shellgpt` and `local-deep-research`,
plus the `shared` and `shell-history` entries, which are not agents.
Windsurf and Cursor need format work first.

Protobuf stores are decoded by `agent_analyzer/protobuf.py`, a small
schema-driven wire decoder, from field tables written into each parser. For
a closed-source agent the field names come from the descriptors embedded in
its binary; `tools/proto_descriptors.py` extracts and queries them. SQLite
stores are copied together with their `-wal` and `-shm` sidecars into a
scratch directory before being opened, so the evidence copy is never touched
and rows still in the write-ahead log are not lost.

## Output

`timeline` writes three files into `-o`:

```
timeline.csv    one row per turn, tool call, tool result or system event
sessions.csv    one row per session with first and last timestamp and counts
detect.json     what detect would have printed, for the record
```

`timeline.csv` columns, in order:

| Column | Meaning |
| --- | --- |
| `timestamp_utc` | ISO 8601 UTC with milliseconds, `2026-10-03T16:55:31.123Z`. Empty when the record has none. |
| `host` | From `collection.json`, or `--host`. |
| `user` | From the manifest, inferred from the path, or `--user`. |
| `agent` | Catalog agent name. |
| `session_id` | The agent's own session or thread identifier. |
| `project_path` | Working directory recorded for the turn. |
| `git_branch` | Branch recorded for the turn, where the agent logs one. |
| `turn_type` | `user`, `assistant`, `tool_use`, `tool_result`, `system`, or `thinking` with `--include-thinking`. |
| `model` | Model that produced the turn, where recorded. |
| `tool_name` | For `tool_use` rows: the tool. Codex shell calls are `shell`. |
| `tool_use_id` | Links a `tool_use` row to its `tool_result`. |
| `text` | The event's text with whitespace runs collapsed: the prompt, the response, the tool output, or for a tool call its most identifying argument (the Bash command, the edited file, the search pattern, the fetched URL), else the arguments as JSON. Full length by default; `--max-text-length` cuts it. |
| `source_file` | Path of the record on the source host, as in the manifest. In loose mode it is relative to the input root. |
| `source_line` | Line number in that file, so the full record can be read. |

Rows are sorted by timestamp, then by source file and line. Rows without a
timestamp sort last. Injected context (`isMeta` user records in Claude Code,
`developer` messages in Codex) is typed `system`, not `user`, so the `user`
rows are what the person typed.

`sessions.csv` columns: `host`, `user`, `agent`, `session_id`,
`project_path`, `first_timestamp_utc`, `last_timestamp_utc`, `models`
(space separated), `user_turns`, `assistant_turns`, `tool_calls`,
`source_file` (the file that contributed most rows).

The two CSV layouts are a compatibility contract with the analysts and
tooling that consume them. A future version may append new columns after the
existing ones, but existing columns keep their names, order and meaning.

## Options

| Option | Meaning |
| --- | --- |
| `detect INPUT` | Print homes, users, agents, file counts and whether a parser exists. `--json` for machine-readable output, `--files` to list every attributed file. |
| `timeline INPUT -o DIR` | Write `timeline.csv`, `sessions.csv` and `detect.json`. |
| `catalog` | Print the bundled catalog; `--agents` prints agent names and parser availability. |
| `--host NAME` | Host to record when the input has no `collection.json`. |
| `--user NAME` | User to record for a home whose owner cannot be inferred. |
| `--work-dir DIR` | Where to extract an archive. Default is a temporary directory. |
| `--keep-extracted` | Keep the extracted archive and print its path. |
| `--max-text-length N` | Cut the `text` column to N characters, marking the cut with an ellipsis. Default `0`, the full text. |
| `--include-thinking` | Emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | Parse only this agent. Repeatable. |

Exit code is `0` when rows were written, `1` when nothing was found or
parsed, `2` for a bad input path.

## Testing

```sh
cd analyzer
tests/run.sh                 # python3 -m unittest discover -s tests
```

The suite builds a fake image with two Linux users and a Windows profile
tree, each holding synthetic state for every parsed agent in the exact shapes
the parsers were validated against, and checks detection in every input mode,
each parser's rows, the CSV output, and the bundled catalog against the
collector's `--list`. When `sh` and `tar` are available it also runs the sh
collector on the fake image and analyses the resulting archive end to end.

## Adding a parser

1. Confirm the record format against source or a real install and write the
   field names into the module docstring, as the two existing parsers do.
2. Subclass `Parser` in `agent_analyzer/parsers/<agent>.py`: set `agent` to
   the catalog name, implement `wants` on `artifact.rel` and `parse` yielding
   `Row` objects. Use `iter_jsonl` so a truncated line is reported, not fatal.
   Timestamps go through `to_utc`; text through `compact`, which collapses
   whitespace and applies `--max-text-length`.
3. Register it in `agent_analyzer/parsers/__init__.py`.
4. Add fixture records to `tests/fixtures.py` and a test class to
   `tests/test_parsers.py`. Then add the row to the table above.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
