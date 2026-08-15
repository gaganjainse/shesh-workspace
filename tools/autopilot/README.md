# Shesh Autopilot

A foolproof, self-running build system for the agent. It exists **before**
the project is built so the agent can work unattended without losing work
or pushing broken code.

## Safety core (`safety.py`)

Hard invariants checked before any git operation:

- Never commit when tests fail (`pytest` must be green).
- Never force-push; never push to a non-canonical remote (local/file
  remotes are allowed for tests).
- Never touch protected paths (`.ssh`, `.gnupg`, vaults, job folders).
- Roll back (soft reset) if a push fails.
- Archive, don't delete.

## Durable ledger (`ledger.py`)

A JSONL journal of tasks at
`~/.local/share/shesh/autopilot/ledger.jsonl`. Each task has a status, so
an interrupted run resumes without redoing completed work.

## Gate (`gate.py`)

Runs `ruff` + `pytest` per component and returns a `GateReport` with the
number of tests. A red gate blocks commit.

## Runner (`runner.py`)

The main loop:

1. Pick the next pending task.
2. Call the implementation callback.
3. Gate the changed component.
4. `safe_commit` + `safe_push`.
5. On failure: retry once with rollback, then mark failed and continue.

## CLI

```bash
python -m tools.autopilot.cli list    # show pending tasks
python -m tools.autopilot.cli seed    # import TODO.md checkboxes
```

The agent itself uses `runner.run(implement=...)`; the CLI is for humans.

## Testing

The autopilot tests itself (`tests/autopilot/`) — safety, ledger, gate, and
runner end-to-end with a local bare remote. 12 tests.
