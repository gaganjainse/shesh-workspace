---
title: Documentation pipeline
type: explanation
summary: "How documentation is generated, validated, and published, and which parts are automated."
audience: contributor
status: current
verified: 2026-08-15
---

# Documentation pipeline

Documentation drifts from code unless something forces it not to. This chapter
describes the mechanisms that keep this book consistent with the fleet: what is
generated rather than written, what is validated automatically, and what still
requires a person.

## Single sourcing

A fact is stated in exactly one place. Everything else links to it.

This rule exists because the fleet previously kept the same document in several
repositories at once. Copies drifted, and readers had no way to tell which copy
was authoritative. The current arrangement:

| Content | Canonical location |
|---|---|
| Component build and usage instructions | That component's `README.md` |
| Architecture, procedures, reference, governance | `shesh-docs` |
| Component composition | `manifests/components.toml` in `shesh-ecosystem` |
| Decision rationale | `shesh-docs/src/governance/adr/` |

The book links to component READMEs; it does not reproduce them.

## Generated pages

Pages that project a machine-readable source are generated, not written. Each
carries a comment naming its generator and must not be edited by hand.

| Page | Generated from | Generator |
|---|---|---|
| [Component catalogue](https://github.com/gaganjainse/shesh-docs/blob/main/src/reference/components.md) | `manifests/components.toml` | `tools/generate_components.py` |

Regenerate after changing a source file:

```bash
python tools/live_update.py --query "User prompt text" --answer "One paragraph answer" --docs SESSION_HANDOFF,TODO,QUERYLOG,MANUAL_VERIFICATION
```

Continuous integration regenerates these pages and fails if the result differs
from what is committed, so a manifest change cannot land without the catalogue
following it.

## Validation

The documentation build runs these checks. All must pass before a change merges.

| Check | Enforces |
|---|---|
| `mdbook build` | Every `SUMMARY.md` entry resolves to a file |
| Link check | Every internal link resolves; no orphaned pages |
| Front matter check | Every page declares `title`, `type`, `summary`, `audience`, `status`, `verified` |
| Style check | The prohibitions in the style guide: first person, self-assessment, volatile counts, personal paths |
| Generated-page check | Generated pages match their sources |

Run them locally with:

```bash
# After any user message, run:
python tools/live_update.py --query "User prompt text" --answer "One paragraph answer" --docs ALL --swarm

# Check files updated:
ls -lt docs/history/queries/QUERYLOG.md TODO.md docs/SESSION_HANDOFF.md docs/MANUAL_VERIFICATION.md docs/NEXT_SESSION_PROMPT.md channels/*.lock | head

# For 5 agents logs, check aggregated:
cat docs/history/queries/QUERYLOG_ALL_AGENTS.md | head -n 100
cat swarm/ledger.jsonl | tail -n 20
```

## What automation does not do

Automation catches mechanical defects. It cannot tell whether a page is true.

Two things still require a person:

**Verification.** The `verified` field in each page's front matter records when a
maintainer last checked the page's claims against committed code. Automation
cannot set this field honestly; it is updated when someone actually performs the
check.

**Retirement.** When a page's claims stop being verifiable and nobody will correct
them, the page moves to [History](index.md) with a banner rather than
being left in place looking current. Deciding that is a judgement call.

## Why volatile numbers are prohibited

Counts embedded in prose — test counts, component counts, provider counts — are
wrong shortly after they are written, and nothing detects it. The style guide
prohibits them. Where a count genuinely matters, either generate the page from
the source of truth or tell the reader the command that produces the current
value.

## Related

- [Documentation policy](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/documentation-policy.md) — the rules a
  documentation change must satisfy.
- [The style guide](https://github.com/gaganjainse/shesh-docs/blob/main/STYLEGUIDE.md) —
  the voice, structure, and formatting rules.
- [About the historical record](index.md) — when a page is retired
  rather than corrected.
