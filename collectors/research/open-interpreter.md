# Open Interpreter: on-disk paths

How the transcripts are encoded and how the parser reads them is in
[`analyzer/research/open-interpreter.md`](../../analyzer/research/open-interpreter.md).

## 1. Source and evidence level

openinterpreter/openinterpreter (the old `open-interpreter` URL redirects
there), Apache-2.0, open source, commit
[`2767e5f20d6927500b8f1938c773c61afb823245`](https://github.com/openinterpreter/openinterpreter/commit/2767e5f20d6927500b8f1938c773c61afb823245)
(2026-10-02). All claims are from source. Paths below are relative to
`codex-rs/` unless they start with another top-level directory.

The current Open Interpreter is a Rust fork of OpenAI Codex CLI, not the
Python tool of 2023-2025: "Open Interpreter is a fork of OpenAI's Codex"
([`README.md:46`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/README.md#L46)), and it keeps Codex crate names, protocol
names and file names on purpose
([`FORK_BRANDING.md:3-6`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/FORK_BRANDING.md#L3-L6), [`67-78`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/FORK_BRANDING.md#L67-L78)). The layout under the
home directory is therefore the Codex layout described in
[codex-cli.md](codex-cli.md), moved to a different directory. The current
source contains no reference to the Python-era paths (`platformdirs`
`open-interpreter` config, `profiles/*.yaml`, `conversations/*.json`); a
grep of the tree for them finds nothing, so they are out of scope here.

## 2. Per-user storage

Home resolution
([`utils/home-dir/src/lib.rs:5-36`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/utils/home-dir/src/lib.rs#L5-L36), [`67-90`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/utils/home-dir/src/lib.rs#L67-L90)): when the running
product is Open Interpreter, `INTERPRETER_HOME` if set (must exist), else
`dirs::home_dir()/.openinterpreter`. `CODEX_HOME` is deliberately ignored "so
the two products stay isolated". No OS branching: `~/.openinterpreter` on
Linux and macOS, `%USERPROFILE%\.openinterpreter` on Windows. The product is
chosen by `codex-package.json` `variant: "open-interpreter"` next to the
binary, or an executable named `interpreter*` or `i`
([`product-info/src/lib.rs:180-218`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/product-info/src/lib.rs#L180-L218)). The installers default to the
same directory and, unlike the runtime, fall back to `CODEX_HOME`
([`scripts/install/install.sh:15-22`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/scripts/install/install.sh#L15-L22),
[`install.ps1:922-930`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/scripts/install/install.ps1#L922-L930)).

Inside `~/.openinterpreter`, the same names as Codex:

- `sessions/YYYY/MM/DD/rollout-<timestamp>-<thread uuid>.jsonl` and
  `archived_sessions/` ([`rollout/src/lib.rs:84-85`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/lib.rs#L84-L85),
  [`rollout/src/rollout_file_name.rs:67`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/rollout_file_name.rs#L67)); rollouts may be
  zstd-compressed `.jsonl.zst` ([`rollout/src/compression.rs:25`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/compression.rs#L25),[`64`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/compression.rs#L64)).
- `session_index.jsonl` thread names ([`rollout/src/session_index.rs:21`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rollout/src/session_index.rs#L21)).
- `history.jsonl` prompt history ([`message-history/src/lib.rs:52`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L52),[`86`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/message-history/src/lib.rs#L86)).
- SQLite: `logs_2.sqlite`, `goals_1.sqlite`, `memories_1.sqlite`,
  `queue_1.sqlite`, `state_5.sqlite`, `thread_history_1.sqlite`
  ([`state/src/sqlite.rs:29-34`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/state/src/sqlite.rs#L29-L34)).
- `config.toml`, which also carries the fork's `harness` and
  `harness_guidance` keys ([`config/src/config_toml.rs:166-170`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/config/src/config_toml.rs#L166-L170)); `log/`
  ([`core/src/config/mod.rs:4009`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/config/mod.rs#L4009)) with `codex-tui.log`
  ([`tui/src/lib.rs:273`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/tui/src/lib.rs#L273)); `shell_snapshots/`
  ([`core/src/shell_snapshot.rs:106`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/shell_snapshot.rs#L106)); `memories/`, `memories_v2/`
  ([`protocol/src/memory_version.rs:17-22`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/memory_version.rs#L17-L22)); `installation_id`
  ([`core/src/installation_id.rs:17`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/installation_id.rs#L17)); `rules/`
  ([`core/src/exec_policy.rs:54`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/exec_policy.rs#L54)); `version.json`
  ([`cli/src/doctor/updates.rs:36`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/cli/src/doctor/updates.rs#L36)); `models-cache/<provider>/`
  ([`app-server/src/models.rs:36`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/app-server/src/models.rs#L36)); `app-server-daemon/` and
  `packages/` ([`app-server-daemon/src/managed_install.rs:22-28`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/app-server-daemon/src/managed_install.rs#L22-L28),[`53`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/app-server-daemon/src/managed_install.rs#L53)).
- Fork additions:
  - `external_agent_session_imports.json`, the ledger of chats imported by
    `/import` ([`external-agent-sessions/src/ledger.rs:15`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/ledger.rs#L15),[`193`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/ledger.rs#L193)) with
    `source_path`, `content_sha256`, `imported_thread_id`, `imported_at`
    ([`ledger.rs:24-30`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/ledger.rs#L24-L30)). Import reads `~/.claude` and `~/.cursor`
    ([`external-agent-migration/src/source/cla.rs:20`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-migration/src/source/cla.rs#L20),
    [`source/cur.rs:19`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-migration/src/source/cur.rs#L19)) and writes the result as ordinary
    rollout items ([`external-agent-sessions/src/export.rs:58-73`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-sessions/src/export.rs#L58-L73)).
  - `.zcode/` (zcode harness emulation): `.zcode/cli/artifacts/sess_<id>/<call>-tool-result-<uuid>.json`
    for tool output too long to inline
    ([`core/src/tools/handlers/harness_aliases.rs:887-902`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L887-L902)),
    `.zcode/oi-current-file-hashes/` and `.zcode/oi-todos/<session>.json`
    ([`harness_aliases.rs:78-79`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L78-L79),[`2520-2523`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L2520-L2523)). The
    hash and todo caches go under `OPEN_INTERPRETER_HOME`,
    `INTERPRETER_HOME` or `CODEX_HOME` only when one is set
    ([`harness_aliases.rs:1460-1465`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L1460-L1465)), so on a default install
    only the artifacts directory is written.
  - Windows sandbox `.sandbox/`, `.sandbox-bin/`, `.sandbox-secrets/` as in
    Codex ([`windows-sandbox-rs/src/uninstall_windows.rs:106-111`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/windows-sandbox-rs/src/uninstall_windows.rs#L106-L111)).

Executables are installed to `~/.local/bin` and
`%LOCALAPPDATA%\Programs\Open Interpreter\bin` (installers, lines cited
above and [`install.ps1:941`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/scripts/install/install.ps1#L941)); the package itself lands in
`~/.openinterpreter/packages/standalone`.

## 3. Credentials

- `auth.json`: OpenAI API key and ChatGPT OAuth tokens
  ([`login/src/auth/storage.rs:155`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/auth/storage.rs#L155)); store mode `file` (default),
  `keyring`, `auto` or `ephemeral` ([`config/src/types.rs:114-124`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/config/src/types.rs#L114-L124)).
- `credentials/kimi-code.json` (Kimi Code OAuth `access_token`,
  `refresh_token`) and `device_id`, fork-only, always files
  ([`login/src/kimi_code.rs:22-24`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/kimi_code.rs#L22-L24),[`39-40`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/kimi_code.rs#L39-L40),[`243-253`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/kimi_code.rs#L243-L253)).
- `.credentials.json`: MCP OAuth fallback when no keyring
  ([`rmcp-client/src/oauth.rs:815`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/rmcp-client/src/oauth.rs#L815)).
- `secrets/` with age-encrypted `local.age`, `gateway_oauth.age` and
  `gateway_oauth.lock`, the same module also names `codex_auth.age` and `mcp_oauth.age` ([`secrets/src/local.rs:41-44`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/secrets/src/local.rs#L41-L44),[`154`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/secrets/src/local.rs#L154);
  [`login/src/gateway_auth_storage.rs:20-24`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/login/src/gateway_auth_storage.rs#L20-L24)).
- `.env` in the home is loaded into the process environment at start, minus
  `CODEX_*` names ([`arg0/src/lib.rs:300-312`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/arg0/src/lib.rs#L300-L312)); it is the obvious place
  for provider API keys. The Codex catalog does not flag `.codex/.env`
  either.
- `config.toml` can embed `experimental_bearer_token` per provider
  ([`model-provider-info/src/lib.rs:171`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/model-provider-info/src/lib.rs#L171)).
- `.sandbox-secrets/` on Windows, as in Codex.

## 4. Exclusions

Same as Codex: `packages/` (managed binaries), `cache/`, `.tmp/`, `tmp/`,
`plugins/cache` ([`core-plugins/src/store.rs:26`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core-plugins/src/store.rs#L26)), `skills/.system`
([`skills/src/lib.rs:57`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/skills/src/lib.rs#L57)), `worktrees/`
([`worktree/src/settings.rs:44`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/worktree/src/settings.rs#L44)), `visualizations/`
([`tui/src/inline_visualization.rs:92`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/tui/src/inline_visualization.rs#L92)), `.sandbox`, `.sandbox-bin`,
plus the fork's `models-cache/`. `.zcode/cli/plugins/cache` is only referenced
as a display path for the emulated skill ([`harness_aliases.rs:2853-2858`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/tools/handlers/harness_aliases.rs#L2853-L2858));
nothing writes it. Keep `.zcode/cli/artifacts`: it holds full tool output.

## 5. Project-local files

- `.openinterpreter/` per project replaces `.codex/` (config, hooks,
  rules) ([`config/src/loader/mod.rs:1121-1126`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/config/src/loader/mod.rs#L1121-L1126)). The `/import` repository scope
  still writes `<repo>/.codex/config.toml`, `.codex/agents`, `.codex/hooks.json`
  ([`external-agent-migration/src/service.rs:560`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-migration/src/service.rs#L560),[`651`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-migration/src/service.rs#L651),[`664`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/external-agent-migration/src/service.rs#L664)).
- `AGENTS.md` and `AGENTS.override.md` ([`core/src/agents_md.rs:43-45`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/agents_md.rs#L43-L45)).
- Harness emulation reads other agents' project files: `.kimi/AGENTS.md`,
  `.kimi/skills`, `.claude/skills`, `.codex/skills`, `.agents/skills`
  ([`core/src/harness/kimi_cli.rs:956`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/harness/kimi_cli.rs#L956),[`1127-1133`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/harness/kimi_cli.rs#L1127-L1133)), and writes
  `.codewhale/instructions.md` in the cwd under the DeepSeek harness
  ([`core/src/harness/deepseek_tui.rs:559-568`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/harness/deepseek_tui.rs#L559-L568)).
- The Terminus-2 harness keeps tmux buffers in
  `${INTERPRETER_HOME:-${CODEX_HOME:-$PWD}}/.terminus-2`
  ([`core/src/harness/terminus_2.rs:1060-1063`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/core/src/harness/terminus_2.rs#L1060-L1063)), so in the project
  directory when neither variable reaches the tool shell.
- No per-project database.

## 6. Where the project path is recorded

As in Codex: `session_meta` first line of every rollout, `payload.cwd`
([`protocol/src/protocol.rs:3117-3141`](https://github.com/openinterpreter/openinterpreter/blob/2767e5f20d6927500b8f1938c773c61afb823245/codex-rs/protocol/src/protocol.rs#L3117-L3141)), and the threads table in
`state_5.sqlite`. The existing Codex discovery (`grep -ho '"cwd":"[^"]*"'`
over `sessions/**/*.jsonl`) applies unchanged with `.openinterpreter` in
place of `.codex`; `.jsonl.zst` rollouts need zstd first.

## 7. Confidence

High: home resolution, `CODEX_HOME` being ignored, every file name in
sections 2-3 (constants in the cited files, identical to upstream Codex),
the Kimi credential file, the import ledger. Medium: `models-cache/` as an
exclusion (written per provider by the app server, contents not inspected);
`.terminus-2` landing in the project (depends on whether the env vars reach
the tool shell, not traced). Not determined: whether `device_id` is
sensitive (an identifier sent to Kimi, not a secret, flagged here for
caution); whether the desktop or IDE surfaces of Open Interpreter exist and
write elsewhere (none found in this repository); the Python-era layout,
excluded by the brief because current source no longer reads it.
