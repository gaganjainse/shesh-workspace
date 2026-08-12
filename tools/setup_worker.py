#!/usr/bin/env python3
"""Setup worker with ONLY needed repos — shallow, selective, efficient.

Cloning 22 repos in every Arena chat is wasteful:
- shesh-voice 41M, shesh-desktop 22M, SheshAOS 7.5M, etc. → workspace 113 MB → HOP after 30 min
- File count 3400 → close to 8000 limit → slowdown

This tool clones ONLY needed repos per role, shallow --depth 1, single branch.

Usage:
  python tools/setup_worker.py --role brain          # audit, secrets, SheshAOS (shallow)
  python tools/setup_worker.py --role mind           # audit + mind family (6 repos ~2 MB)
  python tools/setup_worker.py --role soma           # audit + soma small repos
  python tools/setup_worker.py --role platform       # no src clone, only ecosystem itself
  python tools/setup_worker.py --component shesh-memory  # single component + audit

Efficiency gains:
- Brain (before): 22 repos 36M + 3400 files → 60 min session
- Brain (after): 3 repos ~8M + 600 files → 120-180 min session
- Mind (after): 7 repos ~2M + 500 files → 120 min
- Platform (after): 0 repos, 0 extra → 150 min (only ecosystem)

Integrates with swarm workers — they should call setup_worker before work.

Also sets up uv cache pruning, ruff cache clean, etc.

Free LLM note: All work offline with deterministic stubs — no OpenAI API cost.
Ollama phi4-mini etc only needed on real MSI hardware, not in Arena sandbox.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Component dependency map — minimal needed per role/component
ROLE_MAP = {
    "brain": ["shesh-audit", "shesh-secrets", "SheshAOS"],
    "mind": [
        "shesh-audit",
        "shesh-memory",
        "shesh-mind",
        "shesh-harness",
        "shesh-orchestrator",
        "shesh-skills",
        "shesh-calendar",
    ],
    "soma": [
        "shesh-audit",
        "shesh-files",
        "shesh-shell",
        "shesh-system",
        "shesh-backup",
        "shesh-phone",
        "shesh-containers",
        "shesh-mcp-bundle",
        "shesh-acp",
    ],
    "platform": [],  # no src needed, only ecosystem itself
    "voice": ["shesh-audit", "shesh-voice"],  # large 41M, use shallow
    "desktop": ["shesh-desktop"],  # large 22M, shallow
}

# Single component + its deps (audit always needed)
COMPONENT_DEPS = {
    "shesh-audit": ["shesh-audit"],
    "shesh-secrets": ["shesh-audit", "shesh-secrets"],
    "shesh-memory": ["shesh-audit", "shesh-memory"],
    "shesh-mind": ["shesh-audit", "shesh-mind"],
    "shesh-harness": ["shesh-audit", "shesh-harness"],
    "shesh-orchestrator": ["shesh-audit", "shesh-orchestrator"],
    "shesh-skills": ["shesh-audit", "shesh-skills"],
    "shesh-calendar": ["shesh-audit", "shesh-calendar"],
    "shesh-files": ["shesh-audit", "shesh-files"],
    "shesh-shell": ["shesh-audit", "shesh-shell"],
    "shesh-system": ["shesh-audit", "shesh-system"],
    "shesh-backup": ["shesh-audit", "shesh-backup"],
    "shesh-phone": ["shesh-audit", "shesh-phone"],
    "shesh-containers": ["shesh-audit", "shesh-containers"],
    "shesh-mcp-bundle": ["shesh-audit", "shesh-mcp-bundle"],
    "shesh-acp": ["shesh-audit", "shesh-acp"],
    "shesh-voice": ["shesh-audit", "shesh-voice"],
    "shesh-desktop": ["shesh-desktop"],
}

# Map repo name to GitHub repo URL
REPO_URL = {
    "shesh-audit": "https://github.com/gaganjainse/shesh-audit.git",
    "shesh-secrets": "https://github.com/gaganjainse/shesh-secrets.git",
    "shesh-memory": "https://github.com/gaganjainse/shesh-memory.git",
    "shesh-mind": "https://github.com/gaganjainse/shesh-mind.git",
    "shesh-harness": "https://github.com/gaganjainse/shesh-harness.git",
    "shesh-orchestrator": "https://github.com/gaganjainse/shesh-orchestrator.git",
    "shesh-skills": "https://github.com/gaganjainse/shesh-skills.git",
    "shesh-calendar": "https://github.com/gaganjainse/shesh-calendar.git",
    "shesh-files": "https://github.com/gaganjainse/shesh-files.git",
    "shesh-shell": "https://github.com/gaganjainse/shesh-shell.git",
    "shesh-system": "https://github.com/gaganjainse/shesh-system.git",
    "shesh-backup": "https://github.com/gaganjainse/shesh-backup.git",
    "shesh-phone": "https://github.com/gaganjainse/shesh-phone.git",
    "shesh-containers": "https://github.com/gaganjainse/shesh-containers.git",
    "shesh-mcp-bundle": "https://github.com/gaganjainse/shesh-mcp-bundle.git",
    "shesh-acp": "https://github.com/gaganjainse/shesh-acp.git",
    "shesh-voice": "https://github.com/gaganjainse/shesh-voice.git",
    "shesh-desktop": "https://github.com/gaganjainse/shesh-desktop.git",
    "SheshAOS": "https://github.com/gaganjainse/SheshAOS.git",
    "SheshAOS": "https://github.com/gaganjainse/SeshaOS.git",
    "shesha-kernel": "https://github.com/gaganjainse/shesha-kernel.git",
    "SheshAOS": "https://github.com/gaganjainse/SheshAOS.git",
}


def sh(cmd: str) -> tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=60)
        return 0, out
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
    except Exception as e:
        return 1, str(e)


def clone_repo(name: str, shallow: bool = True) -> bool:
    url = REPO_URL.get(name)
    if not url:
        print(f"Unknown repo {name}, skipping")
        return False
    dest = SRC / name
    if dest.exists():
        # Already exists, pull shallow
        print(f"Already exists {name}, pulling --ff-only")
        rc, out = sh(f"cd {dest} && git pull --ff-only --depth 1 2>&1 | head -n 20")
        return rc == 0
    # Clone
    depth_flag = "--depth 1 --single-branch" if shallow else ""
    # For large repos, always shallow
    if name in ("shesh-voice", "shesh-desktop", "SheshAOS", "SheshAOS", "shesha-kernel", "SheshAOS"):
        depth_flag = "--depth 1 --single-branch --filter=blob:none"
    print(f"Cloning {name} {depth_flag} ...")
    rc, out = sh(f"git clone {depth_flag} {url} {dest} 2>&1 | tail -n 20")
    if rc != 0:
        print(f"Clone {name} failed: {out[-500:]}")
        return False
    print(f"Cloned {name}")
    return True


def clean_caches() -> None:
    print("Cleaning caches for longer session...")
    cmds = [
        "find /home/user -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null; true",
        "rm -rf /home/user/.cache /home/user/.pytest_cache /home/user/.ruff_cache 2>/dev/null; true",
        "rm -rf /home/user/src/*/target /home/user/src/*/dist /home/user/src/*/__pycache__ /home/user/src/*/.pytest_cache 2>/dev/null; true",
        "rm -rf /home/user/src/*/.venv /home/user/.venv 2>/dev/null; true",
    ]
    for c in cmds:
        os.system(c)
    print("Cleaned")


def setup_role(role: str, component: str | None = None) -> None:
    SRC.mkdir(parents=True, exist_ok=True)
    clean_caches()

    if component:
        deps = COMPONENT_DEPS.get(component, [component])
        print(f"Role component {component} needs {deps}")
        for repo in deps:
            clone_repo(repo, shallow=True)
    else:
        repos = ROLE_MAP.get(role, [])
        print(f"Role {role} needs {repos} (vs 22 all = 36M)")
        if not repos:
            print("Platform role — no src clone needed, only ecosystem itself (most efficient)")
            return
        for repo in repos:
            clone_repo(repo, shallow=True)

    # Show final size
    rc, out = sh(f"du -sh {SRC} 2>/dev/null | cut -f1")
    print(f"SRC size after selective clone: {out} (vs 36M for all 22)")
    rc, out = sh(f"find {SRC} -type f | wc -l")
    print(f"File count in SRC: {out} (vs ~3000 for all 22)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Setup worker with minimal repos")
    ap.add_argument("--role", choices=list(ROLE_MAP.keys()), help="role to setup")
    ap.add_argument("--component", help="single component to setup")
    ap.add_argument("--clean", action="store_true", help="only clean caches")
    args = ap.parse_args()

    if args.clean:
        clean_caches()
        return 0

    if args.component:
        setup_role("custom", component=args.component)
    elif args.role:
        setup_role(args.role)
    else:
        print("Need --role or --component")
        ap.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
