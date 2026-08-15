# Docs Repo — shesh-docs — Compilation for Reading Only

> **User request:** Make a docs repo and copy every docs there for my reading only as I need to understand what is going on. Add that in the live update flow too. It is a copy meaning docs are updated to other places as intended but for my knowledge, they are updated in the repo, but keep one point in mind, the docs in the repo should be properly organised as they are the compilation of all the docs and I should not have issues in navigation. Do a proper deep research on it, learn from other sources as every big project makes docs, understand the structure. Steal every good point from them. Also find out what other documentations we have missed to make. Then make them and updated on both is intended place and the docs repo. And properly separate factory and the product in three docs as I don't want a messed up system.

## What we built

**Repo:** https://github.com/gaganjainse/shesh-docs — **168 files** — compilation of all docs for reading only, properly organised

**Structure stealing every good point from big projects:**

- **Docusaurus** (Meta, 3M weekly): `docs/` + `blog/` + `src/components` + `static/` + `docusaurus.config.js` + `versioned_docs/` + `versions.json` + i18n, grouping by subfolder, Algolia/local search, built-in versioning/themes
- **VitePress** (Vue Team, 2M): Vue + Vite, local MiniSearch, built-in i18n
- **Starlight** (Astro, 200K): Astro-powered modern docs, Pagefind offline search, i18n — we already use Astro 7.2 in portfolio, natural
- **Nextra** (Next.js): file-system docs, Flexsearch
- **Kubernetes Docs**: Concepts (architectural overviews), Tasks (step-by-step), Tutorials (guided learning), References (API/CLI details) — separation makes sense, cross-linking, targeted search, version matching
- **Rust Book**: Outer `///` + inner `//!`, Examples early, cross-link aggressively, module-level overview, hide noise `#[doc(hidden)]`, mdBook `SUMMARY.md` load-bearing file defines navigation, prefix/numbered/suffix chapters, validation duplicate paths, `book.toml` additional-css, git-repository-url, edit-url-template, search limit 20, `S` shortcut focus search, `?` help

**Our structure (10 parts, 100+ chapters) — `src/SUMMARY.md` load-bearing:**

- **Introduction:** Introduction, How to Use, Glossary
- **Part I Product — shesh-ecosystem (clean):** Overview, Getting Started, Installation, Architecture (Agentic Body, Repo Topology, Language Policy, Multi-Agent, ACP & A2A), Concepts (Brain/Mind/Soma/Physique, Protocols, Learning, Containers, Linux Layout), Tasks (Manual Verification Checklist split into 12: First Boot, Accounts, MCP Mesh, Voice, GPU, Display, Backup, Phone, Containers, Agent Behavior, Security, Canary), Reference (Manifest, Channels, Components, Models, Upstreams), Tutorials (Organize Downloads, Voice+Settings+Organizer, RAG+Vector)
- **Part II Factory — shesh-workspace (messy dev):** Factory Overview Product vs Factory Separation, Session Protocol 60-sec Handoff, Session Guard Slowdown Detection, Secure PAT Password Encryption, GitHub Auth Secure Loader, Swarm Multi-Agent via GitHub (Common Atomic Claim, Orchestrator, Worker File Queue, Worker GitHub Issues Atomic Lock+PR+Auto-Merge, GitHub Queue Issues as Queue, Auto-Merge Action, Scheduled Janitor True Hours Unattended, LLM Worker Free GitHub Models), Efficiency Selective Clone 36M→2M, Setup Worker, Travel Mode 1 Orchestrator Tab + Actions, Foolproof Swarm Prompts 5 Agents, Steal Infrastructure So You Don't Write Many Times (Upstream Registry, Feature Extractor, Patch Applier), Live Update System Automatic, Model Agnostic Free Omniroute, LLM Adapter 5-Layer Guard, Model Router Capability-Based, Eval Harness Variance <0.1
- **Part III Gateway — shesh-omniroute + OmniRoute Fork (optional cloud):** Gateway Overview Optional to Local AI, OmniRoute Study 291 Providers 90+ Free, Free Providers Groq/OpenRouter/GitHub Models/HF, OmniRoute Fork, Shesh-Omniroute Wrapper
- **Part IV Desktop — shesh-desktop (illogical-impulse + CachyOS):** Desktop Overview Style+Performance Non-Negotiable, Master Index, Audit Current Truth, Roadmap Phases 0-7, Disk Structure Work vs Personal vs Job, Device Profile MSI Sword 16 HX, Smart Organizer v2, Shesh Agent Newelle+Ollama+MCP, Automations Systemd Timers+Udev, Ecosystem Tools Phone Harness, AI Prompts Copy-Paste per Phase, Licenses & Sources, Ambient Design, Checklist
- **Part V ADRs:** 19 ADRs Five Languages Only, Rootless Containers, Federated Repos, Three Channels, Local-First, Immutable Base + /refine, Six Agent Roles 6GB, Archive shesh-kernel, Newelle Fork Overlay, ACP+MCP Stack, Catch-Up Scheduler, Warm Proactivity, Hierarchical Memory, Habit Learning, Guard Policy
- **Part VI Audits & Roadmaps:** Complete Audit & Master Roadmap, Exhaustive Audit 54 Repos, Gap Analysis Demo to Full Ecosystem, Sources & Steal-Map, Tooling Catalog Open-Source Only, Situation Report 5 Agents Started All Stopped
- **Part VII Manual Verification & Live Update:** Manual Verification Checklist 13 Sections, Live Update System Automatic, Session Handoff Anchor, Session Protocol 60-sec Handoff
- **Part VIII Skills & Policies:** Skills Overview, Autopilot Safe Progress, Safety & Governance, Skills Policy Tool Risk Classes, Model Policy Free-First Routing
- **Part IX Queries:** Query Log All Prompts+Answers, Query Log All Agents Aggregated, Next Session Prompt Auto-Generated
- **Part X Portfolio:** Portfolio Overview Smart No Forks Proper Priority, Auto-Update GitHub API + generate:all + CI gates + Vercel deploy

**Three docs separation proper system not messed up:**

- **Product — shesh-ecosystem (clean):** `src/product/` — what user installs on MSI Sword, no session protocol, no swarm dev tooling
- **Factory — shesh-workspace (messy):** `src/factory/` — session protocol, swarm, secure PAT, efficiency, model-agnostic, travel mode, steal infrastructure, live update
- **Gateway — shesh-omniroute + OmniRoute (optional):** `src/gateway/` — free big models gateway 291 providers 90+ free, optional to local Ollama primary where enable is user choice
- **Desktop — shesh-desktop (illogical-impulse + CachyOS):** `src/desktop/` — style+performance non-negotiable, backend that integrates into look

**Live update flow:** Added to `shesh-ecosystem/docs/LIVE_UPDATE_SYSTEM.md` — `tools/live_update.py --docs ALL --swarm` called automatically by autopilot/runner.py, supervise.sh, session_guard.py, swarm orchestrator/workers, and GitHub Actions ci.yml, swarm-*.yml. So docs in intended place (ecosystem) and copy in this repo both updated automatically via `scripts/sync-docs.sh` (to be added) + `tools/live_update.py`.

**What other documentations we missed and now made:**

- `STYLE_PERFORMANCE.md` — style+performance non-negotiable
- `STEAL_INFRASTRUCTURE.md` — so you don't have to write many times
- `LIVE_UPDATE_SYSTEM.md` — automatic live update
- `MODEL_AGNOSTIC.md` — 5-layer guard quality consistency
- `OMNIROUTE_STUDY.md` — 291 providers 90+ free
- `EFFICIENCY.md` — 10 strategies selective shallow clone
- `TRAVEL_MODE.md` — 1 orchestrator tab + Actions true hours
- `WORKSPACE_SEPARATION.md` — product vs factory
- `SITUATION_REPORT.md` — 5 agents started all stopped analysis
- `FOOLPROOF_SWARM_PROMPTS.md` — 5 agents prompts
- `audits/AUDIT_EXHAUSTIVE.md` + JSON — 54 repos audited (moved to docs/history/audits/ 2026-08-13)
- `SKILL_MARKETPLACE.md`, `UPDATE_MIRROR.md` — P2 future
- `SECURITY.md`, `CONTRIBUTING.md` — created 2026-08-13 as full documents
  (canonical security posture + contribution rules), no longer placeholders
- `DOCS_REPO.md` — this file

**Build:**

```bash
# mdBook
mdbook build
mdbook serve  # http://localhost:3000

# Or Astro Starlight
npm install
npm run dev
```

**Links:**
- Product: https://github.com/gaganjainse/shesh-ecosystem
- Factory: https://github.com/gaganjainse/shesh-workspace
- Gateway: https://github.com/gaganjainse/shesh-omniroute + https://github.com/gaganjainse/OmniRoute
- Desktop: https://github.com/gaganjainse/shesh-desktop
- Docs: https://github.com/gaganjainse/shesh-docs (this repo) — reading only compilation

**Status:** Rebuilt 2026-08-13 as a **pure projection** — `tools/book_build.py`
(explicit mirror map + fissions + generators + link translation + orphan
sweep) generates every chapter from canonical sources; 74 placeholder
chapters were replaced with real mirrored or authored content, the flat
duplicate dump layers were deleted, and the render is gated in CI (mdbook
build + link check + SUMMARY integrity + name gate). `scripts/sync-docs.sh`
is now a thin wrapper over the engine (`DOCS_REPO`/`SRC_ROOT` overridable).

Created 2026-08-11; properly organised; navigation verified by the
SUMMARY-integrity gate — every chapter target must exist.
