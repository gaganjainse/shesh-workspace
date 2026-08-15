#!/usr/bin/env python3
"""Supply-chain: sign artifacts + provenance (offline-first)."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lock_sha(channel: str) -> str:
    lock = ROOT / f"channels/{channel}.lock"
    if not lock.exists():
        return "no-lock"
    try:
        data = json.loads(lock.read_text())
        return data.get("sha256", "unknown")
    except (OSError, json.JSONDecodeError):
        # Unreadable/corrupt lock -> visible sentinel, not a fabricated sha.
        return "invalid-lock"


def sign_with_cosign(artifact: pathlib.Path) -> bool:
    if not shutil.which("cosign"):
        return False
    try:
        if "COSIGN_KEYLESS" not in __import__("os").environ:
            return False
        cmd = [
            "cosign",
            "sign-blob",
            "--yes",
            str(artifact),
            "--output-signature",
            str(artifact) + ".sig",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"cosign exception {artifact}: {e}", file=sys.stderr)
        return False
    if r.returncode == 0:
        print(f"signed {artifact} -> {artifact}.sig")
        return True
    print(f"cosign failed {artifact}: {r.stderr}", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign artifacts + provenance")
    ap.add_argument("--channel", default="canary")
    ap.add_argument("--artifacts", nargs="*", default=[])
    ap.add_argument("--out", default="dist/provenance.json", type=pathlib.Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        ok = True
        for art_str in args.artifacts:
            p = pathlib.Path(art_str)
            sig = pathlib.Path(str(p) + ".sig")
            if not sig.exists():
                print(f"MISSING {p}", file=sys.stderr)
                ok = False
            else:
                print(f"ok {p}")
        return 0 if ok else 1

    artifacts = args.artifacts
    if not artifacts:
        artifacts = [
            str(ROOT / f"channels/{args.channel}.lock"),
            str(ROOT / "manifests/components.toml"),
        ]

    prov = {
        "channel": args.channel,
        "lock_sha256": load_lock_sha(args.channel),
        "generated_at": datetime.now(UTC).isoformat(),
        "artifacts": [],
        "builder": "shesh-ecosystem/sign_artifacts.py",
        "version": "0.1.0",
    }

    for art_str in artifacts:
        p = pathlib.Path(art_str)
        if not p.exists():
            print(f"skip {p}", file=sys.stderr)
            continue
        entry = {
            "path": str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p),
            "sha256": sha256_file(p),
            "size": p.stat().st_size,
        }
        if sign_with_cosign(p):
            entry["signature"] = str(p) + ".sig"
            entry["signed"] = True
        else:
            entry["signed"] = False
        prov["artifacts"].append(entry)
        print(f"hashed {p} -> {entry['sha256'][:16]}...")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"Wrote {args.out}")

    slsa_subject = [
        {"name": a["path"], "digest": {"sha256": a["sha256"]}}
        for a in prov["artifacts"]
    ]
    slsa = {
        "_type": "https://in-toto.io/Statement/v0.1",
        "predicateType": "https://slsa.dev/provenance/v0.2",
        "subject": slsa_subject,
        "predicate": {
            "builder": {"id": "https://github.com/gaganjainse/shesh-ecosystem"},
            "buildType": "make-check",
            "invocation": {
                "configSource": {
                    "uri": f"git+https://github.com/gaganjainse/"
                    f"shesh-ecosystem@{args.channel}",
                    "digest": {"sha256": prov["lock_sha256"]},
                }
            },
        },
    }
    (args.out.parent / "slsa-provenance.json").write_text(
        json.dumps(slsa, indent=2) + "\n"
    )
    print("Wrote SLSA provenance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
