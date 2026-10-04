# Shell history

Catalog agent: `shell-history`. Not an AI agent: the interactive shell
histories of every user, collected because they show when and how agents were
invoked (`claude`, `codex`, `agy`, `gemini`, `aider`, `ollama run`) and what
the person did between agent sessions. Evidence level: shell documentation
and the collector's own validation on Linux and Windows.

## 1. Source and evidence level

Formats below come from the shells' manuals: bash (`HISTFILE`,
`HISTTIMEFORMAT`, <https://www.gnu.org/software/bash/manual/html_node/Bash-History-Facilities.html>),
zsh (`HISTFILE`, `EXTENDED_HISTORY`, <https://zsh.sourceforge.io/Doc/Release/Options.html#History>),
fish (<https://fishshell.com/docs/current/interactive.html#history-search>),
PowerShell PSReadLine (`Get-PSReadLineOption` `HistorySavePath`,
<https://learn.microsoft.com/powershell/module/psreadline/get-psreadlineoption>).
Confirmed on the author's Linux and Windows workstation (file names only).

## 2. Per-user storage

| Shell | Path relative to home | Format |
| --- | --- | --- |
| bash | `.bash_history` | one command per line; with `HISTTIMEFORMAT` set, a `#<epoch>` comment line precedes each command |
| zsh | `.zsh_history` | one command per line; with `EXTENDED_HISTORY`, `: <epoch>:<duration>;<command>`; multi-line commands end lines with `\` |
| zsh (macOS Terminal) | `.zsh_sessions/<uuid>.history`, `.zsh_sessions/<uuid>.session` | per-terminal-session history saved by Apple's `/etc/zshrc_Apple_Terminal`; same line format |
| sh, ksh | `.sh_history`, `.history` | one command per line (ksh may write a binary-ish format with NUL separators) |
| fish | `.local/share/fish/fish_history` (XDG), legacy `.config/fish/fish_history` | YAML-like records: `- cmd: <command>`, `  when: <epoch>`, optional `  paths:` list |
| PowerShell | `AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt` (Windows); `.local/share/powershell/PSReadLine/ConsoleHost_history.txt` (PowerShell 7 on Linux and macOS) | one command per line, no timestamps; multi-line commands continue with a trailing backtick |

`HISTFILE` can relocate bash and zsh history, `fish_history` the fish file,
and PSReadLine's `HistorySavePath` the PowerShell file; the collector does
not follow those variables. Codex CLI keeps its own shell history separately
(see `codex-cli.md`), as do Gemini CLI and Qwen Code under their `tmp`
directories.

## 3. Credentials

Histories routinely contain exported API keys (`export ANTHROPIC_API_KEY=...`)
and tokens passed on command lines. They are collected unflagged because the
whole file is evidence; analysts should treat them as sensitive.

## 4. Exclusions

None. Histories are small text files.

## 5. Project-local files

None.

## 6. Project path discovery

Not applicable; the collector does not parse histories. The analyzer's
planned shell-history parser will extract `cd` targets and agent invocations
with timestamps where the shell records them.

## 7. Confidence

High for every format listed; they are documented and stable. Only bash with
`HISTTIMEFORMAT`, zsh with `EXTENDED_HISTORY` and fish carry timestamps; the
other files give order only.
