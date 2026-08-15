#!/usr/bin/env python3
"""tools/verify_worktrees.py — content-verify each worktree against origin/<default>.

Adopted from the orchestrator's recovery toolkit (2026-08-12). Compares file
bytes (not git metadata) of every clone against a clean `git archive` of the
remote default branch — this catches snapshot-restore damage (dropped files,
rewound content, stripped modes invisible to status heuristics) without
trusting any local git state.

Report-only: exits 0 even when dirty. Read the JSON.

Env: SHESH_SRC (default ~/src).
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import subprocess
import tarfile
import tempfile

SRC = pathlib.Path(os.environ.get("SHESH_SRC", pathlib.Path.home() / "src"))
EXCLUDES = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv",
            "node_modules", "target", "dist", "build", ".mypy_cache"}


def run(cmd: list[str], cwd: pathlib.Path | None = None, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=text, timeout=300, check=False)


def files_under(root: pathlib.Path) -> dict[str, pathlib.Path]:
    out: dict[str, pathlib.Path] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in EXCLUDES for part in rel.parts):
            continue
        if p.is_file() and p.suffix != ".pyc":
            out[str(rel)] = p
    return out


def main() -> None:
    results = {}
    for d in sorted(SRC.iterdir()):
        if not (d / ".git").is_dir():
            continue
        rdef = run(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], cwd=d)
        base = rdef.stdout.strip().split("/")[-1] or "main"
        ref = f"origin/{base}"
        arc = run(["git", "archive", ref], cwd=d, text=False)
        if arc.returncode != 0:
            results[d.name] = {"verdict": "NO-ARCHIVE", "ref": ref,
                               "err": arc.stderr.decode()[:100]}
            continue
        with tempfile.TemporaryDirectory() as td:
            with tarfile.open(fileobj=io.BytesIO(arc.stdout)) as t:
                t.extractall(td, filter="data")
            a, b = files_under(pathlib.Path(td)), files_under(d)
            only_remote = sorted(set(a) - set(b))
            only_local = sorted(set(b) - set(a))
            differ = []
            for rel in sorted(set(a) & set(b)):
                try:
                    if a[rel].read_bytes() != b[rel].read_bytes():
                        differ.append(rel)
                except OSError:
                    differ.append(rel)
            verdict = "CLEAN" if not (only_remote or only_local or differ) else "DIRTY"
            results[d.name] = {
                "verdict": verdict, "ref": ref,
                "differ": differ[:10], "only_local": only_local[:10],
                "only_remote": only_remote[:10],
                "counts": [len(differ), len(only_local), len(only_remote)],
            }
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
