# Next Session Prompt — COPY THIS WHOLE FILE into new Arena.ai Agent Mode

You are continuing **Shesh** — federated local-first AI OS for CachyOS/Hyprland
MSI Sword 16 HX B14VEKG (i7-14700HX, RTX 4050 6GB, 1920x1200@144).

**Owner:** Gagan Jain (@gaganjainse) — 53-repo fleet https://github.com/gaganjainse
**Main repo:** shesh-ecosystem **Target OS:** CachyOS 260628 + Hyprland 0.55 + Quickshell
**Lang policy:** Rust, Python 3.11+, Lua, QML/JS, Bash only — MCP/JSON (ADR-0001)

**Federation:**
- 23 components (organs) in manifests/components.toml (brain/mind/soma), 3 channels — 16 of them ship from the single shesh-core repo (ADR-0019)
- Locks: stable 1, canary 19, devel 23 — SHA256 audited
- Component repos (6): shesh-core, shesh-memory, shesh-orchestrator, shesh-harness, shesh-phone, shesh-omniroute + SheshAOS/shesha-kernel
- MCP servers: shesh-*-mcp, 9 in servers.json + containers/secrets/calendar
- Tests: 61 eco (make check), 235+ comp, 26 desktop, 872 SheshAOS (cargo) — all green 2026-08-13

**Stack must respect:**
- docs/SESSION_HANDOFF.md READ FIRST, live anchor
- docs/history/AUDIT_AND_ROADMAP.md 19 decisions D1-D19
- TODO.md ⬜todo ✅done 🟡in-progress 🔴blocked — 11 left
- docs/MANUAL_VERIFICATION.md 16-section checklist (hardware + rolling-deps + security + recovery drill)
- SECURITY.md + docs/THREAT_MODEL.md + docs/RECOVERY.md — canonical security posture/runbooks
- docs/policies/DEPENDENCY_POLICY.md — rolling-release ownership: agent bumps, downgrade-one break-glass
- docs/policies/DOCUMENTATION_POLICY.md + docs/STYLE_GUIDE.md + docs/INDEX.md — docs SSOT + nav root
- tools/book_build.py — shesh-docs pure projection (mirror map/fissions/orphan sweep); sync-docs.sh wraps it
- docs/history/queries/QUERYLOG.md full trail newest first — append after each user msg
- docs/SESSION_PROTOCOL.md 60-sec hop protocol (docs/SESSION_HOP_ALERT.md is transient, untracked)
- docs/history/adr/ 19 ADRs
- docs/GETTING_STARTED.md full install + Ollama 6GB stack
- Containerfile, distrobox.ini, tools/install.sh --channel

**GitHub PAT — SECURED WITH PASSWORD (auto prompt):**
- Encrypted file: ~/.config/shesh/github.pat.enc (600) — uses PBKDF2HMAC 200k + Fernet
- Plain file: ~/.config/shesh/github.pat (600) — auto-deleted on handoff for security
- Current: enc_exists=True plain_exists=False need_password=True
- Flow new session:
  1. Guard detects enc exists but plain missing → NEED_PASSWORD
  2. Agent automatically asks you for password via ask_user UI
  3. You give password (`YOUR_ENCRYPTION_PASSWORD`) → tools/secure_pat.py decrypts enc → plain 600
  4. tools/github_auth.py loads it, never logs value
- Manual: python tools/secure_pat.py --prompt (prompts GetPass) or --password `PW`
- Handoff: python tools/secure_pat.py --handoff deletes plain, keeps enc
- Alt providers if enc missing: env GITHUB_PAT/GH_TOKEN or gh auth login
- Do NOT echo PAT. Tool redacts.

**Commands FIRST in new session:**
```bash
cd /home/user
git pull origin main
python tools/session_guard.py --status
# If NEED_PASSWORD → agent will ask for password automatically
python tools/github_auth.py --check
make check   # GATE OK
ls src/ | wc -l  # component repos (shesh-core + 5 services)
cat docs/SESSION_HANDOFF.md
cat TODO.md | grep -E "⬜|🔴|🟡" | head -n 40
```

**Autopilot rules:**
1. Pick highest ⬜ not blocked from TODO.md
2. Branch feat/`THING` — small change one component
3. Tests — never push red — pytest -q -p no:cacheprovider
4. GuardedMCP from shesh-audit
5. No secrets in config — via shesh-secrets env:, gopass:, file:0600
6. After each user msg: append QUERYLOG.md, update TODO.md
7. Before push: session_guard --tick — if hop needed, handoff not new task
8. Archive not delete, no force-push main

**Handoff metrics (regenerated at hop):**
- Last state-refresh 2026-08-13 — run `python tools/session_guard.py --status` for live numbers

**CI closure status (2026-08-13, new session):**
- ✅ shesh-desktop lock-refresh GREEN — `cb044e2b4ae34f64bc4bc27674c5c686a1741acc` (libgirepository-2.0-dev on
  noble) → bot committed fresh lock `9e9e3984262952fd5df69710672cee97b9f4ed59`; stale desktop lock cleared.
- ✅ portfolio Auto-Update GREEN — `42e5b49abaf1d6073325cf8f70071233de2d78bd` (prettier-normalize after
  regeneration) + `20c651afd51f3507a980496de8f09a4ed6624271` (generator updated for the AI-OS repo rename; 8 curated,
  22/22 tests).
- ✅ AIM CI GREEN — `fdcd2aca13f23c2407e01be9275a7eb845417bd3` (tests patch the real repository module).
- ✅ ClinicLedger CI GREEN — `0ca279b402df54dfc25e90c3153872f8a7df3523` (gradle pin) + `e3e8880dc151bda680704dc21249e686e2b8966a` (wrapper jar
  un-ignored/restored) + `22dde978b7a3767195c2c6e0b675d8c3ff1e915d` (voice parser: phrase-based number groups,
  end-anchored name fillers, rokda/paisa dialects; 34/34 JVM tests).
- ✅ ClinicLedger-Template CI GREEN — `85cb9c3` + `134e050` + `30be902`
  (gradle pin, wrapper jar, gradlew script restored).
- ✅ Canary P0 e2e GREEN on arch/fedora/ubuntu (was red 3 days) — wiring
  fixes `75595fb8e5a5b1e591a86255e347b8b347261fcf`+`8e53e0128f933b97f2f70b521d9060974d5d3bca`; component README auto-sync + CI gate
  (`547a3742e049806cc26cad81e0fb4ae88fca5f94`); failure-memory offline loop tests + 2 real learner bug
  fixes (shesh-memory `c28e8c4947a5ec2bd52ebbf8473b6a54fd378943`); Vyakrti Rust CI fix (`2f67f8a0db88c6f0ebb453695b88075e8b74635b`);
  dompurify CVE closed via override in waveterm/vyakrti-ide/Vyakrti.
- Fleet: 183+ GREEN / 0 PENDING; pipecat transformers alerts CLOSED
  (`ea9e3af`+`a65576b` — dropped [smart] extra, lock bumped to 5.15.0).
- Fresh-session gotchas: `.git/config` (origin) + `~/.git-credentials` are
  excluded from Arena snapshots → re-add remote + credential helper +
  identity; reinstall cryptography/ruff/node24. Repo layout: this repo at
  /home/user root, components in /home/user/src.

**Swarm parallel:**
- docs/SWARM.md — GitHub as bus via swarm/ queue/claims/heartbeats
- Orchestrator: python tools/swarm/orchestrator.py --seed TODO.md --monitor (also supports --seed-issues for GitHub Issues)
- Workers: python tools/swarm/worker.py --component shesh-memory (file queue) OR python tools/swarm/worker_github.py --component shesh-memory --github (Issues + atomic branch + PR + auto-merge Action swarm-auto-merge.yml)
- PAT needed for push/PR — decrypted via password flow above

**Message to give you:** "Continue Shesh — read SESSION_HANDOFF first, TODO top-to-bottom, next ⬜. PAT encrypted at ~/.config/shesh/github.pat.enc — agent will ask password and decrypt. Run session_guard --status and make check."

---
Generated: 2026-08-11T16:49:08 by tools/session_guard.py --handoff · hand-refreshed 2026-08-13 (numbers/canon); regenerates on next hop
PAT status at gen: {'enc_exists': True, 'plain_exists': False, 'need_password': True}
