# Privileges

What a run without root or Administrator still collects, and how it records
what it could not read. Back to the [collectors README](../README.md).

Run as root (sh) or from an elevated PowerShell (Windows) to collect every
user. Without that privilege, a live run still finishes and exits `0`. The
log gets a `WARNING: not running as root` (or `as Administrator`) line,
and:

- A home the responder cannot list or enter is still listed in `users`,
  gets one `error_read` row (`agent` empty, `path` and `home` the home
  directory), and is logged as `read failed: <home>: <error>`. The
  catalog is still tried against it, so a home that can be entered but
  not listed (mode `711`) still yields the entries that are not globs.
  Its `error_read` row does not put the user in `users_with_artifacts`.
  A discovered project directory or a `-p` directory that cannot be read
  gets the same row.
- Inside a walk, a directory that cannot be listed or entered gets one
  `error_read` row under the agent being walked, and a `read failed:` log
  line. sh: every directory `find` reaches is tested with `test -r` and
  `test -x` in the worker, and `error` is the first line `ls` printed for
  the same access, so the decision never depends on `find`'s localised
  message; `find` still logs its own `find:` line for the directory. The
  PowerShell collector writes the row when `Get-ChildItem` fails on the
  directory, with the exception message as `error`. On Linux and macOS a
  directory that can be listed but not entered fails that call only when
  it has entries, so an empty one gets a row from the sh collector alone.
  A catalog path whose parent cannot be entered is not seen by either
  collector and gets no row; the PowerShell collector logs a
  `stat failed:` line, with no row, for a matched path whose metadata it
  cannot read. A file that can be listed but not read is an `error_copy`
  row.
- The root-owned Docker and Podman data roots are reported as unreadable
  (see [docker.md](docker.md#unreadable-volumes)).
