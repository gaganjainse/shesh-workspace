#!/usr/bin/env python3
"""Upstream registry — lists all mainstream forks we track for stealing/improving.

Reads manifests/upstreams.toml and produces report of what to steal,
with conflict risk and improvement notes.

Usage:
  python tools/steal/upstream_registry.py --list
  python tools/steal/upstream_registry.py --report
"""

from __future__ import annotations

import pathlib

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests/upstreams.toml"


def load() -> dict:
    with MANIFEST.open("rb") as f:
        return tomllib.load(f)


def list_upstream():
    data = load()
    for name, cfg in data.get("upstream", {}).items():
        print(f"{name:30} {cfg.get('repo', ''):40} provides={cfg.get('provides','')[:60]}")
        if cfg.get("steal"):
            steal = cfg["steal"]
            if isinstance(steal, list):
                for s in steal:
                    print(f"  - steal: {s[:100]}")
            else:
                print(f"  - steal: {str(steal)[:100]}")
        if cfg.get("improve"):
            print(f"  - improve: {cfg['improve'][:120]}")
        print()


def report():
    data = load()
    total = len(data.get("upstream", {}))
    print(f"Upstream registry — {total} forks tracked for stealing/improving")
    print(f"Source: {MANIFEST}")
    print()
    # Group by conflict risk
    low = []
    med = []
    high = []
    for name, cfg in data.get("upstream", {}).items():
        risk = cfg.get("conflict_risk", "unknown")
        if "low" in risk.lower():
            low.append(name)
        elif "medium" in risk.lower() or "med" in risk.lower():
            med.append(name)
        else:
            high.append(name)
    print(f"Low conflict risk ({len(low)}): {', '.join(low)}")
    print(f"Medium risk ({len(med)}): {', '.join(med)}")
    print(f"High/unknown ({len(high)}): {', '.join(high)}")
    print()
    print("Philosophy: Fork + wrap + UPGRADE wrapper for our needs + customize/specialize for CachyOS/Hyprland/6GB VRAM + improve")
    print("We have a lot of time, freely, no limited time — make proper working versions, not minimal stubs")
    print("First thought when challenged = STEAL, not make tool — check SOURCES.md, TOOLING_CATALOG, upstreams.toml, awesome-hyprland, best MCP 2026")
    print("We can discard what we made if something better exists to steal — never pointless brooding")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.list:
        list_upstream()
    if args.report or not (args.list or args.report):
        report()
