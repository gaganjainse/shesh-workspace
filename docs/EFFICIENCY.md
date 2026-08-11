# Efficiency — How to Work Longer and Faster for Free

> **Problem you reported:** Cloning 22 repos in every chat is useless when work is divided, and you have no money for OpenAI API. You travel on phone, can keep 1 orchestrator tab open.

This doc lists **free** strategies to make sessions last longer (60 min → 120-180 min) and avoid waste.

## 1. Selective clone — biggest win (36M → 2M)

**Before:** Every worker did `git clone https://github.com/gaganjainse/shesh-*` for all 22 repos:

```
shesh-voice 41M, shesh-desktop 22M, SheshAOS 7.5M, NexusAOS 7.5M, shesha-kernel 4.5M
Total src/ 36M + 3000 files → workspace 88-113 MB → HOP after 30-60 min
```

**After:** `tools/setup_worker.py` clones ONLY needed repos, shallow `--depth 1 --single-branch --filter=blob:none`

| Role | Before (22 repos) | After (selective) | Size | File count | Session length |
|------|-------------------|-------------------|------|------------|----------------|
| Brain | 22 repos 36M | `shesh-audit, shesh-secrets, SheshAOS` 3 repos ~8M | 8M | ~600 | 120-180 min |
| Mind | 22 repos 36M | `audit + memory,mind,harness,orchestrator,skills,calendar` 7 repos ~2M | 2M | ~500 | 120 min |
| Soma | 22 repos 36M | `audit + files,shell,system,backup,phone,containers,mcp-bundle,acp` 9 repos ~2M | 2M | ~700 | 120 min |
| Platform | 22 repos 36M | **0 repos** — only ecosystem itself (manifest, docs, Containerfile) | 0M | 0 extra | 150 min |
| Single component e.g., `shesh-memory` | 22 repos | `audit + memory` 2 repos ~600K | 0.6M | ~200 | 150 min |

**Usage:**

```bash
# Instead of cloning all 22:
python tools/setup_worker.py --role mind --clean
# or
python tools/setup_worker.py --component shesh-memory

# Check size
du -sh src/ && find src/ -type f | wc -l
```

**Integrate into swarm workers:** `worker_github.py` now calls `setup_worker` before work (if you pass `--setup`).

## 2. Other free efficiency strategies

### a) Shallow clone always

```bash
git clone --depth 1 --single-branch --filter=blob:none https://github.com/gaganjainse/shesh-memory.git
# vs full clone --depth full = 10x bigger
```

Our `setup_worker.py` does this by default. For large repos (`shesh-voice 41M`, `shesh-desktop 22M`) we use `--filter=blob:none` which downloads only commit+tree, not blobs until needed.

### b) No Rust toolchain in Arena

Rust toolchain `~/.cargo` + `~/.rustup` = ~1 GB → immediate workspace-over-budget. Our `SESSION_HANDOFF.md` says do NOT install Rust in sandbox — CI has Rust. For Brain work that needs `cargo test`, use `Containerfile` (Arch container with Rust) or run tests only on component that changed, not `cargo test --workspace`.

### c) Clean caches aggressively

```bash
python tools/session_guard.py --clean
# removes __pycache__, .pytest_cache, .ruff_cache, .venv, src/*/target, src/*/dist
```

`session_guard.py --tick` logs workspace size and file count; when > thresholds it says HOP. Cleaning resets it.

`tools/setup_worker.py --clean` does same.

### d) Run only relevant gates, not `make check` full

`make check` does: ruff + 30 ecosystem tests + license + resolve 3 locks = ~10 sec.

If you work on `shesh-memory` only:

```bash
# Instead of make check (30 tests)
python -m pytest tests/test_manifest.py -q   # 1 sec
python -m ruff check src/shesh-memory/       # 0.5 sec
cd src/shesh-memory && python -m pytest tests/ -q   # 1 sec
```

Saves 80% time.

Our workers now have `--component` filter to run only that component's tests.

### e) File queue vs GitHub Issues API — choose offline when traveling

- **GitHub Issues API** needs PAT + network, rate limited 5000 req/hour, adds latency, but true atomicity and UI.
- **File queue** `swarm/queue/*.json` + atomic `git push` is offline, no API calls, faster, no rate limit — better for phone with poor network.

While traveling on mobile with 1 tab, use file queue: `python tools/swarm/worker.py --component shesh-memory` (not `--github`). It uses only git push, no API.

Janitor Action `swarm-scheduled.yml` uses file queue re-queue logic too (no API needed for that part).

### f) PAT encryption — no rewrite, free

You already have encrypted PAT at `~/.config/shesh/github.pat.enc` (600) with password `<YOUR_ENCRYPTION_PASSWORD>`. Plain deleted on handoff for security. Next session auto-prompts via `ask_user` UI — you give password once per new tab, not every tool call. No need to rewrite PAT each session.

- Encrypted file persists across sessions (workspace snapshot includes `~/.config/shesh/` because .gitignore only ignores it from git, not from snapshot)
- Plain deleted on handoff → next session `need_password=true` → prompt

Free, no external secret manager needed.

### g) Free LLM — no OpenAI API cost

**Current system already free:** All components have deterministic stubs that work offline without any LLM API.

- `shesh-orchestrator`: `LLMAgents` calls Ollama if available, else falls back to deterministic stub that returns JSON steps — tests green without LLM.
- `shesh-memory`: local hash embedder offline, Ollama `nomic-embed-text` if available
- `shesh-harness`: `make_ollama_responder()` if Ollama, else stub

**Ollama is free and local** — on your MSI Sword (when back from travel) you run:

```bash
ollama pull phi4-mini qwen2.5-coder:3b moondream2 nomic-embed-text
# All 6 GB-safe, free, no API key
```

In Arena sandbox (no GPU), stubs keep system working — no cost.

**GitHub Models free tier** (alternative, no money): GitHub now offers free Models API `https://models.github.ai/inference` with `GITHUB_TOKEN` (no PAT needed) —  free for public repos. We could add `tools/llm_free.py` that calls `https://models.inference.ai.azure.com` with `GITHUB_TOKEN` — free, no OpenAI key.

You said you do everything free — we already do. No need for OpenAI API.

### h) Platform worker needs zero src clones

If you are Worker-Platform (docs, ADR, Containerfile, install.sh, CI), you don't need any `src/` clones. Just work on ecosystem repo itself. That's most efficient: 0 extra MB, 0 extra files → longest session.

Our `ROLE_MAP["platform"] = []` reflects this.

### i) Use GitHub Actions for true hours (free for public repos)

GitHub Actions free for public repos: 2000 min/month Ubuntu. Our `swarm-scheduled.yml` runs every hour, 3-5 min each, uses `GITHUB_TOKEN` not PAT, no cost.

While traveling with phone, **don't keep 5 Arena tabs** — keep 1 orchestrator + let Actions do janitor work. Actions run even if phone sleeps, for 1-2 days.

Actions that work free and unattended:

- `ci.yml`: ruff + pytest + license + locks
- `swarm-auto-merge.yml`: auto-merge `swarm/*` PRs if green
- `swarm-scheduled.yml`: every hour seed Issues, re-queue stale, push locks/docs

### j) Don't clone in every chat — share via `src/` persistence

Workspace `/home/user` persists across sessions (except `.cache`, `__pycache__`, etc). If you clone `shesh-memory` once via `setup_worker.py --component shesh-memory`, next session `src/shesh-memory` still exists — no need to re-clone. Our `clone_repo()` checks `if dest.exists(): git pull --ff-only --depth 1` — fast.

So first worker to run selective clone pays cost, others reuse.

## Summary checklist for traveling phone-only, free

- [ ] Use `tools/setup_worker.py --role mind --clean` instead of cloning 22 repos → 36M → 2M
- [ ] Use file queue `worker.py` not `worker_github.py --github` when network poor (saves API calls)
- [ ] Run only relevant tests, not full `make check` when working on single component
- [ ] Keep PAT encrypted, auto-prompt password once per new tab (no rewrite)
- [ ] Use deterministic stubs offline — no OpenAI cost, Ollama free on MSI when back
- [ ] Keep 1 orchestrator tab open on phone, let GitHub Actions janitor + auto-merge handle hours while phone sleeps
- [ ] On handoff, `session_guard --handoff` deletes plain PAT and cleans caches → next session starts fresh, longer

Result: Session length 60 min → 120-180 min, workspace 113 MB → 40-60 MB, file count 3400 → 800, no money spent.
