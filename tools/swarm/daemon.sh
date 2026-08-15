#!/usr/bin/env bash
# tools/swarm/daemon.sh — run swarm daemons isolated from your working tree.
#
# Why: daemons used to run inside the developer/agent checkout. Their every
# `git add swarm/... && git commit && git push` then raced manual branch work
# (heartbeat commits landed on feature branches, rebases exploded). This
# launcher gives daemons their OWN clone under $SHESH_STATE (default
# ~/.local/state/shesh/swarm-tree), runs them with unbuffered output, and
# appends to real log files. Your checkout is never touched.
#
# Usage:
#   tools/swarm/daemon.sh start [component]   # monitor + (optional) worker
#   tools/swarm/daemon.sh stop                # stop all daemons
#   tools/swarm/daemon.sh status              # pids, heartbeat freshness, log tails
#
# Env:
#   SHESH_STATE            state dir (default ~/.local/state/shesh)
#   SHESH_WORKER_EXECUTOR  module:function — REQUIRED to start a worker
#                          (workers fail closed without one, by design)
#   SWARM_USE_GITHUB=1     GitHub Issues queue (default on here)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${SHESH_STATE:-$HOME/.local/state/shesh}"
TREE="$STATE/swarm-tree"
LOGD="$STATE/logs"
PIDDIR="$STATE/pids"
mkdir -p "$LOGD" "$PIDDIR"

sync_tree() {
    local url
    url="$(git -C "$ROOT" remote get-url origin)"
    if [ ! -e "$TREE/.git" ]; then
        echo "cloning daemon tree -> $TREE"
        git clone --quiet "$url" "$TREE"
        # Daemons need git identity + auth even on fresh machines/sandboxes.
        git -C "$TREE" config user.name  "$(git -C "$ROOT" config user.name  || echo shesh-swarm)"
        git -C "$TREE" config user.email "$(git -C "$ROOT" config user.email || echo shesh-swarm@localhost)"
        if helper="$(git -C "$ROOT" config credential.helper)"; then
            git -C "$TREE" config credential.helper "$helper"
        else
            echo "warn: source repo has no credential helper — daemon tree needs auth setup"
        fi
    fi
    git -C "$TREE" checkout -q main
    git -C "$TREE" pull --rebase origin main --quiet || echo "warn: daemon tree pull failed (auth?) — see bootstrap"
}

is_running() {  # $1 = name
    [ -f "$PIDDIR/$1.pid" ] && kill -0 "$(cat "$PIDDIR/$1.pid")" 2>/dev/null
}

start_one() { # $1 = name, $2.. = command
    local name="$1"; shift
    if is_running "$name"; then echo "$name already running (pid $(cat "$PIDDIR/$name.pid"))"; return; fi
    ( cd "$TREE" && SWARM_USE_GITHUB="${SWARM_USE_GITHUB:-1}" nohup python -u "$@" >>"$LOGD/$name.log" 2>&1 & echo $! >"$PIDDIR/$name.pid" )
    echo "$name started (pid $(cat "$PIDDIR/$name.pid")) — log: $LOGD/$name.log"
}

cmd="${1:-status}"
case "$cmd" in
    start)
        sync_tree
        start_one monitor tools/swarm/orchestrator.py --monitor
        comp="${2:-general}"
        if [ -n "${SHESH_WORKER_EXECUTOR:-}" ]; then
            start_one "worker-$comp" tools/swarm/worker_github.py --component "$comp" --github --poll 45 --executor "$SHESH_WORKER_EXECUTOR"
        else
            echo "worker not started: SHESH_WORKER_EXECUTOR unset (workers fail closed without one — by design)"
        fi
        ;;
    stop)
        for f in "$PIDDIR"/*.pid; do
            [ -e "$f" ] || continue
            name="$(basename "$f" .pid)"
            if is_running "$name"; then kill "$(cat "$f")" && echo "$name stopped"; fi
            rm -f "$f"
        done
        ;;
    status)
        for f in "$PIDDIR"/*.pid; do
            [ -e "$f" ] || continue
            name="$(basename "$f" .pid)"
            if is_running "$name"; then echo "● $name RUNNING (pid $(cat "$f"))"; else echo "○ $name dead"; fi
        done
        echo "--- heartbeats (fresh = daemon alive):"
        find "$TREE/swarm/heartbeats" -name '*.json' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -4 || echo "  none yet"
        echo "--- monitor log tail:"
        tail -3 "$LOGD"/monitor.log 2>/dev/null || echo "  (no log yet)"
        ;;
    logs) tail -n 50 "$LOGD"/*.log ;;
    *) echo "usage: $0 start [component] | stop | status | logs" >&2; exit 2 ;;
esac
