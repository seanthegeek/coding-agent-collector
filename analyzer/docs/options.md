# Options

Every subcommand and option in full, and the exit codes. The short table is
in the [analyzer README](../README.md#options).

## Synopsis

```text
analyze-agent-artifacts detect INPUT [--json] [--files] [common options]
analyze-agent-artifacts timeline INPUT -o DIR [--include-thinking] [--agent NAME]...
                         [--since WHEN] [--until WHEN] [--keep-undated] [--match REGEX]... [-i]
                         [common options]
analyze-agent-artifacts inventory [-o FILE] INPUT...
analyze-agent-artifacts catalog [--agents]
analyze-agent-artifacts --version
```

## Option reference

| Option | Subcommand | Meaning |
| --- | --- | --- |
| `--json` | `detect` | Print the machine-readable object described in [output.md](output.md#detect). |
| `--files` | `detect` | Also list every attributed file. |
| `-o, --output DIR` | `timeline` | Output directory, required. |
| `-o, --output FILE` | `inventory` | CSV to write. Default `fleet-inventory.csv` in the current directory. |
| `--include-thinking` | `timeline` | Emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | `timeline` | Run only the parsers of this agent. Repeatable. An unknown name produces no rows. |
| `--since WHEN` | `timeline` | Keep rows at or after `WHEN`, the first millisecond of the period it names. Forms in [filtering.md](filtering.md). |
| `--until WHEN` | `timeline` | Keep rows at or before `WHEN`, the last millisecond of the period it names. Same forms. |
| `--keep-undated` | `timeline` | With `--since` or `--until`, also keep rows that have no timestamp. |
| `--match REGEX` | `timeline` | Keep rows whose `text` matches this Python regular expression, with the paired tool call or result. Repeatable; a row matching any pattern is kept. |
| `-i, --ignore-case` | `timeline` | Make every `--match` case-insensitive. |
| `--agents` | `catalog` | Print each agent in the catalog with `parser` or `detect only`, instead of the catalog text. |
| `--host NAME` | `detect`, `timeline` | Host name to record. Overrides `collection.json`. |
| `--user NAME` | `detect`, `timeline` | User to record for every home whose user is empty. |
| `--work-dir DIR` | `detect`, `timeline` | Where to extract an archive. A `cac-*` directory is created inside it. Default: a `cac-analyzer-*` directory in the system temp directory. Either is removed afterwards unless `--keep-extracted` is given. |
| `--keep-extracted` | `detect`, `timeline` | Keep the extracted archive and print `extracted to: <path>` on stderr. |

`catalog` prints the bundled `catalog.txt` verbatim.

## Exit codes

| Exit code | Meaning |
| --- | --- |
| `0` | `timeline` wrote at least one row; `detect` found agent artifacts, or `--json` was given; `inventory` wrote at least one row; `catalog`, `--version`. |
| `1` | `timeline` produced no rows, including when every row was filtered out (the three files are still written), `detect` without `--json` found no agent artifacts, or `inventory` found no `host` or `agent` line (the CSV is written with its header only). |
| `2` | The input cannot be opened, printed as `error: <path>: <reason>` (see [inputs.md](inputs.md#unreadable-inputs)), a file input is neither tar nor zip or cannot be extracted, a `detect` or `timeline` input is neither a regular file nor a directory, a `--since` or `--until` value is not an accepted form or `--since` is later than `--until`, a `--match` pattern is not a valid regular expression, an `inventory` input is a symlink, neither a regular file nor a directory, or cannot be read, or the command line is invalid. |
