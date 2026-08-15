#!/usr/bin/env python3
"""Work queue and steer file for agents with no orchestration of their own.

The swarm system assumed a running orchestrator, heartbeats, and a claim
protocol. Most agents have none of that: a fresh session in a chat window has
a filesystem and nothing else. It still needs to know what to do next and to
avoid colliding with another session.

Two artefacts, both plain files:

  QUEUE.md   ordered work items with an explicit owner and status
  STEER.md   the single next action, generated, read first by any agent

Claiming is advisory, not enforced. A lock nobody can break is worse than a
note saying who is working on what, because a crashed session would hold it
forever.

Usage:
    steer.py add "title" --priority p1 --repo shesh-core
    steer.py claim <id> --agent <name>
    steer.py done <id>
    steer.py release <id>            # give it back
    steer.py show                    # regenerate STEER.md and print it
    steer.py check                   # non-zero if stale or inconsistent
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
QUEUE_DB = WS / "swarm" / "queue" / "items.jsonl"
QUEUE_MD = WS / "QUEUE.md"
STEER_MD = WS / "STEER.md"

PRIORITIES = ("p0", "p1", "p2", "p3")
# A claim older than this is treated as abandoned: sessions end without warning.
CLAIM_STALE_HOURS = 8


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def load() -> list[dict]:
    if not QUEUE_DB.exists():
        return []
    out = []
    for line in QUEUE_DB.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def save(items: list[dict]) -> None:
    QUEUE_DB.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_DB.write_text(
        "\n".join(json.dumps(i, sort_keys=True) for i in items) + "\n",
        encoding="utf-8")


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:40] or "item"


def claim_age_hours(item: dict) -> float:
    if not item.get("claimed_at"):
        return 0.0
    then = datetime.datetime.fromisoformat(item["claimed_at"])
    return (datetime.datetime.now(datetime.UTC) - then).total_seconds() / 3600


def is_stale(item: dict) -> bool:
    return (item.get("status") == "claimed"
            and claim_age_hours(item) > CLAIM_STALE_HOURS)


def add(title: str, priority: str, repo: str | None, note: str | None) -> int:
    if priority not in PRIORITIES:
        sys.exit(f"error: priority must be one of {', '.join(PRIORITIES)}")
    items = load()
    base, n, ident = slug(title), 1, slug(title)
    while any(i["id"] == ident for i in items):
        n += 1
        ident = f"{base}-{n}"
    items.append({
        "id": ident, "title": title.strip(), "priority": priority,
        "repo": repo, "note": note, "status": "open",
        "owner": None, "claimed_at": None,
        "created": now(), "done_at": None,
    })
    save(items)
    render()
    print(f"added {ident} [{priority}]")
    return 0


def claim(ident: str, agent: str) -> int:
    items = load()
    for i in items:
        if i["id"] != ident:
            continue
        if i["status"] == "done":
            sys.exit(f"error: {ident} is already done")
        if i["status"] == "claimed" and not is_stale(i):
            sys.exit(f"error: {ident} is held by {i['owner']} "
                     f"({claim_age_hours(i):.1f}h ago). Use release first.")
        if is_stale(i):
            print(f"note: reclaiming from {i['owner']}, "
                  f"idle {claim_age_hours(i):.1f}h")
        i.update(status="claimed", owner=agent, claimed_at=now())
        save(items)
        render()
        print(f"claimed {ident} for {agent}")
        return 0
    sys.exit(f"error: no item {ident!r}")


def done(ident: str) -> int:
    items = load()
    for i in items:
        if i["id"] == ident:
            i.update(status="done", done_at=now())
            save(items)
            render()
            print(f"closed {ident}")
            return 0
    sys.exit(f"error: no item {ident!r}")


def release(ident: str) -> int:
    items = load()
    for i in items:
        if i["id"] == ident:
            i.update(status="open", owner=None, claimed_at=None)
            save(items)
            render()
            print(f"released {ident}")
            return 0
    sys.exit(f"error: no item {ident!r}")


def next_item(items: list[dict]) -> dict | None:
    avail = [i for i in items
             if i["status"] == "open" or is_stale(i)]
    if not avail:
        return None
    return sorted(avail, key=lambda i: (PRIORITIES.index(i["priority"]),
                                        i["created"]))[0]


def render() -> None:
    items = load()
    openq = [i for i in items if i["status"] != "done"]
    donen = sum(1 for i in items if i["status"] == "done")

    lines = [
        "<!-- Generated by tools/steer.py. Do not edit by hand. -->",
        "", "# Work queue", "",
        f"{len(openq)} open, {donen} done. Ordered by priority, then age.",
        "",
        "Claiming is advisory. A claim idle for more than "
        f"{CLAIM_STALE_HOURS} hours is treated as abandoned and may be taken, "
        "because sessions end without warning.",
        "",
    ]
    if openq:
        lines += ["| Item | Priority | Repository | Status | Owner |",
                  "|---|---|---|---|---|"]
        for i in sorted(openq, key=lambda x: (PRIORITIES.index(x["priority"]),
                                              x["created"])):
            state = i["status"]
            if is_stale(i):
                state = f"stale ({claim_age_hours(i):.0f}h)"
            lines.append(
                f"| `{i['id']}` {i['title']} | {i['priority']} "
                f"| {i.get('repo') or '—'} | {state} | {i.get('owner') or '—'} |")
        lines.append("")
    else:
        lines += ["The queue is empty.", ""]
    QUEUE_MD.write_text("\n".join(lines), encoding="utf-8")

    nxt = next_item(items)
    steer = [
        "<!-- Generated by tools/steer.py. Do not edit by hand. -->",
        "", "# Steer", "",
        "The single next action. Any agent, in any tool, reads this first.",
        "",
    ]
    if nxt:
        steer += [
            "## Do this", "",
            f"**{nxt['title']}**", "",
            "| | |", "|---|---|",
            f"| Item | `{nxt['id']}` |",
            f"| Priority | {nxt['priority']} |",
            f"| Repository | {nxt.get('repo') or 'not specified'} |",
        ]
        if nxt.get("note"):
            steer.append(f"| Note | {nxt['note']} |")
        steer += [
            "", "## Claim it first", "",
            "```bash",
            f"python3 tools/steer.py claim {nxt['id']} --agent \"<your-name>\"",
            "```", "",
            "Claiming prevents two sessions doing the same work. If the claim "
            "shows as stale, the previous session ended; take it.", "",
        ]
    else:
        steer += ["## Nothing queued", "",
                  "The queue is empty. Ask the maintainer what to work on, or "
                  "add an item:", "",
                  "```bash",
                  'python3 tools/steer.py add "title" --priority p2 --repo <repo>',
                  "```", ""]

    steer += [
        "## Before you start", "",
        "1. Read `FACTORY.md` for how work is taken, committed, and pushed.",
        "2. Read `../shesh-ecosystem/HANDOFF.md` for where things live.",
        "3. Run `make check` in the affected repository. A red gate on arrival",
        "   is not yours to build on.",
        "",
        "## When you stop", "",
        "```bash",
        "python3 tools/steer.py done <id>        # finished",
        "python3 tools/steer.py release <id>     # not finished; hand it back",
        "python3 tools/journal.py record --query '...' --answer '...'",
        "```",
        "",
    ]
    STEER_MD.write_text("\n".join(steer), encoding="utf-8")


def show() -> int:
    render()
    print(STEER_MD.read_text(encoding="utf-8"))
    return 0


def check() -> int:
    problems = []
    items = load()

    if not QUEUE_MD.exists() or not STEER_MD.exists():
        problems.append("QUEUE.md or STEER.md missing; run: steer.py show")

    ids = [i["id"] for i in items]
    if len(ids) != len(set(ids)):
        problems.append("duplicate item ids in the queue")

    for i in items:
        if i["status"] not in {"open", "claimed", "done"}:
            problems.append(f"{i['id']}: unknown status {i['status']!r}")
        if i["status"] == "claimed" and not i.get("owner"):
            problems.append(f"{i['id']}: claimed with no owner")

    stale = [i for i in items if is_stale(i)]
    for i in stale:
        print(f"note: {i['id']} claimed by {i['owner']} is idle "
              f"{claim_age_hours(i):.1f}h and may be reclaimed")

    if items:
        before = (QUEUE_MD.read_text(encoding="utf-8")
                  if QUEUE_MD.exists() else "")
        render()
        if QUEUE_MD.read_text(encoding="utf-8") != before:
            problems.append("QUEUE.md was stale; regenerated")

    if problems:
        print("Queue problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Queue is consistent ({len(items)} item(s), {len(stale)} stale).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("title")
    p.add_argument("--priority", default="p2", choices=PRIORITIES)
    p.add_argument("--repo")
    p.add_argument("--note")

    p = sub.add_parser("claim")
    p.add_argument("id")
    p.add_argument("--agent", default=os.environ.get("SHESH_AGENT", "unnamed"))

    for name in ("done", "release"):
        p = sub.add_parser(name)
        p.add_argument("id")

    sub.add_parser("show")
    sub.add_parser("check")

    a = ap.parse_args()
    if a.cmd == "add":
        return add(a.title, a.priority, a.repo, a.note)
    if a.cmd == "claim":
        return claim(a.id, a.agent)
    if a.cmd == "done":
        return done(a.id)
    if a.cmd == "release":
        return release(a.id)
    if a.cmd == "show":
        return show()
    if a.cmd == "check":
        return check()
    return 2


if __name__ == "__main__":
    sys.exit(main())
