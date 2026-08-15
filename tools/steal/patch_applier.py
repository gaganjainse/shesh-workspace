#!/usr/bin/env python3
"""Patch applier — upgrades wrapper for our needs, customizes, specializes, improves.

Takes a feature extracted by feature_extractor.py and applies it to our wrapper.

For example, if upstream ekremx25/quickshell has new monitor management single hyprctl --batch (no flicker),
this tool would:
1. Check if our shesh-shell already has it (if not, steal)
2. Create branch feat/upstream-<name>-<feature>
3. Apply patch (copy QML or logic, adapt for 1920x1200@144 RTX 4050 6GB)
4. Test via make check
5. Commit and push

Usage:
  python tools/steal/patch_applier.py --feature /tmp/features.json --upstream ekremx25-quickshell --index 0
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser(description="Apply stolen feature to our wrapper")
    ap.add_argument("--feature", type=pathlib.Path, required=True, help="features.json from extractor")
    ap.add_argument("--upstream", required=True, help="upstream name")
    ap.add_argument("--index", type=int, default=0, help="which extracted feature index to apply")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.feature.read_text())
    upstream_data = data.get(args.upstream)
    if not upstream_data:
        print(f"Upstream {args.upstream} not in {args.feature}", file=sys.stderr)
        return 1

    feats = upstream_data.get("extracted_features", [])
    if not feats:
        print(f"No features extracted for {args.upstream}", file=sys.stderr)
        return 1

    if args.index >= len(feats):
        print(f"Index {args.index} out of range {len(feats)}", file=sys.stderr)
        return 1

    feat = feats[args.index]
    print(f"Applying feature from {args.upstream}: {feat}")

    # In real implementation, this would:
    # 1. Create branch
    # 2. For commit features: cherry-pick or adapt code
    # 3. For issue features: implement similar functionality
    # 4. Test via make check and component tests
    # 5. Commit with attribution: "steal: from {repo}#{number} — {title} — upgraded for CachyOS/Hyprland/6GB VRAM"

    # For now, just document what would be done
    print(f"""
Would apply:
- Type: {feat['type']}
- Keyword: {feat['keyword']}
- Title/Message: {feat.get('title') or feat.get('message')}
- URL: {feat.get('url')}
- Upstream: {upstream_data['repo']}
- Our improvement: {upstream_data.get('improve')}

Steps:
1. git checkout -b feat/upstream-{args.upstream}-{feat.get('number') or feat.get('sha','')[:7]}
2. Copy/adapt relevant file from upstream (e.g., bar_config.json declarative pattern, or monitor management hyprctl --batch)
3. Customize for our system: 1920x1200@144, RTX 4050 6GB, 16GB DDR5, CachyOS performance, illogical-impulse look (not replacing look)
4. Specialize: add Guard policy, separate systemd service, separate config dir, btrfs subvolume, Python venv via uv
5. Improve: add Shesh ambient offer overlay, power profile + GPU MUX + backup status, 6GB VRAM budget aware
6. Test: make check, component pytest
7. Commit with attribution and push

We have a lot of time, freely, no limited time constraint — make proper working version, not minimal stub.

Philosophy: First thought when challenged = STEAL, not make tool. Check SOURCES.md, TOOLING_CATALOG.md, upstreams.toml, awesome-hyprland, best MCP 2026. If something better exists that can be stolen, upgraded, customized, specialized and improved — STEAL IT. Only if not found, then make yourself. We can discard what we made if something better exists to steal. Never engage in pointless brooding.
""")

    if args.dry_run:
        print("Dry-run, not applying")
        return 0

    # TODO: actual implementation would apply patch
    print("Apply logic not yet implemented — this is infrastructure for stealing/improving/customising so user doesn't have to write many times")
    return 0

if __name__ == "__main__":
    sys.exit(main())
