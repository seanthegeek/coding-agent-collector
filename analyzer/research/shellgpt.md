# ShellGPT transcript schema

Catalog agent: `shellgpt`. ShellGPT stores a named chat or REPL session as
the raw OpenAI `messages` array it sends to the API, one JSON file per
session, with no timestamps, model or working directory. Paths cited are
relative to the clone. Storage locations are in
[`collectors/research/shellgpt.md`](../../collectors/research/shellgpt.md).

## 1. Source

TheR1D/shell_gpt at [`a082bd5327ce0c4ef5a0284d9060e833be9444a6`](https://github.com/TheR1D/shell_gpt/commit/a082bd5327ce0c4ef5a0284d9060e833be9444a6)
(2026-07-02), version 1.5.1, MIT. Open source.

## 2. Transcript files

- `<CHAT_CACHE_PATH>/<chat id>`: one file per session started with
  `--chat <id>` or `--repl <id>`, named exactly as typed, no extension
  ([`sgpt/handlers/chat_handler.py:65-78`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L65-L78)).
  `CHAT_CACHE_PATH` defaults to `tempfile.gettempdir()/chat_cache`
  ([`sgpt/config.py:14`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L14),
  [`20`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L20)); before 0.9.0 it was
  `gettempdir()/shell_gpt/chat_cache`, and `.sgptrc` keeps whichever value
  was written at first run. Home-relative globs the catalog can reach:
  `AppData/Local/Temp/chat_cache/*` and
  `AppData/Local/Temp/shell_gpt/chat_cache/*` (Windows). On Linux and macOS
  the files are under `/tmp` or `/var/folders/*/*/T` and arrive only as
  loose input.
- The id `temp` is invalidated at each start, so it holds only the most
  recent throwaway session
  ([`chat_handler.py:106-108`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L106-L108)).
- `<CACHE_PATH>/<md5>` files hold only a response string with no prompt
  ([`sgpt/cache.py:30-41`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/cache.py#L30-L41)). Not a
  transcript; do not parse.

## 3. Record schema

The file is a single JSON array written by `json.dump` with default
settings (one line, ASCII-escaped)
([`chat_handler.py:72-78`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L72-L78)).
Each element is an OpenAI chat message:

- `{"role":"system","content":str}`: always element 0, written only when
  the session is new ([`chat_handler.py:165-170`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L165-L170)).
  The content is `"You are <role name>\n<role text>"`
  ([`sgpt/role.py:44`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/role.py#L44),
  [`role.py:150-153`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/role.py#L150-L153)); sgpt itself parses the
  role name back from the first line
  ([`role.py:106-112`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/role.py#L106-L112)).
- `{"role":"user","content":str}`: the prompt. In REPL mode the first
  prompt is prefixed with any stdin or command-line prompt separated by
  three newlines ([`repl_handler.py:53-55`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/repl_handler.py#L53-L55)).
- `{"role":"assistant","content":null,"tool_calls":[{"id","type":"function","function":{"name","arguments"}}]}`:
  a function call; `arguments` is a JSON string
  ([`sgpt/handlers/handler.py:72-84`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L72-L84)).
  Only one call per turn (`parallel_tool_calls` is false;
  [`handler.py:118-121`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L118-L121)).
- `{"role":"tool","content":str,"tool_call_id":str}`: the function's
  return value ([`handler.py:98-100`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L98-L100)).
  For the bundled `execute_shell_command` it is
  `"Exit code: <n>, Output:\n<stdout+stderr>"`
  ([`llm_functions/common/execute_shell.py:18-25`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/llm_functions/common/execute_shell.py#L18-L25)).
- `{"role":"assistant","content":str}`: the full streamed response,
  appended after the call returns
  ([`chat_handler.py:56-61`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L56-L61)).
  When a function was called it also contains the marker line
  `` > @FunctionCall `name(k="v")` `` and, with
  `SHOW_FUNCTIONS_OUTPUT=true`, the output in a fenced block
  ([`handler.py:89-95`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L89-L95)).

So a turn with a function call is stored as user, assistant(tool_calls),
tool, assistant(content), in that order, because the handler mutates the
same list the session later writes.

No timestamp, model, temperature or cwd is stored. The only time is the
file's mtime, which is the last write. The file is rewritten in full each
turn.

Truncation: on every write the system message is kept and only the last
`CHAT_CACHE_LENGTH` (default 100) other messages survive
([`chat_handler.py:75-77`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/chat_handler.py#L75-L77);
[`config.py:22`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L22)). Older turns of a long session are
gone, and a cut can separate a `tool` message from its call.

## 4. Joins

- Session to project: none recorded.
- Tool call to result: `tool_calls[0].id` equals the next `tool`
  message's `tool_call_id`.
- No subagents. Session id is the file name.

## 5. SQLite or binary stores

None.

## 6. Format versions

No version field. Function calls arrived in 1.1.0
([`20ff0f2`](https://github.com/TheR1D/shell_gpt/commit/20ff0f2eeb26ee816bfd31d2fd0d67da6f1e861f))
using the legacy `functions` API: the call was stored as
`{"role":"assistant","content":"","function_call":{"name","arguments"}}` and
the result as `{"role":"function","content":str,"name":str}`, with no call
id ([`handler.py:65-71`](https://github.com/TheR1D/shell_gpt/blob/6bd0bdebe1f321e397099e430e8ecd93beb965b6/sgpt/handlers/handler.py#L65-L71), [`83`](https://github.com/TheR1D/shell_gpt/blob/6bd0bdebe1f321e397099e430e8ecd93beb965b6/sgpt/handlers/handler.py#L83) at
`6bd0bde`, the parent of the change below). 1.5.0 switched to `tool_calls` and `tool` messages
([`4ea2f83`](https://github.com/TheR1D/shell_gpt/commit/4ea2f834cff5dc020dabb25bb02030c630cd2062),
"Migrate to OpenAI v2"). A parser must accept both: pair a `function`
message with the immediately preceding `function_call` by position. Before
1.1.0 files hold only system, user and assistant messages.

## 7. Secrets

The API key is never written into chat files; it is in `.sgptrc`
([`config.py:63-69`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/config.py#L63-L69)). Tool messages contain
raw shell output and can contain anything the commands printed.

## 8. Parser plan

Detection: any regular file directly under a `chat_cache` directory whose
content parses as a JSON array of objects with `role`.

| Column | Source |
| --- | --- |
| timestamp_utc | empty; the manifest `mtime` may be given to the last row only |
| session_id | file name |
| project_path | empty |
| git_branch | empty |
| turn_type | `user` → user; `assistant` with `content` → assistant; each `tool_calls[]` → tool_use; `tool` → tool_result; `system` → system |
| model | empty |
| tool_name | `tool_calls[].function.name` |
| tool_use_id | `tool_calls[].id` / `tool_call_id` |
| text | `content`; for tool_use, `shell_command` from the parsed `arguments` when present, else `arguments` |
| source_line | 1 for every row (single-line file); the array index can go in the text or a later column |

Fixture (`chat_cache/deploy-check`, shown wrapped; the real file is one line):

```json
[{"role": "system", "content": "You are ShellGPT\nYou are programming and system administration assistant.\nYou are managing Linux/Ubuntu 24.04 LTS operating system with bash shell.\nAPPLY MARKDOWN formatting when possible."},
 {"role": "user", "content": "what is listening on port 8080"},
 {"role": "assistant", "content": null, "tool_calls": [{"id": "call_Q1w2e3r4", "type": "function", "function": {"name": "execute_shell_command", "arguments": "{\"shell_command\": \"ss -ltnp | grep 8080\"}"}}]},
 {"role": "tool", "content": "Exit code: 0, Output:\nLISTEN 0 4096 0.0.0.0:8080 0.0.0.0:* users:((\"python3\",pid=4242,fd=3))\n", "tool_call_id": "call_Q1w2e3r4"},
 {"role": "assistant", "content": "\n> @FunctionCall `execute_shell_command(shell_command=\"ss -ltnp | grep 8080\")` \n\nA python3 process (PID 4242) is listening on 8080."}]
```

Confidence. High: file location, array shape, message keys, ordering,
truncation (source), and the leading `"\n"` before the marker, which is
always emitted because the check runs right after the assistant message is
appended
([`handler.py:86-87`](https://github.com/TheR1D/shell_gpt/blob/a082bd5327ce0c4ef5a0284d9060e833be9444a6/sgpt/handlers/handler.py#L86-L87)). Medium: the
pre-1.5.0 shape, read from the parent of `4ea2f83` in history rather than a
released package.
