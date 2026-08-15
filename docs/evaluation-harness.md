---
title: shesh-harness
type: reference
summary: "A self-improving agent that can edit its own prompt without guardrails will."
audience: contributor
status: current
verified: 2026-08-15
---

# shesh-harness

> **Continual Harness for safe self-improvement.** Implements the Prime Agent
> `/refine` pattern with hard guardrails: an immutable base prompt, evidence-backed
> edits, evaluation before apply, and rollback by ID.

  ![CI](https://github.com/gaganjainse/shesh-harness/actions/workflows/ci.yml/badge.svg)

- **License:** GPL-3.0-or-later
- **Owner:** Gagan Jain ([@gaganjainse](https://github.com/gaganjainse))
- **Layer:** Mind (self-improvement)
- **Part of:** [shesh-ecosystem](https://github.com/gaganjainse/shesh-ecosystem)

---

## Why this repo exists
A self-improving agent that can edit its own prompt without guardrails will
overfit metrics. This harness keeps the base prompt immutable, requires evidence
and evaluation, supports rollback, and promotes changes only after they pass
tests — so the system can learn your intentions without destabilizing itself.

---

## Quick start
```bash
uv sync --extra dev
uv run pytest -q        # the harness test suite
uv run ruff check .
```

## Tools (MCP, stdio)
- `get_prompt_block()` — supplemental prompt + memories for the turn
- `add_memory(text)` / `upsert_skill(name, body)` / `list_skills()`
- `refine(trigger, trajectory)` — propose, evaluate, and apply a small change

Every refinement is append-only with trigger, before/after, score, and outcome;
any change can be **reverted by ID**.

> **Reproducible install:** `uv.lock` pins the full dependency tree. Install with
> `uv sync --frozen` (or `uv pip install -r <(uv export --frozen)`) for a locked build.

## Status
Component CI is green (reusable ecosystem pipeline). Security posture and
vulnerability reporting: [SECURITY.md](https://github.com/gaganjainse/shesh-harness/blob/main/SECURITY.md).

## Documentation index
- **Part of:** [shesh-ecosystem](https://github.com/gaganjainse/shesh-ecosystem)
- **Compiled reading:** [shesh-docs](https://github.com/gaganjainse/shesh-docs)

## License
GPL-3.0-or-later — see [LICENSE](https://github.com/gaganjainse/shesh-harness/blob/main/LICENSE).
