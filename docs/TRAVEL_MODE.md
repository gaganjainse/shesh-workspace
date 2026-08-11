# Travel Mode — 1 Chat Open on Mobile, 1-2 Days No Laptop

> You are traveling, no laptop, only phone, can keep 1 Arena chat (orchestrator) open, maybe 2-3 workers in sidebar as long as arena.ai website not closed. You want true hours unattended.

## What actually keeps working when you keep arena.ai open on phone?

### Arena Agent Mode sidebar — truth

- **Arena Agent Mode chats are NOT independent daemons.** Each chat is a server-side LLM session that makes tool calls via your browser tab's WebSocket. When your phone screen locks or browser goes background, iOS/Android throttles timers and may freeze the tab after ~30-60 sec. Safari on iPhone is aggressive — background tabs suspended quickly. Chrome Android is slightly better but still throttles setInterval.
- **What “still keep working in sidebar” means:** Arena UI shows multiple chats in left sidebar. If you opened 5 chats earlier on laptop and left arena.ai website open on phone, those chat sessions **still exist server-side**, but their Python loops (`while True: sleep(45)`) **only progress when the LLM makes the next tool call**. The LLM only makes next tool call when the previous tool returned AND the model decides to continue. If your phone background-throttles the WebSocket, the tool return may be delayed, and the model may pause.
- **Our tests in this repo:** Workers use `time.sleep(45)` inside Python loop + `git pull --rebase`. If browser freezes, `sh()` call hangs waiting for subprocess, LLM waits, and after ~2-5 min Arena server may mark session as idle and stop auto-advancing. You will see “Continue” button appear — you must tap it on phone to resume. So **sidebar does NOT guarantee 1-2 days unattended**.
- **Orchestrator alone on mobile is okay:** It polls every 60 sec, but if you keep that one tab active (screen on, tap Continue when needed), it will seed Issues and heartbeat. That's better than 5 tabs fighting for background time.

### True hours unattended: GitHub Actions

GitHub Actions runs on GitHub's infra (Ubuntu runners), **not in your browser**. It can run for hours, even days, without your phone.

We have 3 Actions now:

| Action | File | Trigger | What it does for you while traveling | Needs PAT? |
|--------|------|---------|---------------------------------------|------------|
| **CI** | `ci.yml` | push to main/canary/devel, PR | ruff + pytest 30 + license + locks deterministic + clean check | No, uses `GITHUB_TOKEN` |
| **Swarm Auto-Merge** | `swarm-auto-merge.yml` | PR from `swarm/*` branches | If PR from worker (e.g., `swarm/issue-5/agent-X`) has green gates, auto-approves + squash merges + deletes branch + comments issue + labels `swarm:done` | No, `GITHUB_TOKEN` |
| **Swarm Scheduled Janitor** | `swarm-scheduled.yml` **NEW** | `cron: 0 * * * *` every hour + manual `workflow_dispatch` button | While you travel, every hour: resolve locks, sync `docs/components/` from `src/` if cached, ruff+pytest+license, seed GitHub Issues from TODO.md ⬜ (creates Issues with labels `swarm, swarm:pending, component:shesh-memory, P0`), re-queue stale claims >10 min no heartbeat, push changes to main | No, `GITHUB_TOKEN` |

**Janitor is true unattended for 1-2 days:**

- You go to https://github.com/gaganjainse/shesh-ecosystem/actions → click `Swarm Scheduled Janitor` → `Run workflow` → it runs even if your phone sleeps.
- Or it runs automatically every hour at minute 0 UTC.
- It uses `GITHUB_TOKEN` (auto-provided by GitHub, no PAT needed), has `contents:write, issues:write, pull-requests:write`.
- It does NOT do LLM coding (needs API key), but it does janitor work: keeps locks deterministic, docs sync, re-queues dead workers, seeds Issues so workers have work when you wake up.
- When you open orchestrator tab on phone, you see new Issues seeded by janitor overnight.

### What about pushing a branch `swarm/issue-N/agent-id` and letting Action merge?

This is the pattern for **true hours unattended coding** without keeping Arena tabs open:

1. **Before you travel** (on laptop or one-time in Arena): Worker (you or agent) does:
   ```bash
   git checkout -b swarm/issue-42/test-agent
   # edit src/shesh-memory/... or docs/...
   make check  # gate green
   git add -A && git commit -m "feat(shesh-memory): implement ..."
   git push origin swarm/issue-42/test-agent
   gh pr create --title "[swarm] issue 42" --body "Closes #42" --base main --head swarm/issue-42/test-agent --label swarm
   ```

2. **Then close laptop.** GitHub Action `swarm-auto-merge.yml` triggers on that PR (because `head_ref` starts with `swarm/`).
   - It checks out that branch on GitHub runner (not your laptop)
   - Runs `make check` (ruff, pytest, license, locks, component tests)
   - If green, it **auto-merges** via `gh pr merge --squash --auto --delete-branch`
   - Comments linked issue #42, labels `swarm:done`

3. Result: Your branch merged to main while you were traveling, **without any Arena tab open**. The Action ran for ~3-5 min on GitHub infra, not your phone.

**Limitation:** Step 1 still needs someone to push branch. Janitor Action cannot write code without LLM. So for 1-2 days traveling, best is:

- **Day 0 (before travel):** In Arena, run orchestrator → seed Issues → run 1-2 workers to push a few branches + PRs (e.g., 5 PRs for easy docs/tasks)
- **Days 1-2 traveling:** Janitor Action every hour keeps repo healthy + auto-merges those PRs if gates green. Orchestrator tab on phone (one tab) seeds more Issues when you tap Continue occasionally.
- **When back:** `git pull` — all janitor + auto-merged PRs are in main.

### Scheduled Supervise Loop — can it run for hours?

You asked: `scripts/supervise.sh --loop`

- **In Arena:** `supervise.sh --loop` calls `next_todo()` from TODO.md ⬜, then expects agent to implement, then runs gates, commits. It **requires LLM** to implement. In Arena, it can loop as long as agent keeps calling tools, but will hit hop after 60 min.
- **In GitHub Action:** We could run `supervise.sh --loop` in Action, but Action has no LLM to implement code — it would just loop picking TODO and failing to implement. So we made janitor Action do **non-LLM janitor tasks** (locks, docs sync, re-queue) which CAN run for hours unattended.

If you want true LLM coding for hours in GitHub Actions, you need to add an LLM API key secret (e.g., `OPENAI_API_KEY`) and a script that calls LLM to implement tasks — that's possible but not yet built. I can add `tools/llm_worker.py` that calls OpenAI/Anthropic/Ollama API to implement TODO, then Action could run it hourly.

### Recommended travel setup (1-2 days, phone only, one chat)

1. **Before leaving laptop:**
   ```bash
   python tools/secure_pat.py --handoff  # deletes plain, keeps enc
   git push origin main
   ```

2. **On phone — open 1 orchestrator tab (keep arena.ai open, screen on when possible, tap Continue when appears):**
   ```
   Read docs/NEXT_SESSION_PROMPT.md FIRST
   cd /home/user && git pull
   python tools/session_guard.py --status
   # Will say NEED_PASSWORD — ask_user appears → give <YOUR_ENCRYPTION_PASSWORD>
   GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
   python tools/github_auth.py --check
   make check
   SWARM_USE_GITHUB=1 python tools/swarm/orchestrator.py --seed TODO.md --dashboard
   python tools/swarm/orchestrator.py --monitor
   ```
   Leave this tab open. It seeds Issues hourly (when you tap Continue).

3. **Optional: Open 1-2 worker tabs in sidebar (if phone can keep them):**
   - Worker-Mind: `python tools/swarm/worker_github.py --component shesh-memory --github --poll 60`
   - Worker-Platform: `python tools/swarm/worker_github.py --component general --github --poll 60`
   - **Truth:** On mobile, background tabs may pause after 30-60 sec screen lock. Keep phone plugged, disable battery optimization for browser, keep arena.ai foreground. Even then, expect to tap Continue every 10-20 min. Not true hours, but better than nothing.

4. **Enable Janitor Action (true hours):**
   - Go to GitHub repo → Actions → `Swarm Scheduled Janitor` → Enable
   - It will run every hour automatically, even with phone locked, even for 2 days
   - It will seed Issues from TODO ⬜, re-queue stale claims, push locks/docs sync
   - Check runs at https://github.com/gaganjainse/shesh-ecosystem/actions

5. **When back on laptop:**
   ```bash
   git pull origin main
   python tools/session_guard.py --status
   make check
   python tools/swarm/orchestrator.py --dashboard  # see what janitor seeded and what workers did
   ```

### If you want me to add true LLM hours-unattended Action

I can add `.github/workflows/swarm-llm-worker.yml` that:
- Runs every 2 hours via cron
- Uses secret `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (you add in repo Settings → Secrets)
- Calls `tools/llm_worker.py` (I would write) that picks one pending Issue, calls LLM API to generate patch, runs `make check`, pushes branch, opens PR
- Then auto-merge Action merges it

That would be **true hours unattended coding** without any Arena tab open — runs purely on GitHub. It would use `GITHUB_TOKEN` + your LLM API key, not PAT.

Do you want me to add that? If yes, tell me which LLM provider (OpenAI, Anthropic, local Ollama via tunnel) and I will implement.

---

**Bottom line for travel 1-2 days phone-only:**

- Keep **1 orchestrator tab** open on phone, tap Continue when needed — it seeds Issues.
- **Don't rely on 4-5 sidebar workers on phone** — mobile OS will throttle them, they will pause.
- **Rely on GitHub Actions Janitor + Auto-Merge** for true hours — they run every hour on GitHub infra, no phone needed, seed Issues, re-queue stale, auto-merge PRs you pushed before travel.
- When back, `git pull` — everything janitor + auto-merge did is in main.

This is the honest best possible given Arena limits.
