# Shared cross-agent directories

Catalog agent: `shared`. Files and directories read by several agents at
once, so they cannot be attributed to one tool: cross-agent instruction and
skill directories, and the home-level `.env` file that Aider, Gemini CLI,
Qwen Code and Continue read for API keys. Evidence level: the per-agent
documents in this directory, which cite each reader.

## 1. Source and evidence level

Each path below is justified by at least two agents' source. `.env` reading:
Aider (`aider/main.py`, `--env-file`, see `aider.md`), Gemini CLI and Qwen
Code (`.env` and `.gemini/.env` / `.qwen/.env` lookup in their `settings`
loaders, see `gemini-cli.md` and `qwen-code.md`), Continue (`.env` in the
global directory, see `continue.md`). `AGENTS.md` is read by Codex CLI, Amp,
OpenCode, Crush, Factory Droid, Kilo Code and Copilot CLI (see their
documents). `~/.agents` and `~/.config/agents` hold cross-tool skill and
agent definitions adopted by Codex, Copilot CLI and others.

## 2. Per-user storage

| Path relative to home | Holds | Readers |
| --- | --- | --- |
| `.agents` | skills and agent definitions in the cross-tool "agents" layout (`skills/<name>/SKILL.md`) | Codex CLI, Copilot CLI, Amp, others |
| `.config/agents` | XDG variant of the same | same |
| `.config/AGENTS.md` | user-level instructions | Codex CLI, Amp, OpenCode |
| `.env` | environment variables, usually API keys | Aider, Gemini CLI, Qwen Code, Continue |

The layout is identical on every OS because the readers use `homedir()`
without platform branching.

## 3. Credentials

`.env` is flagged `secret: true` (credential glob `.env`). Project-level
`.env` files are collected from discovered project directories with the same
flag.

## 4. Exclusions

None; these are small text files.

## 5. Project-local files

`AGENTS.md` at the project root, collected through the project catalog.

## 6. Project path discovery

Not applicable.

## 7. Catalog review

Current lines, all confirmed by the readers cited above:

```
shared|.agents
shared|.config/AGENTS.md
shared|.config/agents
shared|.env
```

Credential glob `.env` confirmed. Nothing to add. Note for the analyzer: a
directory holding only `shared` matches is treated as a project, not a
home.

## 8. Confidence

High. The only judgement is attribution: a `shared` match says several agents
may have read the file, not which one did.
