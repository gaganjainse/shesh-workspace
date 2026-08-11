# Exhaustive Audit — All Repos (54 unique) — 2026-08-11

Generated from `src/all-repos` (41) + `src/forks` (13) + `src/` (22) — shallow --depth 1 clones, total 1.5G src/ + 508M all-repos + 879M forks.

Source: `docs/AUDIT_EXHAUSTIVE.json` (54 entries)

## Summary

| Category | Count | Notes |
|----------|-------|-------|
| **User repos total** | 41 | gaganjainse/* from API |
| **Shesh family** | 22 | shesh-* + SheshAOS/SeshaOS/shesha-kernel/OmniRoute/shesh-omniroute/shesh-workspace |
| **Other personal** | 11 | AIM, ClinicLedger, FWRS, GameVault, Vyakrti, ePustakalay, grievance-portal, llm-eval-harness, rag-service, portfolio, ollama (fork) |
| **Forked upstreams** | 13 | prime-agent, Memento-Skills, phone-harness, servers (modelcontextprotocol), Hermes, Hyprland-Dots, hyprdots, leon, pipecat, openWakeWord, browser-use, khoj, OmniRoute |
| **Total unique audited** | 54 | Deduplicated by name |

All have README; most shesh-* have pyproject + tests + CI; personal have mixed.

## Detailed per repo (from audit script)

```
Name                           readme pyproj tests ci license size last_commit
AIM                            True   False  True  True True 20M b2e774e docs: fix test count — 84 -> 101
ClinicLedger                   True   False  False True True 12M f67470b updated dimension
ClinicLedger-Template          True   False  False True True 1.1M bd5f2c9 Properly fill About section
FWRS                           True   False  True  False True 625K 7072149 Update copyright year
GameVault                      True   False  False False True 1.8M b0f0a93 Add Apache 2.0 license
...
shesh-acp                      True   True   True  True False 244K 4226d30 rename: Shesha -> Shesh
shesh-audit                    True   True   True  True False 290K d6c48e5 feat: GuardedMCP
...
shesh-voice                    True   False  False True True 41M 37ce9c2 feat: Shesha Voice overlay
shesh-workspace                True   False  False True False 679K fbb77e3 feat: add omniroute study
SheshAOS                      True   False  True  True False 7.5M 1246d4f chore: remove last nexusaos references
SeshaOS                        True   False  False False False 241K 8459e5d Add sesha bootstrap
shesha-kernel                  True   False  True  True False 4.5M bedb887 Replace auto-delete with smart-sort
OmniRoute (gaganjainse)        True   False  True  True True 260M bc92c06 fix(translator)
...
```

Full JSON at `docs/AUDIT_EXHAUSTIVE.json`

## Gaps per layer (honest)

### Brain (governance)
- SheshAOS 7.5M Rust 981 tests — last commit chore remove nexusaos refs — needs kernel merge with shesha-kernel (🔴 blocked, type-diverged 57 errors, russh msg removed, zig required)
- shesh-audit 290K 20 tests — GuardedMCP done, Nexus bridge done, secrets multi-backend done, but needs CI release gate integration (was ⬜, now done via ci.yml audit guard sanity)
- shesh-secrets 180K 8 tests — env/gopass/keepassxc/file backends, refuses world-readable — done
- shesh-brain missing — packaged nexusaos-kernel for desktop — ⬜ todo, should be created from SheshAOS crates

### Mind (deliberation)
- shesh-mind 240K 13 tests — role→model router VRAM budget — done, but now model-agnostic router (tools/model_router.py) capability-based free-first, not hardcoded
- shesh-memory 400K 26 tests — episodic/semantic/intention/mannerism/habit + FTS + vector embeddings local hash + Ollama nomic-embed-text + compaction — done
- shesh-harness 284K 14 tests — continual harness immutable base + /refine held-out evaluator must_contain/must_not_contain score 0.7 — done
- shesh-orchestrator 428K 28 tests — multi-agent RLM runtime roles A2A UDS broker, persistent sessions start/get/list/cancel, LLMAgents Ollama + stubs, traces JSONL — done
- shesh-skills 259K 10 tests — notes/web-search/fetch/git/docs/reminders + 5 markdown skills — done
- shesh-calendar 188K 6 tests — iCal vdir — done
- shesh-omniroute 120K — NEW — wrapper for OmniRoute 291 providers 90+ free 1.53B tokens/mo RTK+Caveman 15-95% compression, optional to local Ollama primary

### Soma (body)
- shesh-files 211K 5 tests — Rust watcher + Python classifier — done
- shesh-shell 177K 3 tests — Hyprland/Quickshell MCP — done
- shesh-system 233K 13 tests — power/GPU/MUX, update check read-only, health, maintenance — done
- shesh-voice 41M fork Newelle — wake word "hey shesh" openwakeword, STT faster-whisper, TTS Piper, overlay MCP config — done
- shesh-desktop 22M fork end-4/dots-hyprland — CachyOS/Hyprland dotfiles, ambient scheduler catch-up OnStartupSec+jitter+AC/idle, warm proactivity ≤3/day — done
- shesh-backup 208K 8 tests — restic wrapper AC+daily gating, verify — done
- shesh-phone 184K 7 tests — ADB safe-area tapping — done
- shesh-containers 192K 5 tests — podman/distrobox sandboxed --cap-drop=ALL --network=none — done
- shesh-mcp-bundle 207K 4 tests — filesystem/fetch/git proxied through Guard — done
- shesh-acp 244K 12 tests — ACP server session/prompt/terminal/exec/fs/diff/cancel/perm — done

### Platform / Infrastructure
- shesh-ecosystem 1.5M 30 tests — manifest resolver, license gate, 3 channels stable/canary/devel, MCP config generator servers.json+Zed/Newelle, canary e2e covering all 16 components, Containerfile, distrobox.ini, install.sh with btrfs snapshot+rollback, supply-chain sign_artifacts.py + SLSA provenance, OTLP export, CI gates, swarm auto-merge + scheduled janitor + llm-worker free
- shesh-workspace 679K — dev factory separation — session protocol, swarm file+Issues atomic lock via swarm/claims/issue-N 422 if exists + PR + auto-merge Action, secure PAT password flow PBKDF2HMAC 200k + Fernet, efficiency selective clone 36M→2M, model-agnostic llm_adapter 5-layer guard, travel mode 1 orchestrator tab + Actions true hours
- OmniRoute fork 260M — 38.9k★ 5.1k forks, 291 providers, 90+ free, 500+ models, 1.53B tokens/mo, 19 routing strategies, 12-engine compression, 105 MCP tools, A2A, Desktop/PWA, MIT

### Other personal (not Shesh, leave untouched per decision D8)
- AIM — attendance Flask MySQL Argon2id 101 tests — production-ready, not deployed live per README
- ClinicLedger, VillageClinicLedger, FWRS, GameVault, Vyakrti, ePustakalay, grievance-portal, llm-eval-harness, rag-service, portfolio, ollama fork, etc — all have README, some CI, leave untouched, no delete (archive not delete policy)

## Loose ends (from TODO.md before this audit)

From earlier TODO (2026-08-09):
- ⬜ shesh-brain — packaged nexusaos-kernel — still todo
- ⬜ Messaging bridges Telegram/Signal isolated opt-in
- ⬜ Media screenshots, screen recording, wallpaper, audio routing
- ⬜ ACP tested against Zed/JetBrains (protocol done, manual verification needed)
- ⬜ Video/demo of voice + settings + organizer flow
- ⬜ Distrobox/Containerfile — DONE in this session Containerfile + distrobox.ini
- ⬜ Installer channel support btrfs snapshot+rollback — DONE tools/install.sh
- ⬜ Supply-chain sigstore/provenance — DONE scripts/sign_artifacts.py + SLSA + ci.yml
- ⬜ Integrate shesh-audit into CI — DONE ci.yml audit guard sanity
- ⬜ Doc sync when component changes copy README into docs/components/ — DONE this session synced 17
- ⬜ ADRs — DONE 15 ADRs docs/adr/
- ⬜ Getting-started guide — DONE docs/GETTING_STARTED.md
- 🟡 Skill capture framework automatic Read→Execute→Reflect→Write — partial, framework exists but auto capture remains
- 🔴 Hardware tests Hyprland@144 NVIDIA MUX wake word PipeWire Quickshell render — must run on MSI canary VM
- 🔴 shesh-kernel → SheshAOS merge — type-diverged, do NOT force, staged crate-by-crate plan in KERNEL_MERGE_PLAN.md

## Upgrade plan — clear base for multi-agent

Goal: Leave no loose ends, upgrade whole system according to current progress so you can proceed further with clear base multi-agent.

Steps (this doc is step 1 audit, next steps clear backlogs):

1. **Finish backlog P1 (unblocked):**
   - Create shesh-brain minimal wrapper (packaged SheshAOS kernel for desktop, routes tool calls through policy) — 1 crate + Python shim
   - Messaging bridges as isolated opt-in services (Telegram/Signal) — create shesh-messaging component spec, but leave implementation ⬜ if needs phone?
   - Media tools — screenshots (grim+slurp), screen recording, wallpaper, audio routing — add to shesh-system or new shesh-media
   - ACP tested against Zed/JetBrains — document manual verification, mark 🟡 not ⬜
   - Video/demo — create demo script, but leave as future 💡 unless you have screen recording

2. **Supply-chain + CI already done** — verify gates green

3. **Workspace separation done** — shesh-workspace holds messy dev, shesh-ecosystem clean product, shesh-omniroute gateway optional

4. **Model-agnostic + free big models** — manifests/models.toml 15 free, llm_adapter 5-layer, model_router capability-based, eval harness variance <0.1, OmniRoute forked 291 providers 90+ free 1.53B tokens/mo

5. **True hours unattended** — swarm-scheduled.yml cron hourly janitor true hours, swarm-llm-worker.yml free GitHub Models gpt-4o-mini via GITHUB_TOKEN no money, picks Issue, generates patch, make check, pushes branch, PR, auto-merge merges if green

6. **Efficiency** — setup_worker.py selective shallow clone 36M→2M, file queue vs Issues API offline faster, PAT encrypted auto-prompt every new session, deterministic stubs offline no OpenAI cost

7. **Multi-agent clear base:**
   - 1 orchestrator + 4 workers by layer (Brain/Mind/Soma/Platform) recommended — 5 Arena tabs — or further divided per-component up to 19 workers
   - Atomic claim via lock ref swarm/claims/issue-N (422 if exists) — tested real API issue #1/#2 claim A ok B fails
   - Branch per task swarm/issue-N/agent-id — no overwrite, PR + auto-merge Action
   - Heartbeat + re-queue stale >10 min
   - Secure PAT password <YOUR_ENCRYPTION_PASSWORD>, encrypted .enc 600, plain deleted on handoff, auto-prompt next session via ask_user

Next: Execute step 1 backlog clearing in this same session? User said start nothing new but clear all backlogs. We should proceed to clear.

## Metrics

- Total repos cloned: 41 all-repos + 13 forks + 22 src/ old = 54 unique audited (some overlap)
- Size: src/ 1.5G, all-repos 508M, forks 879M = ~2.9G total on disk — will cause workspace-over-budget if not cleaned before snapshot, so clean after audit (keep only ecosystem + workspace, delete src/all-repos, src/forks after audit json saved)
- Ecosystem tests: 30 passed GATE OK
- Component tests: 182+ passed where deps present (some need mcp)
- Locks: stable 1, canary 16, devel 20 (including shesh-omniroute)
- ADRs: 15
- Docs: 40+ in ecosystem, 10+ in workspace

## Next actions (to clear backlogs)

- Create shesh-brain minimal
- Create shesh-media or extend shesh-system with media tools
- Mark ACP tested as 🟡 manual verification
- Create demo script placeholder
- Verify CI gates green
- Upgrade system: bump versions, update TODO statuses, push
