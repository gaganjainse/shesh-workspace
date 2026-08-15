# session_guard.py — session health monitor and handoff generator

Status: living · last verified 2026-08-13
Source: `tools/session_guard.py` · Protocol: [SESSION_PROTOCOL](history/session-protocol.md)

Watches the Arena.ai session for the slowdown patterns that preceded past
context overflows, and produces the hop artifacts before quality degrades.

## Metrics and thresholds

Logged to `~/.local/share/shesh/session_guard.jsonl` on every tick:

| Metric | HOP threshold |
|---|---|
| Workspace size (`du -sh /home/user`) | > 100 MB |
| File count | > 8000 |
| Session age (first guard log → now) | > 60 min |
| Avg tool latency, last 10 calls | > 5 s |
| Uncommitted changes | > 20 files |
| `make check` failing | immediate HOP |

## Commands

```bash
python tools/session_guard.py --status    # read-only health report
python tools/session_guard.py --tick      # autopilot tick: log + alert if hot
python tools/session_guard.py --handoff   # write NEXT_SESSION_PROMPT + handoff.json
python tools/session_guard.py --clean     # drop caches/veneers to shrink workspace
```

## Behavior notes

- On threshold breach the guard writes `docs/SESSION_HOP_ALERT.md`. The file
  is **untracked by design** — a committed alert lies within hours (see
  `.gitignore` and the archived example in `docs/history/attic/`).
- `--status` is read-only. The 2026-08-11 incident (session guard deleting
  the plain PAT mid-flight) is why PAT cleanup happens only on explicit
  `--handoff` — see
  the 2026-08-11 multi-tab swarm incident (post-mortem not carried into this repository).
