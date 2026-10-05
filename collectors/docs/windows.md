# Windows

How the PowerShell collector writes its archive, recreates symlinks and
reparse points, and copies locked or long paths. Back to the
[collectors README](../README.md).

## Archiver: `tar.exe` or `ZipFile`

On Windows 10 1803 and later, Windows 11, and Server 2019 and later the
script writes a `tar.gz` through the built-in `tar.exe`, so the archive is
identical in form to the sh collector's. When `tar.exe` is not on the `PATH`
(older hosts) or fails, the script falls back to `System.IO.Compression` and
produces a `.zip`. The summary's `capabilities.archiver` and `archive` name
the archiver and the archive actually written: the summary is rewritten and
restaged before the zip fallback, so both the copy inside the archive and the
one beside it say `ZipFile` and `.zip` after a `tar.exe` failure.

## Symlinks and reparse points

Symlinks and other reparse points are recreated in the staging directory as
symbolic links with the target string exactly as `Target` reports it, as the
sh collector does with `ln -s`, so a relative target stays relative and a
dangling one is kept. A junction is recreated as a directory symlink to the
same target.

`tar.exe` stores the link, not the file or directory it points to
(libarchive archives a symlink reparse point as a link and does not descend
into it,
[`archive_read_disk_windows.c`](https://github.com/libarchive/libarchive/blob/7219b0134d771dc4b51bf86b4d01761b87398b1b/libarchive/archive_read_disk_windows.c#L2046-L2050)
at v3.8.8); the libarchive 3.3.2 `tar.exe` of early Windows 10 builds stores
the link entry without its target text. `tar.exe` stores a relative target
with its backslashes turned into forward slashes and an absolute target as
`\\?\C:\...`
([`archive_read_disk_windows.c`](https://github.com/libarchive/libarchive/blob/7219b0134d771dc4b51bf86b4d01761b87398b1b/libarchive/archive_read_disk_windows.c#L396-L405)),
so the link in the archive can differ from the manifest row's `target`,
which keeps the original string.

### Creating the link

Creating a symlink on Windows needs the `SeCreateSymbolicLinkPrivilege`
(Administrator) or Developer Mode. Windows PowerShell 5.1 has no managed API
for this, so it runs `cmd.exe /d /v:off /c mklink` (with `/D` for a
directory link or a junction), which keeps the target string verbatim and
accepts a target that does not exist;
[Microsoft documents](https://blogs.windows.com/windowsdeveloper/2016/12/02/symlinks-windows-10/)
that `mklink` creates links without elevation in Developer Mode from the
Windows 10 Creators Update (1703). `cmd.exe` expands `%NAME%` even inside
quotes, so a link whose path or target contains `%` or `"` is not passed to
it. PowerShell 7 uses .NET's `CreateSymbolicLink` instead and has neither
limit.

Without the privilege, for a `%` or `"` under 5.1, or for a reparse point
with no single link target, the row keeps `archive_path` empty and `error`
says why (under 5.1, `mklink`'s message and exit code), and
`collection.json` `notes` counts the links that could not be recreated.

### Symlinks and the zip fallback

A `.zip` cannot hold symlinks and `ZipFile` would copy the target's bytes in
their place, possibly from outside the collection, so the zip archive never
contains them:

- When `tar.exe` is missing from the start, no link is created, every
  `symlink` row has an empty `archive_path` and the `error`
  `not recreated in the archive: zip cannot store symlinks`, and a note
  says how many symlinks are in the manifest only.
- When `tar.exe` fails after the links were staged, they are deleted from
  the staging directory before zipping, the manifest is rewritten so those
  rows have an empty `archive_path` and the `error`
  `not in the archive: tar failed and zip cannot store symlinks`, a note
  records the removal, and the rewritten manifest and summary are what the
  zip and the output directory hold.

### PowerShell 7 on Linux or macOS

Under PowerShell 7 on Linux or macOS the links are made with .NET's
`CreateSymbolicLink`, the archiver is the system `tar`, and the same rules
apply.

### Staged link cleanup

Staged links are deleted one by one before the staging directory is
removed, so the cleanup never descends through a link. If one cannot be
deleted, the staging directory is kept and the log says so, and a zip fall
back is not attempted (the run exits `2` with no archive) rather than
zipping through the link.

## Locked files and long paths

Files held open by a running editor (Cursor's `state.vscdb`, Electron
LevelDB stores) are read with shared access so they still copy. Reparse
points (symlinks and junctions) are recorded with their target and never
followed. Paths longer than 260 characters fail to copy under Windows
PowerShell 5.1 unless long paths are enabled on the host; the failure is
recorded as `error_copy`.
