# setup_worker.py — minimal per-role workspaces

Status: living · last verified 2026-08-13
Source: `tools/setup_worker.py` · Rationale: [EFFICIENCY](../EFFICIENCY.md)

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
  [the incident chronology](../history/incidents/2026-08-11-multi-tab-swarm.md),
  Tab 2).
- `--clean` resets the workspace layout before cloning.

## What it also fixes on boot

- Repo-local git identity (missing identity caused silent empty-commit PR
  422s during the incident).
- Credential wiring via the secure PAT loader, so worker pushes cannot fail
  silently — workers fail closed instead.
