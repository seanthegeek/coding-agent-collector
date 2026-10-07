# Parsers

Which files each parser reads and what it was validated against, how files
are routed to parsers, and the agents that are detected but not parsed.
Back to the [analyzer README](../README.md).

## Parser table

| Agent | Files | Validated against |
| --- | --- | --- |
| `agent-zero` | `usr/chats/<ctxid>/chat.json` (UI log for timestamps, each agent's history for full text and model, `messages/<n>.txt` for long tool results; history-only turns without timestamps when the log was trimmed at 1000 items) under `agent-zero`, `agent-zero/<instance>` or `Desktop/agent-zero`, also the legacy `chats/<ctxid>.json` and `tmp/chats`; project path is the container path `/a0/usr/projects/<name>` | Source at e3051fb, synthetic fixture; see [`research/agent-zero.md`](../research/agent-zero.md) |
| `aider` | `.aider.chat.history.md`, `.aider.input.history`, `.aider.llm.history`, in a home or (as agent `project` in the manifest) a repository; times are host local time, emitted as if UTC | Source at 5dc9490, synthetic fixture; see [`research/aider.md`](../research/aider.md) |
| `antigravity` | `.gemini/antigravity-cli/conversations/*.db` (SQLite of protobuf steps, with WAL sidecars), `conversation_summaries.db`, `history.jsonl` | Protobuf descriptors extracted from the shipped `agy` binary plus a real install, October 2026; see [`research/antigravity.md`](../research/antigravity.md) |
| `claude-code` | `.claude/projects/<slug>/<session>.jsonl`, subagent transcripts under the session directory (each opens with a `subagent <id> of <session>` row), `tool-results/*.txt` in the session directory when a result's `<persisted-output>` stub names it, `.claude/history.jsonl`; the same files under a `.claude-<name>` config home moved with `CLAUDE_CONFIG_DIR` (such as `.claude-work/projects/...`) | Real install, Claude Code 2.1.286 to 2.1.289, and the shipped 2.1.289 package strings, October 2026; see [`research/claude-code.md`](../research/claude-code.md) |
| `cline` | `<editor>/User/globalStorage/saoudrizwan.claude-dev/` and `.cline/data/`: `tasks/<id>/ui_messages.json` (preferred), `api_conversation_history.json` (only when `ui_messages.json` is absent; inherits the task start time), `task_metadata.json`, `state/taskHistory.json`; SDK `.cline/data/sessions/<id>/<id>.json` and `*.messages.json`, `.cline/data/db/sessions.db` | Source at 39ff2359, synthetic fixture; see [`research/cline.md`](../research/cline.md) |
| `codex-cli` | `.codex/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst` (needs `zstandard`), `.codex/history.jsonl` | Real install, Codex CLI, October 2026; archived and `.zst` rollouts, subagent and fork records from source at 3e23877, synthetic fixture. User-role context (environment, AGENTS.md, skills) is `system` by its content kind; a subagent row links each spawned thread to its parent; turn items that no response item carries become rows; see [`research/codex-cli.md`](../research/codex-cli.md) |
| `cody` | The `sourcegraph.cody-ai` row of a VS Code or fork `User/globalStorage/state.vscdb` (its `cody-local-chatHistory-v2` member) and the JetBrains file `Cody-nodejs/[Data/]JetBrains-globalState/cody-local-chatHistory-v2`. Every row of a chat carries the chat's creation time (its id); no project path is recorded | Source at 8e20ac6c, synthetic fixture; see [`research/cody.md`](../research/cody.md) |
| `continue` | `.continue/sessions/<sessionId>.json` (timestamped from `sessions/sessions.json` `dateCreated`; messages have no time of their own), `.continue/dev_data/<schema>/chatInteraction.jsonl` and `toolUsage.jsonl` | Source at 5522c6f, synthetic fixture; see [`research/continue.md`](../research/continue.md) |
| `crush` | `<project>/.crush/crush.db` (SQLite with WAL sidecars; reached as a project artifact, or under a home when Crush ran in `~`), `.local/share/crush/projects.json`, `AppData/Local/crush/projects.json` | Source at ca6ae26, synthetic fixture; see [`research/crush.md`](../research/crush.md) |
| `gemini-cli` | `.gemini/tmp/<slug>/chats/**/*.jsonl` (with `$set`, `$patch` and `$rewindTo` replayed), legacy `chats/**/*.json`, `tmp/<slug>/logs.json`, also under `.cache/.gemini`; project path from `.project_root` or `projects.json` | Source at fb972b2, synthetic fixture; see [`research/gemini-cli.md`](../research/gemini-cli.md) |
| `goose` | `.local/share/goose/sessions/sessions.db` (SQLite with WAL sidecars), legacy `sessions/*.jsonl`, `.local/state/goose/logs/llm_request.*.jsonl`, `history.txt`, and the `AppData/Roaming/Block/goose/data` equivalents | Source at 591edd4, synthetic fixture; see [`research/goose.md`](../research/goose.md) |
| `hermes` | `state.db` (SQLite with WAL sidecars; `sessions` and `messages`, rewound or compacted `active = 0` rows kept with a `[rewound]` prefix) and the fallback `sessions/<id>.jsonl` under `.hermes`, `.hermes_<suffix>`, `AppData/Local/hermes` and their `profiles/<name>/` homes | Source at 8b66a51, synthetic fixture; see [`research/hermes.md`](../research/hermes.md) |
| `kilo-code` | `.local/share/kilo/kilo*.db` and `opencode-*.db` plus the same JSON trees under `.local/share/kilo` (OpenCode parser, Kilo paths), and pre-migration VS Code tasks `<globalStorage>/kilocode.kilo-code/tasks/<id>/api_conversation_history.json` | Source at 76bcfd4, synthetic fixture; see [`research/kilo-code.md`](../research/kilo-code.md) |
| `kiro` | Amazon Q CLI `data.sqlite3` (`conversations` and legacy `history` tables) under `amazon-q/` or `kiro-cli/` in `.local/share`, `Library/Application Support` or `AppData/Local`; `/save` exports (`.json` with `conversation_id` and `history`). Kiro CLI `.kiro/sessions/` files are not parsed until their format is confirmed | Source at 15cc8f3, synthetic fixture; see [`research/kiro.md`](../research/kiro.md) |
| `letta` | Letta Code `.letta/lc-local-backend/conversations/<key>/messages.jsonl` (pi session format), `.letta/transcripts/<agent>/<conversation>/transcript.jsonl` (project path from `sessions.jsonl` by time, a heuristic; skipped when the conversation's `messages.jsonl` is present), `.letta/sessions.jsonl` | Source at 77faf36, synthetic fixture; see [`research/letta.md`](../research/letta.md) |
| `little-coder` | `.pi/agent/little-coder-prompt-history.json` (prompts without timestamps or sessions) and `.little-coder/checkpoints/<session file>/` (one `system` row per session's pre-edit copies); its transcripts are pi sessions, parsed as `pi` | Source at 89d4fa0, synthetic fixture; see [`research/little-coder.md`](../research/little-coder.md) |
| `muse-code` | `.local/share/muse/sessions/YYYY/MM/DD/<id>/session.jsonl` and each subagent's `subagent/<id>/session.jsonl` (event envelopes with microsecond `recorded_at`; tool calls and results joined on `call_id`; approval requests and decisions as `system` rows; a subagent takes its project path and branch from the parent log), `.local/share/muse/tui-history.jsonl` (prompts without timestamps). The approval reviewer's `approval-review/*.jsonl` (synthetic clock), `tool-outputs/` and the SQLite indexes are not read | Shipped binary 1.4.2 strings, vendor skills and a real install (Linux), October 2026, synthetic fixture; see [`research/muse-code.md`](../research/muse-code.md) |
| `nanobot` | `.nanobot*/sessions/<workspace-id>/<key>.jsonl` (project path from the sibling `.workspace`), legacy `sessions/*.jsonl` and `.migration-conflicts/`, and `memory/history.jsonl`; times are host local time, emitted as if UTC | Source at acdae3d, synthetic fixture; see [`research/nanobot.md`](../research/nanobot.md) |
| `ollama` | The desktop app's `Library/Application Support/Ollama/db.sqlite` (macOS) and `AppData/Local/Ollama/db.sqlite` (Windows), SQLite with WAL sidecars, schema versions 16 to 19: `messages` with their `tool_calls` (no call id: the n-th `tool` message after an assistant message pairs with its n-th call, `tool_use_id` is `<chat id>:<tool_calls.id>`) and attachment names and sizes, never their bytes; the `users` and `settings` tables are not read. `.ollama/history` (the `ollama run` prompt history: no timestamp or session, so its rows sort last and drop out of `--since`/`--until`; the last 100 entries only; a pasted multi-line prompt becomes several rows; slash commands are `system` rows). No project path is recorded. Model manifests, `config.json`, `backup/`, `launch/` and `logs/` are not read | Source at v0.35.1 (b0c1ca4), synthetic fixture; no real `db.sqlite`, since the desktop app does not exist on Linux; see [`research/ollama.md`](../research/ollama.md) |
| `open-interpreter` | Codex rollouts (Codex parser, Open Interpreter paths): `.openinterpreter/sessions/**/rollout-*.jsonl` and `archived_sessions/`, also as `.jsonl.zst`, `.openinterpreter/history.jsonl`, and `external_agent_session_imports.json` (one `system` row per `/import`ed thread, naming the Claude Code or Cursor source file; that thread's record times are import time) | Source at 2767e5f, synthetic fixture; see [`research/open-interpreter.md`](../research/open-interpreter.md) |
| `openclaw` | `agents/<id>/agent/openclaw-agent.sqlite` (SQLite with WAL sidecars: `transcript_events`, zstd `event_zstd` rows need `zstandard`; unpublished reset/deleted archives and SQLite cold archives), legacy `agents/<id>/sessions/<id>.jsonl` and `sessions/*.jsonl`, reset and deleted archives `*.jsonl.reset.*` / `*.jsonl.deleted.*` (optionally `.zst`) and `sessions/cold/*.jsonl.zst`, under `.openclaw`, `.openclaw-<profile>`, `.clawdbot` or `.moltbot`. The session key (channel and sender) is in each session's start row; `auth_profile_store` is never read | Source at 3b16db7, synthetic fixture; see [`research/openclaw.md`](../research/openclaw.md) |
| `opencode` | `.local/share/opencode/opencode*.db` (SQLite with JSON columns, WAL sidecars; V1 `message`/`part`, V2 `session_message` for sessions without V1 rows), legacy JSON `storage/session/*/*.json` and `storage/message/*/*.json` with their `part/` files, and the older `project/<slug>/storage/session/` tree | Source at 907b3bc, synthetic fixture; see [`research/opencode.md`](../research/opencode.md) |
| `openhands` | `.openhands/agent-canvas/dev_conversations/<hex>/`, `.openhands/agent-canvas/conversations/<hex>/` and `.openhands/conversations/<hex>/`: one `events/event-<idx>-<id>.json` per event, with the sibling `meta.json` (title, `created_at`, working dir) and `base_state.json` (model). Event times are naive local time, corrected by the offset `meta.json` `created_at` implies, else emitted as if UTC. Legacy 0.x `sessions/<sid>/events/<n>.json` is reported as one `system` row per session, not parsed | Source at b347047 (SDK), synthetic fixture; see [`research/openhands.md`](../research/openhands.md) |
| `pearai` | `.pearai/sessions/<sessionId>.json` (Continue fork, `history` and `perplexityHistory`, timestamped from `sessions.json` `dateCreated`) and `<editor>/User/globalStorage/pearai.pearai-roo-cline/tasks/<id>/` (Roo Code 3.15 fork through the Cline task mapping; XML tool calls in `api_conversation_history.json`; project from `taskHistory` in the sibling `state.vscdb`) | Source at 51eceef6 and 0b6df736, synthetic fixture; see [`research/pearai.md`](../research/pearai.md) |
| `pi` | `.pi/agent/sessions/<cwd>/<time>_<id>.jsonl` and legacy `.pi/agent/*.jsonl` (session tree; fork entries copied from a collected parent file are dropped; a session that looks driven by little-coder gets a `system` row saying so), `.pi/agent/experimental/sessions/<id>/meta.json` (the durable `session.sqlite` beside it is not parsed) | Source at 2003871, synthetic fixture; see [`research/pi.md`](../research/pi.md) |
| `qwen-code` | `.qwen/projects/<slug>/chats/<session>.jsonl` and `chats/archive/`, `.qwen/tmp/<hash>/logs.json` | Source at 2c591ec, synthetic fixture; see [`research/qwen-code.md`](../research/qwen-code.md) |
| `roo-code` | `<editor>/User/globalStorage/rooveterinaryinc.roo-cline/` and `.vscode-mock/global-storage/`: the Cline task files plus `tasks/<id>/history_item.json` and `tasks/_index.json` | Source at b867ec91, synthetic fixture; see [`research/roo-code.md`](../research/roo-code.md) |
| `shellgpt` | Files directly under a `chat_cache/` directory: `AppData/Local/Temp/chat_cache/<id>` and `AppData/Local/Temp/shell_gpt/chat_cache/<id>`, or a copied Linux or macOS temp directory given as loose input. One JSON array of OpenAI messages per chat, `tool_calls` and the pre-1.5.0 `function_call` shape; no timestamp, model or working directory is recorded, so those columns stay empty | Source at a082bd5, synthetic fixture; see [`research/shellgpt.md`](../research/shellgpt.md) |
| `tabby` | Server-side: `.tabby/ee/db.sqlite` or `dev-db.sqlite` (SQLite with WAL sidecars; `threads`, `thread_messages`, `user_events`, thread owner from `users.email`; secret columns never read), the pre-migration backups `ee/db.backup-YYYYMMDD.sqlite` (may hold threads since deleted), and the completion event log `.tabby/events/YYYY-MM-DD.json` (full prompt and generated text). Project is the attached repository URL; no local path is recorded | Source at 21b2904, synthetic fixture; see [`research/tabby.md`](../research/tabby.md) |
| `twinny` | The `rjmacarthy.twinny` row of a VS Code or fork `User/globalStorage/state.vscdb` (`twinny.conversations`). Messages have no time of their own: every row carries the conversation's `updatedAt`. Provider `apiKey`s in the same value are never emitted | Source at 9339bd10, synthetic fixture; see [`research/twinny.md`](../research/twinny.md) |
| `vscode` | `User/workspaceStorage/<hash>/chatSessions/*.jsonl` and `.json` (with the sibling `workspace.json` for the project), `User/globalStorage/emptyWindowChatSessions/*`, `User/globalStorage/transferredChatSessions/*.json`, for Code, Code - Insiders, VSCodium, Positron, Trae and the `.vscode-server*/data` remote layout. Covers Copilot Chat; its model and participant ids are opaque strings | Source at d7622a5, synthetic fixture; see [`research/vscode.md`](../research/vscode.md) |
| `zed` | `threads/threads.db` (zstd-compressed JSON threads; needs `zstandard`) and `db/0-<channel>/db.sqlite` `sidebar_threads` (external-agent threads as `system` rows) under `.local/share/zed`, `Library/Application Support/Zed`, `AppData/Local/Zed` or the Flatpak data dir. No per-message timestamps: messages carry the thread's `updated_at` | Source at a846890, synthetic fixture; see [`research/zed.md`](../research/zed.md) |

## Row content

The field names each parser relies on are listed in its module docstring
under `doubleagent/parsers/`. Thinking and reasoning blocks are left out
unless `--include-thinking` is passed. The `text` field carries the full
text of each event, line breaks included, so the timeline is a complete
transcript, one event per line. History files are parsed even when the
matching session transcript exists, because they survive session deletion;
filter on `source_file` to drop them.

## Routing files to parsers

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

## Detected but not parsed

Agents detected but not yet parsed: `claude-desktop`, `chatgpt-desktop`,
`copilot-cli`, `copilot`, `cursor`, `windsurf`, `amp`, `factory-droid`,
`augment`, `local-deep-research`, `autogen-studio`, `camel-ai`, `crewai`,
`dify`, `flowise`, `langflow`, `metagpt`, `n8n` and `pydantic-clai`.

The `open-interpreter` parser reads only the current Codex-fork layout
under `.openinterpreter`. The legacy Python tool's
`conversations/*.json` files, which the catalog attributes to
`open-interpreter` too, are detected but not parsed.

The Cursor and Windsurf storage formats are not documented, so a parser
needs format research first: Windsurf's Cascade history is protobuf
(`.pb`) with no published schema, and Cursor's chats are `state.vscdb`
rows whose key layout changes between versions, beside a CLI `store.db`
whose blobs may be encrypted. See
[`cursor.md`](../../collectors/research/cursor.md) and
[`windsurf.md`](../../collectors/research/windsurf.md) in the collector
research.

Files that are not transcripts, such as skills and configuration files,
are detected but not parsed.

## Protobuf and SQLite

Protobuf stores are decoded by `doubleagent/protobuf.py`, a small
schema-driven wire decoder, from field tables written into each parser. For
a closed-source agent the field names come from the descriptors embedded in
its binary. `tools/proto_descriptors.py extract BINARY OUT.json` extracts
them, and `show OUT.json MESSAGE...` and `find OUT.json TEXT` query them. SQLite
stores are copied together with their `-wal` and `-shm` sidecars into a
scratch directory before being opened, so the evidence copy is never touched
and rows still in the write-ahead log are not lost.
