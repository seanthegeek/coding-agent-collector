#!/bin/sh
# Drive the agent lab: build the sandbox, run an agent in it, export its
# home as a fake disk image, and run the collector and analyzer on it.
#
#   lab.sh build [--ollama]        build the agent image (and pull Ollama)
#   lab.sh up [--ollama]           start the sandbox, detached
#   lab.sh shell                   bash inside the sandbox as the agent user
#   lab.sh run CMD [ARGS...]       run one command in the sandbox, e.g. run claude
#   lab.sh pull MODEL              pull a model into the Ollama service
#   lab.sh collect [DIR]           export home (+ Ollama state) to DIR/image,
#                                  run the collector into DIR/collection and
#                                  the analyzer into DIR/analysis
#   lab.sh down                    stop containers, keep the home volume
#   lab.sh clean                   stop and delete containers, volumes and the
#                                  agent-lab:latest image
#
# DIR defaults to lab/out/<UTC stamp>. Exports contain whatever credentials
# the agents wrote; lab/out is gitignored, delete it when done.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/.." && pwd)
collector="$repo/collectors/collect-agent-artifacts.sh"
agent_ctr=agent-lab
agent_image=agent-lab:latest
ollama_ctr=agent-lab-ollama

die() { printf 'lab: %s\n' "$*" >&2; exit 1; }

need_docker() {
  command -v docker >/dev/null 2>&1 || die 'docker not found; enable Docker Desktop WSL integration or install docker'
  docker compose version >/dev/null 2>&1 || die 'docker compose v2 not found (on WSL, enable Docker Desktop integration for this distro)'
}

want_ollama=0
for a in "$@"; do
  if [ "$a" = "--ollama" ]; then want_ollama=1; fi
done

# Compose invocation: add the Ollama profile when asked, and the GPU
# override when the host has a working NVIDIA driver.
compose() {
  if [ "$want_ollama" = 1 ] || ctr_exists "$ollama_ctr"; then
    if nvidia-smi -L >/dev/null 2>&1; then
      set -- -f "$here/compose.yaml" -f "$here/compose.gpu.yaml" --profile ollama "$@"
    else
      set -- -f "$here/compose.yaml" --profile ollama "$@"
    fi
  else
    set -- -f "$here/compose.yaml" "$@"
  fi
  docker compose "$@"
}

ctr_exists()  { docker container inspect "$1" >/dev/null 2>&1; }
ctr_running() { [ "$(docker container inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = true ]; }

need_up() { ctr_running "$agent_ctr" || die "sandbox is not running; run $0 up"; }

cmd=${1:-help}
if [ $# -gt 0 ]; then shift; fi
case "$cmd" in help|-h|--help) ;; *) need_docker ;; esac

case "$cmd" in
  build)
    compose build
    if [ "$want_ollama" = 1 ]; then compose pull ollama; fi
    ;;
  up)
    compose up -d
    printf 'lab: sandbox up. Try: %s run claude\n' "$0"
    ;;
  shell)
    need_up
    exec docker exec -it "$agent_ctr" bash
    ;;
  run)
    need_up
    [ $# -gt 0 ] || die 'run needs a command, e.g. run claude'
    exec docker exec -it "$agent_ctr" "$@"
    ;;
  pull)
    ctr_running "$ollama_ctr" || die "Ollama is not running; run $0 up --ollama"
    [ $# -gt 0 ] || die 'pull needs a model name, e.g. pull qwen2.5-coder:7b'
    exec docker exec -it "$ollama_ctr" ollama pull "$1"
    ;;
  collect)
    ctr_exists "$agent_ctr" || die "no sandbox container; run $0 up first"
    out=${1:-"$here/out/$(date -u +%Y%m%dT%H%M%SZ)"}
    image="$out/image"
    mkdir -p "$image/home" "$image/etc"
    # docker cp writes a tar stream: mtimes, modes and symlinks survive, and
    # symlinks are copied as links, not followed.
    printf 'lab: exporting /home/agent to %s\n' "$image"
    docker cp -q "$agent_ctr:/home/agent" "$image/home/"
    docker cp -q "$agent_ctr:/etc/passwd" "$image/etc/passwd"
    if ctr_exists "$ollama_ctr"; then
      printf 'lab: exporting Ollama state (model blobs included; the collector excludes them)\n'
      mkdir -p "$image/root"
      docker cp -q "$ollama_ctr:/root/.ollama" "$image/root/"
    fi
    printf 'lab: collecting\n'
    "$collector" -r "$image" -o "$out/collection" -q
    archive=
    for f in "$out/collection"/*.tar.gz; do
      if [ -f "$f" ]; then archive=$f; break; fi
    done
    if [ -n "$archive" ] && command -v python3 >/dev/null 2>&1; then
      printf 'lab: analyzing\n'
      rc=0
      PYTHONPATH="$repo/analyzer" python3 -m agent_analyzer timeline "$archive" -o "$out/analysis" || rc=$?
      case $rc in
        0) ;;
        1) printf 'lab: no parseable transcripts yet; run an agent for a few turns, then collect again\n' ;;
        *) printf 'lab: analyzer exited %s; the collection is still in %s\n' "$rc" "$out/collection" >&2 ;;
      esac
    fi
    printf 'lab: done. Output under %s (contains any credentials the agents wrote; delete when finished)\n' "$out"
    ;;
  down)
    compose down
    ;;
  clean)
    compose down -v --rmi local
    # --rmi local skips images with a custom tag, and compose.yaml tags the
    # sandbox image, so remove it by name when it exists.
    if docker image inspect "$agent_image" >/dev/null 2>&1; then
      docker image rm "$agent_image"
    fi
    printf 'lab: containers, volumes and the %s image removed. Exports in %s/out are untouched.\n' "$agent_image" "$here"
    ;;
  help|-h|--help)
    # The header comment, from line 2 to the first line that is not one.
    awk 'NR == 1 { next } !/^#/ { exit } { sub(/^# ?/, ""); print }' "$0"
    ;;
  *)
    die "unknown command '$cmd'; try $0 help"
    ;;
esac
