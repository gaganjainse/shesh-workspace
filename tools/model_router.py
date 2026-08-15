#!/usr/bin/env python3
"""Capability-based model router — model-agnostic, free-first, quality-consistent.

Replaces hardcoded role→model mapping in shesh-mind.
Now: task declares required capabilities (planner, coder, vision, embedding, etc.)
Router picks best FREE model satisfying capabilities, ordered by priority (local Ollama first).

Free priority order (from manifests/models.toml):
1. Ollama local — phi4-mini, qwen2.5-coder:3b, moondream2, nomic-embed-text — 100% free, offline, 6GB VRAM
2. Groq free — llama-3.1-8b-instant, llama-3.3-70b — needs GROQ_API_KEY free
3. OpenRouter free — gemma-2-9b-it:free, llama-3.1-8b:free — needs OPENROUTER_API_KEY free
4. GitHub Models free — gpt-4o-mini, Phi-3-medium — uses GITHUB_TOKEN (already have via PAT)
5. HuggingFace free — Phi-3-mini — needs HF_TOKEN free
6. Stub — deterministic, always valid, zero variance — final fallback

Quality consistency:
- Same prompt template for all models (build_prompt in llm_adapter)
- Same JSON schema validation
- Same grading (must_contain, must_not_contain, score >=0.7)
- Fallback chain ensures output shape identical regardless of model

Usage:
  from tools.model_router import Router
  router = Router()
  model = router.pick(role="planner", min_context=4000, require_json=True)
  print(model.name, model.provider)

Integrates with OmniRoute / LiteLLM:
  Set env LITELLM_CONFIG or use litellm proxy — router will use litellm.completion if available,
  else direct Ollama/Groq/OpenRouter/GitHub APIs.

For omniroute: create litellm_config.yaml with free models list — see manifests/models.toml and docs/MODEL_AGNOSTIC.md
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from llm_adapter import ModelSpec, load_models  # noqa: E402


class Router:
    def __init__(self, models_toml: pathlib.Path | None = None):
        self.models = load_models(models_toml or ROOT / "manifests/models.toml")

    def pick(
        self,
        role: str,
        min_context: int = 0,
        require_json: bool = True,
        require_tools: bool = False,
        free_only: bool = True,
    ) -> ModelSpec | None:
        candidates = self.models

        if free_only:
            candidates = [m for m in candidates if m.free]

        # Filter by capability
        # role can be planner, coder, vision, embedding, coordinator, researcher, critic
        filtered = []
        for m in candidates:
            if role not in m.capabilities:
                # Allow coder-lite for coder, etc.
                if role == "coder" and ("coder-lite" in m.capabilities or "coder" in m.capabilities):
                    pass
                else:
                    continue
            if min_context and m.context < min_context:
                continue
            if require_json and not m.supports_json:
                # Still allow if model can do JSON via prompt engineering — but prefer those that support it
                # We will not filter out, just de-prioritize
                pass
            if require_tools and not m.supports_tools:
                pass
            filtered.append(m)

        if not filtered:
            # Fallback to any free that has at least some capability overlap
            filtered = [m for m in candidates if role in m.capabilities or "planner" in m.capabilities]

        # Sort by: priority, then supports_json (prefer true), then context desc, then cost
        def sort_key(m: ModelSpec):
            json_bonus = 0 if m.supports_json else 1
            tools_bonus = 0 if not require_tools or m.supports_tools else 1
            return (m.priority, json_bonus, tools_bonus, -m.context, m.cost)

        filtered.sort(key=sort_key)
        return filtered[0] if filtered else None

    def chain_for_role(self, role: str, free_only: bool = True) -> list[ModelSpec]:
        """Return fallback chain for role — best first, stub last."""
        candidates = self.models
        if free_only:
            candidates = [m for m in candidates if m.free]
        # Filter by capability
        capable = [m for m in candidates if role in m.capabilities or (role == "coder" and "coder-lite" in m.capabilities)]
        if not capable:
            capable = candidates
        # Sort by priority
        capable = sorted(capable, key=lambda m: (m.priority, m.cost))
        # Ensure stub last
        stubs = [m for m in capable if m.provider == "stub"]
        non_stubs = [m for m in capable if m.provider != "stub"]
        return non_stubs + stubs


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Model router")
    ap.add_argument("--role", default="planner")
    ap.add_argument("--free-only", action="store_true", default=True)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    router = Router()
    if args.list:
        for m in router.models:
            print(
                f"{m.name:35} {m.provider:12} prio={m.priority} free={m.free} "
                f"caps={','.join(m.capabilities):40} json={m.supports_json} ctx={m.context}"
            )
    else:
        picked = router.pick(role=args.role, free_only=args.free_only)
        chain = router.chain_for_role(args.role, free_only=args.free_only)
        print(f"Picked for {args.role}: {picked.name if picked else 'None'}")
        print("Fallback chain:")
        for i, m in enumerate(chain):
            print(f"  {i+1}. {m.name} ({m.provider}) prio={m.priority} free={m.free}")
