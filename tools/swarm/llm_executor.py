#!/usr/bin/env python3
"""Real LLM executor for the swarm worker — patches, not artifacts.

Turns a claimed GitHub issue into an *applied, gate-verified* code change in
the checked-out worktree.  There are no marker files and no demo paths:

1. A bounded repo map + the most relevant file contents form the context.
2. The model must answer with a fenced **unified diff** plus a JSON summary.
3. The diff is parsed, size-capped, path-checked, and applied with
   ``git apply --check`` / ``git apply``.
4. File-targeted gates run *before* returning: ``ruff check`` on touched
   Python files and ``pytest tests/`` whenever source under test changes.
   Failure feeds a repair prompt (bounded by ``MAX_ROUNDS``).
5. Only a clean, applied, verified tree returns ``True`` to the worker,
   which then commits, pushes, opens the PR, and lets the auto-merge gate
   re-verify.  Anything else returns ``False`` so the claim is released and
   the circuit breaker counts the failure.

Provider order comes from ``manifests/models.toml`` via
``tools/llm_adapter.py`` — OmniRoute (self-hosted gateway), local Ollama,
GitHub Models, Groq, OpenRouter, HuggingFace.  Nothing here is provider
specific.

Executor protocol (tools/swarm/worker_github.py)::

    --executor llm_executor:implement
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/swarm"))

from llm_adapter import ModelAgnosticAdapter, TaskSpec  # noqa: E402

MAX_ROUNDS = int(os.environ.get("SHESH_EXECUTOR_ROUNDS", "2"))
MAX_DIFF_FILES = int(os.environ.get("SHESH_EXECUTOR_MAX_FILES", "8"))
MAX_DIFF_LINES = int(os.environ.get("SHESH_EXECUTOR_MAX_LINES", "400"))
MAX_CONTEXT_BYTES = int(os.environ.get("SHESH_EXECUTOR_CONTEXT", "24000"))
REPO_MAP_LIMIT = 400  # paths listed for the model

# Paths an autonomous model may never touch.
FORBIDDEN_PREFIXES = (".git", "secrets/", ".github/CODEOWNERS")
FORBIDDEN_GLOBS = ("*.pat", "*.key", "*.pem", "*.enc")

# Where component code usually lives inside this repo (ecosystem = factory).
COMPONENT_HINTS = {
    "general": ("scripts/", "tools/", "docs/", "tests/"),
    "platform": ("tools/", "scripts/"),
    "docs": ("docs/", "README.md", "TODO.md"),
}

KEYWORD_SPLIT = re.compile(r"[A-Za-z][A-Za-z0-9_+-]{2,}")


def _git(root: pathlib.Path, *args: str, timeout: int = 60) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def tracked_files(root: pathlib.Path) -> list[str]:
    rc, out, _ = _git(root, "ls-files")
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def build_repo_map(root: pathlib.Path) -> str:
    files = tracked_files(root)
    if len(files) > REPO_MAP_LIMIT:
        files = files[:REPO_MAP_LIMIT]
    return "\n".join(files)


def _issue_keywords(issue: dict) -> list[str]:
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}"
    seen: set[str] = set()
    words: list[str] = []
    for word in KEYWORD_SPLIT.findall(text.lower()):
        if word not in seen and word not in {"swarm", "issue", "todo", "task", "test", "this", "that", "with", "from"}:
            seen.add(word)
            words.append(word)
    return words


def select_context_files(
    issue: dict, root: pathlib.Path, component: str, limit: int = 6
) -> list[str]:
    """Deterministic context selection: component hints ranked by keyword match."""
    files = tracked_files(root)
    hints = COMPONENT_HINTS.get(component, COMPONENT_HINTS["general"])
    keywords = _issue_keywords(issue)

    def score(path: str) -> tuple[int, int]:
        low = path.lower()
        hinted = any(low.startswith(h.rstrip("/")) or low == h.rstrip("/") for h in hints)
        hits = sum(1 for kw in keywords if kw in low)
        size_penalty = 1 if low.endswith((".lock", ".svg", ".png")) else 0
        # higher hits first, hinted first, then shorter path (stable, cheap)
        return (-hits, 0 if hinted else 1, size_penalty, len(path))

    ranked = sorted(files, key=score)
    chosen = [p for p in ranked[:limit] if not p.endswith((".lock", ".svg", ".png"))]
    return chosen


def read_context(root: pathlib.Path, paths: list[str]) -> str:
    chunks: list[str] = []
    budget = MAX_CONTEXT_BYTES
    for rel in paths:
        p = root / rel
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        chunk = f"--- FILE: {rel} ---\n{text}"
        if len(chunk) > budget:
            chunk = chunk[:budget] + "\n--- (truncated) ---"
        chunks.append(chunk)
        budget -= len(chunk)
        if budget <= 0:
            break
    return "\n\n".join(chunks)


PATCH_SCHEMA = {
    "type": "object",
    "required": ["diff", "summary"],
    "properties": {
        "diff": {"type": "string"},
        "summary": {"type": "string"},
    },
}


def build_prompt(
    issue: dict, repo_map: str, context: str, feedback: str | None
) -> str:
    body = (issue.get("body") or "")[:3000]
    prompt = f"""Repository: shesh-ecosystem (Python tooling factory; gates: `ruff check` + `pytest tests/`).

ISSUE #{issue.get('number')}: {issue.get('title')}

ISSUE BODY:
{body}

REPO FILE MAP (tracked files):
{repo_map}

MOST RELEVANT CURRENT CONTENTS:
{context}

TASK: implement the issue precisely. Output a unified diff as the JSON value
"diff" plus a "summary". Hard rules:
- The diff MUST apply cleanly with `git apply` against the current tree.
- Touch AT MOST {MAX_DIFF_FILES} files and AT MOST {MAX_DIFF_LINES} added/removed lines.
  If the issue is too big, implement the smallest complete, coherent slice.
- NEVER delete or rewrite files the issue did not ask about.
- NEVER touch: {', '.join(FORBIDDEN_PREFIXES)} or files matching {', '.join(FORBIDDEN_GLOBS)}.
- Python you write MUST pass `ruff check` (line length 100 is fine; no unused imports).
- If you touch scripts/, tools/ or tests/, `pytest tests/ -q` MUST still pass.
- If the issue asks for a test, write a real test, not a placeholder.
"""
    if feedback:
        prompt += (
            "\n\nPREVIOUS ATTEMPT FAILED THE LOCAL GATE. Fix it, output corrected diff only.\n"
            f"Gate output (tail):\n{feedback[-3000:]}\n"
        )
    return prompt


def parse_diff(data: dict) -> str | None:
    diff = data.get("diff") or ""
    if not isinstance(diff, str) or "diff --git" not in diff and "+++ " not in diff:
        return None
    return diff


def validate_diff(diff: str) -> tuple[bool, str]:
    """Static policy checks before any subprocess touches the tree."""
    files = set()
    added = removed = 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip().removeprefix("b/")
            if path != "/dev/null":
                files.add(path)
        elif line.startswith("--- "):
            path = line[4:].strip().removeprefix("a/")
            if path != "/dev/null":
                files.add(path)
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    if not files:
        return False, "diff touches no files"
    if len(files) > MAX_DIFF_FILES:
        return False, f"diff touches {len(files)} files > {MAX_DIFF_FILES} allowed"
    if added + removed > MAX_DIFF_LINES:
        return False, f"diff changes {added + removed} lines > {MAX_DIFF_LINES} allowed"
    for path in files:
        if path.startswith(FORBIDDEN_PREFIXES):
            return False, f"forbidden path in diff: {path}"
        if any(pathlib.PurePosixPath(path).match(g) for g in FORBIDDEN_GLOBS):
            return False, f"forbidden secret-like path in diff: {path}"
        if path.startswith("/") or ".." in pathlib.PurePosixPath(path).parts:
            return False, f"unsafe path in diff: {path}"
    return True, "ok"


def apply_diff(root: pathlib.Path, diff: str) -> tuple[bool, str]:
    """Check-apply then real-apply via stdin (no shell, no filenames from model).

    git apply reads the patch from stdin in both passes.
    """
    proc = subprocess.run(
        ["git", "apply", "--check", "-"], cwd=str(root), input=diff,
        capture_output=True, text=True, timeout=60, check=False,
    )
    if proc.returncode != 0:
        return False, f"git apply --check failed: {proc.stderr.strip()[:500]}"
    proc = subprocess.run(
        ["git", "apply", "-"], cwd=str(root), input=diff,
        capture_output=True, text=True, timeout=60, check=False,
    )
    if proc.returncode != 0:
        return False, f"git apply failed: {proc.stderr.strip()[:500]}"
    return True, "applied"


def changed_files(root: pathlib.Path) -> list[str]:
    rc, out, err = _git(root, "status", "--porcelain")
    if rc != 0:
        return []
    paths = []
    for line in out.splitlines():
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        if rel:
            paths.append(rel)
    return paths


def run_local_gates(root: pathlib.Path, touched: list[str]) -> tuple[bool, str]:
    """File-targeted verification before the model's work leaves the machine."""
    py_touched = [p for p in touched if p.endswith(".py")]
    if py_touched and any(
        p.startswith(("scripts/", "tools/", "tests/")) for p in touched
    ):
        rc, out, err = _run(root, [sys.executable, "-m", "ruff", "check", *py_touched])
        if rc != 0:
            return False, f"ruff:\n{out}{err}"
        rc, out, err = _run(root, [sys.executable, "-m", "pytest", "tests/", "-q", "-x"], timeout=600)
        if rc != 0:
            return False, f"pytest:\n{out[-3000:]}{err[-1000:]}"
    return True, "local gates green"


def _run(root: pathlib.Path, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def implement(
    issue: dict, root: pathlib.Path, branch: str, component: str
) -> tuple[bool, str]:
    """Executor entry point used by tools/swarm/worker_github.py."""
    root = pathlib.Path(root)
    adapter = ModelAgnosticAdapter()
    task = TaskSpec(
        role="coder",
        goal=(
            "Produce a small, correct, gate-verified unified diff implementing "
            f"the GitHub issue. Rules are strict: max {MAX_DIFF_FILES} files, "
            f"max {MAX_DIFF_LINES} changed lines, git-apply-clean."
        ),
        schema=PATCH_SCHEMA,
        must_contain=["diff", "summary"],
        must_not_contain=["rm -rf", "git push", "secret", "BEGIN RSA"],
        min_score=0.6,
        context_budget=8192,
    )

    repo_map = build_repo_map(root)
    context_files = select_context_files(issue, root, component)
    context = read_context(root, context_files)
    feedback: str | None = None

    for round_no in range(1, MAX_ROUNDS + 1):
        prompt = build_prompt(issue, repo_map, context, feedback)
        try:
            data, model, score = adapter.generate(task, prompt, max_retries=2)
        except Exception as exc:  # noqa: BLE001
            # Provider-chain boundary: any provider error fails this round —
            # the reason goes into the ledger; nothing is swallowed.
            return False, f"all providers failed: {exc}"

        diff = parse_diff(data)
        if diff is None:
            feedback = f"model {model.name} returned no unified diff; got: {json.dumps(data)[:600]}"
            print(f"[executor] round {round_no}: {feedback}", file=sys.stderr)
            continue

        ok, why = validate_diff(diff)
        if not ok:
            feedback = f"diff policy violation: {why}"
            print(f"[executor] round {round_no}: {feedback}", file=sys.stderr)
            continue

        ok, why = apply_diff(root, diff)
        if not ok:
            feedback = why
            print(f"[executor] round {round_no}: {feedback}", file=sys.stderr)
            continue

        touched = changed_files(root)
        gate_ok, gate_out = run_local_gates(root, touched)
        if not gate_ok:
            # Repair round reuses the failing state: reset so the next diff
            # applies cleanly onto main, then carry the gate output forward.
            _git(root, "checkout", "--", ".")
            _git(root, "clean", "-fd", "--", ".")
            feedback = gate_out
            print(f"[executor] round {round_no}: gates failed, retrying", file=sys.stderr)
            continue

        summary = str(data.get("summary", ""))[:400]
        print(
            f"[executor] issue #{issue.get('number')} implemented via "
            f"{model.name} (score {score}, round {round_no}); files: {touched}"
        )
        return True, f"{summary} (model={model.name}, score={score}, round={round_no})"

    return False, "exhausted repair rounds without a green diff"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Standalone executor smoke test")
    ap.add_argument("--issue-json", help="path to a GitHub issue JSON dump")
    ap.add_argument("--title", default="Add a trivial comment to TODO.md")
    args = ap.parse_args()

    if args.issue_json:
        issue = json.loads(pathlib.Path(args.issue_json).read_text())
    else:
        issue = {"number": 0, "title": args.title, "body": ""}
    ok, msg = implement(issue, ROOT, "local-test", "general")
    print(f"ok={ok} msg={msg}")
    sys.exit(0 if ok else 1)
