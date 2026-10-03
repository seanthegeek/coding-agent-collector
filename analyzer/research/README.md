# Record schema research

Reports from the October 2026 research round on transcript record schemas,
produced by the fan-out process described in AGENTS.md. Each report was
written from a shallow clone of the tool's source at the commit it names, with
file and line citations, and ends with a parser plan and synthetic sample
records intended to become test fixtures. Treat them as the evidence behind
each parser; the field names a parser actually depends on are repeated in its
module docstring under `agent_analyzer/parsers/`.

| Report | Tools | Store type |
| --- | --- | --- |
| [gemini-qwen.md](gemini-qwen.md) | Gemini CLI, Qwen Code | JSONL, with Gemini `$set`/`$patch`/`$rewindTo` operations |
| [cline-roo-kilo.md](cline-roo-kilo.md) | Cline, Roo Code, Kilo Code | JSON arrays, Cline SDK session files, Kilo SQLite |
| [opencode-crush.md](opencode-crush.md) | OpenCode, Crush | SQLite (WAL) with JSON columns |
| [goose-zed.md](goose-zed.md) | Goose, Zed | SQLite; Zed threads are zstd-compressed JSON blobs |
| [continue-vscode-aider.md](continue-vscode-aider.md) | Continue, VS Code chat (Copilot Chat), Aider | JSON, JSONL mutation log, markdown |
| [kiro-amazonq.md](kiro-amazonq.md) | Amazon Q CLI, Kiro CLI | SQLite, one JSON blob per working directory |

Findings that cut across tools:

- Only Claude Code, Codex CLI, Qwen Code and Zed record a git branch, and Zed
  only at thread start. Every other store leaves `git_branch` empty.
- Per-message timestamps are missing in Continue sessions, Zed threads and
  Cline's legacy API history; those parsers inherit session-level times.
- OpenCode, Crush, Goose, Kilo and Zed's sidebar database run SQLite in WAL
  mode, so the `-wal` sidecar must be collected with the database. Amazon Q
  and Zed's `threads.db` use the rollback journal and copy cleanly alone.
- Credentials sit inside transcript databases for OpenCode, Kilo and Amazon
  Q; those files are collected unflagged and the keys to redact are listed in
  each report's section 7.
