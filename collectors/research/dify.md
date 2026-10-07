# Dify: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document: the run history is in PostgreSQL.

## 1. Source and evidence level

langgenius/dify, commit
[`519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e`](https://github.com/langgenius/dify/commit/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e).
The repository ships the self-hosted LLM app platform (Flask API, Celery
worker, Next.js web), a `dify-agent` backend with a Go `shellctl` sandbox
runtime, and `difyctl`, a CLI client. Licence: modified Apache 2.0 with
multi-tenant and logo conditions
([LICENSE:1-5](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/LICENSE#L1-L5)).
All claims are from source unless marked inferred; nothing was installed
or run.

Dify executes tools and shell commands, inside containers on the host. The
Code node posts to `dify-sandbox`
([code_executor.py:19](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/core/helper/code_executor/code_executor.py#L19),
[81](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/core/helper/code_executor/code_executor.py#L81),
[docker-compose.yaml:510-511](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L510-L511)),
and the agent runs shell jobs in `local_sandbox` through shellctl
([539-548](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L539-L548),
[677](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L677)).

## 2. Per-user storage

**The server has no default path under the home.** It is deployed with
Compose from the clone (`cd dify`, `cd docker`, `docker compose up -d`,
[README.md:77-82](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/README.md#L77-L82)),
and almost all state goes to bind mounts under `./volumes` beside the
compose file, not to named volumes:

- user files and tenant keys: `./volumes/app/storage`
  ([docker-compose.yaml:263](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L263));
- PostgreSQL: `./volumes/db/data` (profile `postgresql`, the default,
  [425-428](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L425-L428),
  [444](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L444),
  [.env.example:299](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/.env.example#L299));
- Redis: `./volumes/redis/data`
  ([499](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L499));
- the code sandbox: `./volumes/sandbox/*`
  ([532-533](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L532-L533));
- plugins: `./volumes/plugin_daemon`
  ([644](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L644));
- vector stores: `./volumes/weaviate` and similar.

Chat and run history is in PostgreSQL: tables `conversations`, `messages`
and `message_agent_thoughts` (agent tool calls)
([models/model.py:1117](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/models/model.py#L1117),
[1441](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/models/model.py#L1441),
[2431](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/models/model.py#L2431)),
plus `workflow_runs` and `workflow_node_executions`
([models/workflow.py:797](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/models/workflow.py#L797),
[968](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/models/workflow.py#L968)).
These are raw PostgreSQL data files, which the analyzer cannot read
without a PostgreSQL server.

The clone location is not fixed. The README's `cd dify` suggests a clone
named `dify`, often in a home directory, but that is an inference, so the
bind mounts have no catalog line. Collecting them by hand is a manual step
in [coverage.md](../docs/coverage.md).

**Named volumes.** The compose file declares four
([docker-compose.yaml:1325-1328](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L1325-L1328)).
`dify_agent_local_sandbox_home` is mounted at `/home/dify` and
`dify_agent_local_sandbox_workspace` at `/workspace`
([559-561](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L559-L561));
neither is behind a profile. The container home is `/home/dify`
([dify-agent-runtime/docker/Dockerfile:74-80](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/dify-agent-runtime/docker/Dockerfile#L74-L80)),
and shellctl keeps its state in `~/.local/share/shellctl`
([internal/server/config.go:132-143](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/dify-agent-runtime/internal/server/config.go#L132-L143)):
the `shellctl.db` SQLite database (table `jobs`) and `jobs/<id>/output.log`,
the agent's shell job output
([config.go:114-119](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/dify-agent-runtime/internal/server/config.go#L114-L119),
[db.go:150](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/dify-agent-runtime/internal/server/db.go#L150),
[service.go:173](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/dify-agent-runtime/internal/server/service.go#L173)).
That state is in the home volume. The compose file sets no `name:`, so
Compose prefixes the volume names with the directory name (`docker_`); the
`DOCKER_VOLUMES` lines are `*dify_agent_local_sandbox_home` and
`*dify_agent_local_sandbox_workspace`. `dify_es01_data` and `oradata` are
opt-in vector-store profiles and are left unmatched.

**difyctl.** The CLI client, described as an internal "edge" build, keeps
`config.yml`, `login.yml`, and `tokens.yml` when the OS keyring is
unavailable, in `~/.config/difyctl` on Linux and macOS and
`AppData/Roaming/difyctl` on Windows, with a `LOCALAPPDATA` fallback
([cli/src/sys/index.ts:58-121](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/cli/src/sys/index.ts#L58-L121),
[store/manager.ts:8](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/cli/src/store/manager.ts#L8),
[37-64](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/cli/src/store/manager.ts#L37-L64),
[README.md:1-3](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/cli/README.md#L1-L3)).

## 3. Credentials

- difyctl `tokens.yml`, in all three locations: flagged.
- Not collected (outside the home): `docker/.env` holds `SECRET_KEY`
  ([.env.example:33](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/.env.example#L33)).
  Per-tenant RSA keys are written to `privkeys/<tenant_id>/private.pem` in
  storage ([api/libs/rsa.py:37](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/api/libs/rsa.py#L37)),
  which is the OpenDAL fs root `storage` and so `volumes/app/storage` by
  default ([.env.example:159-161](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/.env.example#L159-L161)).
  These keys decrypt the provider API keys held in PostgreSQL.

## 4. Exclusions

None under the home or in the two named volumes. In the bind mounts the
vector-store directories (`volumes/weaviate`, `qdrant`, `milvus` and so
on) and `volumes/sandbox/dependencies` are large.

## 5. Project-local files

None in the sense of the project catalog; the deployment's own
`docker/` directory is the state (section 2).

## 6. Where the project path is recorded

Nowhere under the home.

## 7. Confidence

High for the named volumes, shellctl's state and the table names (source).
Low for the clone location, which is why it has no catalog line. Not
determined: whether the `dify-agent` Python backend persists anything
beyond Redis; it mounts no volume
([660-697](https://github.com/langgenius/dify/blob/519ef8b8c2d75f597b8a1dfff79ef4b8c5013e3e/docker/docker-compose.yaml#L660-L697)).
