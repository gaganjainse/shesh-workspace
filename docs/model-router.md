# model_router.py — capability-based, free-first model picking

Status: living · last verified 2026-08-13
Source: `tools/model_router.py` · Strategy: [MODEL_AGNOSTIC](model-agnostic.md)

Callers name a **role** (planner, researcher, critic, coder), never a model.
The router maps roles to capabilities and picks the best available provider,
free tier first.

## Selection chain

`Router.pick(role)` → local Ollama if reachable → Groq free → OpenRouter free
→ GitHub Models free → deterministic stub. The chain order and the free-tier
claims are research-backed in
[the OmniRoute study](https://github.com/gaganjainse/shesh-ecosystem/blob/main/docs/omniroute-study.md) (the surveyed providers surveyed, free tiers
re-verified 2026-06-17, CI-gated refresh).

## Why capability-based

Hardcoding `role → phi4-mini` broke the moment a model rename or a pulled
model went missing. Capabilities (`reasoning`, `code`, `long-context`, …)
survive provider churn — the same reason the dependency policy mirrors onto
models: roll forward, degrade honestly, never fabricate.

## Verified

- Chain fallback and stub termination are unit-tested in the ecosystem suite
  (`make check`); shesh-mind consumes the router for its role dispatch.
