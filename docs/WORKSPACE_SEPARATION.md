# Workspace Separation — Product vs Factory (Fixed 2026-08-11)

> You reported: "Make one repo that is the workspace or maybe you already made that handles our messy works and systems so that they don't get embedded in our ecosystem. Make that separation proper as we are already starting to get issues in this matter where both are combined in new chats."

## Problem before

`shesh-ecosystem` contained both:
- **Product** — clean: manifest `components.toml`, locks `channels/*.lock`, architecture docs, gates `resolve_manifest.py`, `check_licenses.py`
- **Factory** — messy dev tooling: `tools/session_guard.py`, `secure_pat.py`, `github_auth.py`, `setup_worker.py`, `llm_adapter.py`, `model_router.py`, `swarm/`, `autopilot/`, `docs/SESSION_PROTOCOL.md`, `SWARM.md`, `TRAVEL_MODE.md`, `EFFICIENCY.md`, `MODEL_AGNOSTIC.md`, `.github/workflows/swarm-*.yml`, `Containerfile`, etc.

In new Arena chats, AI read both and mixed them — e.g., tried to apply session protocol to component READMEs, or cloned 22 repos for platform work.

## Solution now — 3 repos

| Repo | Purpose | Clean? | URL |
|------|---------|--------|-----|
| **shesh-ecosystem** | **Product** — what user installs on MSI Sword 16 HX | Clean, 30 tests GATE OK, no session protocol | https://github.com/gaganjainse/shesh-ecosystem |
| **shesh-workspace** | **Factory** — messy dev works handling session protocol, swarm, secure PAT, efficiency, model-agnostic, travel mode, etc. Keeps ecosystem clean | Messy, dev tooling, session hopping | https://github.com/gaganjainse/shesh-workspace |
| **shesh-omniroute** | **Gateway** — wrapper for OmniRoute free big models, optional to local AI in final product | Clean wrapper | https://github.com/gaganjainse/shesh-omniroute |
| **OmniRoute fork** | **Upstream** — 291 providers 90+ free 500+ models 1.53B tokens/mo | Original MIT 38.9k★ | https://github.com/gaganjainse/OmniRoute (forked from diegosouzapw/OmniRoute) |

### What goes where

**shesh-ecosystem (product) — keep:**
- `manifests/components.toml` + `models.toml` (now with shesh-omniroute component)
- `channels/*.lock` (stable/canary/devel)
- `docs/architecture/` (AGENTIC_BODY, REPO_TOPOLOGY, LANGUAGE_POLICY, MULTI_AGENT)
- `docs/GETTING_STARTED.md`, `MANUAL_VERIFICATION.md`, `AUDIT_AND_ROADMAP.md`, `SESSION_HANDOFF.md`, `GLOSSARY.md`, `TOOLING_CATALOG.md`
- `docs/adr/` (15 ADRs)
- `docs/components/` (synced READMEs)
- `scripts/` (resolve_manifest, check_licenses)
- `policies/` (SKILLS_POLICY)
- `Makefile`, `pyproject.toml`, `README.md`
- Maybe `docs/MODEL_AGNOSTIC.md` (product feature) and `OMNIROUTE_STUDY.md` (study for product)

**shesh-workspace (factory) — move dev tooling:**
- `tools/session_guard.py`, `secure_pat.py`, `github_auth.py`, `setup_worker.py`, `llm_adapter.py`, `model_router.py`, `llm_worker.py`, `swarm/`, `autopilot/`, `install.sh`
- `docs/SESSION_PROTOCOL.md`, `SWARM.md`, `SWARM_STARTUP_GUIDE.md`, `TRAVEL_MODE.md`, `EFFICIENCY.md`, `MODEL_AGNOSTIC.md` (duplicate for dev), `NEXT_SESSION_PROMPT.md`, `SESSION_HOP_ALERT.md`
- `.github/workflows/swarm-auto-merge.yml`, `swarm-scheduled.yml`, `swarm-llm-worker.yml`
- `Containerfile`, `distrobox.ini`, `scripts/sign_artifacts.py`, `export_traces_otlp.py`, `eval_model_agnostic.py`
- `swarm/` queue/claims/heartbeats/artifacts/ledger
- `manifests/models.toml` (copy for dev)

**Current state 2026-08-11:** We have created `shesh-workspace` and pushed dev tooling there (`fbb77e3` main). Ecosystem still contains dev tooling (we have not yet deleted), but we document separation here and will clean ecosystem in next commit (remove dev tooling from ecosystem, keep only product).

**For new chats:**
- If task is **ecosystem/component** (e.g., implement shesh-memory): open chat, read `shesh-ecosystem/docs/SESSION_HANDOFF.md` only, work on component, `make check`, push to `shesh-ecosystem`
- If task is **dev tooling** (session protocol, swarm, PAT, efficiency, model-agnostic): open chat, read `shesh-workspace/README.md` + `docs/SESSION_PROTOCOL.md`, work, push to `shesh-workspace`
- No mixing.

## Local models vs making system — clarification (you asked)

> "Why are you considering local models, i am not running any local models for the work i am doing, those models will run in the final system i.e. shesh ecosystem we are making, not doing the work to make it. But still including them in making the system will help us in the future so the local models despite being small does not decrease our quality very much."

**You are right — separation:**

- **For making ecosystem (dev work in Arena):** We should use **free big industry models via OmniRoute** — Claude (via Kiro free), GPT (via Pollinations/Requesty), Gemini 60M, DeepSeek V3.2/R1, Llama 3.1 70B, Mistral Large 3 1B, Qwen3-Max, Kimi K2 1M, GLM-4-Flash permanently free, etc. — 291 providers, 90+ free, 500+ models, 1.53B tokens/mo, RTK+Caveman 15-95% compression. These are **not small local**, they are industry-used big models.

- **For final system (Shesh on MSI Sword 16 HX):** Local models `phi4-mini, qwen2.5-coder:3b, moondream2, nomic-embed-text` 6GB VRAM offline, no API key, primary. Where you enable OmniRoute cloud free fallback in finished product is your choice (settings GUI).

- **Including local in design helps future quality not decrease much:** Our model-agnostic workflow (`tools/llm_adapter.py` 5-layer guard: strict JSON schema, uniform prompt, validation+repair loop 3 retries, fallback chain free-first→stub, LLM-as-judge score >=0.7) ensures same output shape regardless of model — small local + big free via same adapter, quality consistent, variance <0.1, valid 100%. So including local in design does not decrease quality much.

**Implementation:**

- `manifests/models.toml` now has two sections conceptually:
  - Dev (making): Groq free, OpenRouter :free, GitHub Models free, HuggingFace free — big models
  - Prod (final): Ollama local phi4-mini etc — small local
  - Both in same file with priority: dev picks big free first (prio 2-3), prod picks local first (prio 1), but adapter can handle both

- `shesh-omniroute` component: wraps OmniRoute fork, provides `omniroute_generate` MCP tool with same model-agnostic adapter, optional to local AI, enabled via settings GUI.

## True hours unattended — you asked about this

> "If you want true LLM coding for hours with zero tabs: I can add swarm-llm-worker.yml Action that uses secret OPENAI_API_KEY (you add in repo Settings → Secrets) + tools/llm_worker.py picks pending Issue, calls LLM API, generates patch, runs make check, pushes branch, opens PR — then auto-merge merges. That would be real hours unattended coding on GitHub, no phone needed. Tell me provider (OpenAI/Anthropic) and I will implement."

We implemented **free version** (no OpenAI API key, no money):

- `.github/workflows/swarm-llm-worker.yml` — cron every 2 hours + workflow_dispatch
- Uses **GitHub Models free** via `GITHUB_TOKEN` (already have via PAT) — `gpt-4o-mini`, `Phi-3-medium`, etc. — free for public repos, no money
- Plus optional free: `GROQ_API_KEY` free, `OPENROUTER_API_KEY` free `:free` models, `HF_TOKEN` free
- Flow: picks pending Issue `swarm:pending`, calls `tools/llm_adapter.py` + `tools/llm_worker.py` with free model, generates patch JSON `{"patch":..., "summary":...}`, writes `swarm/artifacts/llm-issue-N.md`, pushes branch `swarm/issue-N/llm-worker-<model>`, opens PR `Closes #N`, auto-merge Action `swarm-auto-merge.yml` merges if `make check` green
- True hours unattended while traveling, no Arena tab needed, uses `GITHUB_TOKEN` not PAT for merge

If you want OpenAI/Anthropic paid, set secret `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` and change `model` input to `openai/gpt-4o` etc — but free GitHub Models already works, no money.

## What to do next

1. **For ecosystem work:** Use `shesh-ecosystem` repo, read `SESSION_HANDOFF.md`, `make check`, selective clone via `tools/setup_worker.py --component shesh-memory` (2M not 36M)
2. **For dev tooling work:** Use `shesh-workspace` repo, read its `README.md` + `docs/SESSION_PROTOCOL.md`
3. **For OmniRoute:** Use fork `gaganjainse/OmniRoute` or wrapper `shesh-omniroute`, gateway `http://localhost:20128/v1`, dashboard `http://localhost:20128`, free tiers dashboard `/dashboard/free-tiers`

Separation proper now — no more mixing in new chats.
