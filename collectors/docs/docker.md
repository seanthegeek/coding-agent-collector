# Docker volumes

How the collectors find and collect agents deployed in Docker or Podman
named volumes, and what they record for Docker Desktop. Back to the
[collectors README](../README.md).

Several agents are commonly deployed in containers with their state in a
named volume rather than a home directory: Agent Zero's README runs it with
`-v a0_usr:/a0/usr`, Local Deep Research's compose file keeps its data in
`ldr_data`, and Ollama's Docker instructions use a volume named `ollama`.

## Where volumes are found

The collectors enumerate volumes themselves, from the filesystem and never
through the `docker` binary, so the same code works live and on a disk
image. The volume directories tried, relative to the root (`/` live, `-r`
in image mode), are `var/lib/docker/volumes` (root Docker),
`var/lib/containers/storage/volumes` (root Podman) and
`ProgramData/Docker/volumes` (Windows containers), and under every
selected home `.local/share/docker/volumes` (rootless Docker) and
`.local/share/containers/storage/volumes` (rootless Podman). `-u` limits
the rootless directories to the named users; the system directories are
always tried.

A volumes directory that is a symlink, or has a symlink on the way to it, is
noted in `collection.json` and not followed. A volume whose own directory is
a symlink is skipped without a row. A volume whose `_data` is missing or a
symlink is counted in `volumes_found`, logged, and skipped without a row.

## Matching and collection

Each volume is `<volumes dir>/<name>/_data`. Its name is matched
case-sensitively against the `DOCKER_VOLUMES` table (`--list` prints it
last, under `# docker volumes (agent|volume name glob)`), and the first
match wins. A matched volume is collected whole: its rows have `user`
`docker`, `home` the volume's `_data` path and `agent` from the table, and
its files are archived under `fs/<original path>` like everything else.
Exclusion and credential patterns apply relative to `_data`, so the tables
carry volume-relative forms such as `tmp/playwright` and `secrets.env`
beside the home-relative ones.

A volume that matches nothing is not collected. It gets one `dir` row with
status `skipped_unmatched_volume`, an empty `agent` and its size, so a
database volume or an agent with an unexpected volume name is still visible.

## Unreadable volumes

`/var/lib/docker` is readable only by root. Run as root to collect system
volumes. When a volume directory exists but cannot be read, or a matched
volume cannot be walked completely, the collection carries on with
everything else, the stdout summary says so
(`docker:     3 volumes found, 1 collected, 1 unreadable (run as root to collect)`)
and `collection.json` gets a note naming the path. The exit code is still
`0` when an archive was written. `--no-docker` skips the enumeration.

## Docker Desktop

Docker Desktop on Windows and macOS keeps Linux volumes inside its virtual
machine disk (the WSL `docker_data.vhdx` on Windows, `Docker.raw` on macOS),
which neither collector can reach. When Docker Desktop data is found
(`%ProgramData%\DockerDesktop`, a profile's `AppData\Local\Docker`, or
`~/Library/Containers/com.docker.docker`) the collectors only record a note
and append `; Docker Desktop VM disk not collected` to the summary line.
Collect those volumes from inside the VM, for example with
`docker run --rm -v VOLUME:/v -v "$PWD":/out alpine tar -czf /out/VOLUME.tgz -C /v .`.
