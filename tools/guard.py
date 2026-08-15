#!/usr/bin/env python3
"""Run every guard in the failure register and fail if a known failure returned.

A failure recorded in prose is read once and forgotten. A failure recorded as a
row with a detector cannot come back silently: this runs in the gate, so
reintroducing any of them breaks the build.

Usage:
    guard.py --check              # run every guard; non-zero if any fires
    guard.py --list               # the register as a table
    guard.py --show F014          # one row in full
    guard.py --gaps               # rows with no guard, worst first
    guard.py --stats              # coverage and cost summary
    guard.py --new                # scaffold a row and a guard
"""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
import tomllib
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
FLEET = WS.parent
REGISTER = WS / "failures" / "register.toml"
GUARDS = WS / "failures" / "guards"

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
VALID_SEVERITY = set(SEVERITY_ORDER)
VALID_STATUS = {"guarded", "manual", "accepted"}
VALID_AREA = {"ci", "docs", "security", "tooling", "process", "packaging", "git"}
REQUIRED = ("title", "date", "severity", "area", "symptom", "cause", "rule",
            "status", "recurrence")


def load() -> dict[str, dict]:
    if not REGISTER.exists():
        sys.exit(f"error: {REGISTER} not found")
    return tomllib.loads(REGISTER.read_text(encoding="utf-8"))


def validate(rows: dict[str, dict]) -> list[str]:
    """The register is data, so it is checked like data."""
    problems = []
    for fid, row in rows.items():
        if not re.fullmatch(r"F\d{3}", fid):
            problems.append(f"{fid}: id must match F000")
        for field in REQUIRED:
            if field not in row:
                problems.append(f"{fid}: missing {field!r}")
        if row.get("severity") not in VALID_SEVERITY:
            problems.append(f"{fid}: severity {row.get('severity')!r} invalid")
        if row.get("status") not in VALID_STATUS:
            problems.append(f"{fid}: status {row.get('status')!r} invalid")
        for a in row.get("area", []):
            if a not in VALID_AREA:
                problems.append(f"{fid}: area {a!r} invalid")
        if row.get("status") == "guarded" and not row.get("guard"):
            problems.append(f"{fid}: status is guarded but no guard is named")
        if row.get("guard") and not (WS / "failures" / row["guard"]).exists():
            problems.append(f"{fid}: guard {row['guard']} does not exist")
        if not isinstance(row.get("recurrence"), int):
            problems.append(f"{fid}: recurrence must be an integer")
    return problems


def run_guard(fid: str, row: dict) -> tuple[bool, str]:
    """Return (passed, output). A guard exits 0 when the failure is absent."""
    path = WS / "failures" / row["guard"]
    try:
        p = subprocess.run([sys.executable, str(path), str(FLEET)],
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "  guard timed out after 120s"
    except OSError as exc:
        return False, f"  guard could not run: {exc}"
    return p.returncode == 0, (p.stdout + p.stderr).rstrip()


def cmd_check() -> int:
    rows = load()
    problems = validate(rows)
    if problems:
        print("Register is invalid:")
        for p in problems:
            print(f"  {p}")
        return 1

    guarded = {k: v for k, v in rows.items() if v.get("guard")}
    failed = []
    for fid in sorted(guarded):
        row = guarded[fid]
        ok, out = run_guard(fid, row)
        if not ok:
            failed.append((fid, row, out))

    manual = sum(1 for v in rows.values() if v["status"] == "manual")
    if failed:
        print(f"{len(failed)} known failure(s) have returned:\n")
        for fid, row, out in failed:
            print(f"  {fid} [{row['severity']}] {row['title']}")
            print(f"       rule: {row['rule']}")
            if out:
                for line in out.splitlines()[:8]:
                    print(f"       {line}")
            print()
        return 1

    print(f"{len(guarded)} guard(s) passed, {manual} rule(s) rely on a person.")
    return 0


def cmd_list(area: str | None, status: str | None) -> int:
    rows = load()
    sel = {
        k: v for k, v in rows.items()
        if (not area or area in v.get("area", []))
        and (not status or v["status"] == status)
    }
    if not sel:
        print("no rows match")
        return 0
    order = sorted(sel.items(),
                   key=lambda kv: (SEVERITY_ORDER[kv[1]["severity"]], kv[0]))
    print(f"{'id':<6} {'severity':<9} {'status':<9} {'n':<3} title")
    print("-" * 78)
    for fid, r in order:
        print(f"{fid:<6} {r['severity']:<9} {r['status']:<9} "
              f"{r['recurrence']:<3} {r['title'][:44]}")
    print(f"\n{len(sel)} of {len(rows)} row(s)")
    return 0


def cmd_show(fid: str) -> int:
    rows = load()
    if fid not in rows:
        print(f"error: no row {fid!r}", file=sys.stderr)
        return 1
    r = rows[fid]
    print(f"{fid}  {r['title']}\n")
    print(f"  severity    {r['severity']}")
    print(f"  status      {r['status']}")
    print(f"  area        {', '.join(r['area'])}")
    print(f"  first seen  {r['date']}")
    print(f"  recurrence  {r['recurrence']}")
    if r.get("cost"):
        print(f"  cost        {r['cost']}")
    print(f"\n  symptom\n    {r['symptom']}")
    print(f"\n  cause\n    " + r["cause"].strip().replace("\n", "\n    "))
    print(f"\n  rule\n    {r['rule']}")
    if r.get("guard"):
        print(f"\n  guard       failures/{r['guard']}")
        ok, out = run_guard(fid, r)
        print(f"  currently   {'absent' if ok else 'PRESENT'}")
        if out and not ok:
            print("  " + out.replace("\n", "\n  "))
    return 0


def cmd_gaps() -> int:
    """Rows relying on a person. These are the automation backlog."""
    rows = load()
    gaps = {k: v for k, v in rows.items() if v["status"] == "manual"}
    if not gaps:
        print("Every recorded failure has a guard.")
        return 0
    print(f"{len(gaps)} failure(s) rely on a person following the rule:\n")
    for fid, r in sorted(gaps.items(),
                         key=lambda kv: SEVERITY_ORDER[kv[1]["severity"]]):
        print(f"  {fid} [{r['severity']}] {r['title']}")
        print(f"       {r['rule']}")
    print("\nEach is a candidate for a guard. Write one when the mechanism")
    print("becomes detectable rather than leaving the count to grow.")
    return 0


def cmd_stats() -> int:
    rows = load()
    by_status: dict[str, int] = {}
    by_area: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    repeats = []
    for fid, r in rows.items():
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
        for a in r["area"]:
            by_area[a] = by_area.get(a, 0) + 1
        if r["recurrence"] > 1:
            repeats.append((fid, r))

    total = len(rows)
    guarded = by_status.get("guarded", 0)
    print(f"{total} recorded failure(s)\n")
    print(f"  guarded     {guarded:>3}  ({100 * guarded // total}% cannot silently return)")
    print(f"  manual      {by_status.get('manual', 0):>3}")
    print(f"  accepted    {by_status.get('accepted', 0):>3}")
    print("\n  by severity")
    for s in ("critical", "high", "medium", "low"):
        if by_sev.get(s):
            print(f"    {s:<10} {by_sev[s]}")
    print("\n  by area")
    for a, n in sorted(by_area.items(), key=lambda kv: -kv[1]):
        print(f"    {a:<10} {n}")
    if repeats:
        print("\n  recurred despite a rule (the rule is not working):")
        for fid, r in repeats:
            print(f"    {fid} x{r['recurrence']}  {r['title'][:46]}")
    return 0


GUARD_TEMPLATE = '''#!/usr/bin/env python3
"""{fid}: {title}

{rule}
"""
from __future__ import annotations

import sys
from pathlib import Path


def check(fleet: Path) -> list[str]:
    """Return findings. An empty list means the failure is absent."""
    findings: list[str] = []
    # TODO: detect the specific mechanism, not the general category.
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found:
        print(f"  {{f}}")
    sys.exit(1 if found else 0)
'''


def cmd_new() -> int:
    rows = load()
    nxt = f"F{max(int(k[1:]) for k in rows) + 1:03d}" if rows else "F001"
    print(f"Next id: {nxt}\n")
    print("Add to failures/register.toml:\n")
    print(f"""[{nxt}]
title = ""
date = {datetime.date.today().isoformat()}
severity = "medium"     # critical | high | medium | low
area = ["ci"]           # ci docs security tooling process packaging git
symptom = ""            # what a person sees, before the cause is known
cause = ""              # the mechanism
rule = ""               # imperative; what prevents it
guard = "guards/{nxt}.py"
status = "guarded"      # guarded | manual | accepted
cost = ""
recurrence = 1
""")
    print(f"Then write failures/guards/{nxt}.py:\n")
    print(GUARD_TEMPLATE.format(fid=nxt, title="<title>", rule="<rule>"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", metavar="ID")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--area")
    ap.add_argument("--status")
    a = ap.parse_args()

    if a.check:
        return cmd_check()
    if a.show:
        return cmd_show(a.show)
    if a.gaps:
        return cmd_gaps()
    if a.stats:
        return cmd_stats()
    if a.new:
        return cmd_new()
    return cmd_list(a.area, a.status)


if __name__ == "__main__":
    sys.exit(main())
