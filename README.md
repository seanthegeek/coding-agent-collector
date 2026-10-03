# coding-agent-collector

Tooling for incident responders investigating hosts where AI coding agents and
assistants have been used: Claude Code, Gemini CLI, Antigravity, Codex CLI,
Copilot CLI, Cursor, Windsurf, Aider, Ollama, VS Code chat extensions and
others. It has two parts, kept in separate directories because they run in
different places and have different dependency rules.

| Part | Directory | Runs on | Status |
| --- | --- | --- | --- |
| Collectors | [`collectors/`](collectors/README.md) | The host under investigation, or an analyst workstation with a mounted image | v1, done |
| Analyzer | `analyzer/` | The analyst workstation | v2, planned |

## Collectors

Two single-file scripts with the same catalog, manifest schema and archive
layout: a POSIX `sh` collector for macOS, Linux and BSD, and a Windows
PowerShell 5.1 collector. Each depends on nothing beyond its base system, so
it can be uploaded and run once through an EDR remote shell (CrowdStrike RTR,
SentinelOne RemoteOps, Defender Live Response, Palo Alto Networks Cortex XDR
Live Terminal), run locally by a responder, or
pointed at a mounted disk image of any of the three platforms. Output is one
`tar.gz` holding the collected files, a hashed JSONL manifest, a run summary
and a live system snapshot.

Usage, options, the list of covered tools, the manifest schema and the test
matrix are in [collectors/README.md](collectors/README.md).

## Analyzer

The planned v2 component: an analyst-side Python tool that reads a collector
archive and parses the transcripts in it (Claude Code JSONL, Codex rollouts,
Gemini and Antigravity SQLite, Cursor `state.vscdb`, and the rest) into a
normalised CSV timeline of turns, tool calls and file edits. Parsing never
happens on the host, so the analyzer is free to carry its own requirements.

## Repository layout

```
collectors/   the sh and PowerShell collectors, their README and smoke tests
AGENTS.md     standards and process for anyone, human or agent, changing the code
CLAUDE.md     Claude Code entry point; imports AGENTS.md
LICENSE       Apache 2.0
```

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](LICENSE).
