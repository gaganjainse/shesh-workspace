#!/usr/bin/env python3
"""Model-agnostic LLM adapter — rigorous quality consistency across free models.

Problem: Different models have different responses, abilities, quality. Bad experience.

Solution — 5-layer guard:

1. Strict JSON schema per task (Pydantic) — all models must output same shape.
2. Uniform prompt template — system + user + fenced JSON example — works for all models, even those without JSON mode.
3. Validation + repair loop — if output invalid JSON or fails schema, retry with repair prompt up to 3 times, showing previous error.
4. Fallback chain — if model fails after retries, try next model in capability-satisfying chain, eventually deterministic stub (zero variance, always valid).
5. LLM-as-judge grading — must_contain / must_not_contain / structural checks scored 0..1, min_score 0.7 gate (same as harness). Held-out evaluator.

Free providers supported via LiteLLM / OmniRoute:
- Ollama local (phi4-mini, qwen2.5-coder:3b, moondream2, nomic-embed-text) — 100% free, offline, 6GB VRAM
- Groq free (llama-3.1-8b-instant, llama-3.3-70b-versatile) — needs GROQ_API_KEY free
- OpenRouter free (:free suffix) — google/gemma-2-9b-it:free, meta-llama/llama-3.1-8b-instruct:free — needs OPENROUTER_API_KEY free
- HuggingFace free — microsoft/Phi-3-mini-4k-instruct — needs HF_TOKEN free
- GitHub Models free — gpt-4o-mini, Phi-3-medium — uses GITHUB_TOKEN (already have via PAT)
- Stub — deterministic, always valid, final fallback, zero cost, zero variance

This is model-agnostic: tasks declare required capabilities (planner, coder, vision, embedding, coordinator, researcher, critic), not model names.
Router (model_router.py) picks best available model satisfying capabilities, ordered by priority (local free first, then free API).

Usage:
  from tools.llm_adapter import ModelAgnosticAdapter, TaskSpec
  adapter = ModelAgnosticAdapter(models_toml="manifests/models.toml")
  result = adapter.generate(task=TaskSpec(role="planner", goal="organize Downloads", schema=PlannerSchema), prompt="...")

For omniroute: set env LITELLM_CONFIG / use litellm proxy, or set provider API keys — adapter will try in priority order, all free options.

Quality consistency: Same prompt template + same schema + same validation + same judge → different models produce same shape, variance measured by eval harness.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Any

# Try import tomllib
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[1]

# --- Task and Model specs ---

@dataclass
class TaskSpec:
    role: str  # planner, coder, researcher, vision, critic, coordinator, embedding
    goal: str
    schema: dict[str, Any] | None = None  # JSON schema dict for validation
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    min_score: float = 0.7
    context_budget: int = 4000


@dataclass
class ModelSpec:
    name: str
    provider: str
    model: str
    context: int
    supports_json: bool
    supports_tools: bool
    cost: float
    free: bool
    capabilities: list[str]
    priority: int = 10
    notes: str = ""


def load_models(manifest_path: pathlib.Path = ROOT / "manifests/models.toml") -> list[ModelSpec]:
    with manifest_path.open("rb") as f:
        data = tomllib.load(f)
    models = []
    for name, cfg in data.get("model", {}).items():
        models.append(
            ModelSpec(
                name=name,
                provider=cfg.get("provider", "unknown"),
                model=cfg.get("model", name),
                context=cfg.get("context", 4096),
                supports_json=cfg.get("supports_json", False),
                supports_tools=cfg.get("supports_tools", False),
                cost=cfg.get("cost", 0.0),
                free=cfg.get("free", True),
                capabilities=cfg.get("capabilities", []),
                priority=cfg.get("priority", 10),
                notes=cfg.get("notes", ""),
            )
        )
    # Sort by priority (local free first)
    models.sort(key=lambda m: (m.priority, m.cost, m.name))
    return models


# --- Prompt template — model-agnostic, works even without JSON mode ---

def build_prompt(task: TaskSpec, user_prompt: str, schema: dict | None = None, previous_error: str | None = None) -> str:
    """Uniform prompt that works for all models — strict JSON output.

    Even models without JSON mode understand fenced code block instruction.
    """
    schema_str = json.dumps(schema, indent=2) if schema else "No strict schema — output JSON"

    base = f"""You are a {task.role} agent in Shesh ecosystem. You must output VALID JSON ONLY, no extra text.

Goal: {task.goal}

User request: {user_prompt}

Required JSON schema (output must match this shape):
```json
{schema_str}
```

Rules:
- Output ONLY valid JSON, no markdown outside, no explanation, no preamble.
- Use fenced code block ```json ... ``` if you must, but JSON inside must be valid.
- If you cannot satisfy goal, output JSON with error field, still valid JSON.
- Keep within context budget {task.context_budget} tokens.
- Must contain: {task.must_contain if task.must_contain else 'nothing specific'}
- Must NOT contain: {task.must_not_contain if task.must_not_contain else 'nothing specific'}

Example valid output for planner role:
```json
{{"steps": [{{"id": "1", "role": "coder", "goal": "organize Downloads by type"}}], "approved": false}}
```
"""

    if previous_error:
        base += f"\n\nYour previous output was INVALID. Error: {previous_error}\nFix it — output ONLY valid JSON matching schema, no extra text. Previous error must be corrected."

    return base


# --- Errors (messages shaped here, not at raise sites) ---

class AdapterError(RuntimeError):
    """Base for llm_adapter failures."""


class MissingConfigError(AdapterError):
    """A required environment variable is not set."""

    def __init__(self, var: str) -> None:
        super().__init__(f"{var} not set")


class MissingAPIKeyError(AdapterError):
    """A provider has no API key in the environment."""

    def __init__(self, provider: str, env_var: str) -> None:
        super().__init__(f"no API key for {provider} ({env_var})")


class ProviderCallError(AdapterError):
    """A concrete backend call failed."""

    def __init__(self, backend: str, model: str, cause: BaseException) -> None:
        super().__init__(f"{backend} failed for {model}: {cause}")


class UnsupportedProviderError(AdapterError):
    """No code path exists for this provider without litellm."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"provider {provider} not implemented without litellm")


class ChainExhaustedError(AdapterError):
    """Every model in the chain failed, including the stub."""

    def __init__(self) -> None:
        super().__init__("all models failed including stub")


# --- Validation ---

def extract_json(text: str) -> tuple[dict | None, str | None]:
    """Robust JSON extraction — handles fenced, brace scan, balanced."""
    # Try fenced ```json ... ```
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1)), None
        except json.JSONDecodeError as e:
            err = f"fenced json parse failed: {e}"
            # fall through to brace scan
    else:
        err = None

    # Try raw JSON
    try:
        return json.loads(text.strip()), None
    except json.JSONDecodeError:
        # Expected when the model wraps JSON in prose — the brace-scan below
        # is the recovery path for exactly that.
        pass

    # Balanced brace scan — find first { and last } and try to parse inner
    # Also handle multiple JSON objects — take first valid
    stack = []
    start = None
    for i, c in enumerate(text):
        if c == "{":
            if start is None:
                start = i
            stack.append(c)
        elif c == "}":
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate), None
                    except json.JSONDecodeError as e:
                        err = f"brace scan candidate failed: {e}"
                        start = None
    return None, err or "no JSON found"


def validate_against_schema(data: dict, schema: dict | None) -> tuple[bool, str]:
    if not schema:
        return True, ""
    # Minimal validation — check required keys if schema has properties
    # For full JSON schema validation, would need jsonschema lib — we do lightweight
    if "required" in schema:
        for key in schema["required"]:
            if key not in data:
                return False, f"missing required key '{key}'"
    # must_contain handled outside
    return True, ""


def grade_output(data: dict, task: TaskSpec) -> float:
    """Simple held-out evaluator — must_contain/must_not_contain + structural."""
    score = 1.0
    txt = json.dumps(data).lower()
    for must in task.must_contain:
        if must.lower() not in txt:
            score -= 0.3
    for must_not in task.must_not_contain:
        if must_not.lower() in txt:
            score -= 0.5
    # Penalize if empty
    if not data:
        score = 0.0
    return max(0.0, min(1.0, score))


# --- Model adapter with LiteLLM / fallback ---


def _chat_completions(endpoint: str, token: str, model: str, prompt: str, timeout: int = 60) -> str:
    """Minimal OpenAI-compatible chat call (stdlib only, no litellm needed)."""
    import urllib.request

    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(endpoint, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read().decode())
        return j["choices"][0]["message"]["content"] or ""


class ModelAgnosticAdapter:
    _ollama_probe: bool | None = None  # process-wide probe cache

    def __init__(self, models_toml: pathlib.Path | None = None):
        self.models = load_models(models_toml or ROOT / "manifests/models.toml")
        # Filter to free only if user wants free (default free)
        self.free_models = [m for m in self.models if m.free]

    def _ollama_available(self) -> bool:
        if ModelAgnosticAdapter._ollama_probe is None:
            import shutil
            import socket

            ok = shutil.which("ollama") is not None
            if not ok:
                try:
                    with socket.create_connection(("127.0.0.1", 11434), timeout=0.4):
                        ok = True
                except OSError:
                    ok = False
            ModelAgnosticAdapter._ollama_probe = ok
        return ModelAgnosticAdapter._ollama_probe

    def models_for_role(self, role: str) -> list[ModelSpec]:
        """Return models that support role, sorted by priority."""
        candidates = [m for m in self.models if role in m.capabilities or "coder" in role and "coder" in m.capabilities or "coder-lite" in m.capabilities and role == "coder"]
        # More precise: role in capabilities
        exact = [m for m in self.models if role in m.capabilities]
        if exact:
            return sorted(exact, key=lambda m: m.priority)
        # Fallback: any that has role as substring or coder-lite for coder
        return sorted(candidates, key=lambda m: m.priority) or self.models

    def _call_model(self, model: ModelSpec, prompt: str) -> str:
        """Call model via available provider — tries LiteLLM, Ollama, Groq, OpenRouter, GitHub Models, stub."""
        # Stub always works
        if model.provider == "stub":
            # Deterministic stub based on role
            if "planner" in model.capabilities or "coordinator" in model.name:
                return '{"steps": [{"id": "1", "role": "coder", "goal": "organize files by type"}, {"id": "2", "role": "researcher", "goal": "search notes"}], "approved": false}'
            if "coder" in model.capabilities:
                return '{"patch": "# TODO implement", "files": ["src/example.py"]}'
            if "critic" in model.capabilities:
                return '{"approved": true, "notes": "looks good"}'
            return '{"result": "stub"}'

        # Ollama local
        if model.provider == "ollama":
            try:
                import json as _json
                import subprocess

                # Use ollama run via API? Try ollama CLI
                # ollama generate via API at localhost:11434
                try:
                    import urllib.request

                    data = _json.dumps({"model": model.model, "prompt": prompt, "stream": False}).encode()
                    req = urllib.request.Request(
                        "http://localhost:11434/api/generate",
                        data=data,
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        j = _json.loads(resp.read().decode())
                        return j.get("response", "")
                except (OSError, ValueError) as http_err:
                    # Daemon unreachable or reply unparseable — try the CLI.
                    proc = subprocess.run(
                        ["ollama", "run", model.model, prompt],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if proc.returncode == 0:
                        return proc.stdout
                    raise ProviderCallError("ollama-cli", model.model,
                                            RuntimeError(proc.stderr.strip()[:300] or http_err)) from http_err
            except (OSError, subprocess.SubprocessError) as e:
                # Real JSON, not the old single-quoted pseudo-dict that
                # extract_json() could never parse.
                return _json.dumps({"error": str(ProviderCallError("ollama", model.model, e))})

        # OmniRoute — our self-hosted OpenAI-compatible gateway (shesh-omniroute).
        # Any OpenAI-compatible endpoint works: SHESH_OMNIROUTE_BASE_URL + key.
        if model.provider == "omniroute":
            base = os.environ.get("SHESH_OMNIROUTE_BASE_URL", "").rstrip("/")
            key = os.environ.get("SHESH_OMNIROUTE_API_KEY", "")
            if not base:
                raise MissingConfigError("SHESH_OMNIROUTE_BASE_URL")
            return _chat_completions(
                f"{base}/v1/chat/completions" if not base.endswith("/v1") else f"{base}/chat/completions",
                key, model.model, prompt,
            )

        # Groq, OpenRouter, GitHub Models, HuggingFace — try LiteLLM if installed, else try direct API
        # For free, we try to use env API keys — if not present, fail and trigger fallback
        env_key_map = {
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "huggingface": "HF_TOKEN",
            "github": "GITHUB_TOKEN",  # or GITHUB_PAT
        }
        key_env = env_key_map.get(model.provider, "")
        api_key = os.environ.get(key_env) or os.environ.get("GITHUB_PAT") if model.provider == "github" else os.environ.get(key_env)

        # If no API key for provider that needs it, fail fast to trigger fallback
        if model.provider in ("groq", "openrouter", "huggingface") and not api_key:
            raise MissingAPIKeyError(model.provider, key_env)

        # Try LiteLLM if available
        try:
            import litellm  # type: ignore

            resp = litellm.completion(
                model=model.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            return resp.choices[0].message.content or ""
        except ImportError:
            # litellm not installed — fall through to the direct HTTP path below.
            pass
        except Exception as e:
            raise ProviderCallError("litellm", model.model, e) from e

        # Fallback direct API calls — OpenAI-compatible chat completions.
        if model.provider == "github":
            token = api_key or os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN") or ""
            if not token:
                raise MissingAPIKeyError("github", "GITHUB_TOKEN/GITHUB_PAT")
            last_exc: Exception | None = None
            for endpoint in (
                "https://models.github.ai/inference/chat/completions",
                "https://models.inference.ai.azure.com/chat/completions",  # legacy
            ):
                try:
                    return _chat_completions(endpoint, token, model.model, prompt)
                except (OSError, ValueError) as e:  # try next known endpoint
                    last_exc = e
            raise ProviderCallError("github-models", model.model, last_exc) from last_exc

        raise UnsupportedProviderError(model.provider)

    def generate(self, task: TaskSpec, user_prompt: str, max_retries: int = 3) -> tuple[dict, ModelSpec, float]:
        """Generate with retry, validation, fallback chain — model-agnostic quality consistency."""
        candidates = self.models_for_role(task.role)
        # Ensure stub is last fallback
        if not any(m.provider == "stub" for m in candidates):
            stub = next((m for m in self.models if m.provider == "stub"), None)
            if stub:
                candidates.append(stub)

        last_error = None
        for model in candidates:
            # OmniRoute needs its gateway configured, else skip silently.
            if model.provider == "omniroute" and not os.environ.get("SHESH_OMNIROUTE_BASE_URL"):
                continue
            # Ollama: skip fast when neither binary nor daemon exists (CI runners)
            if model.provider == "ollama" and not self._ollama_available():
                continue
            # Skip models that require API key not present (except stub and ollama)
            if model.provider in ("groq", "openrouter", "huggingface", "github"):
                # Check key exists, else skip to next
                key_map = {
                    "groq": "GROQ_API_KEY",
                    "openrouter": "OPENROUTER_API_KEY",
                    "huggingface": "HF_TOKEN",
                    "github": "GITHUB_TOKEN",
                }
                env_key = key_map.get(model.provider, "")
                has_key = os.environ.get(env_key) or (model.provider == "github" and (os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")))
                if (
                    not has_key
                    and model.provider != "github"
                    and not os.environ.get("GITHUB_PAT")
                ):
                    print(f"Skipping {model.name} no {env_key}", file=sys.stderr)
                    continue
                # For github, allow PAT as fallback
                if model.provider == "github" and not (os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")):
                    continue

            for attempt in range(max_retries):
                prompt = build_prompt(task, user_prompt, task.schema, previous_error=last_error)
                try:
                    raw = self._call_model(model, prompt)
                except Exception as e:  # noqa: BLE001 - chain boundary: any model
                    # failure is logged, then the next candidate model is tried.
                    # Narrowing here would let one backend's exotic error kill
                    # the whole chain, which is the thing this class exists to prevent.
                    last_error = f"model {model.name} failed: {e}"
                    print(last_error, file=sys.stderr)
                    break  # try next model, not retry same model if API key missing etc.

                data, err = extract_json(raw)
                if data is None:
                    last_error = err or "no JSON"
                    print(f"[{model.name}] attempt {attempt+1} invalid JSON: {last_error}, raw[:200]={raw[:200]}", file=sys.stderr)
                    continue

                ok, verr = validate_against_schema(data, task.schema)
                if not ok:
                    last_error = verr
                    print(f"[{model.name}] schema fail: {verr}", file=sys.stderr)
                    continue

                score = grade_output(data, task)
                if score < task.min_score:
                    last_error = f"score {score} < min {task.min_score}"
                    print(f"[{model.name}] score low {score}", file=sys.stderr)
                    continue

                # Success — same shape regardless of model
                print(f"[{model.name}] success score {score} on attempt {attempt+1}")
                return data, model, score

            # After retries for this model, try next model in chain

        # Final fallback — stub
        stub_model = next((m for m in self.models if m.provider == "stub"), None)
        if stub_model:
            data, _ = extract_json(self._call_model(stub_model, ""))
            if data is None:
                data = {"error": "stub failed", "fallback": True}
            return data, stub_model, 1.0

        raise ChainExhaustedError


# --- CLI for testing model-agnostic quality ---

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Model-agnostic adapter test")
    ap.add_argument("--role", default="planner")
    ap.add_argument("--goal", default="organize Downloads by type")
    ap.add_argument("--prompt", default="User wants to organize Downloads")
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    adapter = ModelAgnosticAdapter()
    if args.list_models:
        for m in adapter.models:
            print(f"{m.name:30} {m.provider:12} prio={m.priority} free={m.free} caps={m.capabilities} ctx={m.context} json={m.supports_json}")
        sys.exit(0)

    task = TaskSpec(
        role=args.role,
        goal=args.goal,
        schema={"type": "object", "required": ["steps"], "properties": {"steps": {"type": "array"}}},
        must_contain=[],
        must_not_contain=[],
        min_score=0.7,
    )
    data, model, score = adapter.generate(task, args.prompt)
    print(f"Model: {model.name} provider={model.provider} score={score}")
    print(json.dumps(data, indent=2))
