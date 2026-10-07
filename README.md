# doubleagent

Forensic analysis of AI agent use on a system, for incident responders.
It covers agents that execute tools or shell commands on a host and leave
transcripts, configuration or credentials on disk: coding agents such as
Claude Code, Gemini CLI, Antigravity, Codex CLI, Copilot CLI, Cursor,
Windsurf, Aider and VS Code chat extensions; autonomous agents such as
Hermes, Agent Zero and OpenClaw; agent framework studios and CLIs such as
AutoGen Studio, CrewAI and MetaGPT; self-hosted agent and workflow
automation platforms such as n8n, Flowise, Langflow and Dify; Ollama; and
others. It has two
parts, kept in separate directories because they run in different places and
have different dependency rules, and a Docker lab for developers.

| Part | Directory | Runs on |
| --- | --- | --- |
| Collectors | [`collectors/`](collectors/README.md) | The host under investigation, or an analyst workstation with a mounted image |
| Analyzer | [`analyzer/`](analyzer/README.md) | The analyst workstation |
| Agent lab | [`lab/`](lab/README.md) | A developer's Docker host, to produce real-install fixtures without installing agents |

## Collectors

Two single-file scripts with the same catalog, manifest schema and archive
layout: a POSIX `sh` collector for macOS, Linux and BSD, and a Windows
PowerShell 5.1 collector. Each depends on nothing beyond its base system, so
it can be uploaded and run once through an EDR remote shell (CrowdStrike RTR,
SentinelOne RemoteOps, Defender Live Response, Palo Alto Networks Cortex XDR
Live Terminal), run locally by a responder, or
pointed at a mounted disk image of any of the three platforms. They also
collect Docker and Podman named volumes that belong to known agents. Output
is one `tar.gz` (a `.zip` from the Windows collector where `tar.exe` is
missing) holding the collected files, a hashed JSONL manifest and a run
summary. Host state such as processes and network connections is left to the
EDR. With `--inventory` they write nothing and print one JSON line per user
and agent found to stdout instead, for a fleet-wide audit through the EDR
console.

Usage and options are in [collectors/README.md](collectors/README.md); the
list of covered tools, the manifest schema, Windows specifics and the test
matrix are in the pages under [collectors/docs/](collectors/docs/).

## Analyzer

`doubleagent`, a Python command-line tool that reads a collector archive, an
extracted collection, or any loose directory such as a copied home or a
mounted image, detects which agents
left state in it using the collectors' own catalog, and parses the transcripts
it understands into a normalised JSONL timeline of turns, tool calls and tool
results, plus a per-session summary. Parsers exist for Claude Code, Codex
CLI, Gemini CLI, Antigravity, Qwen Code, Amazon Q CLI (the `kiro` entry), VS
Code chat (including Copilot Chat), Cline, Roo Code, Kilo Code, Continue,
Aider, OpenCode, Crush, Goose, Zed, Tabby, OpenHands, ShellGPT, pi,
little-coder, Letta, Hermes, Agent Zero, Open Interpreter, OpenClaw, nanobot,
Sourcegraph Cody, Twinny, PearAI, Muse Code and Ollama. Every other agent in
the catalog (Claude Desktop, ChatGPT Desktop, Copilot CLI and the Copilot
editor token store, Cursor, Windsurf, Amp, Factory Droid, Augment,
Local Deep Research, and the agent frameworks and platforms) is detected
and reported but not yet parsed. Parsing never happens
on the host, so the analyzer is free to carry its own requirements. It needs
Python 3.10 or later; `pip install ./analyzer` installs the `doubleagent`
command and the packages in `analyzer/requirements.txt`:
`python-dateutil` and `zstandard`, the second for Zed threads,
zstd-compressed Codex and Open Interpreter rollouts, and OpenClaw's
compressed transcript rows.

Usage and options are in [analyzer/README.md](analyzer/README.md); accepted
inputs, the JSONL schema, recipes for searching large timelines and the
parser table are in the pages under [analyzer/docs/](analyzer/docs/).

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](LICENSE).
