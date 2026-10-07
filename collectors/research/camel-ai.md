# CAMEL: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document: CAMEL keeps no transcripts under the home.

## 1. Source and evidence level

camel-ai/camel, Apache-2.0, open source, commit
[`24fde60ad739b4be8f8f533fea9ba54256fbc4a2`](https://github.com/camel-ai/camel/commit/24fde60ad739b4be8f8f533fea9ba54256fbc4a2)
(2026-10-05), package `camel-ai` 0.2.91a7. A multi-agent framework with
toolkits for the terminal, browser, Gmail and files. All claims are from
source; nothing was installed or run.

CAMEL runs shell commands on the host: the terminal toolkit's `shell_exec`
uses `subprocess.Popen`
([terminal_toolkit.py:757](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/terminal_toolkit/terminal_toolkit.py#L757),
[838](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/terminal_toolkit/terminal_toolkit.py#L838)).

## 2. Per-user storage

| Path (home-relative, all OSes) | Holds | Default or opt-in |
| --- | --- | --- |
| `.camel/gmail_token.json` | Google OAuth token and refresh token, mode 0600 ([gmail_toolkit.py:1316](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/gmail_toolkit.py#L1316), [1390-1402](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/gmail_toolkit.py#L1390-L1402)) | default when `GmailToolkit` is used |
| `.camel/skills`, `.config/camel/skills` | user-scope skills, read ([skill_toolkit.py:201-209](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/skill_toolkit.py#L201-L209)) | read by default by `SkillToolkit` |
| `.camel/runtimes/{go,java}` | downloaded Go and JDK toolchains ([runtime_utils.py:57](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/terminal_toolkit/runtime_utils.py#L57), [terminal_toolkit.py:457-466](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/terminal_toolkit/terminal_toolkit.py#L457-L466)) | default when the terminal toolkit needs them; not collected |

Everything else is relative to the working directory: `./workspace` for
the terminal toolkit
([terminal_toolkit.py:188-195](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/terminal_toolkit/terminal_toolkit.py#L188-L195)),
`./camel_working_dir` for the file toolkits
([file_toolkit.py:69-73](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/toolkits/file_toolkit.py#L69-L73)),
`./chat_history.json` for `JsonStorage`
([json.py:71-73](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/storages/key_value_storages/json.py#L71-L73)),
and `camel_logs` model logs only with `CAMEL_MODEL_LOG_ENABLED`
([base_model.py:287-295](https://github.com/camel-ai/camel/blob/24fde60ad739b4be8f8f533fea9ba54256fbc4a2/camel/models/base_model.py#L287-L295)).
The browser `user_data_dir` is supplied by the caller.

**Name collision.** Apache Camel JBang also uses `~/.camel`
(`CAMEL_DIR = ".camel"` resolved under the home,
[CommandLineHelper.java:44](https://github.com/apache/camel/blob/43fb0300bd10fa74ef37f3eca82d20678b6d3350/dsl/camel-jbang/camel-jbang-core/src/main/java/org/apache/camel/dsl/jbang/core/common/CommandLineHelper.java#L44),
[221-222](https://github.com/apache/camel/blob/43fb0300bd10fa74ef37f3eca82d20678b6d3350/dsl/camel-jbang/camel-jbang-core/src/main/java/org/apache/camel/dsl/jbang/core/common/CommandLineHelper.java#L221-L222)),
so a bare `.camel` entry would collect JBang's state as `camel-ai`. The
catalog names only `.camel/gmail_token.json` and `.camel/skills`, plus the
CAMEL-only `.config/camel`.

Docker: no compose file or named volume.

## 3. Credentials

- `.camel/gmail_token.json`: flagged.

## 4. Exclusions

`.camel/runtimes` would need one only if `.camel` were collected whole; it
is not, so none.

## 5. Project-local files

The working-directory files in section 2 (`workspace/`,
`camel_working_dir/`, `chat_history.json`) are created wherever the
application runs, under no CAMEL-specific name, so they are not project
catalog entries.

## 6. Where the project path is recorded

Nowhere under the home.

## 7. Confidence

High for every path (source). The catalog lines are of low value apart
from the OAuth token, which shows that a Google account was granted to a
CAMEL agent.
