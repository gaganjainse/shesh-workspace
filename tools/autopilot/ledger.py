"""Durable work ledger for the autopilot.

A JSONL journal of tasks the agent is working through. Each task has a
status (pending|running|done|failed|skipped), so an interrupted run can
resume without redoing completed work or losing in-progress state.

The ledger lives at
  ~/.local/share/shesh/autopilot/ledger.jsonl
with a pointer to the current task. This is intentionally separate from
git so an interrupted push doesn't corrupt it.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from collections.abc import Iterable

LEDGER_DIR = Path(
    os.environ.get("SHESH_AUTOPILOT_DIR")
    or (Path.home() / ".local" / "share" / "shesh" / "autopilot")
)


@dataclass
class Task:
    id: str
    title: str
    component: str = ""          # repo/component dir, if any
    status: str = "pending"      # pending|running|done|failed|skipped
    attempts: int = 0
    last_error: str = ""
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    sha: str = ""                # commit pushed, if any

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class Ledger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (LEDGER_DIR / "ledger.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, Task] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                t = Task(**json.loads(line))
                self._tasks[t.id] = t
            except (json.JSONDecodeError, TypeError):
                continue

    def _append(self, t: Task) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(t.to_json() + "\n")

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        self._append(task)
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **fields) -> Task | None:
        t = self._tasks.get(task_id)
        if not t:
            return None
        for k, v in fields.items():
            setattr(t, k, v)
        t.updated = time.time()
        self._append(t)
        return t

    def pending(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status in {"pending", "running"}]

    def next_pending(self) -> Task | None:
        for t in self._tasks.values():
            if t.status == "pending":
                return t
        return None

    def all(self) -> list[Task]:
        return list(self._tasks.values())

    def from_todos(self, todos: Iterable[tuple[str, str]]) -> int:
        """Seed the ledger from (id, title) pairs; skip existing."""
        n = 0
        for tid, title in todos:
            if tid not in self._tasks:
                self.add(Task(id=tid, title=title))
                n += 1
        return n
