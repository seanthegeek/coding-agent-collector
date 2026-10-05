# Inventory

The `inventory` command, which merges collector `--inventory` output into
one fleet CSV, and its columns.
Back to the [analyzer README](../README.md).

`inventory` merges the output of collector runs made with `--inventory`
(sh) or `-Inventory` (PowerShell), described in the
[collectors documentation](../../collectors/docs/inventory.md), into one CSV
for the fleet. Each `INPUT` is a file holding one host's captured stdout,
or a directory whose regular files are all read (not recursively, sorted
by name, symlinks skipped). A symlink given as `INPUT` is an error.

Each file is read line by line as UTF-8 (a byte order mark is dropped,
undecodable bytes are replaced). A line that is not a JSON object with
`type` `host` or `agent`, such as a console banner, a prompt or a record
cut off mid-line, is skipped, and the number skipped is printed on stderr
as `skipped N non-inventory lines in <file>`. Blank lines are skipped
without being counted. A `host` line opens a run, and each later `agent`
line in the same file is a row of that run until the next `host` line, so
one file may hold several runs. An `agent` line before any `host` line
gives a row with its own `host` and empty `collector`, `mode` and `at`.
Rows are written in input order; nothing is deduplicated, so two captures
of the same host give two sets of rows.

The CSV, `fleet-inventory.csv` in the current directory unless `-o` names
another path (missing parent directories are created), is UTF-8 without a
byte order mark, quoted where needed, with CRLF line ends and a header row.
Columns, in order:

| Column | Meaning |
| --- | --- |
| `host` | The run's `host` line `host`: the collector machine's host name. |
| `collector` | The collector version from the `host` line. |
| `mode` | `live` or `image`, from the `host` line. |
| `at` | The run's start time, normalised to ISO 8601 UTC with milliseconds, `2026-10-04T16:31:54.000Z`. |
| `user` | The home's user, or `docker` for a Docker or Podman volume. |
| `agent` | The catalog agent name. |
| `files`, `bytes` | Regular files under the agent's matched paths after exclusions, and their total size. |
| `first`, `last` | Earliest and latest file modification time, normalised like `at`. Empty when the collector reported none. |
| `projects` | The user's discovered project count, the same on each of the user's rows (the collector does not attribute projects to agents). |
| `evidence` | The catalog globs that matched, comma-separated, as the collector printed them. |

A `host` line with no `agent` lines after it gives one row with the four
host columns filled and the eight agent columns empty, so hosts where
nothing was found are still in the sheet. The `host` line's
`users_scanned`, `users_unreadable` and `docker_volumes` are not carried
into the CSV. The columns are an interface like the timeline's: new ones
are appended, existing ones keep their names, order and meaning.

On stdout `inventory` then prints `rows: N from H hosts in <path>` (H
counts distinct `host` values) and, when any row has an agent, a rollup
with one line per agent: `agent`, `hosts` (distinct hosts with a row for
it), `users` (distinct host and user pairs, `docker` included) and
`latest` (the greatest `last`). The rollup is sorted by `hosts`, then
`users`, both descending, then by agent name.
