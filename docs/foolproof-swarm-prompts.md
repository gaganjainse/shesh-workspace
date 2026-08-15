# Foolproof Swarm Prompts — 5 Agents, New Clean Workspace, Encrypted PAT from GitHub

> **Problem before:** Other sandbox does not have `~/.config/shesh/github.pat.enc` — it lived on previous machine's home dir, not in repo, so password alone can't decrypt. Need raw PAT (insecure) or fetch encrypted file from GitHub.

> **Solution now:** Encrypted PAT uploaded to GitHub `gaganjainse/shesh-workspace` at `secrets/github.pat.enc` — safe to commit because encrypted, needs password to decrypt. New clean workspace fetches it via `curl` from raw GitHub, then auto-asks for password.

This doc treats you as **new clean workspace** (`/home/user` empty) and lists exactly what you need to set up to work properly, with foolproof prompts for 5 agents.

---

## Common Setup for ANY new clean workspace (do this first)

Every new Arena chat starts empty. Run these **exactly** in order:

```bash
# 1. Clone ecosystem (product clean) and workspace (factory messy)
cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem
git pull origin main
cd ../shesh-workspace
git pull origin main
cd /home/user/shesh-ecosystem

# 2. Fetch ENCRYPTED PAT from GitHub (now uploaded, foolproof)
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
ls -lh ~/.config/shesh/github.pat.enc  # should exist 341 bytes

# 3. Decrypt — will auto-prompt for password via ask_user UI
# Agent will call ask_user: "🔐 PAT encrypted found — need password"
# You give password: <YOUR_ENCRYPTION_PASSWORD> (or new password if you re-encrypted)
python tools/secure_pat.py --prompt
# Alternatively with env (if you set GITHUB_PAT_PASSWORD):
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt

# 4. Verify PAT loaded, never logs value
python tools/github_auth.py --check
# Should show: PAT found: gith****Q0WZ len 93

# 5. Setup efficient selective clone (not 22 repos 36M)
python tools/setup_worker.py --clean
du -sh . && find . -type f | wc -l  # should be <100 MB, <8000 files

# 6. Make check — must be GATE OK
make check

# 7. Read anchors
cat docs/SESSION_HANDOFF.md | head -n 60
cat docs/SESSION_PROTOCOL.md | head -n 40
cat TODO.md | grep -E "⬜|🔴|🟡" | head -n 20
```

If `github.pat.enc` fetch fails (network), fallback: `gh auth login` or set `GITHUB_PAT` env.

---

## 5 Foolproof Prompts — Copy-Paste Exactly

### Tab 1: Orchestrator (MUST open first)

```
--- ORCHESTRATOR — CLEAN WORKSPACE FOOLPROOF ---

You are ORCHESTRATOR for shesh-ecosystem, GitHub https://github.com/gaganjainse/shesh-ecosystem
Workspace: https://github.com/gaganjainse/shesh-workspace (factory, has secrets/github.pat.enc)

You are NEW CLEAN WORKSPACE — /home/user empty. Do setup first:

cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem

# Fetch ENCRYPTED PAT from GitHub (uploaded, safe, needs password)
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
ls -lh ~/.config/shesh/github.pat.enc

# Decrypt — I will ask for password via ask_user UI, you give <YOUR_ENCRYPTION_PASSWORD>
python tools/secure_pat.py --prompt
python tools/github_auth.py --check

# Efficient setup — platform role 0 repos, most efficient
python tools/setup_worker.py --role platform --clean
make check  # must be GATE OK 63 tests

# Read anchors
cat docs/SESSION_HANDOFF.md | head -n 80
cat docs/SESSION_PROTOCOL.md | head -n 40
cat TODO.md | grep -E "⬜|🔴|🟡" | head -n 20

# Seed Issues from TODO into GitHub Issues (proper implementation, atomic lock)
SWARM_USE_GITHUB=1 python tools/swarm/orchestrator.py --seed TODO.md --dashboard

# Monitor loop — leave open, re-queues stale >10 min, pushes heartbeat
python tools/swarm/orchestrator.py --monitor

If guard says HOP → python tools/session_guard.py --handoff (deletes plain PAT, keeps enc) → git add -A && git commit -m "chore: handoff orchestrator" && git push origin main (PAT already decrypted) → close tab → open new with same prompt.
```

### Tab 2: Worker-Brain

```
--- WORKER-BRAIN — CLEAN WORKSPACE FOOLPROOF ---
You are WORKER-BRAIN — Brain layer: shesh-audit https://github.com/gaganjainse/shesh-audit, shesh-secrets https://github.com/gaganjainse/shesh-secrets, shesh-brain https://github.com/gaganjainse/shesh-brain, SheshAOS https://github.com/gaganjainse/SheshAOS

You are NEW CLEAN WORKSPACE — do setup:

cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
python tools/secure_pat.py --prompt  # ask_user will prompt for password <YOUR_ENCRYPTION_PASSWORD>
python tools/github_auth.py --check
make check
python tools/setup_worker.py --role brain --clean  # 3 repos ~8M vs 22 repos 36M

# Work — GitHub Issues + atomic lock swarm/claims/issue-N (422 if exists) + PR + auto-merge Action
python tools/swarm/worker_github.py --component shesh-audit --github --setup --poll 45

On hop: session_guard --handoff deletes plain PAT → push → close → new tab same prompt, fetch enc from GitHub again, ask password.
```

### Tab 3: Worker-Mind

```
--- WORKER-MIND — CLEAN WORKSPACE FOOLPROOF ---
You are WORKER-MIND — Mind: shesh-memory https://github.com/gaganjainse/shesh-memory, shesh-mind https://github.com/gaganjainse/shesh-mind, shesh-harness https://github.com/gaganjainse/shesh-harness, shesh-orchestrator https://github.com/gaganjainse/shesh-orchestrator, shesh-skills https://github.com/gaganjainse/shesh-skills, shesh-calendar https://github.com/gaganjainse/shesh-calendar

NEW CLEAN WORKSPACE setup same as Tab1/2:

cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check
python tools/setup_worker.py --role mind --clean  # 7 repos ~2M

python tools/swarm/worker_github.py --component shesh-memory --github --setup --poll 45
```

### Tab 4: Worker-Soma

```
--- WORKER-SOMA — CLEAN WORKSPACE FOOLPROOF ---
You are WORKER-SOMA — Soma: shesh-files https://github.com/gaganjainse/shesh-files, shesh-shell https://github.com/gaganjainse/shesh-shell, shesh-system https://github.com/gaganjainse/shesh-system, shesh-backup https://github.com/gaganjainse/shesh-backup, shesh-phone https://github.com/gaganjainse/shesh-phone, shesh-containers https://github.com/gaganjainse/shesh-containers, shesh-mcp-bundle https://github.com/gaganjainse/shesh-mcp-bundle, shesh-acp https://github.com/gaganjainse/shesh-acp, shesh-media https://github.com/gaganjainse/shesh-media, shesh-messaging https://github.com/gaganjainse/shesh-messaging

NEW CLEAN WORKSPACE:

cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check
python tools/setup_worker.py --role soma --clean  # 9 repos ~2M

python tools/swarm/worker_github.py --component shesh-system --github --setup --poll 45
```

### Tab 5: Worker-Platform

```
--- WORKER-PLATFORM — CLEAN WORKSPACE FOOLPROOF ---
You are WORKER-PLATFORM — Platform: shesh-ecosystem itself https://github.com/gaganjainse/shesh-ecosystem, docs, ADR, Containerfile, install.sh, CI, swarm tooling, portfolio auto-update https://github.com/gaganjainse/portfolio (no forks proper priority)

NEW CLEAN WORKSPACE:

cd /home/user
git clone --depth 1 https://github.com/gaganjainse/shesh-ecosystem.git
git clone --depth 1 https://github.com/gaganjainse/shesh-workspace.git
cd shesh-ecosystem
mkdir -p ~/.config/shesh && chmod 700 ~/.config/shesh
curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc
chmod 600 ~/.config/shesh/github.pat.enc
python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check
python tools/setup_worker.py --role platform --clean  # 0 repos, most efficient 0M, 150 min session

python tools/swarm/worker_github.py --component general --github --setup --poll 60
```

---

## Why these prompts are foolproof

1. **Fetch encrypted PAT from GitHub** — `curl https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc` — works in new clean workspace, no file from previous machine needed. Encrypted file safe to commit (needs password).

2. **Auto-ask password** — `tools/secure_pat.py --prompt` calls `getpass` which in Arena triggers `ask_user` UI: "🔐 PAT encrypted found — need password" — you give `<YOUR_ENCRYPTION_PASSWORD>` via password prompt, not raw PAT in chat. Never logs PAT, redacts.

3. **Clean workspace setup** — `git clone --depth 1` shallow, `setup_worker.py --role X --clean` clones only needed repos (Brain 3 repos 8M vs 22 repos 36M), cleans `__pycache__, .pytest_cache, .ruff_cache`, keeps workspace <100 MB, session lasts 120-180 min not 30 min.

4. **No 22 repos waste** — Platform role 0 repos, Mind 7 repos ~2M, etc. `src/` persistence across sessions via gitignored but reused via `git pull --ff-only --depth 1`.

5. **Atomic claim** — `github_queue.py:claim_issue_atomic()` creates lock ref `refs/heads/swarm/claims/issue-N` via POST `/git/refs` — GitHub returns 422 if exists → first wins, second fails "already claimed" — tested real API issue #1/#2.

6. **Branch per task** — `swarm/issue-N/agent-id` — work isolated, `make check` gate, push, PR via `gh pr create` or API, auto-merge Action `swarm-auto-merge.yml` merges if green.

7. **True hours unattended** — `swarm-scheduled.yml` cron hourly janitor (true hours, uses `GITHUB_TOKEN` no PAT, no money) + `swarm-llm-worker.yml` every 2h picks Issue, calls free GitHub Models `gpt-4o-mini` via `GITHUB_TOKEN`, generates patch, pushes branch, PR, auto-merge merges.

8. **Secure handoff** — `session_guard.py --handoff` deletes plain PAT, keeps enc, generates `NEXT_SESSION_PROMPT.md` with live metrics + PAT status `need_password=true`, so next session auto-prompts for password.

Treat yourself as new clean workspace: clone ecosystem + workspace, fetch enc, decrypt, setup selective, make check, read SESSION_HANDOFF.md, pick next ⬜.

All GitHub links included.
