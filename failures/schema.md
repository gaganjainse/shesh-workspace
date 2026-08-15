# Failure register schema

Every failure that cost time is recorded here as a row, not as prose. Prose is
read once and forgotten; a row can be counted, queried, and — the part that
matters — attached to a check that runs on every build.

## Why a register rather than a section in the manual

A narrative section grows until nobody reads it, and it cannot answer the two
questions that matter:

- Which failures can still recur, because nothing detects them?
- Did this change reintroduce one?

A register answers both mechanically. `guard.py --check` runs every detector
and fails the build if a known failure has come back.

## Layout

```text
failures/
├── schema.md          this file
├── register.toml      the rows
└── guards/            one detector per failure that can be detected
    └── <id>.py
```

One file for the data keeps diffs readable and merges sane. Guards are separate
so a detector can be non-trivial without bloating the register.

## Row

```toml
[F014]
title      = "A shallow clone has no merge base"
date       = 2026-08-15
severity   = "high"
area       = ["ci"]
symptom    = "A conflict is reported for branches that merge cleanly."
cause      = """git merge-tree returns non-zero when the clone shares no
history with the base, and the step read that as a conflict."""
rule       = "Deepen the fetch before comparing branches; match on CONFLICT."
guard      = "guards/F014.py"
status     = "guarded"
cost       = "45m"
recurrence = 1
```

## Fields

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | One line, stated as the failure, not the fix |
| `date` | yes | When it was first observed, ISO 8601 |
| `severity` | yes | `critical`, `high`, `medium`, `low` |
| `area` | yes | One or more of `ci`, `docs`, `security`, `tooling`, `process`, `packaging`, `git` |
| `symptom` | yes | What a person sees. Written so it is recognisable before the cause is known |
| `cause` | yes | Why it happened. Mechanism, not blame |
| `rule` | yes | The behaviour that prevents it, imperative |
| `guard` | no | Path to an executable detector |
| `status` | yes | `guarded`, `manual`, or `accepted` |
| `cost` | no | Rough time lost, so priority is evidence-based |
| `recurrence` | yes | How many times observed. Above one means the rule is not working |

## Status

**`guarded`** — a detector exists and runs in the gate. The failure cannot
silently return.

**`manual`** — no detector is possible or none is written yet. The rule relies
on a person following the manual. Every `manual` row is a candidate for
automation; the count is reported so the gap stays visible.

**`accepted`** — understood, judged not worth preventing. Requires a reason in
`cause`.

## Guards

A guard is an executable that exits `0` when the failure is absent and non-zero
when present. It receives the fleet root as `argv[1]`.

```python
#!/usr/bin/env python3
"""F014: a shallow clone has no merge base."""
import sys

def check(fleet: str) -> list[str]:
    """Return a list of findings. Empty means the failure is absent."""
    return []

if __name__ == "__main__":
    findings = check(sys.argv[1] if len(sys.argv) > 1 else ".")
    for f in findings:
        print(f"  {f}")
    sys.exit(1 if findings else 0)
```

A guard must be fast, offline, and free of false positives. A noisy guard gets
disabled, and a disabled guard is worse than none because it looks like cover.

## Adding a row

When something breaks in a way that was avoidable:

1. Add the row in the same change that fixes the failure.
2. Write a guard unless it is genuinely undetectable. Prefer a narrow guard
   that catches the specific mechanism over a broad one that catches nothing.
3. If no guard is possible, set `status = "manual"` and say why in `cause`.
4. Run `python3 tools/guard.py --check`.

If the same failure recurs, increment `recurrence` rather than adding a row.
A rising count means the rule is not working and the guard needs to be
stronger, not that the register needs another entry.
