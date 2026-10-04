# coding-agent-collector

Tooling for incident responders investigating hosts where AI coding agents and
assistants have been used: Claude Code, Gemini CLI, Antigravity, Codex CLI,
Copilot CLI, Cursor, Windsurf, Aider, Ollama, VS Code chat extensions and
others. It has two parts, kept in separate directories because they run in
different places and have different dependency rules.

| Part | Directory | Runs on |
| --- | --- | --- | --- |
| Collectors | [`collectors/`](collectors/README.md) | The host under investigation, or an analyst workstation with a mounted image |
| Analyzer | [`analyzer/`](analyzer/README.md) | The analyst workstation | v2, in progress |
| Agent lab | [`lab/`](lab/README.md) | A developer's Docker host, to produce real-install fixtures without installing agents |

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

A Python tool that reads a collector archive, an extracted collection, or any
loose directory such as a copied home or a mounted image, detects which agents
left state in it using the collectors' own catalog, and parses the transcripts
it understands into a normalised CSV timeline of turns, tool calls and tool
results, plus a per-session summary. Parsers exist for Claude Code and Codex
CLI; every other agent in the catalog is detected and reported but not yet
parsed. Parsing never happens on the host, so the analyzer is free to carry
its own requirements. It currently needs only Python 3.9 and the standard
library.

Usage, accepted inputs, the CSV schema and the parser table are in
[analyzer/README.md](analyzer/README.md).

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](LICENSE).
