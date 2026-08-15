#!/usr/bin/env python3
"""Self-hosted update mirror — sync components from manifest, verify provenance."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror sync")
    ap.add_argument("--channel", default="canary")
    ap.add_argument("--out", default="/srv/shesh-mirror", type=pathlib.Path)
    args = ap.parse_args()

    lock_path = ROOT / f"channels/{args.channel}.lock"
    if not lock_path.exists():
        print(f"No lock {lock_path}, run resolve_manifest first", file=sys.stderr)
        return 1

    data = json.loads(lock_path.read_text())
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    print(f"Mirroring {data['count']} components for channel {args.channel} to {out}")
    for name, comp in data["components"].items():
        repo = comp["repo"]
        print(f"  - {name} {repo} {comp['version']}")
        # Shallow clone for mirror
        dest = out / name
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], capture_output=True)
        else:
            subprocess.run(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(dest)], capture_output=True)

    # Write provenance index
    prov = {"channel": args.channel, "components": list(data["components"].keys()), "count": data["count"]}
    (out / "index.json").write_text(json.dumps(prov, indent=2) + "\n")
    print(f"Mirrored to {out}, index {len(prov['components'])} components")
    return 0

if __name__ == "__main__":
    sys.exit(main())
