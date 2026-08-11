# OmniRoute Study — Free Big Models for Shesh (Proper Research 2026-08-11)

> **Source:** Forked `gaganjainse/OmniRoute` from `diegosouzapw/OmniRoute` — 38.9k★, 5.1k forks, 6k commits, MIT, 291 providers, 90+ free, 500+ models, ~1.53B free tokens/month documented, RTK+Caveman compression 15-95% tokens (~89% avg), MCP/A2A, Desktop/PWA, built by 500+ contributors.

## What OmniRoute actually is

OmniRoute is **not** just OpenRouter. It's a **free MIT AI gateway** — one endpoint `http://localhost:20128/v1` (OpenAI-compatible) that aggregates **291 providers**:

- 90+ with free tier, 40+ free forever no card
- 516 models in catalog `open-sse/config/freeModelCatalog.ts`
- 19 routing strategies, 12-engine token compression (Session-Dedup, CCR, Lite, RTK, Responses Tool Output, Headroom, Relevance, Caveman, Aggressive, LLMLingua-2, Ultra, OmniGlyph) — saves 15-95% tokens, avg 89% on tool-heavy sessions
- Quota-aware auto-fallback: Tier1 Subscription (Claude Code, Codex, Copilot) → Tier2 API (DeepSeek, Groq, xAI) → Tier3 Cheap (GLM $0.5, MiniMax $0.2) → Tier4 Free (Kiro, Qoder, Pollinations, etc.)
- Built-in MCP server 105 tools, A2A v0.3 protocol, persistent memory, guardrails, cloud agents, TLS fingerprint stealth, Desktop/Electron/PWA, 43 i18n locales

**Dashboard:** `http://localhost:20128` shows live free-tier budget, used/remaining, per-model grid, 43 provider pools.

## Free tiers — honest numbers (2026-06-17 refresh, CI-gated)

| Metric | Tokens/mo | Meaning |
|--------|-----------|---------|
| **Documented recurring steady** | **~1.51B** | Free-tier pools, each shared pool counted once. Source `freeModelCatalog.ts`, API `/api/free-tier/summary`, dashboard Free-Tier Budget. **Use this.** |
| + first month signup credits | ~2.13B | Steady + one-time (Together $25, Z.AI 20M, DeepSeek 5M) first month only |
| + permanently free no cap | un-quantifiable | `siliconflow`, `glm-cn` GLM-4-Flash, `tencent`, `baidu`, `kilo-gateway`, `opencode-zen` — real recurring, rate-limited, no token cap, never summed (counting RPM×24/7 would inflate to ~10B fantasy) |
| + deposit-unlock boost | +~24M | OpenRouter $10 top-up raises free 50→1000 req/day |
| Theoretical ceiling (all rate limits 24/7) | ~10B | Fantasy, not guarantee |

**Biggest contributors:** `mistral` 1.00B, `llm7` 150M, `groq` 117M, `gemini` 60M, `cerebras` 30M, `cloudflare-ai` 30M, `sambanova` 30M

**Per-provider free (sample 2026-06-17):**

| Provider | Type | Steady/mo | Models | Notes |
|----------|------|-----------|--------|-------|
| `mistral` | recurring | ~1.00B | 5 | Consumer ToS personal needs |
| `llm7` | recurring | ~150M | 4 | Experimentation |
| `gemini` | recurring | ~60M | 6 | Flash family only, pooled |
| `cerebras` | recurring | ~30M | 2 | |
| `cloudflare-ai` | recurring | ~30M | 6 | 10k Neurons/day |
| `groq` | recurring | ~15M | 5 | 14.4k req/day free tier |
| `openrouter` | recurring | ~1M | 1 | 50 req/day free |
| `cohere` | recurring | ~800K | 6 | |
| `huggingface` | recurring | ~200K | 6 | |
| `glm-cn` | uncapped | uncapped* | 4 | GLM-4-Flash permanently free +20M signup |
| `kilo-gateway` | uncapped | uncapped* | 7 | Auto free rotating set: Nemotron 3, StepFun, Poolside |
| `opencode-zen` | uncapped | uncapped* | 6 | 6 rotating free coding models |
| `siliconflow` | uncapped | uncapped* | 10 | DeepSeek V3.2/R1 free tier |

**Free forever, no card, no token cap (rate-limited):** Qoder AI (Qwen3-Max, Kimi-K2 unlimited), Pollinations (GPT, Llama, Claude no key), Cloudflare AI (50+ models 10k neurons/day), NVIDIA NIM (GLM, MiniMax ~40 RPM free), Cerebras (GLM), Kilo Code, OpenCode Zen, Z.AI GLM, Requesty (GPT-OSS 120B, Nemotron free), SiliconFlow (DeepSeek V3.2/R1)

**Why numbers dropped from 1.94B→1.51B:** Honesty correction — gemini pooled (was inflated counting each Flash variant 462M→60M), cloudflare corrected 122M→30M, doubao reclassified as one-time credit, removed shutdown tiers (chutes, phind, kluster). New free providers added Kilo, OpenCode Zen, Z.AI.

## Big industry-used free models (not small local)

OmniRoute catalog includes **industry-used big models** free, not only small local:

- **Claude** via Kiro AI free (Claude Sonnet 4.5, Haiku 4.5, Opus 4.6) ~50 credits/month per account free
- **GPT** via Pollinations, OpenCode, Requesty, Puter — GPT-4o mini 150M tokens/mo documented, GPT-OSS 120B free forever
- **Gemini** via Gemini free tier — 60M tokens/mo, Flash family
- **DeepSeek** via DeepSeek V3.2/R1, V4 Flash/Pro — free tier 5M signup + recurring via SiliconFlow, NVIDIA NIM
- **Llama** via Groq, Cloudflare, Together, SambaNova — Llama 3.1 8B/70B/3.3 70B
- **Mistral** Large 3 — 1B tokens/mo biggest contributor
- **Qwen** Qwen3-Max, Qwen3-Next-80B-A3B via Qoder, Alibaba
- **Kimi** K2, K3 1M context — Moonshot AI founding friend, free via Kimi provider
- **GLM** GLM-4-Flash/4.5-Flash/4.7-Flash permanently free via Z.AI, GLM-CN
- **MiniMax** M2.1, M2 — cheap $0.2 + free via NVIDIA NIM

These are **not small local** — they are frontier 70B-120B-550B models with free tiers.

## How OmniRoute works for Shesh

**Local models in final product (Shesh ecosystem):** phi4-mini, qwen2.5-coder:3b, moondream2, nomic-embed-text — 6GB VRAM, offline, primary, no API key — run on MSI Sword 16 HX final system, not for making system.

**OmniRoute as optional cloud fallback (where you enable in finished product is your choice):**

- Shesh local primary → if offline or need bigger reasoning → OmniRoute gateway `http://localhost:20128/v1` auto-fallback to free big models
- Where you enable is your choice — via `shesh-mind` router: if `cloud.enabled=true` (opt-in) + policy allows (not protected path), then route to OmniRoute, else stay local
- OmniRoute compression RTK+Caveman saves 15-95% tokens → stretches free tiers further → 1.53B tokens/mo lasts longer

**Separation of concerns (you asked):**

- **shesh-ecosystem = product** — clean, manifest `components.toml`, locks, architecture docs, gates, `shesh-*` components. No session protocol, no swarm dev tooling.
- **shesh-workspace = factory** — messy dev works handling session protocol, swarm (file+Issues atomic lock+PR auto-merge), secure PAT password flow, efficiency selective clone, model-agnostic adapter, travel mode, etc. Keeps ecosystem clean, new chats don't mix.
- **OmniRoute forked as `gaganjainse/OmniRoute`** — embedded as optional component `shesh-omniroute` (planned) — local primary, OmniRoute optional cloud free fallback

We already created `gaganjainse/shesh-workspace` repo and pushed dev tooling there, and forked OmniRoute to `gaganjainse/OmniRoute`. Now ecosystem repo stays clean.

## How to use OmniRoute to MAKE ecosystem (free, no money) — optional to local AI

You said: "We can use it to make the ecosystem, where I enable it in finished product is my choice"

Yes — for **making** ecosystem (development work in Arena), you can use OmniRoute free big models to get better quality than small local, even though final product runs local:

1. **Install OmniRoute locally (free, no keys needed for basic):**
   ```bash
   npm install -g omniroute
   omniroute
   # Dashboard http://localhost:20128, API http://localhost:20128/v1
   ```

2. **Point any OpenAI-compatible tool at it:**
   ```bash
   # Claude Code
   ANTHROPIC_BASE_URL=http://localhost:20128 claude
   # Codex CLI
   OPENAI_BASE_URL=http://localhost:20128/v1 codex
   # Cursor, Cline, Continue, etc.
   Base URL: http://localhost:20128/v1
   Model: auto  # smart routing, or specific like kimi-k2, claude-sonnet-4.5, gpt-4o-mini, gemini-2.5-flash
   ```

3. **Connect free providers (no signup for some):**
   - Dashboard → Providers → Kiro AI (free Claude ~50 credits/month) or OpenCode Free (no auth) → done
   - Or add Groq free API key (console.groq.com), OpenRouter free, etc.

4. **Use for making ecosystem:**
   - In Arena, set `OPENAI_BASE_URL=http://localhost:20128/v1` + `OPENAI_API_KEY=any` (OmniRoute key from dashboard)
   - Model `auto` or `kimi-k2` or `claude-sonnet-4.5` — OmniRoute picks cheapest free that works, auto-fallback across 4 tiers: Subscription → API → Cheap → Free
   - Quality: big models (Claude, GPT, Gemini, DeepSeek) produce better code than small local, but our model-agnostic adapter (`tools/llm_adapter.py`) ensures same JSON schema, validation, grading, so quality consistent even if different free models used

5. **Where you enable in finished product is your choice:**
   - Final Shesh on MSI: local Ollama primary (free offline) → if you opt-in `cloud.enabled=true` in settings GUI, then it routes via OmniRoute gateway to free big models
   - Via `shesh-mind` router: capability-based, free-first, stub last — same as dev, but on device
   - Policy `SKILLS_POLICY.md`: protected paths (`.ssh`, `Vaults/`, `Job`) never sent to cloud regardless of setting

**Free, no money:** OmniRoute free tiers 90+ providers, 1.53B tokens/mo aggregated, 40+ free forever, plus compression 15-95% → never hit limits. Works second you install, no keys, no config for basic free models (Pollinations, Cloudflare, etc.)

## Integration into Shesh ecosystem

- **As component:** `shesh-omniroute` (planned) — wraps OmniRoute gateway as MCP tool `omniroute_generate` with same model-agnostic adapter, optional to local AI, enabled via settings GUI `SeshaConfig.qml`
- **As dev tool:** `tools/omniroute/` (future) — uses OmniRoute free big models to make ecosystem (code generation) with rigorous quality (schema + validation + fallback chain + grading)
- **Separation:** Dev tooling (OmniRoute usage for making) lives in `shesh-workspace`, not in `shesh-ecosystem` clean product — you enable in finished product is your choice

## References

- Fork: https://github.com/gaganjainse/OmniRoute (from diegosouzapw/OmniRoute)
- Workspace: https://github.com/gaganjainse/shesh-workspace (messy dev)
- Ecosystem: https://github.com/gaganjainse/shesh-ecosystem (clean product)
- OmniRoute docs: https://github.com/diegosouzapw/OmniRoute/tree/main/docs
- Free tiers methodology: `open-sse/config/freeModelCatalog.ts` + `docs/reference/FREE_TIERS.md`
- Dashboard: http://localhost:20128 and `/dashboard/free-tiers` live budget
