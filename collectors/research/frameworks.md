# Agent frameworks and self-hosted platforms: default-path sweep

The sweep asked for in issue #64: sixteen agent frameworks, framework
studios and self-hosted agent platforms, checked for a default per-user
directory that the collectors could add as catalog lines. It is not an
agent document. The frameworks that got a catalog agent each have their
own document, linked from the table; this document holds the evidence for
the ones that got no catalog line, and the reason.

Three kinds of software were checked:

- **Libraries** (AutoGen, Microsoft Agent Framework, Semantic Kernel,
  LangGraph, Pydantic AI, Atomic Agents, CAMEL, CrewAI, MetaGPT). A library
  runs inside someone else's application, so it gets a catalog line only
  when it writes to a fixed place under the home by default, whatever the
  application.
- **CLIs and studios** built on a library (AutoGen Studio, `clai` and
  CLAI 2.0, TaskWeaver, the CrewAI and MetaGPT CLIs, the legacy Open
  Interpreter SDK and CLI).
- **Self-hosted platforms** (Dify, Flowise, Langflow, n8n, IntentKit),
  checked against `DOCKER_VOLUMES` as well as the home, and against the
  manual steps in [coverage.md](../docs/coverage.md) for state outside the
  home.

"Default" means a path the software writes or reads without the user
choosing it: a constant, an `appdirs` or `platformdirs` directory, or
`Path.home()` joined with a fixed name. Paths the caller must pass, paths
relative to the working directory, and in-memory stores do not count.

Repositories were shallow-cloned on 2026-10-06 and only read; nothing was
installed or run. Two PyPI wheels that are not in any repository were
downloaded and unpacked for reading (section LangGraph).

## Summary

| Framework | Repository and commit | Default per-user path | Catalog agent | Evidence |
| --- | --- | --- | --- | --- |
| AutoGen (libraries and Studio) | microsoft/autogen `027ecf0` | Studio: `~/.autogenstudio`; libraries: none | `autogen-studio`, see [autogen-studio.md](autogen-studio.md); libraries none, see [AutoGen libraries](#autogen-libraries) | source |
| Microsoft Agent Framework | microsoft/agent-framework `279d97f` | none | none, see [Microsoft Agent Framework](#microsoft-agent-framework) | source |
| Semantic Kernel | microsoft/semantic-kernel `64005c7` | none (opt-in MSAL cache `sk.msal.cache`) | none, see [Semantic Kernel](#semantic-kernel) | source |
| TaskWeaver | microsoft/TaskWeaver `d44ddef` | none; state in the project directory | none, see [TaskWeaver](#taskweaver) | source |
| CrewAI | crewAIInc/crewAI `e836a19` | `~/.local/share/<project>`, `~/Library/Application Support/<project>`, `AppData/Local/CrewAI`; `~/.config/crewai`, `~/.crewai` | `crewai`, see [crewai.md](crewai.md) | source |
| LangGraph | langchain-ai/langgraph `39c523e` | none; `.langgraph_api` in the project directory | none, see [LangGraph](#langgraph) | source and PyPI wheels |
| Pydantic AI (library, `clai`, CLAI 2.0; Logfire noted) | pydantic/pydantic-ai `0ba01f9`, pydantic/logfire `bae9db2` | library: none; `clai`: `~/.pydantic-ai`; CLAI 2.0: `~/.config/pydantic-clai2`; Logfire: `~/.logfire` | `pydantic-clai`, see [pydantic-clai.md](pydantic-clai.md); library and Logfire none, see [Pydantic AI library](#pydantic-ai-library) and [Logfire](#logfire) | source |
| MetaGPT | FoundationAgents/MetaGPT `11cdf46` | `~/.metagpt` | `metagpt`, see [metagpt.md](metagpt.md) | source |
| CAMEL | camel-ai/camel `24fde60` | `~/.camel/gmail_token.json`, `~/.camel/skills`, `~/.config/camel` | `camel-ai`, see [camel-ai.md](camel-ai.md) | source |
| Atomic Agents | BrainBlend-AI/atomic-agents `d2b61b9` | none | none, see [Atomic Agents](#atomic-agents) | source |
| IntentKit | crestalnetwork/intentkit `afc8cc4` | none; Postgres in Compose volumes | none, see [IntentKit](#intentkit) | source |
| Open Interpreter, legacy Python SDK | openinterpreter/openinterpreter `13061d2` (v0.4.2) | platformdirs `open-interpreter`, older `Open Interpreter*`; `~/.cache/open-interpreter` | added to `open-interpreter`, see [open-interpreter.md](open-interpreter.md) | source and the 0.4.3 sdist |
| Dify | langgenius/dify `519ef8b` | server: none (bind mounts beside the compose file); `difyctl`: `~/.config/difyctl` | `dify`, see [dify.md](dify.md) | source |
| Flowise | FlowiseAI/Flowise `9291856` | `~/.flowise` | `flowise`, see [flowise.md](flowise.md) | source |
| Langflow | langflow-ai/langflow `504c02f` | platformdirs cache dir `langflow`, `~/.langflow`; Desktop `com.LangflowDesktop` | `langflow`, see [langflow.md](langflow.md) | source; Desktop from docs only |
| n8n | n8n-io/n8n `0e1c754` | `~/.n8n`, `~/.n8n-local-gateway`, `~/.n8n-gateway` | `n8n`, see [n8n.md](n8n.md) | source |

The Docker volumes added in the same round are Dify's
`*dify_agent_local_sandbox_home` and `*dify_agent_local_sandbox_workspace`,
Langflow's `*langflow-data`, and n8n's `*n8n_data` and `*n8n-data`; the
evidence is in each agent's document.

## AutoGen libraries

microsoft/autogen at
[`027ecf0a379bcc1d09956d46d12d44a3ad9cee14`](https://github.com/microsoft/autogen/commit/027ecf0a379bcc1d09956d46d12d44a3ad9cee14),
code MIT. AutoGen Studio is in the catalog; see
[autogen-studio.md](autogen-studio.md). The libraries (`autogen-core`,
`autogen-agentchat`, `autogen-ext`) write nothing under the home by
default:

- ChromaDB memory defaults to `./chroma_db` in the working directory
  ([_chroma_configs.py:127](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/memory/chromadb/_chroma_configs.py#L127)).
  `~/.chromadb_autogen` appears only in a docstring example
  ([_chromadb.py:93](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/memory/chromadb/_chromadb.py#L93)).
- Task-centric memory defaults to `./memory_bank/default`
  ([_memory_bank.py:57](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/experimental/task_centric_memory/_memory_bank.py#L57))
  and its page logs to `./pagelogs/default`
  ([page_logger.py:80](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/experimental/task_centric_memory/utils/page_logger.py#L80)).
- Mem0 defaults to the cloud client
  ([_mem0.py:28](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-ext/src/autogen_ext/memory/mem0/_mem0.py#L28)).

Searched for `expanduser`, `Path.home`, `homedir`, `platformdirs`,
`appdirs`, `user_*_dir`, `XDG_`, `APPDATA`, `LOCALAPPDATA`, `SpecialFolder`,
`"HOME"`, `"~/"`, `persist_directory`, `.db`, `sqlite`, `Path.cwd`,
`getcwd`, `CurrentDirectory`, compose files and `volumes`, leaving out
tests, samples and notebooks.

**No catalog line:** nothing is written under the home unless the
application chooses a path there. Confidence high.

## Microsoft Agent Framework

microsoft/agent-framework at
[`279d97f75cb2e7eee885dcdc2c741ef7361ee903`](https://github.com/microsoft/agent-framework/commit/279d97f75cb2e7eee885dcdc2c741ef7361ee903),
MIT
([LICENSE](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/LICENSE)),
with Python, .NET and Go code; the successor to AutoGen and Semantic
Kernel. It writes nothing under the home by default:

- `FileCheckpointStorage` requires a path
  ([_checkpoint.py:534-551](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/core/agent_framework/_workflows/_checkpoint.py#L534-L551)).
- The harness file memory goes to `{cwd}/agent-file-memory`
  ([_harness/_agent.py:186-190](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/core/agent_framework/_harness/_agent.py#L186-L190)).
- DevUI keeps conversations in memory
  ([_conversations.py:215](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/devui/agent_framework_devui/_conversations.py#L215)).
- The .NET `FileSystemAgentSessionStore` writes `$HOME/.checkpoints` only
  inside a Foundry-hosted container (default `/home/session`) and
  `{cwd}/.checkpoints` locally
  ([FileSystemAgentSessionStore.cs:27-34](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/dotnet/src/Microsoft.Agents.AI.Foundry.Hosting/FileSystemAgentSessionStore.cs#L27-L34),
  [106-121](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/dotnet/src/Microsoft.Agents.AI.Foundry.Hosting/FileSystemAgentSessionStore.cs#L106-L121)).

It does execute on the host: it ships `LocalShellTool`
([shell/_tool.py:71](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/tools/agent_framework_tools/shell/_tool.py#L71)).
`agent-framework-claude` drives Claude Code through `claude_agent_sdk`
([claude/_agent.py:37](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/claude/agent_framework_claude/_agent.py#L37)),
and `agent-framework-github-copilot` drives the Copilot SDK
([github_copilot/_agent.py:60](https://github.com/microsoft/agent-framework/blob/279d97f75cb2e7eee885dcdc2c741ef7361ee903/python/packages/github_copilot/agent_framework_github_copilot/_agent.py#L60)),
so those sessions land in the `claude-code` and `copilot-cli` state
directories, which the catalog already covers. That last point is an
inference that was not traced into either SDK.

**No catalog line:** no default state under the home. No compose file or
named volume. Confidence high.

## Semantic Kernel

microsoft/semantic-kernel at
[`64005c77870a3b8a157f8aefefd45093f1e6fc00`](https://github.com/microsoft/semantic-kernel/commit/64005c77870a3b8a157f8aefefd45093f1e6fc00),
MIT
([LICENSE](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/LICENSE)),
Python and .NET SDKs (the `java/` directory holds only a README). The
README says Semantic Kernel "is now Microsoft Agent Framework"
([README.md](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/README.md)).

The grep found no home, XDG or AppData resolution in `python/semantic_kernel`
or `dotnet/src`. Vector stores persist only when the caller passes a path:
Chroma's `persist_directory` is `None` by default
([chroma.py:80-111](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/python/semantic_kernel/connectors/chroma.py#L80-L111)),
as is USearch's
([usearch_memory_store.py:126-145](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/python/semantic_kernel/connectors/memory_stores/usearch/usearch_memory_store.py#L126-L145)).

The one per-user file is opt-in. The .NET MS Graph plugin's
`LocalUserMSALCredentialManager.CreateAsync()` builds an MSAL token cache
named `sk.msal.cache` in `MsalCacheHelper.UserRootDirectory`
([LocalUserMSALCredentialManager.cs:53-70](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/dotnet/src/Plugins/Plugins.MsGraph/Connectors/CredentialManagers/LocalUserMSALCredentialManager.cs#L53-L70));
only two .NET samples call it. Per OS, checked in
AzureAD/microsoft-authentication-library-for-dotnet at
`2d15026e7f9e3e84d27f0b97a9d620273eb8860c`:

- Windows: `AppData/Local/sk.msal.cache`, a DPAPI-encrypted file
  ([SharedUtilities.cs:120-124](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/2d15026e7f9e3e84d27f0b97a9d620273eb8860c/src/client/Microsoft.Identity.Client.Extensions.Msal/Shared/SharedUtilities.cs#L120-L124),
  [Storage.cs:72-74](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/2d15026e7f9e3e84d27f0b97a9d620273eb8860c/src/client/Microsoft.Identity.Client.Extensions.Msal/Storage.cs#L72-L74)).
- macOS: `~/sk.msal.cache` is only touched; the token goes to the Keychain
  ([MacKeyChainAccessor.cs:74](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/2d15026e7f9e3e84d27f0b97a9d620273eb8860c/src/client/Microsoft.Identity.Client.Extensions.Msal/Accessors/MacKeyChainAccessor.cs#L74)).
- Linux: the token goes to the keyring, with a plaintext file fallback at
  `~/sk.msal.cache`
  ([Storage.cs:84-92](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/2d15026e7f9e3e84d27f0b97a9d620273eb8860c/src/client/Microsoft.Identity.Client.Extensions.Msal/Storage.cs#L84-L92)).
- All three also get a `.lockfile` sidecar
  ([MsalCacheHelper.cs:387](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/2d15026e7f9e3e84d27f0b97a9d620273eb8860c/src/client/Microsoft.Identity.Client.Extensions.Msal/MsalCacheHelper.cs#L387)).

It does not execute on the host by default: the Python code tool,
`sessions_python_tool`, runs code in remote Azure Container Apps sessions
([sessions_python_tool/](https://github.com/microsoft/semantic-kernel/blob/64005c77870a3b8a157f8aefefd45093f1e6fc00/python/semantic_kernel/core_plugins/sessions_python_tool/__init__.py#L3)),
and the grep found no local subprocess use.

**No catalog line:** no default state under the home, and the only
per-user file is an opt-in MS Graph token cache from a plugin used in
samples. If it is wanted later, a secret-only line
`semantic-kernel|AppData/Local/sk.msal.cache*` would be the form.
Confidence high for the negative; the Linux plaintext fallback condition
(`UseLinuxUnencryptedFallback`) was not traced into Semantic Kernel, which
does not set it.

## TaskWeaver

microsoft/TaskWeaver at
[`d44ddef23f90059fb17999d3095db4240e98f955`](https://github.com/microsoft/TaskWeaver/commit/d44ddef23f90059fb17999d3095db4240e98f955)
(last commit 2026-03-23), MIT
([LICENSE](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/LICENSE)).
A code-first agent framework that plans and executes Python for data
analytics
([README.md:13](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/README.md#L13)),
with a CLI, a web UI and a sample `project/` directory.

All state lives in the project directory, which is an explicit `--project`
or the nearest ancestor of the working directory that holds
`taskweaver_config.json`, falling back to the working directory
([app_utils.py:6-46](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/utils/app_utils.py#L6-L46),
[config_mgt.py:48](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/config/config_mgt.py#L48)):

- `<project>/workspace/sessions/<session_id>/`
  ([workspace.py:13-28](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/workspace/workspace.py#L13-L28))
  holds `<id>.json` and `<id>_<round>.json`, the session and per-round
  transcript dumps
  ([session.py:122-125](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/session/session.py#L122-L125),
  [267-273](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/session/session.py#L267-L273));
  `planner_prompt_log_*.json` and `code_generator_prompt_log_*.json`
  ([session.py:183-197](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/session/session.py#L183-L197));
  and `cwd/`, the execution working directory, and `ces/`
  ([environment.py:194-198](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/ces/environment.py#L194-L198)).
- `<project>/logs/task_weaver.log`
  ([logging/\_\_init\_\_.py:28-30](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/logging/__init__.py#L28-L30)),
  `<project>/experience/`
  ([session.py:23-25](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/session/session.py#L23-L25)),
  `<project>/env/`
  ([execution_service.py:13-16](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/module/execution_service.py#L13-L16)),
  `<project>/plugins/`
  ([plugin.py:303-309](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/memory/plugin.py#L303-L309)).
- Credentials: `<project>/taskweaver_config.json` key `llm.api_key`
  ([project/taskweaver_config.json:3](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/project/taskweaver_config.json#L3)).

Docker: no named volumes. Container kernel mode bind-mounts the session's
`ces/` and `cwd/` directories
([environment.py:255-263](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/ces/environment.py#L255-L263)),
and the documented `docker run` commands pass no `-v`
([docker.md:38](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/website/docs/usage/docker.md#L38)).

It executes on the host in `local` kernel mode. The default `kernel_mode`
is `container`, which runs code in Docker; `local` runs a Jupyter kernel on
the host and prints a warning
([execution_service.py:17-29](https://github.com/microsoft/TaskWeaver/blob/d44ddef23f90059fb17999d3095db4240e98f955/taskweaver/module/execution_service.py#L17-L29)).

**No catalog line:** no home-relative state, and nothing under the home
records the project path, so `discover_projects` has nothing to read. The
manual step (find `taskweaver_config.json`, collect `workspace/sessions`
beside it) is in [coverage.md](../docs/coverage.md). Confidence high; the
Chainlit UI (`playground/`) was not read.

## LangGraph

langchain-ai/langgraph at
[`39c523eb0af1d192f739fd2b7ddfea38f3002a2a`](https://github.com/langchain-ai/langgraph/commit/39c523eb0af1d192f739fd2b7ddfea38f3002a2a),
MIT. Ships `langgraph`, checkpoint savers (memory, SQLite, PostgreSQL),
`prebuilt`, `langgraph-cli` and SDKs. `langgraph dev` imports
`langgraph_api.cli.run_server` from the separate `langgraph-api` package
([cli.py:790-820](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/cli/langgraph_cli/cli.py#L790-L820)),
whose in-memory runtime is `langgraph-runtime-inmem`. **Neither package is
in this repository.** They were read from the PyPI wheels
`langgraph_api-0.15.2-py3-none-any.whl` (sha256 `dda39356…943d`, Elastic
License 2.0) and `langgraph_runtime_inmem-0.35.2-py3-none-any.whl` (sha256
`bc6133fe…5557`, Elastic-2.0), so those citations are wheel paths, not
links.

No default path under the home: a grep of `libs/` for `expanduser`,
`Path.home`, `platformdirs`, `appdirs`, `XDG`, `APPDATA` finds nothing
outside tests, and neither wheel has `expanduser` or `Path.home`.
`InMemorySaver` is the default checkpointer
([checkpoint/memory/\_\_init\_\_.py:34](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/checkpoint/langgraph/checkpoint/memory/__init__.py#L34)),
and `SqliteSaver.from_conn_string(conn_string)` takes a caller-supplied
path
([checkpoint/sqlite/\_\_init\_\_.py:104](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py#L104)).

`langgraph dev` writes `.langgraph_api/` in its working directory (the
project), holding pickled `PersistentDict` files
([checkpoint/memory/\_\_init\_\_.py:637](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/checkpoint/langgraph/checkpoint/memory/__init__.py#L637)):
`.langgraph_checkpoint.<n>.pckl`, thread checkpoints
(`langgraph_runtime_inmem/checkpoint.py:59-70`); `.langgraph_ops.pckl`,
runs, threads, assistants and crons (`database.py:82-100`, `165-166`);
`.langgraph_retry_counter.pckl` (`database.py:100`); and `store.pckl`,
`store.vectors.pckl`, the long-term store (`store.py:83-85`). They are
pickles, which the analyzer must never unpickle.

`langgraph up` writes a compose file with a `langgraph-postgres`
(pgvector pg16) service mounting `langgraph-data:/var/lib/postgresql/data`,
unless `--postgres-uri` is given
([docker.py:207-209](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/cli/langgraph_cli/docker.py#L207-L209),
[233-242](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/cli/langgraph_cli/docker.py#L233-L242),
[296-298](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/cli/langgraph_cli/docker.py#L296-L298)).
Compose runs with `--project-directory <config dir>` and no `-p`
([cli.py:961-968](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/cli/langgraph_cli/cli.py#L961-L968)),
so the volume is `<dirname>_langgraph-data`; the prefix comes from
Compose's documented default, not from this source. It holds a raw
PostgreSQL cluster. No credentials are written; the default PostgreSQL
password is the literal `postgres` (`docker.py:239`). LangGraph Studio is a
web UI on smith.langchain.com in this version. LangGraph executes only
user-supplied tools, through `ToolNode`
([prebuilt/tool_node.py:622](https://github.com/langchain-ai/langgraph/blob/39c523eb0af1d192f739fd2b7ddfea38f3002a2a/libs/prebuilt/langgraph/prebuilt/tool_node.py#L622)).

**No catalog line:** state is in memory, at an application-chosen path,
or in the project directory, and nothing records LangGraph project paths
for discovery. A `PROJECT_CATALOG` line `.langgraph_api` would only help
when another agent's state names the project, and a `*_langgraph-data`
volume line would collect a PostgreSQL cluster the analyzer cannot parse;
both are manual steps in [coverage.md](../docs/coverage.md) instead.
Confidence high (source and wheels); the source repository for
`langgraph-api` and `langgraph-runtime-inmem` was not found.

## Pydantic AI library

pydantic/pydantic-ai at
[`0ba01f92be3fc361f89970502cd6e7dd3611aec3`](https://github.com/pydantic/pydantic-ai/commit/0ba01f92be3fc361f89970502cd6e7dd3611aec3),
MIT. The `clai` and CLAI 2.0 CLIs are in the catalog as `pydantic-clai`;
see [pydantic-clai.md](pydantic-clai.md). The library itself has no
default path under the home: a grep of `pydantic_ai_slim`,
`pydantic_graph` and `pydantic_evals` for `expanduser`, `Path.home`, `XDG`
and `platformdirs` finds only the CLI and a user-supplied workspace
directory
([workspaces/local.py:126](https://github.com/pydantic/pydantic-ai/blob/0ba01f92be3fc361f89970502cd6e7dd3611aec3/pydantic_ai_slim/pydantic_ai/workspaces/local.py#L126)).
Message history is returned to the caller.

## Logfire

pydantic/logfire at
[`bae9db2c9926bdde91feae92ba9f423ebe95ed55`](https://github.com/pydantic/logfire/commit/bae9db2c9926bdde91feae92ba9f423ebe95ed55),
MIT, the observability SDK that Pydantic AI integrates with. `logfire
auth` writes user tokens to `~/.logfire/default.toml`
([auth.py:22-25](https://github.com/pydantic/logfire/blob/bae9db2c9926bdde91feae92ba9f423ebe95ed55/logfire-sdk/logfire/_internal/auth.py#L22-L25)),
and project credentials go to `./.logfire/logfire_credentials.json` in the
working directory
([config.py:144](https://github.com/pydantic/logfire/blob/bae9db2c9926bdde91feae92ba9f423ebe95ed55/logfire-sdk/logfire/_internal/config.py#L144),
[cli/\_\_init\_\_.py:710](https://github.com/pydantic/logfire/blob/bae9db2c9926bdde91feae92ba9f423ebe95ed55/logfire-sdk/logfire/_internal/cli/__init__.py#L710)).

**No catalog line:** Logfire is an observability SDK, not an agent; it
executes no tools. CLAI 2.0's own Logfire token is flagged inside the
`pydantic-clai` entry.

## Atomic Agents

BrainBlend-AI/atomic-agents at
[`d2b61b90b2816dbdf9f42f8638b7d375bf08cd11`](https://github.com/BrainBlend-AI/atomic-agents/commit/d2b61b90b2816dbdf9f42f8638b7d375bf08cd11)
(2026-10-04), `atomic-agents` 2.10.3, MIT. The library, the
`atomic-assembler` TUI, `atomic-forge` tools, and a Claude Code plugin that
installs into Claude Code's own directory, which is already collected.

A grep of the whole tree for `Path.home`, `expanduser`, `platformdirs`,
`appdirs`, `XDG`, `APPDATA` finds only an example application
(`atomic-examples/fastapi-memory`, `~/.fastapi_memory_user_id`) and a
caller-supplied path in the PDF tool. Chat history is in memory and
serialized only to a string the caller stores
([chat_history.py:253](https://github.com/BrainBlend-AI/atomic-agents/blob/d2b61b90b2816dbdf9f42f8638b7d375bf08cd11/atomic-agents/atomic_agents/context/chat_history.py#L253)).
The assembler clones the tool repository into `tempfile.mkdtemp()`
([utils.py:15](https://github.com/BrainBlend-AI/atomic-agents/blob/d2b61b90b2816dbdf9f42f8638b7d375bf08cd11/atomic-assembler/atomic_assembler/utils.py#L15))
and logs to `./atomic_assembler.log` only with logging enabled
([main.py:7-15](https://github.com/BrainBlend-AI/atomic-agents/blob/d2b61b90b2816dbdf9f42f8638b7d375bf08cd11/atomic-assembler/atomic_assembler/main.py#L7-L15)).
No credentials on disk, no Docker volumes. Neither the library nor the
forge tools execute shell commands (a grep for `subprocess` and
`os.system` in `atomic_agents/`, `atomic-assembler/` and
`atomic-forge/tools/` finds nothing); applications may add such tools.

**No catalog line:** no state of its own under the home. Confidence high.

## IntentKit

crestalnetwork/intentkit at
[`afc8cc44255210db6352f7437e569ed8b88ed5e1`](https://github.com/crestalnetwork/intentkit/commit/afc8cc44255210db6352f7437e569ed8b88ed5e1)
(2026-09-16), MIT. A self-hosted "cloud agent cluster" (FastAPI,
PostgreSQL, Redis, RustFS) with crypto, social and web tools.

No default path under the home: a grep for `Path.home`, `expanduser`,
`platformdirs`, `XDG`, `APPDATA` in `intentkit/`, `app/`, `integrations/`
and `scripts/` finds nothing. State lives in PostgreSQL, with in-memory
SQLite only as an import fallback
([db.py:100-106](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/intentkit/config/db.py#L100-L106));
secrets (`CDP_WALLET_SECRET`, `master_wallet_private_key`, Privy keys) come
from `.env` in the repository checkout
([config.py:27-28](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/intentkit/config/config.py#L27-L28),
[120-148](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/intentkit/config/config.py#L120-L148)).

Docker named volumes: `postgres_data` at `/var/lib/postgresql`,
`rustfs_data` at `/data` and `redis_data` at `/data`
([docker-compose.yml:1-46](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/docker-compose.yml#L1-L46));
the production compose adds `caddy_data` and `caddy_config`
([deployment/docker-compose.yml:1-6](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/deployment/docker-compose.yml#L1-L6)).
Compose prefixes them with the project directory name (for example
`intentkit_postgres_data`). The suffixes are generic and the content is a
raw database cluster and object storage, so only a project-prefixed glob
would be safe, and the analyzer could not read it.

IntentKit does not execute on the host: there is no `subprocess` in
`intentkit/` or `app/`, MCP is SSE or streamable HTTP only
([client.py:13-14](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/intentkit/clients/mcp/client.py#L13-L14),
[69-73](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/intentkit/clients/mcp/client.py#L69-L73)),
and the README says "Agents are fundamentally unable to access any of your
secret keys"
([README.md:30](https://github.com/crestalnetwork/intentkit/blob/afc8cc44255210db6352f7437e569ed8b88ed5e1/README.md#L30)).
It does act on-chain and on social accounts.

**No catalog line:** it fails the catalog criterion (no tool or shell
execution on the host) and has no state under the home; its volumes hold
a PostgreSQL cluster. The volumes are noted as a manual step in
[coverage.md](../docs/coverage.md). Confidence high for paths and volumes;
medium for "no host execution", which is grep-based (more than 60 tool
packages were not read one by one).
