# CrewAI: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document yet.

## 1. Source and evidence level

crewAIInc/crewAI, MIT, open source, commit
[`e836a191cfe524feb519c6952a458c9f1e1ff0ef`](https://github.com/crewAIInc/crewAI/commit/e836a191cfe524feb519c6952a458c9f1e1ff0ef).
The repository ships the `crewai` library, `crewai-core`, the `crewai` CLI
(`lib/cli`) and `crewai-tools`. All claims are from source; nothing was
installed or run.

Path resolution uses `appdirs~=1.4.4`
([lib/crewai-core/pyproject.toml:11](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/pyproject.toml#L11)),
not platformdirs, read in ActiveState/appdirs at
[`8734277956c1df3b85385e6b308e954910533884`](https://github.com/ActiveState/appdirs/commit/8734277956c1df3b85385e6b308e954910533884).
`user_data_dir(appname, appauthor)` is `$XDG_DATA_HOME/<appname>` or
`~/.local/share/<appname>` on Linux, `~/Library/Application Support/<appname>`
on macOS, and `%LOCALAPPDATA%\<appauthor>\<appname>` on Windows, where
`appauthor` defaults to `appname` and is ignored on Linux and macOS
([appdirs.py:76-93](https://github.com/ActiveState/appdirs/blob/8734277956c1df3b85385e6b308e954910533884/appdirs.py#L76-L93)).
`user_cache_dir` is `~/.cache/<appname>`, `~/Library/Caches/<appname>` and
`%LOCALAPPDATA%\<appauthor>\<appname>\Cache`
([appdirs.py:297-315](https://github.com/ActiveState/appdirs/blob/8734277956c1df3b85385e6b308e954910533884/appdirs.py#L297-L315)).

CrewAI runs on the host: agents run arbitrary user-defined Python tools,
`FileWriterTool` writes host files
([file_writer_tool.py:165](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-tools/src/crewai_tools/tools/file_writer_tool/file_writer_tool.py#L165)),
and MCP stdio servers are spawned
([mcp/transports/stdio.py:83-97](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/mcp/transports/stdio.py#L83-L97)).
The built-in CodeInterpreterTool is gone
([agent/core.py:293-297](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/agent/core.py#L293-L297)).

## 2. Per-user storage

The run data directory comes from `db_storage_path()`:
`appdirs.user_data_dir(<CREWAI_STORAGE_DIR or the basename of the working directory>, "CrewAI")`
([crewai_core/paths.py:11-26](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/paths.py#L11-L26)).
The directory is therefore named after the project folder:
`~/.local/share/<project>`, `~/Library/Application Support/<project>` and
`%LOCALAPPDATA%\CrewAI\<project>`. Only Windows has a fixed `CrewAI`
component, which is why the Linux and macOS catalog lines are anchored on
CrewAI's own file names below a `*` segment.

| Path (`<data>` = the run data directory) | Holds | Default or opt-in |
| --- | --- | --- |
| `<data>/latest_kickoff_task_outputs.db` (+ WAL) | table `latest_kickoff_task_outputs`: task_id, task_key, expected_output, output JSON (raw, pydantic, agent, messages), inputs, timestamp ([crew.py:224-225](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/crew.py#L224-L225), [task_output_storage_handler.py:25-27](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/utilities/task_output_storage_handler.py#L25-L27), [crew.py:1510-1520](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/crew.py#L1510-L1520), [kickoff_task_outputs_storage.py:25-60](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/memory/storage/kickoff_task_outputs_storage.py#L25-L60)) | default: every `Crew` creates it and every task writes a row |
| `<data>/.crewai_user.json` | trace consent, first-execution flag ([user_data.py:23-26](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/user_data.py#L23-L26)) | default (tracing check) |
| `<data>/memory/` (LanceDB), `memory/qdrant-edge` | agent memory ([crew.py:256-269](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/crew.py#L256-L269), [lancedb_storage.py:69-75](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/memory/storage/lancedb_storage.py#L69-L75), [qdrant_edge_storage.py:104-110](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/memory/storage/qdrant_edge_storage.py#L104-L110)) | opt-in (`memory=True`; default `False`) |
| `<data>/flow_states.db` | Flow state snapshots ([flow/persistence/sqlite.py:71](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/flow/persistence/sqlite.py#L71)) | opt-in (`@persist`) |
| `<data>/` Chroma files, `qdrant/` | knowledge and RAG stores ([rag/chromadb/constants.py:11](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/rag/chromadb/constants.py#L11), [rag/qdrant/constants.py:12](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/rag/qdrant/constants.py#L12)) | opt-in (knowledge sources) |
| `.config/crewai/settings.json` on every OS (falls back to the temp dir, then the working directory) | CLI settings: enterprise URL, org, OAuth2 config, `tool_repository_username` and `password` ([settings.py:26](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/settings.py#L26), [85-89](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/settings.py#L85-L89), [166-171](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/settings.py#L166-L171), [246-259](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/settings.py#L246-L259)) | written by CLI login and config |
| `.local/share/crewai/credentials/`, `Library/Application Support/crewai/credentials/`, `AppData/Local/crewai/credentials/` | `secret.key` (Fernet key), `tokens.enc` (encrypted access token and expiry) ([token_manager.py:22-34](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/token_manager.py#L22-L34), [87-97](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/token_manager.py#L87-L97)) | written by `crewai login` |
| `user_data_dir("crewai", "CrewAI")/eval-awaiting` | CLI TUI eval markers ([crew_run_tui.py:320-323](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/cli/src/crewai_cli/crew_run_tui.py#L320-L323)) | CLI |
| `.crewai/skills/<org>/<name>`, `.crewai/model_catalog_cache.json`, `.crewai/provider_cache.json` | downloaded skills, model lists ([skills/cache.py:24](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai/src/crewai/skills/cache.py#L24), [model_catalog.py:594-599](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/cli/src/crewai_cli/model_catalog.py#L594-L599), [provider.py:215-217](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/cli/src/crewai_cli/provider.py#L215-L217)) | CLI and skills |
| `user_cache_dir("crewai")/version_cache.json` | update check ([version.py:44](https://github.com/crewAIInc/crewAI/blob/e836a191cfe524feb519c6952a458c9f1e1ff0ef/lib/crewai-core/src/crewai_core/version.py#L44)) | cache only, not collected |

On Windows `%LOCALAPPDATA%\crewai\credentials` and
`%LOCALAPPDATA%\CrewAI\<project>` share one parent (NTFS is
case-insensitive), and the token directory looks like a project named
`credentials`. A Windows image mounted on Linux can hold either spelling,
so the catalog line is the class `AppData/Local/[Cc]rew[Aa][Ii]` rather
than two lines that differ only by case (issue 29).

**Memory gap.** On Linux and macOS the opt-in `memory/`, Chroma and Qdrant
stores under `<data>/` have no CrewAI-specific name to anchor a glob on, so
the catalog collects the run database, the flow database and
`.crewai_user.json` but not the memory stores beside them. A responder who
finds a run database should copy its sibling directory by hand; see
[coverage.md](../docs/coverage.md). On Windows the whole `CrewAI`
directory is collected.

Docker: no compose file or named volume.

## 3. Credentials

- `credentials/secret.key` and `credentials/tokens.enc`: the key decrypts
  the token, so both are flagged.
- `.config/crewai/settings.json`: flagged; it can hold
  `tool_repository_password` in plaintext.

## 4. Exclusions

None at default. The opt-in Chroma and LanceDB stores can be large, but
they are agent memory, and on Linux and macOS they are not collected
anyway (section 2).

## 5. Project-local files

None written by CrewAI itself; a CrewAI project is ordinary Python code.
The run directory is per project but lives under the home (section 2).

## 6. Where the project path is recorded

Only indirectly: the run data directory is named after the project
folder's basename, not its full path. Nothing records the full path, so
`discover_projects` has nothing to read.

## 7. Confidence

High for the paths and the default or opt-in status of each store
(source). Medium for the Windows class line covering both spellings, which
follows from appdirs and NTFS rather than a Windows run. Not determined:
whether `CREWAI_STORAGE_DIR` is commonly set in deployments, which would
rename the run directory.
