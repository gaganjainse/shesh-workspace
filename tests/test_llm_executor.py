"""Offline tests for the real LLM executor and the swarm circuit breaker."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import tools.swarm.github_queue as github_queue
import tools.swarm.llm_executor as llu


GOOD_DIFF = """diff --git a/hello.txt b/hello.txt
new file mode 100644
index 0000000..3b18e51
--- /dev/null
+++ b/hello.txt
@@ -0,0 +1 @@
+hello world
"""


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("# demo\n")
    (repo / "scripts").mkdir()
    (repo / "scripts").joinpath("x.py").write_text("print('x')\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


def test_validate_diff_accepts_small_safe_patch() -> None:
    ok, why = llu.validate_diff(GOOD_DIFF)
    assert ok, why


def test_validate_diff_rejects_empty() -> None:
    ok, _ = llu.validate_diff("no diff here\njust prose")
    assert not ok


def test_validate_diff_rejects_forbidden_paths() -> None:
    diff = GOOD_DIFF.replace("hello.txt", "secrets/api.key")
    ok, why = llu.validate_diff(diff)
    assert not ok and "forbidden" in why


def test_validate_diff_rejects_parent_traversal() -> None:
    diff = GOOD_DIFF.replace("hello.txt", "../escape.txt")
    ok, why = llu.validate_diff(diff)
    assert not ok and "unsafe" in why


def test_validate_diff_rejects_too_many_files() -> None:
    parts = []
    for i in range(llu.MAX_DIFF_FILES + 1):
        parts.append(GOOD_DIFF.replace("hello.txt", f"f{i}.txt"))
    ok, why = llu.validate_diff("".join(parts))
    assert not ok and "files" in why


def test_validate_diff_rejects_too_many_lines() -> None:
    big = """diff --git a/big.txt b/big.txt
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/big.txt
@@ -0,0 +1,N @@
""" + "".join(f"+line {i}\n" for i in range(llu.MAX_DIFF_LINES + 5))
    ok, why = llu.validate_diff(big)
    assert not ok and "lines" in why


def test_parse_diff_requires_actual_diff() -> None:
    assert llu.parse_diff({"diff": GOOD_DIFF}) == GOOD_DIFF
    assert llu.parse_diff({"diff": "sure, here you go"}) is None
    assert llu.parse_diff({"summary": "x"}) is None


def test_context_selection_ranks_keyword_hits(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tools").mkdir()
    (repo / "tools" / "session_guard.py").write_text("# guard\n")
    (repo / "docs").mkdir()
    (repo / "docs" / "unrelated.md").write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "more"], cwd=repo, check=True)
    issue = {"number": 1, "title": "Fix session_guard timeout", "body": ""}
    chosen = llu.select_context_files(issue, repo, "platform")
    assert "tools/session_guard.py" in chosen
    assert chosen.index("tools/session_guard.py") == 0


def test_apply_and_change_detection(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    ok, why = llu.apply_diff(repo, GOOD_DIFF)
    assert ok, why
    assert (repo / "hello.txt").read_text().strip() == "hello world"
    assert "hello.txt" in llu.changed_files(repo)


def test_implement_applies_verified_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)

    class _StubAdapter:
        def generate(self, task, prompt, max_retries=2):  # noqa: ARG002
            return {"diff": GOOD_DIFF, "summary": "add hello"}, _StubModel(), 0.9

    class _StubModel:
        name = "stub-test"

    monkeypatch.setattr(llu, "ModelAgnosticAdapter", lambda: _StubAdapter())
    ok, msg = llu.implement({"number": 7, "title": "t", "body": ""}, repo, "b", "general")
    assert ok, msg
    assert "stub-test" in msg
    assert (repo / "hello.txt").exists()


def test_implement_refuses_diffless_model_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)

    class _EmptyAdapter:
        def generate(self, task, prompt, max_retries=2):  # noqa: ARG002
            return {"summary": "no diff"}, _M(), 0.9

    class _M:
        name = "stub-empty"

    monkeypatch.setattr(llu, "ModelAgnosticAdapter", lambda: _EmptyAdapter())
    ok, msg = llu.implement({"number": 8, "title": "t", "body": ""}, repo, "b", "general")
    assert not ok and "exhausted" in msg
    assert not (repo / "hello.txt").exists()


class _FakeAPI:
    """Records GitHub API calls made by the circuit breaker (no network)."""

    def __init__(self, labels: set[str]) -> None:
        self.labels = labels
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method: str, url: str, data: dict | None = None):
        self.calls.append((method, url, data))
        if method == "GET" and "/issues/" in url:
            return 200, {"labels": [{"name": n} for n in sorted(self.labels)]}
        if method == "POST" and "/labels" in url:
            self.labels.update(data.get("labels", []))
        if method == "DELETE" and "/labels/" in url:
            self.labels.discard(url.rsplit("/", 1)[1])
        return 200, {}


def test_circuit_breaker_trips_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _FakeAPI({"swarm", "swarm:pending", "swarm:attempt-1", "swarm:attempt-2"})
    monkeypatch.setattr(github_queue, "_request", api)
    monkeypatch.setattr(github_queue, "MAX_ATTEMPTS", 3)

    attempts = github_queue.record_attempt(9)
    assert attempts == 3
    github_queue.block_issue(9, "third failure in test")

    assert "swarm:attempt-3" in api.labels
    assert "swarm:blocked" in api.labels
    assert "swarm:pending" not in api.labels


def test_attempt_count_defaults_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _FakeAPI({"swarm"})
    monkeypatch.setattr(github_queue, "_request", api)
    assert github_queue.attempt_count(5) == 0
    assert github_queue.record_attempt(5) == 1
    assert "swarm:attempt-1" in api.labels
