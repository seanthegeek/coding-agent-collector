# Pydantic AI CLIs (clai and CLAI 2.0): on-disk paths

This document came out of the agent framework sweep for issue #64; the
Pydantic AI library itself and Logfire, which got no catalog line, are
covered in [frameworks.md](frameworks.md). There is no analyzer document
yet.

## 1. Source and evidence level

pydantic/pydantic-ai, MIT, open source, commit
[`0ba01f92be3fc361f89970502cd6e7dd3611aec3`](https://github.com/pydantic/pydantic-ai/commit/0ba01f92be3fc361f89970502cd6e7dd3611aec3).
The repository ships `pydantic-ai(-slim)`, `pydantic-graph`,
`pydantic-evals`, the `clai` CLI, and under `src/` two newer packages:
`pydantic-ai-harness` and CLAI 2.0 (`pydantic-clai2`, commands `clai2` and
`pydantic-clai2`,
[pyproject.toml:62-65](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pyproject.toml#L62-L65);
`pydantic_clai2-0.54.0` is on PyPI and its wheel was fetched and read, not
installed). CLAI 2.0 is a terminal coding agent with a `coder` plugin on
by default
([README.md:3-5](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/README.md#L3-L5)).
All claims are from source. The catalog agent `pydantic-clai` covers both
CLIs.

CLAI 2.0 runs commands on the host: `LocalWorkspaceBackend` "runs commands
as plain host subprocesses — it isolates nothing"
([workspaces/local.py:1-5](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/pydantic_ai_slim/pydantic_ai/workspaces/local.py#L1-L5)),
and the harness ships a shell toolset
([shell/_toolset.py:50](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_ai_harness/pydantic_ai_harness/shell/_toolset.py#L50),
[365](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_ai_harness/pydantic_ai_harness/shell/_toolset.py#L365)).
`clai` v1 runs only provider-native tools
([_cli/\_\_init\_\_.py:60-62](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/pydantic_ai_slim/pydantic_ai/_cli/__init__.py#L60-L62)).

## 2. Per-user storage

The library has no default path under the home; message history is
returned to the caller (see [frameworks.md](frameworks.md)). The CLIs
write:

| Path (home-relative, all OSes) | Holds | Default or opt-in |
| --- | --- | --- |
| `.pydantic-ai/prompt-history.txt` | `clai` v1 prompt_toolkit input history ([_cli/\_\_init\_\_.py:52-58](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/pydantic_ai_slim/pydantic_ai/_cli/__init__.py#L52-L58), [460-463](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/pydantic_ai_slim/pydantic_ai/_cli/__init__.py#L460-L463)) | default for `clai` |
| `.config/pydantic-clai2/` (`$XDG_CONFIG_HOME` honoured; `~/.config` on macOS and Windows too) | the CLAI 2.0 folder ([settings_store.py:60-70](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/settings_store.py#L60-L70)) | default |
| `.config/pydantic-clai2/config.db` | settings (`settings` table), "never credentials or conversation messages" (same citation; [\_\_main\_\_.py:29](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/__main__.py#L29)) | default |
| `.config/pydantic-clai2/sessions.db` | table `conversations` (id, metadata JSON including `workspace`, `model`, `title`; `messages`; `updated_at`) ([_app.py:540](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/_app.py#L540), [conversations.py:37-58](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/conversations.py#L37-L58), [154-156](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_ai_harness/pydantic_ai_harness/step_persistence/conversations.py#L154-L156)) | default |
| `.config/pydantic-clai2/input-history` | prompt history ([_app.py:789](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/_app.py#L789)) | default |
| `.config/pydantic-clai2/credentials-<account>.enc` (the keyring holds the Fernet key, service `pydantic-clai2`) or `credentials-<account>.json` (plaintext, no keyring), with `.lock` sidecars | provider logins, `api-keys`, Copilot ([credential_store.py:1-5](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/credential_store.py#L1-L5), [23-42](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/credential_store.py#L23-L42), [149-152](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/credential_store.py#L149-L152)) | on login |
| `.config/pydantic-clai2/mcp.json`, `mcp_logs/` | user MCP servers (headers "may be sensitive"), server logs ([mcp/_store.py:70-88](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/mcp/_store.py#L70-L88)) | on `/mcp install` |
| `.config/pydantic-clai2/logfire/logfire_credentials.json` | Logfire write token ([builtin_plugins/logfire.py:221-227](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/builtin_plugins/logfire.py#L221-L227)) | opt-in plugin |

**Other agents' sessions.** CLAI 2.0's `/resume` reads Claude Code
sessions (`~/.claude/projects/*/*.jsonl`) and Codex rollouts
(`~/.codex/sessions/**`) and copies them into `sessions.db`
([imported_sessions.py:1-5](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/runtime/imported_sessions.py#L1-L5),
[claude_code_sessions.py:41-43](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/runtime/claude_code_sessions.py#L41-L43),
[codex_sessions.py:35-37](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/runtime/codex_sessions.py#L35-L37)).
A Claude Code or Codex session can therefore appear in CLAI's store as
well as in its own; see [claude-code.md](claude-code.md) and
[codex-cli.md](codex-cli.md). Both are already in the catalog.

Docker: none.

## 3. Credentials

- `.config/pydantic-clai2/credentials-*` (the `.enc` and `.json` forms and
  their `.lock` sidecars): flagged. Without a keyring the `.json` form is
  plaintext; with one, the `.enc` form needs the keyring's Fernet key.
- `.config/pydantic-clai2/logfire/logfire_credentials.json`: flagged.
- `mcp.json` is collected unflagged although its headers may embed tokens.

## 4. Exclusions

None under the home. CLAI 2.0 puts git worktrees at
`<repo>/.worktrees/<name>`
([worktrees.py:46](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/runtime/worktrees.py#L46));
`.worktrees` is not a project catalog entry, and it is too generic a name
to exclude.

## 5. Project-local files

`.clai/settings.json` and `.clai/mcp_servers.json`
([project_settings.py:10](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/project_settings.py#L10),
[mcp/_store.py:25](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/mcp/_store.py#L25)),
collected through the `project|.clai` project catalog entry.

## 6. Where the project path is recorded

`sessions.db`, `conversations.metadata`, JSON key `workspace`. It is
recorded only inside SQLite, so `discover_projects` and `Find-Projects`
cannot read it; a project's `.clai` directory is collected when another
agent's state or a `-p` option names the project. The analyzer is the
place to read it.

## 7. Confidence

High (source at the commit). Not determined: whether the
`credentials-*.lock` files hold anything (the docstring says the SQLite
lock file holds no secrets,
[credential_store.py:80](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/src/pydantic_clai2/pydantic_clai2/config/credential_store.py#L80));
the full `messages` encoding in `sessions.db` (media externalised to a
`SqliteMediaStore`), which needs an analyzer research document.
