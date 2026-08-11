# Session Protocol — Hot Hopping Without Losing Flow

> **Problem:** shesh-ecosystem is massive (20 repos, 100+ tests, 40 docs). One Arena.ai session slows down after ~60 min / 100 MB / 8000 files / many tool calls. Context overflows, tool latency spikes, and we get interrupted.

This doc makes session hopping **perfect** — zero loss, zero re-explaining.

---

## 1. The 60-second handoff (you do this)

When guard says **HOP NOW** or you feel lag:

```bash
cd ~/shesh-ecosystem   # or /home/user
python tools/session_guard.py --status
python tools/session_guard.py --handoff   # generates NEXT_SESSION_PROMPT + handoff.json
make check
git status
git add -A
git commit -m "chore: handoff $(date -Iseconds) — $(cat docs/SESSION_HANDOFF.md | head -n1)"
git push origin main
```

Then close this chat. You are done.

Open a **new Agent Mode chat** and paste the content of `docs/NEXT_SESSION_PROMPT.md` (see §3). That's it — the new AI knows everything.

**Time:** ~60 seconds. No re-explaining.

---

## 2. How the guard decides to hop (automatic)

`tools/session_guard.py` runs on every autopilot tick and logs to `~/.local/share/shesh/session_guard.jsonl`:

| Metric | Threshold → HOP alert |
|--------|-----------------------|
| Workspace size `du -sh /home/user` | >100 MB |
| File count `find /home/user -type f \| wc -l` | >8000 |
| Session age (first guard log → now) | >60 min |
| Avg tool latency last 10 calls | >5s (Arena slowdown) |
| Uncommitted changes | >20 files |
| `make check` fails | Immediate HOP + rollback |

When threshold hit, it creates `docs/SESSION_HOP_ALERT.md` with red banner and prints:

```
🚨 SESSION HOP RECOMMENDED — reason: workspace 112 MB >100 MB, 94 min old
👉 Run: python tools/session_guard.py --handoff && git push
```

The autopilot runner `tools/autopilot/runner.py` calls guard before each task — if HOP needed, it finishes current task, commits, pushes, and exits cleanly instead of starting new big task.

Integration points:
- `scripts/supervise.sh` — loop calls `session_guard.py --tick`
- `tools/autopilot/gate.py` — gate calls guard after tests
- `tools/autopilot/cli.py` seed/run — checks guard

---

## 3. What you paste in next session (zero explanation)

File `docs/NEXT_SESSION_PROMPT.md` is **auto-generated** by `session_guard.py --handoff`. It contains:

- Your GitHub: `gaganjainse` (owner of 27 repos)
- Project: shesh-ecosystem federation (19 components, 3 channels, manifest `manifests/components.toml`, locks `channels/*.lock`, 30 ecosystem tests, 182 component tests in `src/`)
- Stack: Rust + Python + Lua/QML/Bash, rootless Podman, uv, pipx MCP servers `shesh-*-mcp`
- Workflow: read `docs/SESSION_HANDOFF.md` FIRST, then `AUDIT_AND_ROADMAP.md`, `TODO.md`, `MANUAL_VERIFICATION.md`, `queries/QUERYLOG.md`
- Session protocol: this doc, how to hop
- PAT: **NOT included** but instructions how to provide: set env `GITHUB_PAT` or file `~/.config/shesh/github.pat` with 0600, or `gh auth login`. The tool `tools/github_auth.py` reads it securely.
- Commands: `cd /home/user && git pull && make check && python tools/session_guard.py --status`

You don't type anything else. Just paste that file.

Example NEXT_SESSION_PROMPT (template, generated file has live numbers):

```md
You are continuing Shesh — local-first AI body for CachyOS/Hyprland on MSI Sword 16 HX.
GitHub owner: gaganjainse. Main repo: shesh-ecosystem. Cloned components in /home/user/src.
Read docs/SESSION_HANDOFF.md FIRST, then AUDIT_AND_ROADMAP, TODO, MANUAL_VERIFICATION, QUERYLOG.
Your PAT: set GITHUB_PAT env or ~/.config/shesh/github.pat (0600) — do not echo it.
Run: git pull origin main && make check && python tools/session_guard.py --status
Then pick next ⬜ from TODO.md and continue autopilot.
```

**Why other AIs didn't know your profile before:** Arena resets workspace each session. Without this protocol, every session starts empty. With it, GitHub is source of truth and NEXT_SESSION_PROMPT bootstraps context in 1 paste.

---

## 4. Files that make hopping work

- `docs/SESSION_HANDOFF.md` — live anchor, updated after each task. Contains repo list, done/remains, commands.
- `docs/SESSION_PROTOCOL.md` — this file
- `docs/NEXT_SESSION_PROMPT.md` — auto-generated, copy-paste for next session
- `docs/queries/QUERYLOG.md` — every user prompt + answer, newest first
- `TODO.md` — single source of tasks ⬜/✅/🟡/🔴
- `tools/session_guard.py` — health monitor + handoff generator
- `tools/github_auth.py` — secure PAT loader (env/file/gh, 0600 check, refuses world-readable)
- `tools/autopilot/` — ledger at `~/.local/share/shesh/autopilot/ledger.jsonl` persists across sessions via GitHub push

All are committed to `main` before hop — no local-only state.

---

## 5. Emergency: session interrupted mid-work

Arena can kill session without warning (workspace-over-budget). Mitigation:

- Every autopilot task commits after gate green (`safe_commit` + `safe_push`)
- Ledger is append-only JSONL, pushed each task — next session replays `ledger.next_pending()`
- If interrupted: new session runs `git pull`, `ledger` finds last task `running` → `rollback()` soft resets and redoes

No data loss if you push frequently (autopilot does every ~5 min).

---

## 6. Quick reference

```bash
# Check health anytime
python tools/session_guard.py --status
# -> {workspace_mb: 61, file_count: 3421, age_min: 23, avg_latency_ms: 120, hop: false}

# Force handoff file
python tools/session_guard.py --handoff
cat docs/NEXT_SESSION_PROMPT.md  # copy this

# Clean to reduce size before hop
python tools/session_guard.py --clean
# removes __pycache__, .pytest_cache, .ruff_cache, .venv, .cache, target/
```

**Rule:** When guard says HOP, don't argue — 60s handoff is cheaper than 30 min slowdown.
