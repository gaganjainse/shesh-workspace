# Shesh — Model Manifest — free, model-agnostic routing
# Every model declares capabilities, context, cost, provider, and free tier.
# Router picks best model that satisfies task requirements, not hardcoded names.

[ecosystem]
name = "shesh-models"
schema_version = 1

# ── Local Ollama — 100% free, offline, 6GB VRAM budget — PRIMARY ──

[model.phi4-mini]
provider = "ollama"
model = "phi4-mini"
context = 8192
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coordinator", "researcher", "critic", "coder-lite"]
notes = "Primary/planner/researcher/critic — 6GB safe, local, no API key"
priority = 1

[model.qwen2_5-coder-3b]
provider = "ollama"
model = "qwen2.5-coder:3b"
context = 8192
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["coder"]
notes = "Coder — 3B, fast, local"
priority = 1

[model.moondream2]
provider = "ollama"
model = "moondream2"
context = 2048
supports_json = false
supports_tools = false
cost = 0.0
free = true
capabilities = ["vision"]
notes = "Vision — screenshot description, OCR->tap loop"
priority = 1

[model.nomic-embed-text]
provider = "ollama"
model = "nomic-embed-text"
context = 8192
supports_json = false
supports_tools = false
cost = 0.0
free = true
capabilities = ["embedding"]
notes = "Embeddings — RAG, semantic search"
priority = 1

# ── Groq free tier — fast, free API key, rate limited ──

[model.groq-llama-3_1-8b]
provider = "groq"
model = "llama-3.1-8b-instant"
context = 8192
supports_json = true
supports_tools = true
cost = 0.0
free = true
free_tier = "14.4k req/day"
capabilities = ["planner", "coordinator", "researcher", "critic", "coder-lite"]
notes = "Groq free — fast, needs GROQ_API_KEY env (free)"
priority = 2

[model.groq-llama-3_3-70b]
provider = "groq"
model = "llama-3.3-70b-versatile"
context = 16384
supports_json = true
supports_tools = true
cost = 0.0
free = true
free_tier = "14.4k req/day"
capabilities = ["planner", "coordinator", "coder", "critic"]
notes = "Groq 70B — stronger reasoning, free tier"
priority = 2

# ── OpenRouter free models — :free suffix, no cost, needs OPENROUTER_API_KEY free ──

[model.openrouter-gemma-2-9b-free]
provider = "openrouter"
model = "google/gemma-2-9b-it:free"
context = 8192
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coordinator", "researcher", "critic"]
notes = "OpenRouter free — Gemma 2 9B"
priority = 3

[model.openrouter-llama-3_1-8b-free]
provider = "openrouter"
model = "meta-llama/llama-3.1-8b-instruct:free"
context = 8192
supports_json = true
supports_tools = true
cost = 0.0
free = true
capabilities = ["planner", "coder-lite", "critic"]
notes = "OpenRouter free — Llama 3.1 8B"
priority = 3

[model.openrouter-qwen-2-7b-free]
provider = "openrouter"
model = "qwen/qwen-2-7b-instruct:free"
context = 8192
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coder-lite"]
notes = "OpenRouter free — Qwen 2 7B"
priority = 3

# ── HuggingFace Inference free — needs HF_TOKEN free ──

[model.hf-phi-3-mini]
provider = "huggingface"
model = "microsoft/Phi-3-mini-4k-instruct"
context = 4096
supports_json = false
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coder-lite"]
notes = "HF free — Phi-3-mini"
priority = 4

# ── GitHub Models free — uses GITHUB_TOKEN or PAT, free for public repos ──

[model.github-gpt-4o-mini]
provider = "github"
model = "gpt-4o-mini"
context = 16384
supports_json = true
supports_tools = true
cost = 0.0
free = true
capabilities = ["planner", "coordinator", "researcher", "critic", "coder"]
notes = "GitHub Models free — gpt-4o-mini, uses GITHUB_TOKEN"
priority = 3

[model.github-phi-3-medium]
provider = "github"
model = "Phi-3-medium-128k-instruct"
context = 131072
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coder-lite"]
notes = "GitHub Models free — Phi-3-medium"
priority = 3

# ── Fallback deterministic stubs — always free, offline, zero quality variance ──

[model.stub-planner]
provider = "stub"
model = "stub-planner"
context = 8192
supports_json = true
supports_tools = false
cost = 0.0
free = true
capabilities = ["planner", "coordinator", "researcher", "critic", "coder", "vision", "embedding"]
notes = "Deterministic stub — returns fixed JSON steps, always valid, zero variance — final fallback"
priority = 99
