"""Shesh autopilot: self-running, foolproof build system.

This package makes the agent safe to run unattended:

- `safety`  — hard invariants (never push red, never force-push main,
              archive don't delete, never touch protected paths).
- `ledger`  — durable journal of work so a run resumes after interruption
              without redoing or losing tasks.
- `gate`    — runs tests + lint per component before commit/push.
- `runner`  — the main loop: pick next TODO, implement, gate, commit, push,
              record; on failure, retry once then roll back and move on.

The autopilot is itself fully tested so it cannot silently break safety.
"""
from __future__ import annotations

__version__ = "0.1.0"
