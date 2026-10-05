# ShellGPT: on-disk paths

Catalog agent: `shellgpt`. ShellGPT (`sgpt`) is a Python command-line client
for OpenAI-compatible chat APIs. It answers one-shot prompts, generates shell
commands that the user can execute from a prompt, keeps named chat and REPL
sessions, and can let the model run shell commands through a "function"
plug-in. Its configuration lives under the home, but its chat history lives in
the system temporary directory. Transcript schema is in
[`analyzer/research/shellgpt.md`](../../analyzer/research/shellgpt.md).

## 1. Source and evidence level

TheR1D/shell_gpt, MIT, open source, commit
[`a082bd5327ce0c4ef5a0284d9060e833be9444a6`](https://github.com/TheR1D/shell_gpt/commit/a082bd5327ce0c4ef5a0284d9060e833be9444a6)
(2026-07-02), version 1.5.1
([`sgpt/__version__.py:1`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/__version__.py#L1)).
All claims from source. The older temp-directory layout is cited from the
history commits [`1465c4a`](https://github.com/TheR1D/shell_gpt/commit/1465c4af12ad313bd4948cf6434de06c6ca4e087)
(first in tag 0.7.3) and [`a054a90`](https://github.com/TheR1D/shell_gpt/commit/a054a900958954400004e54bc7739ba94a75de1f)
(first in tag 0.9.0).

## 2. Per-user storage

The config folder is `os.path.expanduser("~/.config")/shell_gpt` on every OS,
Windows included: there is no platform branch and no `XDG_CONFIG_HOME`
support ([`sgpt/config.py:9-13`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L9-L13)).
So Windows hosts have `C:\Users\<u>\.config\shell_gpt`, and macOS uses
`~/.config`, not `Library`.

- `~/.config/shell_gpt/.sgptrc`: `KEY=value` lines, one per setting
  ([`config.py:75-87`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L75-L87)).
  On first run every default in `DEFAULT_CONFIG` is written out, and keys
  added in later versions are appended to an existing file
  ([`config.py:18-46`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L18-L46),
  [`53-69`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L53-L69)).
  An environment variable of the same name overrides the file
  ([`config.py:89-94`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L89-L94)).
- `~/.config/shell_gpt/roles/<name>.json`: system roles, JSON with `name`
  and `role` ([`role.py:142-153`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/role.py#L142-L153)).
  Four defaults are created (`ShellGPT`, `Shell Command Generator`,
  `Shell Command Descriptor`, `Code Generator`;
  [`role.py:63-73`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/role.py#L63-L73));
  others come from `--create-role`. Overridable with `ROLE_STORAGE_PATH`
  ([`config.py:28`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L28)).
- `~/.config/shell_gpt/functions/*.py`: the function store, overridable with
  `OPENAI_FUNCTIONS_PATH` ([`config.py:32`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L32)).
  Every `.py` file here is imported and executed on every `sgpt` start
  ([`function.py:31-36`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/function.py#L31-L36),
  [`54-56`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/function.py#L54-L56)).
  `--install-functions` copies in `execute_shell.py`, which runs any command
  the model asks for with `shell=True`
  ([`llm_functions/init_functions.py:13-35`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/llm_functions/init_functions.py#L13-L35);
  [`common/execute_shell.py:18-25`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/llm_functions/common/execute_shell.py#L18-L25)).
  A file planted here is a code-execution and persistence point.

Chat history is **not under the home**. `CHAT_CACHE_PATH` defaults to
`tempfile.gettempdir()/chat_cache` and the response cache `CACHE_PATH` to
`gettempdir()/cache` ([`config.py:14-15`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L14-L15),
[`20-21`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L20-L21)).
That resolves to `/tmp/chat_cache` on Linux, `$TMPDIR/chat_cache`
(`/var/folders/.../T/`) on macOS and `%TEMP%\chat_cache`
(`AppData\Local\Temp\chat_cache`) on Windows. Before 0.9.0 the defaults were
`gettempdir()/shell_gpt/chat_cache` and `gettempdir()/shell_gpt/cache`
([`1465c4a config.py:10-11`](https://github.com/TheR1D/shell_gpt/blob/1465c4af12ad313bd4948cf6434de06c6ca4e087/sgpt/config.py#L10-L11));
0.9.0 dropped the `shell_gpt` level
([`a054a90 config.py:15-16`](https://github.com/TheR1D/shell_gpt/blob/a054a900958954400004e54bc7739ba94a75de1f/sgpt/config.py#L15-L16)).
Because `.sgptrc` freezes the value written at first run and only appends
missing keys, a user who installed before 0.9.0 still writes to
`/tmp/shell_gpt/chat_cache`; the current README also shows that form
([`README.md:368-373`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/README.md#L368-L373)).
The official Docker image mounts a volume at `/tmp/shell_gpt`
([`Dockerfile:12-14`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/Dockerfile#L12-L14)).
**Read `CHAT_CACHE_PATH` and `CACHE_PATH` from `.sgptrc` to find the real
location.**

- `<chat cache>/<chat id>`: one JSON file per `--chat` or `--repl` session,
  named exactly as the user typed the id, no extension
  ([`chat_handler.py:65-78`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L65-L78)).
  The id `temp` is deleted at the start of each use
  ([`chat_handler.py:106-108`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L106-L108)).
- `<cache>/<md5>`: one file per cached one-shot completion holding only the
  response text; the name is an MD5 of the request arguments, so the prompt
  is not recoverable from it. The oldest files beyond `CACHE_LENGTH` (100)
  are deleted ([`cache.py:30-61`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/cache.py#L30-L61)).
  Caching is on by default ([`app.py:88-91`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/app.py#L88-L91)).

One-shot prompts without `--chat` are not stored anywhere except as that
response cache ([`app.py:222-239`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/app.py#L222-L239);
[`default_handler.py:17-22`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/default_handler.py#L17-L22)).
The interactive `[E]xecute` prompt uses an in-memory `PromptSession` with no
history file ([`app.py:241`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/app.py#L241)).
The command line itself lands in the shell history, which the collector
leaves to the EDR.

`--install-integration` appends a `Shell-GPT integration` block binding
Ctrl+L to `sgpt --shell` to `~/.zshrc` or `~/.bashrc`
([`utils.py:66-87`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/utils.py#L66-L87);
[`integration.py:1-27`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/integration.py#L1-L27)).

Environment variables: `OPENAI_API_KEY`, `API_BASE_URL`, `CHAT_CACHE_PATH`,
`CACHE_PATH`, `ROLE_STORAGE_PATH`, `OPENAI_FUNCTIONS_PATH`, `USE_LITELLM`,
`DEFAULT_MODEL` and the rest of `DEFAULT_CONFIG`.

## 3. Credentials

- `~/.config/shell_gpt/.sgptrc`: `OPENAI_API_KEY=<key>` in plain text. On
  first run sgpt prompts for the key and writes it, unless `OPENAI_API_KEY`
  is already in the environment
  ([`config.py:63-69`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L63-L69);
  [`README.md:10`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/README.md#L10)).
  The key is passed to whichever backend `API_BASE_URL` names
  ([`handler.py:15-21`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L15-L21)),
  so `API_BASE_URL` identifies the provider or proxy. No keychain use.
- With `USE_LITELLM=true` other providers' keys come from their own
  environment variables; nothing extra is written by sgpt.

## 4. Exclusions

Nothing large. The function store and roles are a few KB. The response cache
is capped at 100 files by default.

## 5. Project-local files

None. ShellGPT reads nothing from the working directory and records no
project.

## 6. Where the project path is recorded

Nowhere: chat files carry no working directory. For discovery of the
history location rather than projects, `.sgptrc` keys `CHAT_CACHE_PATH`,
`CACHE_PATH`, `ROLE_STORAGE_PATH` and `OPENAI_FUNCTIONS_PATH` hold absolute
paths that may point outside the defaults.

## 7. Confidence

High: config folder, `.sgptrc` format and key, roles, function store, chat
and cache layout, the 0.9.0 change of temp path (source and history).
Medium: that `/tmp` is the effective Linux location; `gettempdir` honours
`TMPDIR`, `TEMP` and `TMP`, so a user with any of those set writes
elsewhere. Not determined: how long the chat files survive. `/tmp` is a
tmpfs cleared at boot on many distributions and macOS purges old
`/var/folders` content, but this depends on the host and was not checked.
