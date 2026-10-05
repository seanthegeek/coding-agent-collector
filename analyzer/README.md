# Analyzer

The analyst-side half of coding-agent-collector. It takes a collector archive,
an extracted collection, or any loose directory tree, detects which AI coding
agents left state in it, and parses the transcripts it knows how to read into
one normalised JSONL timeline. It never runs on the host under investigation,
so unlike the collectors it may carry dependencies.

It needs Python 3.10 or later and the packages in `requirements.txt`
(`pip install -r requirements.txt`): `python-dateutil`, required, which reads
the `--since` and `--until` times, and `zstandard`, optional, for Zed threads,
Codex and Open Interpreter `.jsonl.zst` rollouts and OpenClaw's compressed
transcript rows. Without `zstandard` each such thread, rollout or row is
reported as an undecodable `system` row and everything else still runs.

`pip install .` in this directory installs the package
`coding-agent-analyzer`, which provides the same tool as the
`analyze-agent-artifacts` command. `--version` prints
`analyze-agent-artifacts <version>`. [CHANGELOG.md](CHANGELOG.md) lists what
changed in each version, including changes to the `timeline.jsonl` and
`sessions.jsonl` fields.

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

## Commands

| Command | What it does | Writes | Page |
| --- | --- | --- | --- |
| `detect` | Reports the host, users, homes and agents found in an input, with file counts, bytes and whether a parser exists. | stdout only; `--json` for one object | [docs/output.md](docs/output.md#detect) |
| `timeline` | Parses every transcript it can read into one timeline, optionally filtered by time or text. | `timeline.jsonl`, `sessions.jsonl` and `detect.json` in `-o` | [docs/output.md](docs/output.md#timeline), [docs/filtering.md](docs/filtering.md) |
| `inventory` | Merges saved collector `--inventory` output from many hosts into one CSV. | `fleet-inventory.csv`, or the `-o` path | [docs/inventory.md](docs/inventory.md) |
| `catalog` | Prints the bundled catalog, or with `--agents` each agent with `parser` or `detect only`. | stdout only | [docs/inputs.md](docs/inputs.md#detection) |

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

| Option | Meaning |
| --- | --- |
| `--json` | `detect`: print one machine-readable object. |
| `--files` | `detect`: also list every attributed file. |
| `-o, --output` | `timeline`: output directory, required. `inventory`: CSV path. |
| `--include-thinking` | `timeline`: emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | `timeline`: run only this agent's parsers. Repeatable. |
| `--since WHEN`, `--until WHEN` | `timeline`: keep rows inside this window. |
| `--keep-undated` | `timeline`: with a window, also keep rows without a timestamp. |
| `--match REGEX` | `timeline`: keep rows whose `text` matches, with the paired call or result. Repeatable. |
| `-i, --ignore-case` | `timeline`: make every `--match` case-insensitive. |
| `--agents` | `catalog`: list agents and whether each has a parser. |
| `--host NAME` | Host name to record; overrides `collection.json`. |
| `--user NAME` | User to record for every home whose user is empty. |
| `--work-dir DIR` | Where to extract an archive. |
| `--keep-extracted` | Keep the extracted archive. |

[docs/options.md](docs/options.md) has the full meaning of each option,
which subcommands take it, and the full exit-code table.

| Exit code | Meaning |
| --- | --- |
| `0` | Rows or agents were found, or the command always succeeds (`detect --json`, `catalog`, `--version`). |
| `1` | Nothing was found: no timeline rows, no agent artifacts, or no inventory lines. |
| `2` | The input cannot be opened or extracted, an option value is invalid, or the command line is invalid. |

## Parsers

Parsers exist for Claude Code, Codex CLI, Gemini CLI, Antigravity, Qwen
Code, Amazon Q CLI (the `kiro` entry), VS Code chat (including Copilot
Chat), Cline, Roo Code, Kilo Code, Continue, Aider, OpenCode, Crush, Goose,
Zed, Tabby, OpenHands, ShellGPT, pi, little-coder, Letta, Hermes, Agent
Zero, Open Interpreter, OpenClaw, nanobot, Sourcegraph Cody, Twinny, PearAI
and Muse Code; [docs/parsers.md](docs/parsers.md) lists the files each one
reads and the evidence it was validated against. Every other agent in the
catalog (Claude Desktop, ChatGPT Desktop, Copilot CLI and the Copilot editor
token store, Cursor, Windsurf, Amp, Factory Droid, Augment, Ollama, Local
Deep Research) is detected and reported but not yet parsed. Thinking and
reasoning blocks are left out unless `--include-thinking` is passed.

## Documentation

| Page | Covers |
| --- | --- |
| [docs/inputs.md](docs/inputs.md) | Accepted inputs, loose mode, unreadable inputs and `problem:` lines, detection from the bundled catalog |
| [docs/parsers.md](docs/parsers.md) | The parser table, how files are routed to parsers, agents detected but not parsed, protobuf and SQLite handling |
| [docs/output.md](docs/output.md) | `detect` output and `--json` keys, `timeline` files and stdout, the `timeline.jsonl` and `sessions.jsonl` schemas |
| [docs/filtering.md](docs/filtering.md) | `--since`, `--until`, `--keep-undated` and `--match`, the `WHEN` forms and periods |
| [docs/searching.md](docs/searching.md) | Reading and searching large output with jq, grep, DuckDB, Python and PowerShell |
| [docs/inventory.md](docs/inventory.md) | The `inventory` command, its CSV columns and rollup |
| [docs/options.md](docs/options.md) | Every option with its subcommands, and the exit codes |
| [docs/development.md](docs/development.md) | Running the tests and lint checks, adding a parser |

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
