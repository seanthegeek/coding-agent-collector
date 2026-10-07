# MetaGPT: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document: MetaGPT keeps no transcripts under the home.

## 1. Source and evidence level

FoundationAgents/MetaGPT (geekan/MetaGPT redirects there), MIT
([setup.py:107](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/setup.py#L107)),
open source, commit `11cdf466d042aece04fc6cfd13b28e1a70341b1f`
(2026-01-21). A Python multi-agent "software company" framework with the
`metagpt` CLI. All claims are from source; nothing was installed or run.

MetaGPT runs shell commands on the host: the `Terminal` tool spawns a
persistent shell
([terminal.py:47-52](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/tools/libs/terminal.py#L47-L52)).

## 2. Per-user storage

| Path (home-relative, all OSes) | Holds | Default or opt-in |
| --- | --- | --- |
| `.metagpt/config2.yaml` (`Path.home()`) | LLM configuration including `api_key` ([const.py:39](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/const.py#L39), [config2.py:115-118](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/config2.py#L115-L118), [software_company.py:130-148](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/software_company.py#L130-L148), [README.md:70-73](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/README.md#L70-L73)) | read by every run; written by `metagpt --init-config` |
| `.metagpt/config2.bak` | the previous config, renamed on re-init ([software_company.py:146-148](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/software_company.py#L146-L148)) | on a second `--init-config` |

`CONFIG_ROOT / "config2.yaml"` is the only home path in the package (grep
for `CONFIG_ROOT`, `Path.home`, `expanduser`, `platformdirs`).

Generated projects and serialized team state go to
`<METAGPT_ROOT>/workspace` and `workspace/storage/team/team.json`, where
`METAGPT_ROOT` is `$METAGPT_PROJECT_ROOT`, else the package parent if it
holds `.git` (an editable install from a clone), else the working
directory
([const.py:19-41](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/const.py#L19-L41),
[const.py:58](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/const.py#L58),
[workspace_config.py:18-37](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/configs/workspace_config.py#L18-L37),
[team.py:59-65](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/team.py#L59-L65)).
`team.json` is written when `Team.run` ends in an exception or Ctrl-C
([common.py:675-684](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/utils/common.py#L675-L684)).
These are relative to the working directory or the clone, not the home,
so they have no catalog line; `workspace` is also too generic a name to
anchor a glob on. The git tool reads, but does not write,
`~/.git-credentials`
([git.py:69-71](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/tools/libs/git.py#L69-L71)).

Docker: no named volume.

## 3. Credentials

- `.metagpt/config2.yaml` and `.metagpt/config2.bak`: flagged.

## 4. Exclusions

None.

## 5. Project-local files

The `workspace/` tree in section 2, under no MetaGPT-specific name.

## 6. Where the project path is recorded

Nowhere under the home.

## 7. Confidence

High (source). Not determined: the workspace location when the working
directory is the home (then `~/workspace`, too generic for a glob).
