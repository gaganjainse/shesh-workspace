#!/usr/bin/env python3
"""Eval harness — measure quality variance across free models."""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from llm_adapter import ModelAgnosticAdapter, TaskSpec  # noqa: E402
from model_router import Router  # noqa: E402


def sample_tasks(role: str) -> list[TaskSpec]:
    if role == "planner":
        return [
            TaskSpec(
                role="planner",
                goal="organize Downloads by type",
                schema={
                    "type": "object",
                    "required": ["steps"],
                    "properties": {"steps": {"type": "array"}},
                },
                must_contain=["organize"],
                must_not_contain=["rm -rf /"],
            ),
            TaskSpec(
                role="planner",
                goal="backup old notes",
                schema={
                    "type": "object",
                    "required": ["steps"],
                    "properties": {"steps": {"type": "array"}},
                },
                must_contain=["backup"],
            ),
        ]
    if role == "coder":
        return [
            TaskSpec(
                role="coder",
                goal="write python function to list files by type",
                schema={
                    "type": "object",
                    "required": ["patch"],
                    "properties": {"patch": {"type": "string"}},
                },
                must_contain=["def"],
            )
        ]
    return [
        TaskSpec(
            role=role,
            goal=f"test task for {role}",
            schema={"type": "object", "required": ["result"]},
        )
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval model-agnostic variance")
    ap.add_argument("--role", default="planner")
    ap.add_argument("--tasks", type=int, default=2)
    ap.add_argument("--free-only", action="store_true", default=True)
    ap.add_argument("--models", nargs="*", help="specific models")
    args = ap.parse_args()

    router = Router()
    models = router.models
    if args.free_only:
        models = [m for m in models if m.free]
    if args.models:
        models = [m for m in models if m.name in args.models]

    print(f"Testing {len(models)} free models for role {args.role}:")
    for m in models:
        print(f"  - {m.name:35} {m.provider:12} prio={m.priority}")

    tasks = sample_tasks(args.role)[: args.tasks]
    results = []
    for task in tasks:
        print(f"\n=== Task: {task.goal} ===")
        for model in models:
            single_adapter = ModelAgnosticAdapter()

            # Capture model and adapter in closure correctly
            def make_single_role(target_model, adapter_ref):
                def single_role(_role):
                    stub = next(
                        (mm for mm in adapter_ref.models if mm.provider == "stub"),
                        None,
                    )
                    return [target_model] + ([stub] if stub else [])

                return single_role

            single_adapter.models_for_role = make_single_role(model, single_adapter)

            try:
                data, used, score = single_adapter.generate(
                    task, task.goal, max_retries=2
                )
                print(
                    f"  [{model.name:30}] score={score:.2f} valid=True "
                    f"used={used.name} keys={list(data.keys())}"
                )
                results.append(
                    {
                        "model": model.name,
                        "task": task.goal,
                        "score": score,
                        "valid": True,
                    }
                )
            except Exception as e:
                print(f"  [{model.name:30}] FAILED: {e}")
                results.append(
                    {
                        "model": model.name,
                        "task": task.goal,
                        "score": 0.0,
                        "valid": False,
                    }
                )

    if results:
        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        var = sum((s - avg) ** 2 for s in scores) / len(scores) if scores else 0
        valid_rate = sum(1 for r in results if r["valid"]) / len(results) * 100
        print("\n=== Summary ===")
        print(f"Avg {avg:.2f} Var {var:.4f} Valid {valid_rate:.1f}%")
        print(f"Goal var<0.1 valid 100% — {'PASS' if var < 0.1 and valid_rate == 100 else 'FAIL'}")
        by_model: dict[str, list[float]] = defaultdict(list)
        for r in results:
            by_model[r["model"]].append(r["score"])
        for m, sc in by_model.items():
            print(f"  {m:30} avg={sum(sc)/len(sc):.2f} min={min(sc):.2f} max={max(sc):.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
