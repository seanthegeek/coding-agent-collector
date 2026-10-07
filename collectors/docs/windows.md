# Windows

How the PowerShell collector writes its archive, recreates symlinks and
reparse points, and copies locked or long paths. Back to the
[collectors README](../README.md).

## Archiver: `tar.exe`, the PowerShell tar writer or `ZipFile`

The script tries up to three archivers in order, and the first that writes
an archive wins:

| Archiver | `capabilities.archiver` | Archive | Used when |
| --- | --- | --- | --- |
| `tar.exe -czf <archive> -C <stage> .` | `tar.exe` | `.tar.gz` | first, when `tar.exe` is on the `PATH` (Windows 10 1803 and later, Windows 11, Server 2019 and later) |
| the PowerShell tar writer in the script | `PowerShell tar writer` | `.tar.gz` | `tar.exe` is not on the `PATH`, exits non-zero or leaves no archive |
| `System.IO.Compression.ZipArchive` | `ZipFile` | `.zip` | the PowerShell tar writer failed too |

Some builds of the built-in `tar.exe` exit `0xC0000005`, an access
violation, when the staging tree holds a name outside the ANSI code page,
such as a CJK or Cyrillic one. This was seen with bsdtar 3.8.8 (`tar.exe`
10.0.26100) on Windows 11, where no option or format makes it store such
names; the `tar.exe` on the GitHub `windows-latest` runner stores them. When `tar.exe` fails, the log has a line
`tar.exe failed: exit code 0xC0000005` (hex for a negative exit code,
decimal otherwise), its partial archive is removed, and `collection.json`
`notes` gets `tar.exe failed (exit code 0xC0000005); fell back to PowerShell
tar writer`. A failure of the PowerShell tar writer is logged with the
exception's message (`PowerShell tar writer failed: <message>`) and noted in
the same way before the zip is written.

The PowerShell tar writer uses only .NET Framework APIs (`GZipStream` over a
`FileStream`). It writes POSIX ustar headers with the member names
`tar -czf <archive> -C <stage> .` gives (`./`, `./fs/...`,
`./manifest.jsonl`, `./collection.json`, `./collector.log`, directories
ending in `/`), so the archive layout is the same as with `tar.exe` and the
sh collector. A path that is not ASCII, or does not fit the ustar name and
prefix fields, goes in a pax extended header (typeflag `x`) as a UTF-8
`path` record, as does a symlink target (`linkpath`) and a size above 8 GiB
(`size`). It stores directories (mode 0755), regular files (0644) and
symlinks (0777) with uid and gid 0 and each staged item's last write time.
It reads the staged files with shared access in 1 MiB chunks, lists the
staging tree without following reparse points, and stores a symlink's target
string exactly as the link was staged, so unlike `tar.exe` it keeps a
relative target's backslashes and does not add `\\?\` to an absolute one.

The zip is written entry by entry with `/` separators and no `./` prefix
(the .NET Framework `ZipFile.CreateFromDirectory` used up to 1.10.2 wrote
`\`), with an entry for each empty directory.

The summary's `capabilities.archiver` and `archive` name the archiver and
the archive actually written: the summary and the log are rewritten and
restaged before each fallback, so both the copy inside the archive and the
one beside it name the archiver that wrote it.

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
with its backslashes turned into forward slashes and an absolute target with
a `\\?\` prefix; the `tar.exe` on the GitHub `windows-latest` runner writes
that one with forward slashes too, `//?/C:/...`
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

- When the zip is the archiver from the start, which happens only when the
  `CAC_ARCHIVER` test hook says so (see [testing.md](testing.md)), no link
  is created, every `symlink` row has an empty `archive_path` and the
  `error` `not recreated in the archive: zip cannot store symlinks`, and a
  note says how many symlinks are in the manifest only. Without `tar.exe`
  the PowerShell tar writer comes first and stores the links.
- When `tar.exe` and the PowerShell tar writer both fail after the links
  were staged, they are deleted from
  the staging directory before zipping, the manifest is rewritten so those
  rows have an empty `archive_path` and the `error`
  `not in the archive: tar failed and zip cannot store symlinks`, a note
  records the removal, and the rewritten manifest and summary are what the
  zip and the output directory hold.

### PowerShell 7 on Linux or macOS

Under PowerShell 7 on Linux or macOS the links are made with .NET's
`CreateSymbolicLink`, the first archiver is the system `tar` (still named
`tar.exe` in `capabilities.archiver`), which stores UTF-8 names, and the
same fallbacks and rules apply when it fails or is missing.

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
