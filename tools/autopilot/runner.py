"""Autopilot runner: safe, resumable, self-verifying build loop.

Usage:
    python -m tools.autopilot.runner [--max N] [--dry-run]

The runner reads TODO.md-derived tasks from the ledger, executes an
implementation callback per task, then gates/commits/pushes. On failure it
retries once; if it still fails, it rolls back (soft reset) and marks the
task failed, then continues with the next task.

The implementation function is injected so the actual coding work stays in
the agent's hands; this module enforces the foolproof lifecycle around it.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import safety
from .gate import run_gate
from .ledger import Ledger, Task

ROOT = Path(__file__).resolve().parents[3]  # ecosystem root

Implement = Callable[[Task], Path | None]  # returns repo path on success


@dataclass
class RunStats:
    done: int = 0
    failed: int = 0
    skipped: int = 0
    retried: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"done={self.done} failed={self.failed} "
                f"skipped={self.skipped} retried={self.retried}")


def process_task(task: Task, implement: Implement, dry_run: bool,
                 stats: RunStats) -> None:
    """Implement, gate, commit, and push one task with retry+rollback."""
    print(f"\n▶ {task.id}: {task.title}")
    task.attempts += 1
    repo: Path | None = None
    try:
        for attempt in (1, 2):
            try:
                repo = implement(task)
                if repo is None:
                    stats.skipped += 1
                    print(f"  ⊘ skipped (nothing to do)")
                    return
                if dry_run:
                    print(f"  · dry-run; would gate/commit {repo}")
                    stats.done += 1
                    return
                report = run_gate(repo)
                if not report.ok:
                    raise RuntimeError(
                        f"gate failed: tests={report.tests_passed} "
                        f"ruff={report.ruff_passed}\n{report.test_output[:1000]}")
                # Commit and push through safety guards.
                safety.safe_commit(repo, f"{task.id}: {task.title}")
                safety.safe_push(repo)
                stats.done += 1
                print(f"  ✓ pushed ({report.n_tests} tests)")
                return
            except Exception as e:  # noqa: BLE001
                if attempt == 1:
                    stats.retried += 1
                    print(f"  ↻ retry after: {e}")
                    if repo:
                        safety.rollback(repo)
                    continue
                raise
        stats.failed += 1
        stats.errors.append(f"{task.id}: {e}")
        print(f"  ✗ failed: {e}")
    except Exception as e:  # noqa: BLE001
        stats.failed += 1
        stats.errors.append(f"{task.id}: {e}")
        if repo:
            try:
                safety.rollback(repo)
            except Exception:
                pass
        traceback.print_exc()


def run(implement: Implement, max_tasks: int = 50, dry_run: bool = False,
        ledger: Ledger | None = None) -> RunStats:
    ledger = ledger or Ledger()
    stats = RunStats()
    for _ in range(max_tasks):
        task = ledger.next_pending()
        if not task:
            break
        ledger.update(task.id, status="running")
        process_task(task, implement, dry_run, stats)
        ledger.update(
            task.id,
            status="done" if task.id not in [e.split(":")[0] for e in stats.errors]
            else "failed",
        )
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shesh autopilot runner")
    ap.add_argument("--max", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    # In standalone mode there's no implementation callback; the agent uses
    # this module as a library. We print pending tasks and exit.
    ledger = Ledger()
    pending = ledger.pending()
    print(f"{len(pending)} pending tasks in {ledger.path}")
    for t in pending:
        print(f"  [{t.id}] {t.title}")
    if not pending:
        print("Nothing pending. Populate the ledger from TODO.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
