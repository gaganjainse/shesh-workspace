#!/usr/bin/env python3
"""Shesh autopilot CLI — list/seed/run pending tasks.

Examples:
  # Show what's pending
  python -m tools.autopilot.cli list

  # Seed tasks from TODO.md checkboxes
  python -m tools.autopilot.cli seed

  # Run (the agent provides the implementation; in autonomous mode)
  python -m tools.autopilot.cli run --max 10
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.autopilot.ledger import Ledger, Task  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def cmd_list(args: argparse.Namespace) -> int:
    ledger = Ledger()
    tasks = ledger.pending()
    print(f"{len(tasks)} pending:")
    for t in tasks:
        print(f"  [{t.id}] {t.title} (attempts={t.attempts})")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Parse '- [ ]' items from TODO.md into the ledger (idempotent)."""
    todo = ROOT / "TODO.md"
    text = todo.read_text(encoding="utf-8")
    n = 0
    ledger = Ledger()
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*-\s*\[\s\]\s*(.+)", line)
        if not m:
            continue
        title = m.group(1).strip()
        tid = f"todo-{i}"
        if not ledger.get(tid):
            ledger.add(Task(id=tid, title=title))
            n += 1
    print(f"Seeded {n} new task(s) from TODO.md")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    print("Autopilot run requires an implementation callback (run from agent).")
    print("Use: python -m tools.autopilot.runner via the agent loop.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shesh autopilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("seed").set_defaults(func=cmd_seed)
    r = sub.add_parser("run"); r.add_argument("--max", type=int, default=10)
    r.set_defaults(func=cmd_run)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
