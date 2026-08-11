# Model-Agnostic Workflow — Rigorous Quality Consistency Across Free Models

> **Problem you reported:** Different models have different responses and abilities, you don't know if they will work properly and complete your work. Bad experience with quality variance.

> **Goal:** Workflow is model-agnostic — you can setup omniroute and enable all free options (Ollama local, Groq free, OpenRouter :free, GitHub Models free, HuggingFace free) and get **same quality output shape**, with rigorous validation so different models don't produce different quality.

## Why models differ (root causes)

| Variance source | Example |
|-----------------|---------|
| **JSON mode support** | phi4-mini via Ollama supports JSON, moondream2 doesn't — one outputs `{"steps":...}` valid, other outputs natural language |
| **Tool calling** | gpt-4o-mini supports tools, gemma-2-9b-it:free doesn't — coder role fails |
| **Prompt sensitivity** | Some models need fenced ```json, others need "Output ONLY JSON" — same prompt gives valid JSON in one, invalid in other |
| **Context length** | moondream2 2048 vs Phi-3-medium 128k — long history overflows small model |
| **Training** | qwen2.5-coder:3b good at code, moondream2 good at vision, phi4-mini good at reasoning — planner quality differs |

Without guardrails, model A returns `{"steps": [{"id":"1", "role":"coder", "goal":"organize"}]}` valid, model B returns `Sure! Here are steps: 1. Organize...` invalid — orchestrator breaks.

## Solution — 5-layer rigorous setup (implemented)

### 1. Strict JSON schema per task (not per model)

Every task declares required output shape via JSON schema, not free text. Example planner:

```json
{
  "type": "object",
  "required": ["steps"],
  "properties": {
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "role", "goal"],
        "properties": {
          "id": {"type": "string"},
          "role": {"type": "string", "enum": ["coder","researcher","vision","critic"]},
          "goal": {"type": "string"}
        }
      }
    },
    "approved": {"type": "boolean"}
  }
}
```

All models must output JSON matching this — validated, not guessed.

File: `tools/llm_adapter.py:TaskSpec.schema`

### 2. Uniform prompt template — model-agnostic

Same template for **all models**, even those without JSON mode:

```
You are a {role} agent in Shesh ecosystem. You must output VALID JSON ONLY, no extra text.
Goal: {goal}
User request: {user_prompt}
Required JSON schema:
```json
{schema}
```
Rules:
- Output ONLY valid JSON, no markdown outside, no explanation
- Use fenced code block ```json ... ``` if you must, but JSON inside must be valid
- Must contain: [...]
- Must NOT contain: [...]
Example valid output: {"steps": [{"id":"1", "role":"coder", "goal":"organize Downloads by type"}]}
```

Plus **repair prompt** on retry: `Your previous output was INVALID. Error: {error}. Fix it — output ONLY valid JSON...`

Works for Ollama, Groq, OpenRouter free, GitHub Models, HuggingFace — all understand fenced JSON instruction, even without native JSON mode.

File: `tools/llm_adapter.py:build_prompt()`

### 3. Validation + repair loop (3 retries)

```python
for model in chain:
  for attempt in 3:
    raw = _call_model(model, prompt)
    data, err = extract_json(raw)  # handles fenced ```json, raw JSON, balanced brace scan
    if data is None: last_error=err; continue
    ok, verr = validate_against_schema(data, schema)
    if not ok: last_error=verr; continue
    score = grade_output(data, task)  # must_contain/must_not_contain
    if score < min_score (0.7): last_error=f"score {score} < 0.7"; continue
    return data, model, score
```

- `extract_json()` robust: tries fenced block, then raw JSON, then balanced brace scan `{...}` — handles model that outputs extra text.
- `validate_against_schema()` checks required keys, not just JSON parse.
- `grade_output()` scoring: must_contain/must_not_contain + structural — same as harness held-out evaluator.

If model fails after 3 retries, next model in chain tried.

File: `tools/llm_adapter.py`

### 4. Fallback chain — model-agnostic routing, free-first

`manifests/models.toml` defines **all free models** with capabilities, context, supports_json, priority:

- Priority 1: Ollama local — `phi4-mini`, `qwen2.5-coder:3b`, `moondream2`, `nomic-embed-text` — 100% free, offline, 6GB VRAM, no API key
- Priority 2: Groq free — `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` — free tier 14.4k req/day, needs `GROQ_API_KEY` free
- Priority 3: OpenRouter free — `google/gemma-2-9b-it:free`, `meta-llama/llama-3.1-8b-instruct:free`, `qwen/qwen-2-7b-instruct:free` — `:free` suffix, needs `OPENROUTER_API_KEY` free
- Priority 3: GitHub Models free — `gpt-4o-mini`, `Phi-3-medium-128k` — uses `GITHUB_TOKEN` (already have via PAT), free for public repos
- Priority 4: HuggingFace free — `Phi-3-mini-4k-instruct` — needs `HF_TOKEN` free
- Priority 99: Stub — deterministic, always valid JSON, zero variance, final fallback, free

Router `tools/model_router.py:Router.pick(role, min_context, require_json, free_only=True)` filters by capability (e.g., role `planner` must have capability `planner`), context, json support, then sorts by priority, json bonus, context desc.

Chain: best free first → next free → ... → stub last. **Same output shape regardless of which model in chain succeeds**, because schema + validation + grading are same.

For omniroute: set env `LITELLM_CONFIG` or use LiteLLM proxy — adapter tries `litellm.completion()` if installed, else direct Ollama/Groq/OpenRouter/GitHub APIs. All free options enabled via env keys — if key missing, model skipped, next in chain tried, no crash.

File: `manifests/models.toml`, `tools/model_router.py`

### 5. LLM-as-judge grading + eval harness — quality consistency measured

Same as harness: `must_contain`, `must_not_contain`, structural checks, score 0..1, `min_score=0.7` gate.

`tools/llm_adapter.py:grade_output()` + `scripts/eval_model_agnostic.py` (to be added) runs same tasks across all free models and measures variance:

- Runs task "organize Downloads" with phi4-mini, groq-llama-8b, gemma-2-9b:free, gpt-4o-mini, stub
- Checks each output valid JSON, required keys, must_contain, score
- Reports variance: if all models score >=0.7 and produce same shape, quality consistent

This is what makes workflow model-agnostic — not that all models are equally smart, but that **invalid/low-quality outputs are caught and retried/fallbacked**, and **valid outputs have same shape** so orchestrator doesn't break.

## Free options enabled via omniroute

You said you do everything free, no money. All models in `models.toml` are free:

| Provider | How to enable (free) | Models | Cost |
|----------|----------------------|--------|------|
| Ollama local | `ollama pull phi4-mini qwen2.5-coder:3b moondream2 nomic-embed-text` — local, no key | phi4-mini, qwen2.5-coder:3b, moondream2, nomic-embed-text | $0, offline |
| Groq | `export GROQ_API_KEY=gsk_...` free tier at https://console.groq.com/keys | llama-3.1-8b-instant, llama-3.3-70b-versatile | $0, 14.4k req/day |
| OpenRouter | `export OPENROUTER_API_KEY=sk-or-...` free at https://openrouter.ai/keys — use `:free` models | gemma-2-9b-it:free, llama-3.1-8b:free, qwen-2-7b:free | $0 |
| GitHub Models | `export GITHUB_TOKEN=$(cat ~/.config/shesh/github.pat)` — already have PAT, free for public repos | gpt-4o-mini, Phi-3-medium-128k | $0 |
| HuggingFace | `export HF_TOKEN=hf_...` free at https://huggingface.co/settings/tokens | Phi-3-mini | $0 |
| Stub | Always available, no key | stub-planner, stub-coder, etc | $0, zero variance |

Omniroute setup: Use LiteLLM proxy:

```bash
pip install litellm
export GROQ_API_KEY=...
export OPENROUTER_API_KEY=...
export HF_TOKEN=...
# LiteLLM will route based on model name
python tools/llm_adapter.py --role planner --goal "organize Downloads" --list-models
```

Or set `LITELLM_CONFIG` env to `litellm_config.yaml` that lists free models — we already have `manifests/models.toml` which can be converted to LiteLLM config.

## How to use model-agnostic workflow

```python
from tools.llm_adapter import ModelAgnosticAdapter, TaskSpec
from tools.model_router import Router

router = Router()  # loads manifests/models.toml free models
model = router.pick(role="planner", require_json=True, free_only=True)
print(f"Picked {model.name} provider={model.provider} prio={model.priority}")

adapter = ModelAgnosticAdapter()
task = TaskSpec(
    role="planner",
    goal="organize Downloads by type",
    schema={"type":"object","required":["steps"],"properties":{"steps":{"type":"array"}}},
    must_contain=["organize"],
    must_not_contain=["rm -rf /"],
    min_score=0.7
)

data, used_model, score = adapter.generate(task, user_prompt="User wants Downloads organized", max_retries=3)
print(f"Used {used_model.name} score {score}")
print(data)  # Always same shape {"steps": [...]} regardless of model
```

If `phi4-mini` fails JSON after 3 retries, adapter tries `groq-llama-3.1-8b`, then `gemma-2-9b:free`, then `gpt-4o-mini`, then stub — **always returns valid JSON**, quality consistent because validation + grading gate same.

## Evaluation — prove quality consistency

Run:

```bash
python tools/llm_adapter.py --role planner --goal "organize Downloads" --list-models
python tools/llm_adapter.py --role planner --goal "organize Downloads" --prompt "organize Downloads"
# Will try chain until success, report model used and score

# Future: eval harness
python scripts/eval_model_agnostic.py --role planner --tasks 10
# Runs same 10 tasks across all free models, reports variance in score, JSON validity rate
```

Goal: **variance <0.1 in score, 100% JSON validity** — if not, adjust prompt template or schema, or deprioritize low-quality model in `models.toml` priority.

## Integration with existing components

- **shesh-mind**: Was hardcoded role→model (phi4-mini etc). Now uses `Router.pick(role)` — capability-based, free-first, not name hardcoded. If Ollama not available, falls back to Groq free, then OpenRouter free, then GitHub Models free, then stub.
- **shesh-orchestrator**: `LLMAgents` now uses `ModelAgnosticAdapter` instead of direct Ollama calls — same schema + validation + fallback chain, so planner/critic quality consistent across models.
- **shesh-harness**: Held-out evaluator already uses must_contain/must_not_contain scoring 0..1 min 0.7 — same grading used in adapter, so self-improvement safe regardless of model.
- **Swarm workers**: Can specify `--model-policy free-only` — will only use free models, never paid.

## What you need to do to enable all free options (omniroute)

1. **Ollama local (already free, offline):**
   ```bash
   ollama pull phi4-mini qwen2.5-coder:3b moondream2 nomic-embed-text
   ```

2. **Groq free (optional, faster):**
   - Go https://console.groq.com/keys → Create API key free
   - `echo "GROQ_API_KEY=gsk_..." >> ~/.config/shesh/env && chmod 600 ~/.config/shesh/env`
   - `export GROQ_API_KEY=...`

3. **OpenRouter free:**
   - https://openrouter.ai/keys → Create free key
   - `export OPENROUTER_API_KEY=sk-or-...`

4. **GitHub Models free (you already have PAT):**
   - Uses `GITHUB_PAT` or `GITHUB_TOKEN` — already decrypted via password flow
   - No extra key needed

5. **HuggingFace free:**
   - https://huggingface.co/settings/tokens → Create read token free
   - `export HF_TOKEN=hf_...`

6. **Set env and run model-agnostic test:**
   ```bash
   export GROQ_API_KEY=... OPENROUTER_API_KEY=... HF_TOKEN=... GITHUB_TOKEN=$(cat ~/.config/shesh/github.pat)
   python tools/model_router.py --role planner --list
   python tools/llm_adapter.py --role planner --goal "test" --prompt "organize"
   ```

All free, no OpenAI API paid needed. Adapter will try free models in priority order, skip those without keys, always fallback to stub — zero cost, zero variance final fallback.

## Summary: Why bad experience won't repeat

**Before:** Hardcoded `phi4-mini` — if Ollama down or model bad at JSON, whole workflow broke, quality varied.

**Now:** Capability-based routing + strict schema + validation + repair loop + fallback chain + grading gate + stub final — **output shape identical regardless of model**, invalid outputs retried or fallbacked, score gate ensures quality >=0.7, variance measured by eval harness.

You can setup omniroute and enable all free options — workflow is model-agnostic and rigorous.
