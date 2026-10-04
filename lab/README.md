# Agent lab

A disposable Docker sandbox for running CLI coding agents and local models
without installing them on the workstation. Its main use in this repository
is producing real-install fixtures: an agent runs against a scratch home
inside the container, the home is exported as a fake disk image, and the
collector reads it in image mode exactly as it would a mounted volume.

Nothing from the host is mounted into the container. The agent's home is a
named volume, the container runs as an unprivileged user with every
capability dropped, and the only things that cross the boundary are the API
keys you choose to pass in and the export you ask for.

## Requirements

Docker Engine or Docker Desktop with Compose v2. On WSL2, enable Docker
Desktop's integration for this distro. The NVIDIA Container Toolkit is only
needed for GPU inference in Ollama; `lab.sh` adds the GPU override when
`nvidia-smi` works on the host and leaves it out otherwise.

## Quick start

```sh
cd lab
./lab.sh build                      # Claude Code, Codex CLI and Gemini CLI by default
cp .env.example .env && $EDITOR .env  # keys; .env is gitignored
./lab.sh up
./lab.sh run claude                 # work for a few turns, then exit
./lab.sh run codex
./lab.sh collect                    # export, collect, analyze
./lab.sh down                       # keeps the home volume for next time
```

`collect` writes to `lab/out/<UTC stamp>/`:

```
image/        home/agent/..., etc/passwd, root/.ollama (when Ollama ran)
collection/   the collector's archive, manifest, summary and log
analysis/     timeline.csv and sessions.csv from the analyzer
```

Read the manifest for `secret: true` and `skipped_excluded` rows, compare
what the agent wrote against `collectors/research/<agent>.md`, and lift
record shapes from the exported home into analyzer fixtures. The export holds
whatever credentials the agents wrote, so `lab/out` is gitignored. Delete it
when finished, and never copy a real token into a committed fixture.

## Choosing agents

The image installs npm packages globally, outside the home, so the export
holds agent state and no agent binaries. Pick a different set at build time:

```sh
NPM_AGENTS="@anthropic-ai/claude-code @github/copilot @qwen-code/qwen-code opencode-ai" ./lab.sh build
PIP_AGENTS="aider-chat" ./lab.sh build
```

Both variables can also live in `lab/.env`. Copy `.env.example` to `.env` and
fill in the keys you need; the file is gitignored and every variable in it
is passed into the sandbox. Keys already exported in your shell
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`,
`GH_TOKEN`, `OPENROUTER_API_KEY`) pass through as well. Use throwaway keys. OAuth device-code logins work from the
container; browser-redirect logins generally need a published port and are
not worth the trouble.

Electron tools such as Cursor, Windsurf, Antigravity and VS Code need a
display and are out of scope here. Validate those from source.

## Local models

```sh
./lab.sh up --ollama
./lab.sh pull qwen2.5-coder:7b
./lab.sh run aider --model ollama/qwen2.5-coder:7b
```

`OLLAMA_HOST` inside the sandbox already points at the Ollama service.
Models live in a named volume, so the host never grows a `~/.ollama`.
`collect` exports Ollama's state under `image/root/.ollama`, which exercises
the collector's model-blob exclusions against real weights.

## What this does not test

A container home is not a host account. Live-mode user enumeration, the
system snapshot and the `ps` wrappers are not exercised; use a throwaway WSL
distro or VM for those. The layout is Linux only, so macOS `Library` and
Windows `AppData` paths still need validation from source.

Docker on WSL2 shares the kernel with the distro. The sandbox is a good guard
against clutter and accidental damage and a reasonable one against a hostile
tool, not a substitute for a VM when you are running something you distrust.
The container has unrestricted outbound network; Anthropic's devcontainer
reference for Claude Code shows an allowlisting firewall if you need one.

## Cleaning up

```sh
./lab.sh down     # stop, keep volumes
./lab.sh clean    # remove containers, volumes and the image; lab/out stays
rm -rf out        # the exports, once you have what you need
```
