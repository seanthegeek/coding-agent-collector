# Record schema research

One document per catalog agent, named after the agent as it appears in
`collect-agent-artifacts.sh --list`, describing how that agent records
transcripts on disk and how a parser should read them. Each was written from
a shallow clone of the tool's source at the commit it names, with file and
line citations, or for a closed-source tool from the evidence named in its
first section (for Antigravity, the protobuf descriptors embedded in its
binary). Each ends with a parser plan mapped to the timeline columns and
synthetic sample records meant to become test fixtures. Treat them as the
evidence behind each parser; the field names a parser actually depends on
are repeated in its module docstring under `agent_analyzer/parsers/`.

The research itself may be done in groups (forks of one codebase are best
studied together, because the differences are what matter), but the
findings are split per agent before they land here. Where two agents share
a lineage, each document says so and links to the other instead of repeating
it.

| Agent | Document | Store | Parser |
| --- | --- | --- | --- |
| `antigravity` | [antigravity.md](antigravity.md) | SQLite of protobuf blobs; schema from the `agy` binary's embedded descriptors | yes |
| `gemini-cli` | [gemini-cli.md](gemini-cli.md) | JSONL with `$set`/`$patch`/`$rewindTo` operations | planned |
| `qwen-code` | [qwen-code.md](qwen-code.md) | JSONL, Claude-Code-like records with `cwd` and `gitBranch` | planned |
| `cline` | [cline.md](cline.md) | JSON arrays per task; SDK session files; SQLite indexes | planned |
| `roo-code` | [roo-code.md](roo-code.md) | Cline task layout with Roo extensions | planned |
| `kilo-code` | [kilo-code.md](kilo-code.md) | OpenCode-style SQLite (`kilo.db`) | planned |
| `opencode` | [opencode.md](opencode.md) | SQLite (WAL) with JSON columns | planned |
| `crush` | [crush.md](crush.md) | per-project SQLite (WAL), parts as a JSON array | planned |
| `goose` | [goose.md](goose.md) | SQLite (WAL), `content_json` arrays | planned |
| `zed` | [zed.md](zed.md) | SQLite with zstd-compressed JSON thread blobs | planned, needs `zstandard` |
| `continue` | [continue.md](continue.md) | JSON per session, session-level timestamps only | planned |
| `vscode` | [vscode.md](vscode.md) | VS Code chat sessions (Copilot Chat): JSONL mutation log, legacy JSON | planned |
| `aider` | [aider.md](aider.md) | markdown and readline-style text in the repository | planned |
| `kiro` | [kiro.md](kiro.md) | Amazon Q CLI SQLite, one JSON blob per working directory; Kiro CLI unverified | planned |
| `pi` | [pi.md](pi.md) | JSONL session tree, header line with `cwd` | planned |
| `little-coder` | [little-coder.md](little-coder.md) | pi session JSONL; prompt history as a JSON array | planned |
| `open-interpreter` | [open-interpreter.md](open-interpreter.md) | Codex rollout JSONL under `~/.openinterpreter` | planned, reuses the Codex format |
| `openhands` | [openhands.md](openhands.md) | one JSON file per event per conversation, naive local timestamps | planned |
| `letta` | [letta.md](letta.md) | JSONL transcripts per agent and conversation, sessions index | planned |
| `hermes` | [hermes.md](hermes.md) | SQLite (WAL) `state.db`, JSONL fallback transcripts | planned |
| `openclaw` | [openclaw.md](openclaw.md) | SQLite (WAL) per agent with JSON or zstd events, legacy JSONL | planned |
| `nanobot` | [nanobot.md](nanobot.md) | JSONL per session key under `sessions/<workspace-id>/` | planned |
| `agent-zero` | [agent-zero.md](agent-zero.md) | JSON per chat context, rewritten whole | planned |
| `pearai` | [pearai.md](pearai.md) | Continue-fork session JSON, Roo-fork task files | planned |
| `cody` | [cody.md](cody.md) | rows in the editor `state.vscdb`; JetBrains global-state JSON | planned |
| `twinny` | [twinny.md](twinny.md) | rows in the editor `state.vscdb` | planned |
| `tabby` | [tabby.md](tabby.md) | server SQLite (WAL) `ee/db.sqlite`, event JSON logs | planned |
| `shellgpt` | [shellgpt.md](shellgpt.md) | one JSON message array per chat id in the temp dir | planned |

Claude Code and Codex CLI were validated directly against real installs and
are documented in their parser modules.

Findings that cut across agents:

- Only Claude Code, Codex CLI, Qwen Code and Zed record a git branch, and Zed
  only at thread start. Every other store leaves `git_branch` empty.
- Per-message timestamps are missing in Continue sessions, Zed threads and
  Cline's legacy API history; those parsers inherit session-level times.
- OpenCode, Crush, Goose, Kilo, Antigravity and Zed's sidebar database run
  SQLite in WAL mode, so the `-wal` sidecar must be collected with the
  database. Amazon Q and Zed's `threads.db` use the rollback journal and copy
  cleanly alone.
- Credentials sit inside transcript databases for OpenCode, Kilo and Amazon
  Q; those files are collected unflagged and the keys to redact are listed in
  each document's section 7.
