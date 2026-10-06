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
| `agent-zero` | [agent-zero.md](agent-zero.md) | JSON per chat context, rewritten whole | yes |
| `aider` | [aider.md](aider.md) | markdown and readline-style text in the repository | yes |
| `antigravity` | [antigravity.md](antigravity.md) | SQLite of protobuf blobs; schema from the `agy` binary's embedded descriptors | yes |
| `claude-code` | [claude-code.md](claude-code.md) | JSONL per session with `uuid`/`parentUuid` chains, subagent files beside it, prompt history | yes |
| `cline` | [cline.md](cline.md) | JSON arrays per task; SDK session files; SQLite indexes | yes |
| `codex-cli` | [codex-cli.md](codex-cli.md) | JSONL rollouts (`session_meta`, `response_item`, `event_msg`), optionally zstd-compressed | yes |
| `cody` | [cody.md](cody.md) | rows in the editor `state.vscdb`; JetBrains global-state JSON | yes |
| `continue` | [continue.md](continue.md) | JSON per session, session-level timestamps only | yes |
| `crush` | [crush.md](crush.md) | per-project SQLite (WAL), parts as a JSON array | yes |
| `gemini-cli` | [gemini-cli.md](gemini-cli.md) | JSONL with `$set`/`$patch`/`$rewindTo` operations | yes |
| `goose` | [goose.md](goose.md) | SQLite (WAL), `content_json` arrays | yes |
| `hermes` | [hermes.md](hermes.md) | SQLite (WAL) `state.db`, JSONL fallback transcripts | yes |
| `kilo-code` | [kilo-code.md](kilo-code.md) | OpenCode-style SQLite (`kilo.db`) | yes |
| `kiro` | [kiro.md](kiro.md) | Amazon Q CLI SQLite, one JSON blob per working directory; Kiro CLI unverified | yes, Amazon Q CLI only |
| `letta` | [letta.md](letta.md) | JSONL transcripts per agent and conversation, sessions index | yes |
| `little-coder` | [little-coder.md](little-coder.md) | pi session JSONL; prompt history as a JSON array | yes |
| `muse-code` | [muse-code.md](muse-code.md) | event-sourced JSONL per session and subagent; closed source, from the binary's strings, vendor skills and a real install | yes |
| `nanobot` | [nanobot.md](nanobot.md) | JSONL per session key under `sessions/<workspace-id>/` | yes |
| `ollama` | [ollama.md](ollama.md) | desktop-app SQLite (WAL) on macOS and Windows; REPL prompt history without times; no server-side transcripts | no |
| `open-interpreter` | [open-interpreter.md](open-interpreter.md) | Codex rollout JSONL under `~/.openinterpreter` | yes, the Codex parser |
| `openclaw` | [openclaw.md](openclaw.md) | SQLite (WAL) per agent with JSON or zstd events, legacy JSONL | yes |
| `opencode` | [opencode.md](opencode.md) | SQLite (WAL) with JSON columns | yes |
| `openhands` | [openhands.md](openhands.md) | one JSON file per event per conversation, naive local timestamps | yes |
| `pearai` | [pearai.md](pearai.md) | Continue-fork session JSON, Roo-fork task files | yes |
| `pi` | [pi.md](pi.md) | JSONL session tree, header line with `cwd` | yes |
| `qwen-code` | [qwen-code.md](qwen-code.md) | JSONL, Claude-Code-like records with `cwd` and `gitBranch` | yes |
| `roo-code` | [roo-code.md](roo-code.md) | Cline task layout with Roo extensions | yes |
| `shellgpt` | [shellgpt.md](shellgpt.md) | one JSON message array per chat id in the temp dir | yes |
| `tabby` | [tabby.md](tabby.md) | server SQLite (WAL) `ee/db.sqlite`, event JSON logs | yes |
| `twinny` | [twinny.md](twinny.md) | rows in the editor `state.vscdb` | yes |
| `vscode` | [vscode.md](vscode.md) | VS Code chat sessions (Copilot Chat): JSONL mutation log, legacy JSON | yes |
| `zed` | [zed.md](zed.md) | SQLite with zstd-compressed JSON thread blobs | yes, needs `zstandard` |

The Parser column says whether `agent_analyzer/parsers/` has a parser for
the agent; the parser table in [`docs/parsers.md`](../docs/parsers.md) lists the files each one
reads. `tools/check_research_links.py` at the repository root verifies the
citation links in these documents; see the
[collectors research index](../../collectors/research/README.md).

Findings that cut across agents:

- Only Claude Code, Codex CLI, Qwen Code, Antigravity, Hermes and Zed
  record a git branch, and Zed only at thread start. Every other store
  leaves `git_branch` empty.
- Per-message timestamps are missing in Continue sessions, Zed threads and
  Cline's legacy API history; those parsers inherit session-level times.
- OpenCode, Crush, Goose, Kilo, Antigravity and Zed's sidebar database run
  SQLite in WAL mode, so the `-wal` sidecar must be collected with the
  database. Amazon Q and Zed's `threads.db` use the rollback journal and copy
  cleanly alone.
- Credentials sit inside transcript databases for OpenCode, Kilo and Amazon
  Q; those files are collected unflagged and the keys to redact are listed in
  each document's section 7.
