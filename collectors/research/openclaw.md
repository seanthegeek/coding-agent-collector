# OpenClaw: on-disk paths

## 1. Source and evidence level

openclaw/openclaw, commit [`3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9`](https://github.com/openclaw/openclaw/commit/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9)
(2026-10-04, package version `2026.9.8`), MIT, open source, TypeScript with a
Swift macOS app. Every claim is source-level unless it cites `docs/` or
`CHANGELOG/` in the same checkout. OpenClaw was previously named Clawdbot and
then Moltbot. It runs a persistent gateway that takes messages from chat
channels (Telegram, WhatsApp, Slack, Signal, iMessage and others under
`extensions/`), runs agents with shell, browser and file tools, and keeps
per-agent sessions. Transcript schema is in `analyzer/research/openclaw.md`.

## 2. Per-user storage

Home is `$OPENCLAW_HOME`, else `HOME`, else `USERPROFILE`
([`normalization-core/src/home-dir.ts:30-31`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/normalization-core/src/home-dir.ts#L30-L31),[`50`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/packages/normalization-core/src/home-dir.ts#L50)).
The state directory is `$OPENCLAW_STATE_DIR`, else `~/.openclaw` if it
exists, else a legacy `~/.clawdbot` if that exists, else `~/.openclaw`
([`src/config/state-dir.ts:8-43`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/state-dir.ts#L8-L43)). A named profile
(`OPENCLAW_PROFILE=work`) uses `~/.openclaw-<profile>`
([`src/cli/profile-utils.ts:26-37`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/cli/profile-utils.ts#L26-L37)); remote worker machines
get `~/.openclaw-worker` ([`gateway/worker-environments/project-setup-script.ts:142`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/gateway/worker-environments/project-setup-script.ts#L142)).
There is no platform branch: the same tree is used on Linux, macOS and
Windows (`%USERPROFILE%\.openclaw`). No XDG directories except one env file
(section 3).

Contents of the state directory ([`docs/openclaw-agent-runtime.md:49-60`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/openclaw-agent-runtime.md#L49-L60)):

- `openclaw.json` config, JSON5 ([`config/paths.ts:36-37`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/paths.ts#L36-L37); [`io.read-helpers.ts:262`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/io.read-helpers.ts#L262)), with
  `.bak` rotation, `.clobbered.<ts>` and `.last-good` siblings
  ([`backup-rotation.ts:167`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/backup-rotation.ts#L167), [`io.clobber-snapshot.ts:178`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/io.clobber-snapshot.ts#L178), [`io.observe-recovery.ts:554`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/io.observe-recovery.ts#L554)). Legacy name `clawdbot.json`.
- `state/openclaw.sqlite`: shared gateway database, 133 tables
  ([`src/state/openclaw-state-schema.sql`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql)), including `audit_events` (actor,
  agent, session, tool name per action, [`:149-171`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L149-L171)), `channel_ingress_events`
  (raw inbound channel messages, [`:1301-1323`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L1301-L1323)), `exec_approvals_config` and
  `operator_approvals` ([`:401-437`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L401-L437)), `cron_jobs`, `subagent_runs`, `projects`
  and `worktrees`.
- `agents/<agentId>/agent/openclaw-agent.sqlite`: per-agent database holding
  sessions, transcripts, memory index and auth profiles
  ([`src/state/openclaw-agent-schema.sql`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql)); `agentDir` is configurable per agent
  ([`agents/agent-scope-config.ts:577-588`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/agent-scope-config.ts#L577-L588)). Also `models.json` ([`agents/models-config.ts:259`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/models-config.ts#L259)).
- `agents/<agentId>/sessions/` ([`config/sessions/paths.ts:44-54`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/paths.ts#L44-L54)): legacy `sessions.json`
  and `<sessionId>.jsonl` transcripts awaiting `doctor --fix` import, plus
  retained archives `<id>.jsonl.reset.<ts>` and `<id>.jsonl.deleted.<ts>`
  (optionally `.zst`), `<id>.checkpoint.<uuid>.jsonl`, `<id>.trajectory.jsonl`,
  and `.migrated` rollback copies ([`config/sessions/artifacts.ts:8-17`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/artifacts.ts#L8-L17),[`101-147`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/artifacts.ts#L101-L147)).
  `sessions/` at the state root is the single-agent layout of old installs.
- `workspace/` (default agent) and `workspace-<agentId>/` (others), unless
  `OPENCLAW_WORKSPACE_DIR` or config moves them
  ([`agents/workspace-default-path.ts:14-31`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/workspace-default-path.ts#L14-L31), [`agent-scope-config.ts:461-485`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/agent-scope-config.ts#L461-L485)). A
  workspace holds `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`,
  `BOOTSTRAP.md`, `MEMORY.md` ([`agents/workspace-bootstrap-policy.ts:10-36`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/workspace-bootstrap-policy.ts#L10-L36)), legacy `memory.md`
  ([`memory/root-memory-files.ts:6-8`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/memory/root-memory-files.ts#L6-L8)), `memory/` and `skills/<name>/SKILL.md`
  ([`agents/workspace.ts:208`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/workspace.ts#L208),[`234`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/workspace.ts#L234)), and is a git repository ([`workspace-git.ts:33`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/workspace-git.ts#L33)).
  These are the agent's instructions and memory and are prime evidence of
  prompt injection or persistence.
- `credentials/` (`$OPENCLAW_OAUTH_DIR` overrides, [`config/paths.ts:372-381`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/paths.ts#L372-L381)).
- `skills/` managed skills from the marketplace ([`skills/runtime/refresh-source-roots.ts:49`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/skills/runtime/refresh-source-roots.ts#L49));
  `~/.agents/skills` is also read ([`:52`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/skills/runtime/refresh-source-roots.ts#L52)). `extensions/` installed plugins
  ([`docs/cli/backup.md:649`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/backup.md#L649)).
- `logs/`: `commands.log` ([`hooks/bundled/command-logger/handler.ts:19-22`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/hooks/bundled/command-logger/handler.ts#L19-L22)),
  `config-audit.jsonl` ([`infra/state-migrations.audit-checkpoints.ts:121`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/state-migrations.audit-checkpoints.ts#L121)), and debug traces
  that hold full prompts: `raw-stream.jsonl`, `anthropic-payload.jsonl`,
  `cache-trace.jsonl` ([`embedded-agent-subscribe.raw-stream.ts:22`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/embedded-agent-subscribe.raw-stream.ts#L22), [`anthropic-payload-log.ts:88`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/anthropic-payload-log.ts#L88), [`cache-trace.ts:101`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/cache-trace.ts#L101)).
- `browser/<profile>/user-data/`: Chromium profile driven by the agent
  ([`extensions/browser/src/browser/chrome.ts:720`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/extensions/browser/src/browser/chrome.ts#L720)).
- `worktrees/` managed git worktrees ([`infra/state-migrations.doctor-discovery.ts:53`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/state-migrations.doctor-discovery.ts#L53)),
  `delivery-queue-media/` ([`config/paths.ts:367-368`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/paths.ts#L367-L368)), `cron/runs/`, `delivery-queue/`,
  `sandbox/` ([`docs/cli/backup.md:587-594`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/backup.md#L587-L594)), `service-env/` (section 3).

Outside the state directory:

- Rolling logs `openclaw[-<profile>]-YYYY-MM-DD.log` in `/tmp/openclaw` or a
  per-user `os.tmpdir()` fallback ([`logging/log-file-path.ts:43-56`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/logging/log-file-path.ts#L43-L56); [`infra/tmp-openclaw-dir.ts:4`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/tmp-openclaw-dir.ts#L4)). On Windows that is under `AppData/Local/Temp`.
- macOS app: `~/Library/Application Support/OpenClaw/databases/` chat
  transcript cache and `OpenClaw/canvas` ([`apps/macos/Sources/OpenClaw/ChatTranscriptCacheSupport.swift:121-126`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/apps/macos/Sources/OpenClaw/ChatTranscriptCacheSupport.swift#L121-L126), [`CanvasManager.swift:22-25`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/apps/macos/Sources/OpenClaw/CanvasManager.swift#L22-L25)).
- Persistence: `~/Library/LaunchAgents/ai.openclaw.gateway.plist` and
  `ai.openclaw.node.plist`, systemd user units `~/.config/systemd/user/openclaw-gateway.service`
  (legacy `clawdbot-gateway`), Windows scheduled task `OpenClaw Gateway` running
  `<state>/gateway.cmd` ([`daemon/constants.ts:5-7`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/constants.ts#L5-L7),[`29-35`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/constants.ts#L29-L35); [`launchd-service-files.ts:48`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/launchd-service-files.ts#L48); [`systemd-service-files.ts:52`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/systemd-service-files.ts#L52); [`daemon/paths.ts:52-63`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/paths.ts#L52-L63)).

**Legacy names.** `~/.clawdbot` is still read and `doctor --fix` renames it to
`~/.openclaw`, leaving `~/.clawdbot` as a symlink (Windows junction) to the new
directory ([`infra/state-migrations.state-dir.ts:186`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/state-migrations.state-dir.ts#L186),[`206`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/state-migrations.state-dir.ts#L206),[`447-459`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/state-migrations.state-dir.ts#L447-L459)). `~/.moltbot` and
`moltbot.json` detection was removed ([`CHANGELOG/2026.2.13.md:119`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/CHANGELOG/2026.2.13.md#L119), [`CHANGELOG/2026.3.22.md:13`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/CHANGELOG/2026.3.22.md#L13)),
so a `~/.moltbot` on an old host is orphaned state that the current tool
ignores. `CLAWDBOT_*` and `MOLTBOT_*` environment variables are ignored
([`gateway/env-deprecation.ts:7`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/gateway/env-deprecation.ts#L7)).

## 3. Credentials

- `agents/*/agent/openclaw-agent.sqlite` tables `auth_profile_store` and
  `auth_profile_state` hold provider API keys and OAuth tokens
  ([`state/secret-state-tables.ts:31-35`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/secret-state-tables.ts#L31-L35); [`openclaw-agent-schema.sql:742-752`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-agent-schema.sql#L742-L752)). The same file
  holds every transcript, so collect it unflagged and redact those tables.
- `state/openclaw.sqlite` has 18 credential-bearing tables, among them
  `device_auth_tokens`, `mcp_oauth_stores`, `secret_store_entries`,
  `worker_environment_credentials` ([`secret-state-tables.ts:2-21`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/secret-state-tables.ts#L2-L21)). Collect unflagged.
- Legacy files that `doctor --fix` imports: `agents/*/agent/auth-profiles.json`
  ([`security/audit-extra.async.ts:441`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/security/audit-extra.async.ts#L441)) and `credentials/oauth.json`
  ([`agents/auth-profiles/legacy-source-files.ts:19`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/auth-profiles/legacy-source-files.ts#L19)). `models.json` provider entries can
  carry keys that doctor migrates ([`commands/doctor-model-catalog-credentials.ts:247-255`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/commands/doctor-model-catalog-credentials.ts#L247-L255)).
- `credentials/` subtrees written by channel plugins: `whatsapp/<accountId>/`
  session keys ([`extensions/whatsapp/src/accounts.ts:81`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/extensions/whatsapp/src/accounts.ts#L81)), `matrix/`
  ([`extensions/matrix/src/storage-paths.ts:60`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/extensions/matrix/src/storage-paths.ts#L60)), `zalouser/` ([`extensions/zalouser/src/session-state.ts:41`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/extensions/zalouser/src/session-state.ts#L41)),
  browser relay secret ([`extensions/browser/src/browser/extension-relay/relay-auth.ts:29`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/extensions/browser/src/browser/extension-relay/relay-auth.ts#L29)).
- `openclaw.json` embeds `gateway.auth.token`/`password`
  ([`config/zod-schema.gateway.ts:307-309`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/zod-schema.gateway.ts#L307-L309)), channel bot tokens and provider `apiKey`
  values, plaintext or as SecretRefs. The `.bak`/`.clobbered`/`.last-good`
  copies carry the same.
- `.env` in the state directory, and `~/.config/openclaw/gateway.env` when
  the state directory is the default ([`infra/dotenv-global-core.ts:190-204`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/infra/dotenv-global-core.ts#L190-L204)).
- `service-env/<label>.env` (mode 0600) beside the macOS LaunchAgent wrapper
  holds the service secrets ([`daemon/launchd-service-files.ts:35-60`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/daemon/launchd-service-files.ts#L35-L60)).
- OpenClaw keeps its own secrets in files and SQLite, but reads Claude
  Code's macOS keychain item `Claude Code-credentials` to reuse that login
  ([`plugin-sdk/provider-auth-claude-compat.ts:13-15`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/plugin-sdk/provider-auth-claude-compat.ts#L13-L15)), so a Claude Code
  token can appear in its auth profiles.

## 4. Exclude

The backup command's own skip list is a good guide
([`docs/cli/backup.md:649-653`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/backup.md#L649-L653), [`659-663`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/docs/cli/backup.md#L659-L663)): `dev/`, `git/`, `npm/`,
`npm-runtime/`, `tmp/` and `tools/` (managed checkouts, packages, downloaded
runtimes such as signal-cli and sherpa-onnx TTS models), `extensions/*/node_modules`,
`plugin-skills/` (a symlink index), `sandbox/skills-workspaces/`, and
`agents/*/agent/**/tmp`. Add `worktrees/` (git worktrees of user repositories,
the equivalent of `.claude/worktrees`) and the Chromium cache subtrees under
`browser/*/user-data/`. Do not exclude `browser/*/user-data` as a whole: its
History and Cookies show what the agent browsed.

## 5. Project-local files

The agent workspace is the main "project". Inside user repositories OpenClaw
reads `.openclaw/worktree-setup.sh` when it creates a managed worktree
([`agents/worktrees/service-preparation.ts:329`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/agents/worktrees/service-preparation.ts#L329)) and the workspace bootstrap files
listed in section 2 when a repository is configured as a workspace. A crashed
memory migration leaves `.openclaw-repair/root-memory/` ([`root-memory-files.ts:9`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/memory/root-memory-files.ts#L9)).
No per-project database.

## 6. Where the project path is recorded

- `openclaw.json`: `agents.defaults.workspace` and `agents.entries.<id>.workspace`
  / `agentDir` ([`config/zod-schema.agents.ts:30-39`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/zod-schema.agents.ts#L30-L39); [`zod-schema.agent-defaults-base.ts:72`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/zod-schema.agent-defaults-base.ts#L72); [`zod-schema.agent-entry-base.ts:98-100`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/zod-schema.agent-entry-base.ts#L98-L100)).
  JSON5, so the key may be unquoted.
- `state/openclaw.sqlite` tables `projects.repo_root` and `worktrees.repo_root`/`path`
  ([`openclaw-state-schema.sql:1854-1870`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L1854-L1870),[`1901-1909`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/state/openclaw-state-schema.sql#L1901-L1909)): SQLite only.
- The transcript header record `{"type":"session",...,"cwd":...}` in
  `transcript_events` and in legacy `.jsonl` files
  ([`config/sessions/transcript-header.ts:20-29`](https://github.com/openclaw/openclaw/blob/3b16db73c0b5209aad2ee7c3fb5ddfb12fb208f9/src/config/sessions/transcript-header.ts#L20-L29)). Headers are short, so they are stored
  uncompressed and a byte grep of the database finds them.

## 7. Catalog proposal

```
openclaw|.openclaw
openclaw|.openclaw-*
openclaw|.clawdbot
openclaw|.moltbot
openclaw|.config/openclaw
openclaw|Library/Application Support/OpenClaw
openclaw|Library/LaunchAgents/ai.openclaw.*
openclaw|.config/systemd/user/openclaw-*
openclaw|.config/systemd/user/clawdbot-*
```

```
project|.openclaw
project|SOUL.md
project|IDENTITY.md
project|USER.md
project|TOOLS.md
project|BOOTSTRAP.md
project|MEMORY.md
```

```
.openclaw*/dev
.openclaw*/git
.openclaw*/npm
.openclaw*/npm-runtime
.openclaw*/tmp
.openclaw*/tools
.openclaw*/worktrees
.openclaw*/plugin-skills
.openclaw*/extensions/*/node_modules
.openclaw*/sandbox/skills-workspaces
.openclaw*/agents/*/agent/tmp
.openclaw*/agents/*/agent/.tmp
.openclaw*/browser/*/user-data/*/Cache
.openclaw*/browser/*/user-data/*/Code Cache
.openclaw*/browser/*/user-data/*/GPUCache
.openclaw*/browser/*/user-data/*/Service Worker
.clawdbot/tools
.clawdbot/npm
```

```
.openclaw*/openclaw.json*
.openclaw*/clawdbot.json*
.openclaw*/.env
.openclaw*/credentials/*
.openclaw*/service-env/*
.openclaw*/agents/*/agent/auth-profiles.json*
.openclaw*/agents/*/agent/models.json
.openclaw*/browser/*/user-data/*/Cookies*
.clawdbot/clawdbot.json*
.clawdbot/.env
.clawdbot/credentials/*
.moltbot/moltbot.json*
.moltbot/.env
.moltbot/credentials/*
.config/openclaw/gateway.env
```

Discovery sources:

```
.openclaw*/openclaw.json        workspace
.openclaw*/openclaw.json        agentDir
.clawdbot/clawdbot.json         workspace
```

## 8. Confidence

High: state directory resolution, profiles, legacy `.clawdbot` migration,
database file names and schemas, workspace and agentDir defaults, archive
file naming, credential tables, service names. Medium: the exclusion list
comes from the backup documentation rather than each writer; `models.json`
holding literal keys (inferred from the doctor migration);
`browser/*/user-data/*/Cache` assumes Chromium's usual `Default/` profile
layout; `.moltbot` layout assumed identical to `.clawdbot` (current source
no longer reads it). The `tmp` and `.tmp` exclusions only cover the agent
directory itself, not nested runtime homes, because catalog globs cannot
express `**`. Not determined: the Windows log location beyond `os.tmpdir()`;
what the macOS transcript cache stores; whether the iOS and Android apps keep
transcripts on the phone.
