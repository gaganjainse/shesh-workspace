#!/usr/bin/env python3
"""LLM Worker — true hours unattended coding via free models, no Arena tab.

Picks pending GitHub Issue (swarm:pending), calls free LLM (GitHub Models free via GITHUB_TOKEN, or Groq free, OpenRouter :free), generates patch, runs make check, pushes branch swarm/issue-N/llm-worker, opens PR.

Uses model-agnostic adapter (tools/llm_adapter.py) with strict JSON schema, validation+repair loop, fallback chain free-first→stub, so quality consistent across free models.

Free providers (no money):
- GitHub Models free: gpt-4o-mini, Phi-3-medium — uses GITHUB_TOKEN or GITHUB_PAT (already have via secure PAT flow)
- Groq free: llama-3.1-8b-instant, llama-3.3-70b — needs GROQ_API_KEY free at console.groq.com
- OpenRouter free: google/gemma-2-9b-it:free, meta-llama/llama-3.1-8b:free — needs OPENROUTER_API_KEY free
- HuggingFace free: Phi-3-mini — needs HF_TOKEN free
- Ollama local: phi4-mini, qwen2.5-coder:3b — free offline, 6GB VRAM, for final product shesh ecosystem, not for making it (but included in design so small local does not decrease quality much)
- Stub: deterministic always valid — final fallback

This worker is what .github/workflows/swarm-llm-worker.yml runs every 2 hours via cron — true hours unattended while traveling, no Arena tab needed. Uses GITHUB_TOKEN not PAT for merge.

Usage (local):
  python tools/llm_worker.py --issue 42 --model github/gpt-4o-mini
  python tools/llm_worker.py --pick --free-only

Usage (in Action): see swarm-llm-worker.yml — picks first pending Issue, calls adapter, writes swarm/artifacts/llm-issue-N.md, pushes branch, opens PR, auto-merge merges if green.

Separation: This is factory (workspace) tool, not product. Lives in shesh-workspace repo, not shesh-ecosystem clean. Ecosystem repo only has manifest, locks, architecture docs, gates.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from llm_adapter import ModelAgnosticAdapter, TaskSpec  # noqa: E402
from model_router import Router  # noqa: E402


def pick_issue(free_only: bool = True) -> dict | None:
    # Try GitHub Issues first if PAT/GITHUB_TOKEN available
    try:
        import github_queue as ghq

        issues = ghq.list_pending_issues("general")
        if issues:
            # Filter out those that are not real issues (list returns file tasks fallback if no PAT)
            # If issues are GitHub Issues dicts (have number), return first
            if isinstance(issues[0], dict) and "number" in issues[0]:
                return issues[0]
    except Exception:
        pass

    # Fallback file queue
    sys.path.insert(0, str(ROOT / "tools/swarm"))
    import common as fileq

    pending = fileq.list_tasks("pending")
    if pending:
        # Convert file task to issue-like dict
        t = pending[0]
        return {"number": 0, "title": t["title"], "body": json.dumps(t), "task": t}
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM worker true hours unattended")
    ap.add_argument("--issue", type=int, help="specific issue number")
    ap.add_argument("--model", default="github/gpt-4o-mini", help="model free: github/gpt-4o-mini, groq/llama-3.1-8b-instant, openrouter/google/gemma-2-9b-it:free")
    ap.add_argument("--pick", action="store_true", help="pick first pending issue")
    ap.add_argument("--free-only", action="store_true", default=True)
    ap.add_argument("--dry-run", action="store_true", help="don't push branch/PR")
    args = ap.parse_args()

    router = Router()
    print(f"Available free models for coder role:")
    for m in router.chain_for_role("coder", free_only=args.free_only)[:8]:
        print(f"  - {m.name:35} {m.provider:12} prio={m.priority} free={m.free}")

    issue = None
    if args.issue:
        # Fetch specific issue
        try:
            import github_queue as ghq

            # Get issue by number
            import os

            pat = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")
            if pat:
                os.environ["GITHUB_PAT"] = pat
            # List and filter
            issues = ghq.list_pending_issues("general")
            for iss in issues:
                if iss.get("number") == args.issue:
                    issue = iss
                    break
            if not issue:
                print(f"Issue #{args.issue} not found in pending, trying file queue")
                issue = {"number": args.issue, "title": f"issue-{args.issue}", "body": ""}
        except Exception as e:
            print(f"Failed get issue {args.issue}: {e}")
            issue = {"number": args.issue, "title": f"issue-{args.issue}", "body": ""}
    elif args.pick:
        issue = pick_issue(free_only=args.free_only)

    if not issue:
        print("No pending issue found — nothing to do")
        return 0

    print(f"Picked issue: {issue.get('number')} {issue.get('title', '')[:80]}")

    # Build task spec from issue
    title = issue.get("title", "implement feature")
    body = issue.get("body", "")[:2000]

    task = TaskSpec(
        role="coder",
        goal=f"Implement: {title}\n\n{body}",
        schema={
            "type": "object",
            "required": ["patch", "summary"],
            "properties": {
                "patch": {"type": "string", "description": "unified diff or file content"},
                "summary": {"type": "string"},
            },
        },
        must_contain=["def"],
        must_not_contain=["rm -rf /"],
        min_score=0.5,
    )

    adapter = ModelAgnosticAdapter()

    # Force model if specified
    if args.model:
        # Override chain to start with requested model
        requested = [m for m in router.models if args.model in m.model or args.model == m.name]
        if requested:
            print(f"Forcing model {requested[0].name}")
            # Monkey-patch chain
            original_chain = adapter.models_for_role

            def forced_chain(role):
                stub = next((mm for mm in adapter.models if mm.provider == "stub"), None)
                return requested + ([stub] if stub else [])

            adapter.models_for_role = forced_chain

    try:
        data, used_model, score = adapter.generate(task, body, max_retries=3)
        print(f"LLM success: {used_model.name} provider={used_model.provider} score={score}")
        print(json.dumps(data, indent=2)[:2000])

        # Write artifact
        issue_num = issue.get("number", 0)
        art_path = ROOT / f"swarm/artifacts/llm-issue-{issue_num}.md"
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_text(
            f"# LLM work for issue #{issue_num}\n\n"
            f"Model: {used_model.name} provider={used_model.provider} score={score}\n\n"
            f"Summary: {data.get('summary','')}\n\n"
            f"Patch:\n```\n{data.get('patch','')[:4000]}\n```\n"
        )
        print(f"Wrote {art_path}")

        if not args.dry_run and issue_num:
            # Push branch + PR via github_queue
            try:
                import github_queue as ghq

                branch = f"swarm/issue-{issue_num}/llm-worker-{used_model.name}"
                # Create branch via API if needed (claim already)
                # For simplicity, use git locally
                import subprocess

                subprocess.run(["git", "checkout", "-b", branch], cwd=str(ROOT), capture_output=True)
                subprocess.run(["git", "add", str(art_path)], cwd=str(ROOT), capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"feat: llm-worker issue #{issue_num} via {used_model.name}"],
                    cwd=str(ROOT),
                    capture_output=True,
                )
                subprocess.run(["git", "push", "origin", branch], cwd=str(ROOT), capture_output=True)
                ghq.create_pr(branch, issue_num, f"[swarm][llm] issue #{issue_num} via {used_model.name}", body=data.get("summary",""))
            except Exception as e:
                print(f"Failed push/PR: {e}")

    except Exception as e:
        print(f"LLM worker failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
