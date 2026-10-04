# Aider transcript schema

Catalog agent: `aider`. Aider writes plain-text history files into the
repository it runs in, so most of its evidence is project-level. Paths cited
are relative to the clone.

## 1. Source

Aider-AI/aider at [`5dc9490bb35f9729ef2c95d00a19ccd30c26339c`](https://github.com/Aider-AI/aider/commit/5dc9490bb35f9729ef2c95d00a19ccd30c26339c), Apache-2.0
([`LICENSE.txt`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/LICENSE.txt)). Open source. The input history format comes from the
upstream prompt_toolkit `history.py`, which is not vendored.

## 2. Transcript files

In the git root, else the cwd ([`aider/args.py:271-275`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/args.py#L271-L275)):
`.aider.chat.history.md` (markdown), `.aider.input.history` (prompt_toolkit
`FileHistory` text), `.aider.llm.history` (text; default `None`, written
only when `--llm-history-file` is set, [`args.py:295-299`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/args.py#L295-L299)). One file holds
every session in that repository, appended.

## 3. Record schema

`.aider.chat.history.md` (append-only, [`aider/io.py:1117-1136`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L1117-L1136)):

- Session header: `\n# aider chat started at YYYY-MM-DD HH:MM:SS\n\n` (local
  time, [`:335-336`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L335-L336)). The only dated line in the file.
- User prompt: `\n#### <line1>  \n#### <line2>  \n`; empty input is `####`
  followed by a blank ([`:775-789`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L775-L789)). Slash commands appear the same way
  (`#### /add foo.py`).
- Tool and system output, including `Applied edit to <path>`, `Commit <hash>
  <msg>`, errors and confirmations: `> text  \n` blockquote lines
  ([`:966-973`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L966-L973), [`:995-999`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L995-L999), [`base_coder.py:2334`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L2334), [`repo.py:313`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repo.py#L313)).
- Assistant: raw markdown with no prefix, `\n<content>\n\n` ([`:793-795`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L793-L795),
  called from [`base_coder.py:1829`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1829)), so SEARCH/REPLACE edit blocks appear
  verbatim inside fenced code. The function-call fallback writes
  `json.dumps(args)` ([`:1834`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1834)).
- Aider's own reader ([`utils.py:148-188`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/utils.py#L148-L188)): skip lines starting `# `; `> ` is
  tool output; `#### ` is user; anything else is assistant.

`.aider.input.history` (prompt_toolkit `FileHistory`, [`io.py:19`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L19),[`356`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L356),[`740`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L740);
format `prompt_toolkit/history.py:298-307`): an entry is
`\n# YYYY-MM-DD HH:MM:SS.ffffff\n` followed by one `+<line>` per input line
(local time).

`.aider.llm.history` ([`io.py:754-764`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/io.py#L754-L764)): `TO LLM YYYY-MM-DDTHH:MM:SS\n`
followed by `format_messages` output ([`utils.py:112-134`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/utils.py#L112-L134)): a `-------`
separator, then `ROLE <line>` per content line (`SYSTEM`, `USER`,
`ASSISTANT`), and `LLM RESPONSE <ts>\n` plus `ASSISTANT <line>` lines
([`base_coder.py:1793`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1793), [`:1822-1826`](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py#L1822-L1826)).

## 4. Joins

The project is the directory containing the files (the git root). There is
no session id; synthesise one per `# aider chat started at` header. Input
history timestamps join to `#### ` prompts by order and text. No model name
and no git branch are recorded.

## 5. SQLite stores

None. `.aider.tags.cache.v*` is a repository-map cache, not chat, and is
excluded by the collector.

## 6. Format versions

None; the format has not changed across sessions.

## 7. Secrets

`.aider.llm.history` contains the complete system prompt with every added
file; `.aider.chat.history.md` contains any pasted secrets. Aider writes no
keys itself; the collector flags `.aider.conf.yml` and the model settings
files.

## 8. Parser plan

Globs: `**/.aider.chat.history.md`, `**/.aider.input.history`,
`**/.aider.llm.history` (project-level, so they arrive through the
collector's project catalog).

Rows: one per `#### ` block (user), per assistant run, per `> ` run
(tool_result); `# aider chat started` becomes `system`.

| Column | Source |
| --- | --- |
| timestamp_utc | last `# aider chat started at` header, or the matching `# ` input-history line, converted from local time |
| session_id | synthesised `<path>#<header timestamp>` |
| project_path | the directory holding the file |
| git_branch | empty |
| model | empty |
| tool_name, tool_use_id | empty |
| text | prompt text, assistant text, blockquote text |

Fixture `.aider.chat.history.md`:

```
# aider chat started at 2026-10-02 12:00:00

#### rename foo to bar  
Here is the change:

a.py
<<<<<<< SEARCH
foo
=======
bar
>>>>>>> REPLACE

> Applied edit to a.py  
> Commit abc1234 refactor: rename foo to bar  
```

`.aider.input.history`: `\n# 2026-10-02 12:00:05.123456\n+rename foo to bar\n`

`.aider.llm.history`: `TO LLM 2026-10-02T12:00:05\n-------\nSYSTEM Act as an expert\n-------\nUSER rename foo to bar\nLLM RESPONSE 2026-10-02T12:00:09\nASSISTANT Here is the change:\n`

Confidence. High: chat and LLM history formats (read from the writers).
Medium-high: input history (upstream prompt_toolkit source, not pinned to
Aider's dependency version). Local-time timestamps need the host time zone
to convert exactly.
