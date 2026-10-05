# Deployment through an EDR

Running the collectors through an EDR remote shell, for a collection or a
fleet inventory. Back to the [collectors README](../README.md).

## Collection

The script is a single file with no interactive prompts, reads nothing from
stdin, and writes everything under `-o`. From CrowdStrike RTR, SentinelOne
RemoteOps, Defender Live Response or Palo Alto Networks Cortex XDR Live
Terminal, upload the script, run it with `-o` pointing at a directory you can
retrieve from, then pull the `tar.gz`. Use `-q` to keep the console output to
the final summary. Runtime on a developer workstation with several agents
installed is well under a minute.

On Windows, files held open by a running editor still copy and paths longer
than 260 characters can fail under Windows PowerShell 5.1; see
[windows.md](windows.md#locked-files-and-long-paths).

## Fleet inventory

For a fleet inventory, run the script with `--inventory` (`-Inventory`) and
no `-o`: nothing is uploaded back or left on the host, and the console
output of the run is the result. Save each host's stdout as its own file
(the EDR console's output export or a copy and paste of the response) and
pass the files to the analyzer's `inventory` command. Add `-q` so stderr
stays empty; stderr never mixes into stdout, but some consoles show both
together. The lines are described in [inventory.md](inventory.md).

## Access times

Copying a file updates its `atime` on filesystems that track it. The
manifest records the pre-copy `atime` from `lstat`, taken before the copy.
On a disk image, mount it read-only with `noatime`.
