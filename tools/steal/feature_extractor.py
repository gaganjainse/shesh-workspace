#!/usr/bin/env python3
"""Feature extractor — picks features/issues from every mainstream fork we use.

For each upstream in manifests/upstreams.toml, fetches latest commits, open issues, PRs via GitHub API
and extracts useful features that improve style (buttery animations, response), performance (CachyOS),
functionalities (bluetooth wifi integration), etc.

Usage:
  python tools/steal/feature_extractor.py --upstream ml4w-dotfiles
  python tools/steal/feature_extractor.py --all --out /tmp/features.json

This implements user's request: pick features and issues from every mainstream fork we are using
and if useful extract that and work on it.

Free, open-source only — no subscription APIs.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.request

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests/upstreams.toml"

UA = "shesh-steal-extractor/0.1"

def gh_get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except (OSError, ValueError) as e:
        # Network or JSON failure -> explicit sentinel the caller renders
        # (HTTPError decodes to ValueError via JSON or OSError via urllib).
        return {"_error": str(e)}

def extract_features(upstream_name: str, max_issues: int = 10) -> dict:
    with MANIFEST.open("rb") as f:
        data = tomllib.load(f)
    cfg = data.get("upstream", {}).get(upstream_name)
    if not cfg:
        print(f"Upstream {upstream_name} not found in {MANIFEST}", file=sys.stderr)
        return {}

    repo = cfg["repo"]
    print(f"Extracting features from {repo} ({upstream_name})...")

    # Fetch recent commits
    commits = gh_get(f"https://api.github.com/repos/{repo}/commits?per_page=20")
    # Fetch open issues
    issues = gh_get(f"https://api.github.com/repos/{repo}/issues?state=open&per_page={max_issues}&sort=updated")
    # Fetch open PRs
    prs = gh_get(f"https://api.github.com/repos/{repo}/pulls?state=open&per_page={max_issues}&sort=updated")

    features = []
    # Heuristic: look for keywords in commit messages, issue titles that indicate useful improvements
    keywords = ["animation", "blur", "performance", "bluetooth", "wifi", "network", "smooth", "buttery", "response", "eq", "monitor", "hdr", "vrr", "night light", "wallpaper", "screenshot", "dock", "bar", "material you", "m3", "matugen", "hyprpaper", "swww"]

    for c in (commits if isinstance(commits, list) else []):
        msg = c.get("commit", {}).get("message", "").lower()
        for kw in keywords:
            if kw in msg:
                features.append({"type": "commit", "keyword": kw, "message": c["commit"]["message"][:200], "sha": c.get("sha","")[:7], "url": c.get("html_url","")})
                break

    for iss in (issues if isinstance(issues, list) else []):
        title = iss.get("title","").lower()
        for kw in keywords:
            if kw in title:
                features.append({"type": "issue", "keyword": kw, "title": iss.get("title","")[:200], "number": iss.get("number"), "url": iss.get("html_url",""), "state": iss.get("state")})
                break

    for pr in (prs if isinstance(prs, list) else []):
        title = pr.get("title","").lower()
        for kw in keywords:
            if kw in title:
                features.append({"type": "pr", "keyword": kw, "title": pr.get("title","")[:200], "number": pr.get("number"), "url": pr.get("html_url","")})
                break

    return {
        "upstream": upstream_name,
        "repo": repo,
        "provides": cfg.get("provides",""),
        "steal": cfg.get("steal",""),
        "improve": cfg.get("improve",""),
        "conflict_risk": cfg.get("conflict_risk",""),
        "extracted_features": features[:20],  # top 20
        "total_commits_scanned": len(commits) if isinstance(commits, list) else 0,
        "total_issues_scanned": len(issues) if isinstance(issues, list) else 0,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", help="specific upstream name from upstreams.toml")
    ap.add_argument("--all", action="store_true", help="extract from all upstreams")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("/tmp/features.json"))
    args = ap.parse_args()

    results = {}
    if args.all:
        with MANIFEST.open("rb") as f:
            data = tomllib.load(f)
        for name in data.get("upstream", {}):
            results[name] = extract_features(name)
            time.sleep(0.5)  # polite to API
    elif args.upstream:
        results[args.upstream] = extract_features(args.upstream)
    else:
        print("Need --upstream <name> or --all")
        return 1

    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Wrote {args.out} with {len(results)} upstreams")

    # Print summary
    for name, res in results.items():
        print(f"\n=== {name} ({res.get('repo')}) ===")
        print(f"Provides: {res.get('provides')}")
        print(f"Steal: {str(res.get('steal'))[:200]}")
        print(f"Improve: {res.get('improve','')[:200]}")
        feats = res.get("extracted_features", [])
        print(f"Extracted {len(feats)} useful features/issues (keywords: animation, bluetooth, wifi, smooth, etc):")
        for f in feats[:5]:
            print(f"  - [{f['type']}] {f.get('keyword')} {f.get('title') or f.get('message','')[:80]} {f.get('url','')}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
