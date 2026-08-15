# llm_adapter.py — one guarded shape over every model

Status: living · last verified 2026-08-13
Source: `tools/llm_adapter.py` · Strategy: [MODEL_AGNOSTIC](model-agnostic.md)

Whatever model sits behind it, the adapter hands callers the same validated
output shape. That is the 5-layer guard:

1. **Schema** — the caller declares the expected JSON shape.
2. **Generation** — through the model-agnostic router (free-first chain).
3. **Parse + validate** — malformed output never reaches callers.
4. **Grading** — responses are scored; weak answers retry fall down the chain.
5. **Stub last** — the chain always terminates in an honest deterministic
   stub rather than a fabricated answer.

## Why it exists

Swarm LLM workers run unattended for hours. Without the guard, a provider
regression would silently land garbage patches; with it, output quality is
consistent to variance < 0.1 across providers (see
[MODEL_AGNOSTIC](model-agnostic.md) for the full measurement).

## Related

- `tools/llm_worker.py` — the GitHub Models swarm worker built on the adapter
  (free tier, `GITHUB_TOKEN` only, no paid key).
- `tools/model_router.py` — the capability-based picker, documented in
  [model-router](model-router.md).
