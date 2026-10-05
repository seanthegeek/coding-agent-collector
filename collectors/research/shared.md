# Shared cross-agent directories

Catalog agent: `shared`. Files and directories read by several agents at
once, so they cannot be attributed to one tool: cross-agent instruction and
skill directories. Evidence level: the per-agent
documents in this directory, which cite each reader.

## 1. Source and evidence level

Each path below is justified by at least two agents' source. `AGENTS.md` is read by Codex CLI, Amp,
OpenCode, Crush, Factory Droid, Kilo Code and Copilot CLI (see their
documents). `~/.agents` and `~/.config/agents` hold cross-tool skill and
agent definitions adopted by Codex, Copilot CLI and others.

## 2. Per-user storage

| Path relative to home | Holds | Readers |
| --- | --- | --- |
| `.agents` | skills and agent definitions in the cross-tool "agents" layout (`skills/<name>/SKILL.md`) | Codex CLI, Copilot CLI, Amp, others |
| `.config/agents` | XDG variant of the same | same |
| `.config/AGENTS.md` | user-level instructions | Codex CLI, Amp, OpenCode |

The layout is identical on every OS because the readers use `homedir()`
without platform branching.

## 3. Credentials

None. The home-level and project-level `.env` files that Aider, Gemini
CLI, Qwen Code and Continue read for API keys are general-purpose
environment files and are not collected (collector 1.7.0); they are left to
the EDR. Agent-specific `.env` files inside an agent's own directory, such
as `.gemini/.env` and `.qwen/.env`, are collected under that agent.

## 4. Exclusions

None; these are small text files.

## 5. Project-local files

`AGENTS.md` at the project root, collected through the project catalog.

## 6. Project path discovery

Not applicable.

## 7. Confidence

High. The only judgement is attribution: a `shared` match says several agents
may have read the file, not which one did.
