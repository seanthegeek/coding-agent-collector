# Langflow: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document yet.

## 1. Source and evidence level

langflow-ai/langflow, MIT
([LICENSE:1-3](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/LICENSE#L1-L3)),
commit
[`504c02fc47e76087b82b0e7cbe4186e9cdd916d4`](https://github.com/langflow-ai/langflow/commit/504c02fc47e76087b82b0e7cbe4186e9cdd916d4).
A Python visual agent builder (`langflow` and the `lfx` package). The OSS
paths are from source. **Langflow Desktop is closed source; its paths rest
on the documentation in this repository only.** Platform directory
resolution is cited from tox-dev/platformdirs at
[`960ff632eb575deb6f0d5bf49519d5a2ee2098b6`](https://github.com/tox-dev/platformdirs/commit/960ff632eb575deb6f0d5bf49519d5a2ee2098b6).
Nothing was installed or run.

Langflow executes code on the host: custom component code is `exec`'d in
the server process
([validate.py:692](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/custom/validate.py#L692)),
there is a Python Interpreter component
([python_repl_core.py:13-14](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/components/utilities/python_repl_core.py#L13-L14)),
and MCP stdio servers are spawned on the host
([mcp/util.py:2166](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/base/mcp/util.py#L2166)).

## 2. Per-user storage

The config directory is `LANGFLOW_CONFIG_DIR`, otherwise
`platformdirs.user_cache_dir("langflow", "langflow")`
([paths.py:55-62](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/services/settings/groups/paths.py#L55-L62)):

- Linux: `~/.cache/langflow`, or under `XDG_CACHE_HOME`
  ([unix.py:58-60](https://github.com/tox-dev/platformdirs/blob/960ff632eb575deb6f0d5bf49519d5a2ee2098b6/src/platformdirs/unix.py#L58-L60),
  [_xdg.py:55-56](https://github.com/tox-dev/platformdirs/blob/960ff632eb575deb6f0d5bf49519d5a2ee2098b6/src/platformdirs/_xdg.py#L55-L56)).
- macOS: `~/Library/Caches/langflow`
  ([macos.py:49-51](https://github.com/tox-dev/platformdirs/blob/960ff632eb575deb6f0d5bf49519d5a2ee2098b6/src/platformdirs/macos.py#L49-L51)).
- Windows: `%LOCALAPPDATA%\langflow\langflow\Cache`
  ([windows.py:37-51](https://github.com/tox-dev/platformdirs/blob/960ff632eb575deb6f0d5bf49519d5a2ee2098b6/src/platformdirs/windows.py#L37-L51),
  [70-73](https://github.com/tox-dev/platformdirs/blob/960ff632eb575deb6f0d5bf49519d5a2ee2098b6/src/platformdirs/windows.py#L70-L73)).
  The author segment is doubled even where the code omits `appauthor`
  (`user_cache_dir("langflow")` in
  [logger.py:1217](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/log/logger.py#L1217)).

**The OSS database is not under the home.** `langflow.db` defaults to the
installed package directory (`site-packages/langflow/`), because
`save_db_in_config_dir` is `False`
([database.py:18](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/services/settings/groups/database.py#L18),
[110-121](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/services/settings/groups/database.py#L110-L121)).
It holds the tables `message`, `transaction` (run history) and
`vertex_build`
([message/model.py:183](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/services/database/models/message/model.py#L183),
[transactions/model.py:158](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/services/database/models/transactions/model.py#L158),
[vertex_builds/model.py:70](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/services/database/models/vertex_builds/model.py#L70)),
plus `variable` (encrypted credentials). A virtual environment has no
fixed home path, so the database is a manual step in
[coverage.md](../docs/coverage.md). A `uv tool` install would put it under
`.local/share/uv/tools/langflow/...`, but uv was not cited, so that line
was not added.

| Path | Holds | Default or opt-in |
| --- | --- | --- |
| `.cache/langflow`; `Library/Caches/langflow`; `AppData/Local/langflow/langflow/Cache` | `secret_key` (Fernet key for `variable`), `cache_secret_key`, `<user_id>/` uploaded files and `_mcp_servers_<id>.json`, `profile_pictures` (copied assets), and `langflow.db` only when opted in ([auth.py:352-361](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/services/settings/auth.py#L352-L361), [cache/service.py:35](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/services/cache/service.py#L35), [services/utils.py:316-317](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/services/utils.py#L316-L317), [setup.py:690-691](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/initial_setup/setup.py#L690-L691)) | default |
| `.langflow/knowledge_bases` | Chroma knowledge and memory bases ([paths.py:13](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/lfx/src/lfx/services/settings/groups/paths.py#L13)) | default |
| `.langflow/fs_tool/fs_sandbox` | files the Langflow Assistant's FileSystem tool reads and writes ([assistant_workspace.py:34](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/agentic/helpers/assistant_workspace.py#L34), [64](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/src/backend/base/langflow/agentic/helpers/assistant_workspace.py#L64)) | default when the Assistant runs |
| Desktop, macOS: `.langflow/data` (`database.db`, `.env`), `Library/Application Support/com.LangflowDesktop` (venv), `Library/Logs/com.LangflowDesktop`, `Library/Caches/com.LangflowDesktop` | Desktop database, environment, logs ([memory.mdx:15-17](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/memory.mdx#L15-L17), [environment-variables.mdx:329](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/environment-variables.mdx#L329), [logging.mdx:18-21](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/logging.mdx#L18-L21), [troubleshooting.mdx:142](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Support/troubleshooting.mdx#L142), [315-319](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Support/troubleshooting.mdx#L315-L319)) | default (docs) |
| Desktop, Windows: `AppData/Roaming/com.LangflowDesktop` (`data/database.db`, `data/.env`, `knowledge_bases`), `AppData/Local/com.LangflowDesktop` (venv, `logs`, `cache`) | as above ([memory.mdx:18](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/memory.mdx#L18), [environment-variables.mdx:345](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/environment-variables.mdx#L345), [logging.mdx:21](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/logging.mdx#L21), [troubleshooting.mdx:331](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Support/troubleshooting.mdx#L331)) | default (docs) |

`Library/Caches/com.LangflowDesktop` is a cache and has no catalog line.
The docs disagree with the code on the OSS knowledge bases:
[memory-bases.mdx:173-179](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docs/docs/Develop/memory-bases.mdx#L173-L179)
places them in `site-packages`, but the code default is
`~/.langflow/knowledge_bases`. The code wins.

Docker: the named volume `langflow-data` is mounted at `/app/langflow`,
which is the config directory (`LANGFLOW_CONFIG_DIR=/app/langflow`), so its
root holds `secret_key`, `cache_secret_key` and `profile_pictures`.
PostgreSQL uses the volume `langflow-postgres`
([docker_example/docker-compose.yml:13-15](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docker_example/docker-compose.yml#L13-L15),
[30-34](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docker_example/docker-compose.yml#L30-L34)),
which is a whole PostgreSQL cluster the analyzer cannot read and is left
unmatched. The image home is `/app/data`
([build_and_push.Dockerfile:209](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docker/build_and_push.Dockerfile#L209),
[226](https://github.com/langflow-ai/langflow/blob/504c02fc47e76087b82b0e7cbe4186e9cdd916d4/docker/build_and_push.Dockerfile#L226)).

## 3. Credentials

- `secret_key` and `cache_secret_key` in the config directory, in each
  OS's location and at the root of a `*langflow-data` volume: flagged.
- The Desktop `data/.env` (macOS `.langflow/data/.env`, Windows
  `AppData/Roaming/com.LangflowDesktop/data/.env`): flagged.
- `_mcp_servers_*.json` may embed environment values for MCP servers; not
  flagged.

## 4. Exclusions

`.langflow/knowledge_bases`, the Desktop `knowledge_bases`, `venv`,
`python_env` and `cache` directories, and `profile_pictures` in the config
directory (home-relative in each OS's location, and volume-relative).

## 5. Project-local files

None. Flows are rows in the database.

## 6. Where the project path is recorded

Nowhere; Langflow has no project concept.

## 7. Confidence

High for the OSS paths (source). Medium for Desktop, which rests on docs
only. Not determined: where Desktop keeps its `secret_key`, and the Desktop
Linux layout, which the docs do not give.
