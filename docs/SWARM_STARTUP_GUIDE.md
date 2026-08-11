# SWARM STARTUP GUIDE — How many chats and what to send

> **Goal:** Run orchestrator + workers in parallel via GitHub as bus, without overwrite, with secure PAT password prompt every new session.

## How many Arena Agent Mode chats to open?

**Recommended: 5 chats** (tested balance — more than 4 increases git push conflicts)

| Chat # | Role | What it does | Component filter | Why |
|--------|------|--------------|------------------|-----|
| 1 | **Orchestrator** | Seeds GitHub Issues from TODO.md ⬜, monitors heartbeats, re-queues stale claims >10 min, dashboard | all | Brain of swarm, must be 1 only |
| 2 | **Worker-Brain** | Governance kernel tasks | `shesh-audit, shesh-secrets, shesh-brain, SheshAOS` | Brain layer, Rust + policy |
| 3 | **Worker-Mind** | Memory, model routing, harness, orchestrator, skills, calendar | `shesh-memory, shesh-mind, shesh-harness, shesh-orchestrator, shesh-skills, shesh-calendar` | Mind layer, LLM + RAG |
| 4 | **Worker-Soma** | Desktop body, voice, files, phone, containers | `shesh-files, shesh-shell, shesh-system, shesh-backup, shesh-phone, shesh-containers, shesh-mcp-bundle, shesh-acp, shesh-voice, shesh-desktop` | Soma layer, Hyprland + MCP |
| 5 | **Worker-Platform** | Ecosystem itself, docs, CI, swarm tooling | `shesh-ecosystem` (manifest, docs/adr, Containerfile, install.sh, swarm) | Platform/docs, no code overlap |

**Can it be further divided? Yes — two modes:**

- **Coarse (recommended now):** 4 workers by layer as above — minimal file overlap, 1 TODO task per worker at a time, low git conflicts.
- **Fine-grained (if you want 10+ workers):** 1 worker per component e.g., `shesh-memory` alone, `shesh-system` alone, etc. But then `manifests/components.toml` and `docs/` become contention hotspots — last merge wins, needs manual rebase more often. Use only if you have many independent components (e.g., `shesh-phone` and `shesh-calendar` don't touch same files).

**Start with 5, scale to 8 if needed.** Never more than 1 orchestrator.

---

## What to send to each chat — COPY-PASTE PROMPTS

All prompts start with reading `docs/NEXT_SESSION_PROMPT.md` (auto-generated, contains live metrics + PAT status). That file already contains your GitHub profile, all repos, PAT decryption instructions, and commands. You just add role specialization.

### Common preface for ALL chats (paste first)

```
Read docs/NEXT_SESSION_PROMPT.md FIRST — it is auto-generated with current PAT status need_password=true

You will be asked for password to decrypt GitHub PAT — when ask_user UI appears, give <YOUR_ENCRYPTION_PASSWORD> (or your custom). Tool will decrypt ~/.config/shesh/github.pat.enc -> plain 600 and then github_auth loads it.

After that:
cd /home/user && git pull origin main && python tools/session_guard.py --status && python tools/github_auth.py --check && make check

Then read docs/SESSION_HANDOFF.md, docs/SESSION_PROTOCOL.md, docs/SWARM.md, TODO.md
```

Then add role-specific below.

---

### Chat 1: Orchestrator (copy this whole block)

```
--- ORCHESTRATOR ---

You are ORCHESTRATOR for shesh-ecosystem, GitHub gaganjainse/shesh-ecosystem

Read docs/NEXT_SESSION_PROMPT.md FIRST (it contains PAT auto-prompt flow)
PAT encrypted at ~/.config/shesh/github.pat.enc — agent will ask password via ask_user, you give <YOUR_ENCRYPTION_PASSWORD> → decrypt → plain 600

cd /home/user && git pull origin main
python tools/session_guard.py --status
# if NEED_PASSWORD → ask_user will prompt → give <YOUR_ENCRYPTION_PASSWORD>
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check

Seed GitHub Issues from TODO:
SWARM_USE_GITHUB=1 python tools/swarm/orchestrator.py --seed TODO.md --dashboard

Then monitor:
python tools/swarm/orchestrator.py --monitor

Leave this tab open. It seeds queue, re-queues stale claims >10 min, dashboard every 60s.
Commit and push is done via PAT (already decrypted).

If guard says HOP → python tools/session_guard.py --handoff (deletes plain PAT for security) → git add -A && git commit -m "chore: handoff orchestrator" && git push origin main → close tab → open new with same prompt.
```

### Chat 2: Worker-Brain

```
--- WORKER-BRAIN ---

You are WORKER-BRAIN for shesh-ecosystem
Focus: Brain layer — shesh-audit, shesh-secrets, shesh-brain, SheshAOS kernel merge tasks
GitHub gaganjainse/shesh-ecosystem, PAT same flow as orchestrator (encrypted, ask password)

Read docs/NEXT_SESSION_PROMPT.md FIRST

cd /home/user && git pull origin main
python tools/session_guard.py --status
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check
ls src/ | grep -E "audit|secrets|brain|SheshAOS"

Work:
python tools/swarm/worker_github.py --component shesh-audit --github --poll 45
# This worker will only claim Issues with label component:shesh-audit or component:shesh-secrets etc.
# Atomic claim via lock ref swarm/claims/issue-N — first push wins, second fails Already claimed
# Branch per task: swarm/issue-N/<agent-id> → push → PR → swarm-auto-merge.yml auto-merges if make check green

If want file queue fallback (offline):
python tools/swarm/worker.py --component shesh-audit --poll 45

For kernel merge tasks (🔴 blocked — do NOT force, document only):
Read SheshAOS/KERNEL_MERGE_PLAN.md, port leaf crates first, never push red.

On hop: session_guard --handoff deletes plain PAT → push → close → new tab same prompt.
```

### Chat 3: Worker-Mind

```
--- WORKER-MIND ---

You are WORKER-MIND
Focus: Mind — shesh-memory, shesh-mind, shesh-harness, shesh-orchestrator, shesh-skills, shesh-calendar
GitHub gaganjainse/shesh-ecosystem

Read docs/NEXT_SESSION_PROMPT.md FIRST

cd /home/user && git pull origin main
python tools/session_guard.py --status
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check

Work:
python tools/swarm/worker_github.py --component shesh-memory --github --poll 45
# Or loop all mind components:
for comp in shesh-memory shesh-mind shesh-harness shesh-orchestrator shesh-skills shesh-calendar; do
  python tools/swarm/worker_github.py --component $comp --github --once
done

Mind tasks: RAG embeddings, role-router VRAM budget, /refine evaluator, SessionManager, semantic_search, habit learning.
Use GuardedMCP from shesh-audit, never hardcode secrets.
```

### Chat 4: Worker-Soma

```
--- WORKER-SOMA ---

You are WORKER-SOMA
Focus: Soma body — shesh-files, shesh-shell, shesh-system, shesh-backup, shesh-phone, shesh-containers, shesh-mcp-bundle, shesh-acp, shesh-voice, shesh-desktop
GitHub gaganjainse/shesh-ecosystem

Read docs/NEXT_SESSION_PROMPT.md FIRST

cd /home/user && git pull origin main
python tools/session_guard.py --status
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check

Work:
python tools/swarm/worker_github.py --component shesh-files --github --poll 45
# Or cycle:
for comp in shesh-files shesh-shell shesh-system shesh-backup shesh-phone shesh-containers shesh-mcp-bundle shesh-acp; do
  python tools/swarm/worker_github.py --component $comp --github --once
done

Soma tasks: Hyprland/Quickshell MCP, power/GPU/MUX, restic backup AC-gated, ADB safe-area, podman sandbox --cap-drop=ALL --network=none, third-party MCP bundle via Guard.
Hardware items (Hyprland@144, NVIDIA MUX, wake word) mark 🟡 not fake ✅ — manual verification only.
```

### Chat 5: Worker-Platform

```
--- WORKER-PLATFORM ---

You are WORKER-PLATFORM
Focus: shesh-ecosystem itself — manifests/components.toml, channels/*.lock, docs/adr, Containerfile, distrobox.ini, tools/install.sh, scripts/sign_artifacts.py, scripts/export_traces_otlp.py, CI, swarm tooling, GETTING_STARTED
GitHub gaganjainse/shesh-ecosystem

Read docs/NEXT_SESSION_PROMPT.md FIRST

cd /home/user && git pull origin main
python tools/session_guard.py --status
GITHUB_PAT_PASSWORD="<YOUR_ENCRYPTION_PASSWORD>" python tools/secure_pat.py --prompt
python tools/github_auth.py --check
make check

Work:
python tools/swarm/worker_github.py --component general --github --poll 60
# general picks docs, platform, TODO P1: Distrobox/Containerfile, installer btrfs snapshot+rollback, supply-chain sigstore, OTLP traces, ADRs, getting-started

Tasks: Keep docs/queries/QUERYLOG.md appended, TODO.md updated, make check green, locks deterministic, provenance.
```

---

## Further division? Yes — here's how

**If 5 not enough, split workers finer:**

- **Per-component workers (up to 19):** Open chat per component: `shesh-audit` alone, `shesh-memory` alone, etc. Use `--component shesh-memory`. Risk: `manifests/components.toml` edited by many workers → merge conflicts. Mitigate by having platform worker own manifest/locks, others only edit their `src/<component>/`.

- **Per-layer sub-workers:** Brain → `shesh-audit` worker + `shesh-secrets` worker; Mind → `shesh-memory` + `shesh-orchestrator`; Soma → `shesh-system` + `shesh-phone`. Up to 8-10 workers.

- **Docs worker:** Dedicated for ADRs, GETTING_STARTED, wiki sync — `component:general`.

**Rule:** Never more than 1 worker per component at same time. Use orchestrator dashboard `python tools/swarm/orchestrator.py --dashboard` to see who owns what.

**Atomicity guarantees still hold:** GitHub Issues lock ref `swarm/claims/issue-N` ensures only 1 worker owns issue, even with 10 workers. Branch per task prevents file overwrite. PR auto-merge Action ensures gate green before merge.

## Security & session hopping with swarm

- PAT encrypted at `~/.config/shesh/github.pat.enc` (600) — password <YOUR_ENCRYPTION_PASSWORD> — plain deleted on handoff
- Every new Arena tab: guard detects `need_password=true` → ask_user UI → you give password → decrypt → plain 600 → `github_auth` loads
- On handoff: `python tools/session_guard.py --handoff` deletes plain, keeps enc → next session prompts again
- No PAT in git — `.gitignore` has `.config/shesh/`
- No token in swarm files — only agent_id

## Commands to verify swarm working

```bash
# In orchestrator tab after seeding
python tools/swarm/orchestrator.py --dashboard
# Should show: Queue pending: 20+, Claims active, Heartbeats N agents

# List GitHub Issues queue
python tools/swarm/github_queue.py --list  # via API
# Or
gh issue list --label "swarm:pending" --limit 20  # if gh CLI

# Check auto-merge Action
cat .github/workflows/swarm-auto-merge.yml | head -n 40

# Check PAT
python tools/github_auth.py --check
python tools/secure_pat.py --check
```

Close this guide after reading — next step open 5 Arena tabs with prompts above.
