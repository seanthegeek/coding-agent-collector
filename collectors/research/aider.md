# Aider: on-disk paths

## 1. Source and evidence level

Aider-AI/aider, open source, commit `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`. All claims from source; the config-key example is from the shipped docs in the same tree. Transcript format is in `analyzer/research/aider.md`.

## 2. Per-user storage

Aider has no platform branching; everything is `Path.home()` (`%USERPROFILE%` on Windows), so the layout is identical on Linux, macOS and Windows. No `XDG` use.

Home-level files, all optional:
- `~/.aider.conf.yml`: the config search is cwd, git root, home (`aider/main.py:464-477`; `aider/args.py:790-796`), or `--config`.
- `~/.aider.model.settings.yml` and `~/.aider.model.metadata.json`: `generate_search_path_list` tries home, git root, then cwd or the `--model-settings-file`/`--model-metadata-file` value (`main.py:305-310,336-338,397-399`; defaults `args.py:121-131`).
- `~/.env`: `load_dotenv_files` loads `~/.env`, `<git root>/.env`, then `.env` in cwd or `--env-file` (`main.py:361-385`; `args.py:31-32,801-804`). This is a shared dotfile, not aider-owned.
- `~/.aider/oauth-keys.env`: loaded first (`main.py:370-374`), written by the OpenRouter OAuth flow (`aider/onboarding.py:363-367`).
- `~/.aider/analytics.json`: anonymous `uuid` and disable flag (`aider/analytics.py:139-152`). `--analytics-log <file>` writes JSONL events wherever the user says (`args.py:575-578`).
- `~/.aider/caches/`: `model_prices_and_context_window.json` (`aider/models.py:169-170`), `openrouter_models.json` (`aider/openrouter.py:34-35`), `versioncheck` (`aider/versioncheck.py:12`), `help.<version>/` llama-index embedding store (`aider/help.py:93`).
- History files default to the git root (section 5); when aider runs outside a repository they land in the cwd (`args.py:271-276`), so `~/.aider.chat.history.md` and friends exist only for sessions started in the home directory.

No relocation environment variable; everything is `--option` or config-file driven. `pip`/`uv` install directories are out of scope.

## 3. Credentials

- `~/.aider/oauth-keys.env`: `OPENROUTER_API_KEY="..."` appended in plaintext (`onboarding.py:365-367`).
- `.aider.conf.yml` at any of the three levels accepts `openai-api-key`, `anthropic-api-key`, `api-key: provider=key` and `set-env` (`args.py:69-110`; documented example `aider/website/docs/config/aider_conf.md:81-84,109`).
- `.env` files at home, git root and cwd carry `*_API_KEY` values by design.
- `.aider.model.settings.yml` has no key field; `extra_params` is passed to litellm and could carry one, so flagging it is harmless but not evidence-based.
- `.aider.llm.history` contains full request bodies; keys are not logged.
- No keychain use.

## 4. Exclusions

`.aider/caches` (model price tables, embedding store, version stamp). In repositories: `.aider.tags.cache.v<N>` tree-sitter tag cache, currently `v3` (`aider/repomap.py:35,43,186,218`).

## 5. Project-local files

Defaults placed in the git root, or cwd without git (`args.py:271-276,422-426`): `.aider.input.history` (prompt_toolkit `FileHistory`, `aider/io.py:356`), `.aider.chat.history.md` (appended per session, `io.py:336`), `.aider.llm.history` only when `--llm-history-file` is given (`args.py:296-300`; written at `io.py:755-764`), `.aiderignore`, `.aider.tags.cache.v3/`, and per-level `.aider.conf.yml`, `.aider.model.settings.yml`, `.aider.model.metadata.json`, `.env`. `CONVENTIONS.md` is a documented convention loaded with `--read` (`aider/website/docs/usage/conventions.md`), not a hard-coded name. Aider adds `.aider*` and `.env` to the repository `.gitignore` on first run (`main.py:160-168`), so git-based enumeration misses all of this; the collector must walk the directory.

## 6. Where the project path is recorded

Nowhere under home. Aider keeps no index of repositories; `analytics.json` holds only a UUID, and the chat history lives inside each repository. Discovery sources for other agents (and shell history) are the only way to find aider projects; the `# aider chat started at <timestamp>` headers in `.aider.chat.history.md` date the sessions once found.

## 7. Catalog review

Home: `.aider` confirmed; `.aider.conf.yml`, `.aider.model.settings.yml`, `.aider.model.metadata.json` confirmed; `.aider.chat.history.md`, `.aider.input.history`, `.aider.llm.history` confirmed as the cwd fallback when run from home.
Project: `.aider.chat.history.md`, `.aider.input.history`, `.aider.llm.history`, `.aider.conf.yml`, `.aider.model.settings.yml`, `.aider.model.metadata.json`, `.aiderignore` confirmed. `.env` is already a generic project entry (catalog line 239) and `.env` a generic credential glob (line 466).
Excluded: `.aider/caches` confirmed; `.aider.tags.cache*` confirmed.
Credential: `.aider/oauth-keys.env` confirmed; `.aider.conf.yml` confirmed; `.aider.model.settings.yml` doubtful (no key field in source, harmless).

Add:
```
# home (aider reads it; shared dotfile, label generic if preferred)
aider|.env
# credential, only if the secret matcher is anchored to home
*/.aider.conf.yml
```
Nothing else is missing. `.aider.tags.cache*` as a project exclusion should be verified to apply inside project directories, since the cache is never under home.

## 8. Confidence

High: all file names and search orders (source). Medium: whether the collector's exclusion and secret globs are evaluated against project paths (affects `.aider.tags.cache*` and project `.aider.conf.yml`). Not determined: nothing material; aider is the simplest layout of the five.
