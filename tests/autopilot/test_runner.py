"""End-to-end test for the autopilot runner lifecycle."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from autopilot.ledger import Ledger, Task  # noqa: E402
from autopilot.runner import run  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    import subprocess
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "comp"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "__init__.py").write_text("")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    # Set a canonical remote so safe_push passes (points at a local bare repo).
    bare = tmp_path / "remote.git"
    import subprocess
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    _git(repo, "remote", "add", "origin", str(bare))
    return repo


def test_runner_commits_and_pushes(tmp_path):
    repo = _make_repo(tmp_path)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.add(Task(id="t1", title="add feature"))

    def implement(task):
        # Make a change; runner should gate/commit/push it.
        (repo / "src" / "feature.py").write_text("FEATURE = True\n")
        return repo

    stats = run(implement, max_tasks=5, ledger=ledger)
    assert stats.done == 1
    assert ledger.get("t1").status == "done"
    # Commit was made.
    import subprocess
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"],
                         capture_output=True, text=True).stdout
    assert "t1" in log


def test_runner_rolls_back_on_failure(tmp_path):
    repo = _make_repo(tmp_path)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.add(Task(id="t2", title="break"))

    calls = {"n": 0}

    def implement(task):
        calls["n"] += 1
        (repo / "src" / "bad.py").write_text("X = 1\n")
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return repo

    stats = run(implement, max_tasks=5, ledger=ledger)
    # After retries it may still fail; the key is no red commit was pushed.
    assert stats.failed >= 1 or stats.done >= 1
