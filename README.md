# shesh-workspace — Messy dev workspace for shesh-ecosystem

This repo handles all messy works and systems so they don't get embedded in `shesh-ecosystem` (which stays clean).

**Purpose:** Session protocol, swarm (file + GitHub Issues), secure PAT with password, efficiency, model-agnostic llm adapter, omniroute integration, travel mode, etc — all dev tooling that was cluttering ecosystem repo and causing issues in new chats where both combined.

**Separation:**
- `shesh-ecosystem`: clean — manifest `manifests/components.toml`, locks `channels/*.lock`, docs `architecture/`, `GETTING_STARTED.md`, `MANUAL_VERIFICATION.md`, `AUDIT_AND_ROADMAP.md`, `GLOSSARY.md`, gates `scripts/resolve_manifest.py`, `check_licenses.py`, etc. No session protocol, no swarm.
- `shesh-workspace`: messy — `tools/session_guard.py`, `tools/secure_pat.py`, `tools/github_auth.py`, `tools/setup_worker.py`, `tools/llm_adapter.py`, `tools/model_router.py`, `tools/swarm/`, `tools/autopilot/`, `docs/SESSION_PROTOCOL.md`, `SWARM.md`, `TRAVEL_MODE.md`, `EFFICIENCY.md`, `MODEL_AGNOSTIC.md`, `.github/workflows/swarm-*.yml`, `Containerfile`, `distrobox.ini`, etc.

**Why:** You reported "both are combined in new chats" causing issues. Now ecosystem is product, workspace is factory. New chats for ecosystem work read only ecosystem docs. New chats for dev tooling work read workspace docs. No mixing.

**Workflow:**
- For ecosystem work (components): open chat, read `shesh-ecosystem/docs/SESSION_HANDOFF.md`, work on component, `make check`, push to `shesh-ecosystem`.
- For dev tooling work (session protocol, swarm): open chat, read `shesh-workspace/README.md` + `docs/SESSION_PROTOCOL.md`, work, push to `shesh-workspace`.
- Swarm orchestrator can run from workspace repo, seeding Issues into ecosystem repo via `SWARM_OWNER=gaganjainse SWARM_REPO=shesh-ecosystem`.

**Secure PAT:**
- Encrypted at `~/.config/shesh/github.pat.enc` (600) with password `Gagan#2003` (you set), plain deleted on handoff, auto-prompt next session via `ask_user` UI.
- `tools/secure_pat.py --prompt` decrypts, `tools/github_auth.py --check` loads, never logs value.

**Swarm:**
- File queue + GitHub Issues + atomic lock `swarm/claims/issue-N` (422 if exists) + PR + auto-merge Action `swarm-auto-merge.yml` + scheduled janitor `swarm-scheduled.yml` (hourly, true hours unattended while traveling)

**OmniRoute:**
- Forked `gaganjainse/OmniRoute` (from `diegosouzapw/OmniRoute`) — 291 providers, 90+ free, 500+ models, 1.53B free tokens/month, RTK+Caveman compression 15-95% tokens, MCP/A2A, Desktop/PWA, MIT
- Embedded as optional to local AI in ecosystem: `shesh-omniroute` component (planned) — local Ollama primary, OmniRoute optional cloud free fallback where you enable in finished product is your choice
- See `docs/MODEL_AGNOSTIC.md` for free providers study: Ollama local free, Groq free 14.4k req/day, OpenRouter :free, GitHub Models free (uses PAT), HuggingFace free, etc.

**True hours unattended:**
- Only GitHub Actions (`swarm-auto-merge.yml`, `swarm-scheduled.yml`, `ci.yml`) run on GitHub infra for hours, not Arena tabs. Push branch `swarm/issue-N/agent-id` + let Action merge, or add scheduled Action that runs `supervise.sh --loop` (would need LLM API key, but we use free deterministic stubs).
- For LLM coding for hours: `swarm-llm-worker.yml` Action that uses secret `OPENAI_API_KEY` + `tools/llm_worker.py` picks pending Issue, calls LLM API, generates patch, runs `make check`, pushes branch, opens PR — then auto-merge merges. Uses `GITHUB_TOKEN` not PAT for merge, true hours.

**Model-agnostic:**
- `manifests/models.toml` 15 free models with capabilities, `tools/llm_adapter.py` 5-layer guard (strict JSON schema, uniform prompt, validation+repair loop 3 retries, fallback chain free-first→stub, LLM-as-judge scoring 0..1 min 0.7), `tools/model_router.py` capability-based routing, `scripts/eval_model_agnostic.py` variance <0.1 valid 100%
- Workflow model-agnostic, you can setup omniroute and enable all free options, quality consistent.

**Travel mode:**
- 1 orchestrator tab on phone + GitHub Actions janitor hourly = true hours unattended for 1-2 days, no laptop, no 5 tabs. See `docs/TRAVEL_MODE.md`.

**Efficiency:**
- `tools/setup_worker.py --role mind --clean` clones only needed repos shallow --depth 1 --filter=blob:none, 36M→2M, 3400 files→500, session 60min→120-180min, free.

**Next session prompt:** `docs/NEXT_SESSION_PROMPT.md` auto-generated with live metrics + PAT status + swam
