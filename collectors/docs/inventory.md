# Inventory mode

What `--inventory` (sh) and `-Inventory` (PowerShell) walk and the JSON
Lines they print. Back to the [collectors README](../README.md).

Inventory mode answers a fleet question, which users have used which agents
on which hosts, without collecting anything. Run the script on every host
through the EDR console and keep what it prints: stdout is the whole result
(see [deployment.md](deployment.md#fleet-inventory)). Nothing is created,
copied, hashed or written, not even a log, and `-o` is ignored. When `-o` or
`-OutputDir` is given, a `NOTE: --inventory writes nothing; -o <dir>
ignored` line (PowerShell: `-OutputDir <dir>`) goes to stderr, unless `-q`
is given. `-k`, `--no-secrets` and `--max-file-size` have no effect.

## What is walked

The walk is the collection walk with the copy step removed. Homes are
enumerated as for a collection and honour `-u` and `-r`. Every `CATALOG`
entry is expanded against every home, nested entries claim their subtree
from the enclosing entry, and the `EXCLUDES` patterns prune their subtrees
(not with `--full`), so the counts cover what a collection would take.
Regular files are counted with their `lstat` size and modification time
(PowerShell: `Length` and `LastWriteTimeUtc`); symlinks and reparse points
are neither followed nor counted. Docker and Podman volumes are enumerated
as in [docker.md](docker.md) unless `--no-docker` is given, and a volume
that matches a `DOCKER_VOLUMES` line is walked like a home.

Project discovery runs, so the project count is available, but
`PROJECT_CATALOG` files are not walked. Credential files are never opened:
discovery sources that match `SECRET_GLOBS` (`.claude.json`,
`.openclaw*/openclaw.json`, `.clawdbot/clawdbot.json`,
`.nanobot*/config.json`, `.tabby/config.toml`) are skipped in this mode, so
the project count can be lower than the number of projects a collection
takes from. The other discovery sources are read as in a collection, which
updates their access time on filesystems that track it.

## Output

stdout carries JSON Lines and nothing else: first one `host` line, then one
`agent` line per user and agent, users in enumeration order and each user's
agents in order of their first catalog match, then the Docker volume agents
under user `docker`. Progress lines go to stderr unless `-q` is given. The
exit code is `0` once the walk has run, including when homes or Docker data
roots were unreadable.

```jsonl
{"type":"host","host":"host01","collector":"1.6.0","mode":"live","at":"2026-10-04T16:31:54Z","users_scanned":3,"users_unreadable":0,"docker_volumes":3}
{"type":"agent","host":"host01","user":"alice","agent":"claude-code","files":6,"bytes":318,"first":"2026-09-15T01:02:03Z","last":"2026-10-04T16:31:11Z","projects":29,"evidence":".claude,.claude.json*"}
{"type":"agent","host":"host01","user":"docker","agent":"agent-zero","files":2,"bytes":63,"first":"2026-10-04T16:31:11Z","last":"2026-10-04T16:31:11Z","projects":0,"evidence":"*a0_usr"}
```

### Host line

The `host` line, one per run, keys in this order:

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | string | `host`. |
| `host` | string | The host name, as in `collection.json` `hostname`: sh `hostname`, else `uname -n`; PowerShell `COMPUTERNAME`, else the DNS host name. Read from the machine running the collector, so with `-r` it is the analyst workstation's name. |
| `collector` | string | The collector version, as printed by `--version`. |
| `mode` | string | `live`, or `image` with `-r`. |
| `at` | string | UTC start time to the second, `2026-10-04T16:31:54Z`. |
| `users_scanned` | number | Home directories walked after `-u`. sh: every enumerated home that exists as a directory, readable or not. PowerShell: the same, plus enumerated profiles that .NET reports as missing although their parent directory lists them (access denied). A `ProfileList` entry whose directory is gone is not counted. |
| `users_unreadable` | number | Of those, the homes that cannot be read. sh: a home for which `test -r` or `test -x` fails, so it cannot be listed or entered; its globs match nothing. PowerShell: a profile .NET reports as missing although its parent lists it, or one whose entries cannot be listed. Each is also logged to stderr as `WARNING: home of <user> is not readable: <home>` (sh, and PowerShell for listable-but-unreadable profiles; the PowerShell `profile not accessible (skipped)` line covers the rest). As root, or as Administrator with access, this is `0`; without, other users' homes are counted here. A directory that cannot be listed inside a readable home is not counted anywhere: its files are simply missing from the totals. |
| `docker_volumes` | number | Volume directories found under the Docker and Podman volume roots, matched or not, as `collection.json` `docker.volumes_found`. `0` with `--no-docker`. Without root the root-owned data roots cannot be entered, so their volumes are not found; a `NOTE: docker:` line on stderr says so unless `-q` is given. |

### Agent lines

One `agent` line per user and agent with at least one regular file under
its matched `CATALOG` paths after exclusions and nested claims, keys in this
order. A match that holds no files of its own gives no line: an empty
directory, a symlink, an excluded-only tree, or a `~/.gemini` that holds
only the `antigravity-cli` directory claimed by the nested `antigravity`
entry. The same rule applies to Docker volumes. `files` is therefore never
`0`. The `shared` entries are not inventoried, and `project` never appears.

| Field | Type | Meaning |
| --- | --- | --- |
| `type` | string | `agent`. |
| `host` | string | As on the host line. |
| `user` | string | The home's user, as in the manifest, or `docker` for a matched Docker or Podman volume. |
| `agent` | string | The catalog agent name, or for a volume the `DOCKER_VOLUMES` agent. |
| `files` | number | Regular files under the agent's matched paths after exclusions, with nested entries' subtrees left to their own agent. |
| `bytes` | number | Their total size in bytes. |
| `first`, `last` | string | The earliest and latest modification time of those files, UTC to the second. Empty when no modification time was available (sh on a host with neither GNU nor BSD `stat`). |
| `projects` | number | Project directories discovered for this user, the same number on each of the user's lines: discovery does not record which agent's state named a project. A project named by several users counts for the first of them in enumeration order, as in a collection, and a `-p` directory counts for the user whose home contains it. `0` for `docker` lines and with `--no-projects`. |
| `evidence` | string | The `CATALOG` globs (the part after `agent\|`) that matched, in catalog order, joined by commas, so no path below the home is printed. For a volume, the `DOCKER_VOLUMES` globs that matched. |

### Escaping

Strings are JSON-escaped: the sh collector escapes backslash, double
quote, tab, carriage return and newline; PowerShell's `ConvertTo-Json`
also escapes other control characters, and Windows PowerShell 5.1 escapes
`<`, `>`, `&` and `'` as `\u` sequences. The analyzer's
`inventory` command reads these lines from saved stdout files and builds a
fleet CSV; see [the analyzer's inventory page](../../analyzer/docs/inventory.md).
