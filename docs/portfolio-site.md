---
title: Portfolio
type: explanation
summary: "Repository: gaganjainse/portfolio."
audience: contributor
status: current
verified: 2026-08-15
---

# Portfolio

Repository: [gaganjainse/portfolio](https://github.com/gaganjainse/portfolio)
(Astro, deploys to Vercel via `vercel.json`).

House rules for the portfolio, in priority order:

1. **No forks** — original work only; nothing padded.
2. **Proper priority** — projects are ordered by real signal, not recency.
3. **Zero manual upkeep** — the site regenerates from the GitHub API (see
   [the pipeline](#the-pipeline)); stale project data is treated as a bug,
   same standard as stale docs.

## Quality floor (enforced by scripts, not intentions)
- `npm run check` (astro check), `npm run lint` (eslint), `npm test`
  (vitest), `npm run format:check` (prettier) — all wired into the `auto`
  pipeline and CI.
- Generated assets (favicons, OpenGraph image, résumé PDF) are reproducible
  from `npm run generate:all` — never hand-edited binaries.

## Automation

Everything below is wired in the
[portfolio repo](https://github.com/gaganjainse/portfolio) today.

### The pipeline
```bash
npm run auto
# = update:projects  (scripts/auto-update-projects.mjs — GitHub API pull)
#   + generate:all   (favicons, og-image, résumé PDF)
#   + check && lint && test && build
```

Two GitHub Actions workflows carry it:

| Workflow | Job |
|---|---|
| `auto-update.yml` | scheduled refresh of project data from the GitHub API |
| `ci.yml` | check + lint + test + build gate on every push |

Deploys: Vercel, configured by `vercel.json` — main is production.

### What to verify by hand (quarterly)
- [ ] Last `auto-update.yml` run is green and its commit landed.
- [ ] The projects shown match the real pinned order on the GitHub profile.
- [ ] `npm run auto` exits 0 locally end-to-end — if any stage fails, the
      pipeline must fail loudly (a green run with a broken stage is the one
      outcome this design exists to prevent).
