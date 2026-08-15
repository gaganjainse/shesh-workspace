---
title: setup_worker.py
type: how-to
summary: "Status: living · last verified 2026-08-13."
audience: contributor
status: current
verified: 2026-08-15
---

# setup_worker.py

Status: living · last verified 2026-08-13
Source: `tools/setup_worker.py` · Rationale: [EFFICIENCY](clone-efficiency.md)

A swarm worker does not need the 22-repo fleet. This tool clones exactly what
a role touches, shallow and blob-filtered, so a fresh workspace boots in
seconds instead of minutes.

## Usage
```bash
python tools/setup_worker.py --role brain --clean
python tools/setup_worker.py --role platform --clean
```

- Roles: `brain`, `mind`, `soma`, `platform` — each maps to a fixed component
  list in the tool (single source: the role table inside `setup_worker.py`).
- Clones are `--depth 1 --filter=blob:none`: measured 36 MB → ~1.3–3.3 MB and
  ~3000 → ~300 files on 2026-08-11 (see
  [the incident chronology](https://github.com/gaganjainse/shesh-docs-archive/blob/main/src/incident-2026-08-11-swarm-collision.md),
  Tab 2).
- `--clean` resets the workspace layout before cloning.

## What it also fixes on boot
- Repo-local git identity (missing identity caused silent empty-commit PR
  422s during the incident).
- Credential wiring via the secure PAT loader, so worker pushes cannot fail
  silently — workers fail closed instead.
