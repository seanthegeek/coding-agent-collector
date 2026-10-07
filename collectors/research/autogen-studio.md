# AutoGen Studio: on-disk paths

This document came out of the agent framework sweep for issue #64; the
AutoGen libraries and Microsoft Agent Framework, which write nothing under
the home by default, are covered in [frameworks.md](frameworks.md). There
is no analyzer document yet.

## 1. Source and evidence level

microsoft/autogen, commit
[`027ecf0a379bcc1d09956d46d12d44a3ad9cee14`](https://github.com/microsoft/autogen/commit/027ecf0a379bcc1d09956d46d12d44a3ad9cee14).
Code is MIT ([LICENSE-CODE](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/LICENSE-CODE)),
docs CC-BY-4.0. The repository ships `autogen-core`, `autogen-agentchat`,
`autogen-ext`, `magentic-one-cli` and `autogen-studio` 0.4.3
([version.py:1](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/version.py#L1)).
The README marks AutoGen as in maintenance mode and points new users to
Microsoft Agent Framework
([README.md:14-25](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/README.md#L14-L25)).
All claims are from source; nothing was installed or run.

AutoGen Studio is the web UI (`autogenstudio ui`) for building and running
multi-agent teams. It is in the catalog because its default gallery runs
code on the host: a Python code execution tool built on
`LocalCommandLineCodeExecutor(work_dir=".coding")`, relative to the working
directory
([builder.py:433-439](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/gallery/builder.py#L433-L439)),
and an MCP filesystem workbench rooted at the home directory
([builder.py:562-573](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/gallery/builder.py#L562-L573)).

## 2. Per-user storage

The app directory is `~/.autogenstudio` (`Path.home()`) on every OS, unless
`AUTOGENSTUDIO_APPDIR` or `--appdir` is set
([initialization.py:41-45](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/initialization.py#L41-L45),
[cli.py:58-59](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/cli.py#L58-L59),
[README.md:130](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/README.md#L130)).

| Path under `~/.autogenstudio` | Holds | Default or opt-in |
| --- | --- | --- |
| `autogen04203.db` | SQLite: tables `team`, `message`, `session`, `run` (task, `team_result`, messages as JSON), `gallery`, `settings`, eval tables. The README's `database.sqlite` name is out of date ([config.py:7](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/config.py#L7), [initialization.py:47-51](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/initialization.py#L47-L51), [db.py:51-170](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/datamodel/db.py#L51-L170)) | default unless `--database-uri` is set |
| `files/`, `files/user/`, `configs/` | static files, user files, team configs ([initialization.py:53-70](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/initialization.py#L53-L70), [config.py:11](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/config.py#L11)) | default |
| `alembic/`, `alembic.ini` | migration scaffolding, small ([deps.py:142](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/deps.py#L142), [schema_manager.py:43-45](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/database/schema_manager.py#L43-L45)) | default |
| `temp_env_vars.env` | host, port, app dir, database URI, auth config path; always under the home, even when `--appdir` is set ([cli.py:18-22](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/cli.py#L18-L22), [cli.py:51-74](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/cli.py#L51-L74), [lite/studio.py:131-135](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/lite/studio.py#L131-L135)) | default |
| `.env` | environment variables (API keys) that the user puts there and Studio loads ([initialization.py:72-77](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/web/initialization.py#L72-L77)) | read if present |

Studio lite mode uses an in-memory database
([lite/studio.py:150](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/lite/studio.py#L150)).

Docker: no compose file and no named volume. The Studio Dockerfile sets
`AUTOGENSTUDIO_APPDIR=/home/user/app` inside the image
([Dockerfile:11](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/Dockerfile#L11)),
so no `DOCKER_VOLUMES` line.

## 3. Credentials

- `.autogenstudio/.env`: secret glob.
- `.autogenstudio/temp_env_vars.env`: secret glob; its database URI can
  embed a Postgres password
  ([README.md:133](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/README.md#L133)).
- The `settings` table in `autogen04203.db` holds environment variables
  typed `secret` and the default model client config with its `api_key`
  ([types.py:88-109](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-studio/autogenstudio/datamodel/types.py#L88-L109)).
  The database also holds the run history, so it is collected unflagged,
  as the catalog does for Cursor's `state.vscdb`; redact the `settings`
  table before sharing.

## 4. Exclusions

None. The directory is small.

## 5. Project-local files

None written by Studio itself. The gallery's code executor works in
`.coding` relative to the directory Studio was started from; nothing
records that directory.

## 6. Where the project path is recorded

Nowhere. Studio has no project concept; teams and sessions are rows in
`autogen04203.db`.

## 7. Confidence

High for the app directory, the database name and tables, and the
credential locations (source). Not determined: whether older Studio
releases used another database name (the README mentions
`database.sqlite`), and whether `.coding` lands under the home when Studio
is started there.
