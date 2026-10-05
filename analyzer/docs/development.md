# Development

Running the analyzer's tests and lint checks, and adding a parser; for
developers changing the analyzer.
Back to the [analyzer README](../README.md).

## Testing

```sh
cd analyzer
tests/run.sh                 # python3 -m unittest discover -s tests -t tests
tests/run.sh -v -k Glob      # options only: passed to unittest discover
tests/run.sh test_catalog    # one module
tests/run.sh test_parsers.ClaudeCodeTests            # one class
tests/run.sh test_parsers.ClaudeCodeTests.test_rows  # one method
```

`tests/run.sh` changes to the `analyzer/` directory itself, so it can be run
from anywhere. What it runs depends on whether a test name is given:

| Arguments | Command run | Options accepted |
| --- | --- | --- |
| none, or options only | `python3 -m unittest discover -s tests -t tests <options>` | every `unittest discover` option, including `-p`, `-k`, `-v`, `-f` |
| one or more test names, module, `module.Class` or `module.Class.method` | `python3 -m unittest <options> <names>` with `tests/` prepended to `PYTHONPATH`, so the modules import under the same names as under discover | the `unittest` options `-v`, `-q`, `-k`, `-f`, `-c`, `-b`, `--locals`; `-p`, `-s` and `-t` (and their long forms) are discover-only, so the script prints `run.sh: <option> applies only without test names` and exits 2 |

An argument that does not start with `-` and is not the value of `-k`,
`-p`, `-s`, `-t` or `--durations` counts as a test name.

The suite builds a fake image with two Linux users and a Windows profile
tree, each holding synthetic state for every parsed agent in the exact shapes
the parsers were validated against, and checks detection in every input mode,
each parser's rows, the JSONL output, and the bundled catalog against the
collector's `--list`. When `sh` and `tar` are available it also runs the sh
collector on the fake image and analyses the resulting archive end to end.
`test_inventory.py` feeds `inventory` captured outputs of three hosts, one
with console junk lines and one with a `host` line only, and checks the
columns, the default file name, `-o`, the rollup and the empty-host row;
with `sh` available it also runs the collector's `--inventory` on the fake
image and reads that.
Tests that need `zstandard`, the collector script, `sh` and `tar`, or
permission to create symlinks are skipped, with the reason, when it is
missing. CI runs the suite on Python 3.10, 3.11, 3.12, 3.13 and 3.14 with
`requirements.txt` installed.

Lint and type checks, from the repository root, at the versions CI pins
(see "Quality gates" in AGENTS.md):

```sh
uvx ruff@0.16.10 check . && uvx ruff@0.16.10 format --check .
uvx --from pyright==1.1.414 --with zstandard --with python-dateutil pyright   # also clean without zstandard
```

## Adding a parser

The full checklist, including the fixture, test class, parser table row,
version bump and the lists to update, is "Adding a parser" in
[AGENTS.md](../../AGENTS.md#adding-a-parser). In short:

1. Confirm the record format against source or a real install and write the
   field names into the module docstring, as the existing parsers do.
2. Subclass `Parser` in `agent_analyzer/parsers/<agent>.py`: set `agent` to
   the catalog name, implement `wants` on `artifact.rel` and `parse` yielding
   `Row` objects. Use `iter_jsonl` so a truncated line is reported, not fatal.
   Timestamps go through `to_utc`; text through `compact`, which strips
   leading and trailing whitespace and keeps inner line breaks.
3. Register it in `agent_analyzer/parsers/__init__.py`. A parser that must
   read a file the catalog attributes to another agent sets `reads_agents`.
4. Add fixture records to `tests/fixtures.py` and a test class to
   `tests/test_parsers.py`. Then add the row to the table in
   [parsers.md](parsers.md).
