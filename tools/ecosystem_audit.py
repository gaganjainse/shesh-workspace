#!/usr/bin/env python3
"""tools/ecosystem_audit.py — per-repo health sweep across the whole ecosystem.

Adopted from the orchestrator home directory (audit_all.py, 2026-08-12),
fixed for real before adoption:

- default-branch aware via origin/HEAD (the ad-hoc version hardcoded `main`,
  which is wrong for shesh-voice=master);
- REPORT-ONLY: the ad-hoc version ran `git reset --hard origin/main` on
  clean repos and `pip install -e .` into the ambient interpreter. Both are
  gone. Realignments are reviewable decisions (see sync_repos.py), and test
  environments are provisioned explicitly (see bootstrap_workspace.sh);
- report goes to stdout; --out writes JSON where you ask it to.

Checks per repo: branch, dirt, remote branches, file/test/CI/README counts,
old-name hits, stub-shaped patterns, ruff (when available), pytest tail
(when SHESH_AUDIT_PYTEST=1 and a venv provides fastmcp-compatible pytest).

Env:
    SHESH_SRC            clones dir (default ~/src)
    SHESH_AUDIT_PYTEST   set to 1 to run pytest per component (slow)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(os.environ.get("SHESH_SRC", Path.home() / "src"))
EXTRA = [Path.home() / "shesh-ecosystem", Path.home() / "shesh-workspace"]
SKIP = {"waveterm", "shesh-kernel", "SeshaOS"}  # fork tail / archived

NAME_PATTERNS = {
    "auto-desktopenv": re.compile(r"auto[-_ ]?desk(env|top)?", re.I),
    "shesha": re.compile(r"\bshesha([_-]\w+)?\b", re.I),
    "seshaos": re.compile(r"\bseshaos\b", re.I),
    "nexusaos": re.compile(r"\bnexusaos\b", re.I),
    "dots-hyprland": re.compile(r"dots[-_]hyprland", re.I),
}
STUB_PATTERNS = {
    "NotImplementedError": re.compile(r"NotImplementedError"),
    "TODO_FIXME": re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"),
    "bare_pass": re.compile(r"^\s+pass\s*$", re.M),
    "placeholder": re.compile(r"placeholder|stub implement|demo only|minimal implement", re.I),
}


def sh(args: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    return p.returncode, p.stdout, p.stderr


def tracked_files(repo: Path) -> list[str]:
    rc, out, _ = sh(["git", "ls-files", "--cached", "--others", "--exclude-standard"], repo)
    return [line for line in out.splitlines() if line.strip()] if rc == 0 else []


def grep_names(repo: Path, files: list[str]) -> dict[str, list]:
    hits: dict[str, list] = {}
    text_ext = (".py", ".md", ".toml", ".yml", ".yaml", ".json", ".sh", ".txt", ".qml", ".rs", ".cfg", ".ini")
    for f in files:
        if not f.endswith(text_ext):
            continue
        try:
            content = (repo / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pat in NAME_PATTERNS.items():
            m = pat.findall(content)
            if m:
                hits.setdefault(name, []).append((f, len(m)))
    return hits


def grep_stubs(repo: Path, files: list[str]) -> dict[str, list]:
    hits: dict[str, list] = {}
    for f in files:
        if not f.endswith((".py", ".rs")):
            continue
        try:
            content = (repo / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pat in STUB_PATTERNS.items():
            m = pat.findall(content)
            if m:
                hits.setdefault(name, []).append((f, len(m)))
    return hits


def audit(repo: Path) -> dict:
    r = {"repo": repo.name, "path": str(repo)}
    sh(["git", "fetch", "--all", "--prune", "-q"], repo, 120)
    _, branch, _ = sh(["git", "branch", "--show-current"], repo)
    r["branch"] = branch.strip()
    def_rc, def_out, _ = sh(["git", "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], repo)
    r["default_branch"] = def_out.strip().split("/", 1)[-1] if def_rc == 0 else None
    if r["default_branch"] and r["branch"] != r["default_branch"]:
        r["NOTE"] = f"HEAD on {r['branch']}, default is {r['default_branch']}"
    _, out, _ = sh(["git", "status", "--porcelain"], repo)
    r["dirty"] = [line for line in out.splitlines() if line.strip()]
    if r["default_branch"]:
        _, counts, _ = sh(["git", "rev-list", "--left-right", "--count",
                           f"origin/{r['default_branch']}...HEAD"], repo)
        r["vs_default(behind_ahead)"] = counts.strip()
    _, out, _ = sh(["git", "branch", "-r", "--format=%(refname:short)"], repo)
    r["remote_branches"] = [b.strip() for b in out.splitlines() if b.strip() and "HEAD" not in b]
    files = tracked_files(repo)
    r["n_files"] = len(files)
    r["py_files"] = len([f for f in files if f.endswith(".py")])
    r["rs_files"] = len([f for f in files if f.endswith(".rs")])
    r["has_tests"] = any(f.startswith("tests/") for f in files)
    r["has_ci"] = any(f.startswith(".github/workflows/") for f in files)
    r["has_readme"] = any(f.lower() == "readme.md" for f in files)
    r["old_names"] = grep_names(repo, files)
    r["stub_hits"] = grep_stubs(repo, files)
    if r["py_files"]:
        rc, out, err = sh([sys.executable, "-m", "ruff", "check", "."], repo, 180)
        ruff_blob = out + err
        if rc != 0 and "No module named ruff" in ruff_blob:
            r["ruff"] = "skipped(ruff not installed in this interpreter)"
        else:
            r["ruff"] = "clean" if rc == 0 else f"FAIL({ruff_blob.count(chr(10))} lines)"
    if r["has_tests"] and os.environ.get("SHESH_AUDIT_PYTEST") == "1":
        rc, out, err = sh([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], repo, 420)
        tail = (out + err).strip().splitlines()
        r["pytest"] = tail[-1][:140] if tail else ("PASS" if rc == 0 else "FAIL")
        r["pytest_rc"] = rc
    return r


def main() -> int:
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    repos = sorted([p for p in SRC.iterdir() if p.is_dir() and (p / ".git").exists() and p.name not in SKIP])
    repos += [p for p in EXTRA if (p / ".git").exists()]
    report = []
    for repo in repos:
        print(f"auditing {repo.name} …", flush=True)
        try:
            r = audit(repo)
        except Exception as e:  # noqa: BLE001 — audit must survive one broken clone and report the rest
            r = {"repo": repo.name, "error": str(e)}
        report.append(r)
        names = ",".join(f"{k}×{sum(n for _, n in v)}" for k, v in r.get("old_names", {}).items()) or "-"
        stubs = ",".join(f"{k}×{sum(n for _, n in v)}" for k, v in r.get("stub_hits", {}).items()) or "-"
        print(
            f"  py={r.get('py_files', 0)} rs={r.get('rs_files', 0)} br={len(r.get('remote_branches', []))} "
            f"ruff={r.get('ruff', '-')} pytest={r.get('pytest', '-')} "
            f"names[{names}] stubs[{stubs}] dirty={len(r.get('dirty', []))} ci={r.get('has_ci')} readme={r.get('has_readme')}",
            flush=True,
        )
    blob = json.dumps(report, indent=2)
    if out_path:
        Path(out_path).write_text(blob)
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
