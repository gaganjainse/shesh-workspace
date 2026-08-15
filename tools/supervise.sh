#!/usr/bin/env bash
# supervise.sh — autonomous work loop for an AI agent on Shesh.
#
# Usage:
#   scripts/supervise.sh            # one tick (pick next todo, implement, commit)
#   scripts/supervise.sh --loop     # repeat until no actionable todos
#   scripts/supervise.sh --dry-run  # show what it would do, change nothing
#
# It does NOT replace the agent's judgment: it enforces the workflow from
# TODO.md — pick the next unblocked item, work on a branch, test, document,
# commit, and update TODO + QUERYLOG. Safety: never force-push, never delete
# repos, stop on test failure.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOOP=0; DRY=0
for arg in "$@"; do case "$arg" in
  --loop) LOOP=1 ;; --dry-run) DRY=1 ;; esac done

log(){ printf '\033[36m[supervise]\033[0m %s\n' "$*"; }

next_todo() {
  # Print the first ⬜ line in TODO.md that isn't under a 🔴 heading.
  awk '
    /🔴/{block=1} /^## /&&!/🔴/{block=0}
    /⬜/ && !block {print; exit}
  ' TODO.md
}

run() {
  if [ "$DRY" = 1 ]; then echo "DRY: $*"; else "$@"; fi
}

tick() {
  # --- Session guard check FIRST ---
  if [ -f tools/session_guard.py ]; then
    python3 tools/session_guard.py --tick || log "WARN: session_guard tick failed (continuing)"
    if [ -f docs/SESSION_HOP_ALERT.md ]; then
      log "🚨 SESSION HOP ALERT exists — recommend handoff before new task"
      head -n 20 docs/SESSION_HOP_ALERT.md
      # Don't start new big task if hop needed — finish and exit
      if grep -q "HOP RECOMMENDED" docs/SESSION_HOP_ALERT.md 2>/dev/null; then
        log "Hop needed — not starting new task, generating handoff"
        python3 tools/session_guard.py --handoff || log "WARN: handoff generation failed"
        return 1
      fi
    fi
  fi

  if [ ! -f TODO.md ]; then
    log "TODO.md missing — nothing to do"
    return 1
  fi
  local item
  # next_todo reads a file we just verified exists; an awk failure from here
  # is a real error and kills the tick loudly (set -e).
  item="$(next_todo)"
  if [ -z "$item" ]; then
    log "No actionable todos found."
    return 1
  fi
  log "Next: $item"
  local branch
  branch="feat/auto-$(date +%s)"
  run git checkout -b "$branch" 2>/dev/null || run git checkout "$branch"

  # The actual implementation is done by the agent (human or LLM) invoking this
  # script as part of its tool loop. This script enforces the gates AFTER work:
  if [ "$DRY" = 0 ]; then
    log "Running gates..."
    if [ -d tests ]; then python3 -m pytest tests/ -q || { echo "tests failed"; return 2; }; fi
    # Lint is a REAL gate: output visible, failure blocks the tick. Same scope
    # as `make lint` (scripts/ tests/ tools/).
    python3 -m ruff check scripts/ tests/ tools/ || { echo "lint failed"; return 2; }
  fi

  # Append to query log (agent fills in the answer).
  local today; today="$(date -u +%Y-%m-%d)"
  if [ "$DRY" = 0 ]; then
    cat >> docs/history/queries/QUERYLOG.md <<EOF

---

## Autopilot tick ($today)

Worked on: ${item}
(Branch: $branch — fill in outcome + doc links.)
EOF
  fi

  log "Commit + update TODO status for: $item"
  run git add -A
  if run git commit -q -m "wip: ${item//✅/}"; then
    :
  elif [ "$DRY" = 0 ]; then
    log "WARN: nothing was committed — the tick produced no changes"
  fi
  log "Tick complete on branch $branch. Push when ready."
}

if [ "$LOOP" = 1 ]; then
  while tick; do sleep 1; done
else
  tick
fi
