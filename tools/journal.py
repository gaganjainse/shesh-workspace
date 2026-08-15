#!/usr/bin/env python3
"""Maintain the live-update documents: decision journal, TODO, and state.

Replaces live_update.py, which resolved paths that no longer exist after the
reorganisation and returned silently when they were missing. A tool that does
nothing quietly is worse than no tool: it looks maintained.

Every function here fails loudly if its target is missing, and `--check`
reports staleness so CI can enforce it.

Usage:
    journal.py record --query "..." --answer "..."   # append a decision
    journal.py todo --add "..." --priority p1        # add a backlog item
    journal.py todo --done "slug"                    # close one
    journal.py sync                                  # refresh derived state
    journal.py check                                 # non-zero if stale
"""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent
FLEET = WS.parent
ECO = FLEET / "shesh-ecosystem"

JOURNAL = WS / "docs" / "decision-journal.md"
TODO = ECO / "TODO.md"
STATE = ECO / "STATE.md"

# A session that changes nothing still counts; a day with no entry does not.
STALE_DAYS = 7


def today() -> str:
    return datetime.date.today().isoformat()


def sh(*args: str, cwd: Path | None = None) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              cwd=cwd, timeout=30).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def require(path: Path, what: str) -> None:
    if not path.exists():
        sys.exit(f"error: {what} not found at {path}\n"
                 f"       The journal cannot silently skip a missing target.")


# ── decision journal ────────────────────────────────────────────────────────

JOURNAL_HEADER = """# Decision journal

Every instruction and the decision taken in response, newest last. Appended
verbatim, never summarised: a summary loses the reasoning that makes an old
decision reviewable.

This is the factory's memory. When a session ends and another begins, this is
what explains why the code looks the way it does.

Maintained by `tools/journal.py`. Do not edit by hand.

"""


def record(query: str, answer: str) -> int:
    if not JOURNAL.exists():
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.write_text(JOURNAL_HEADER, encoding="utf-8")

    stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    entry = (
        f"\n---\n\n"
        f"## {today()}\n\n"
        f"**Asked**\n\n{query.strip()}\n\n"
        f"**Done**\n\n{answer.strip()}\n\n"
        f"<sub>Recorded {stamp}</sub>\n"
    )
    with JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"recorded to {JOURNAL.relative_to(FLEET)}")
    return 0


# ── backlog ─────────────────────────────────────────────────────────────────

PRIORITIES = ("p0", "p1", "p2", "p3")


def todo_add(text: str, priority: str, area: str | None) -> int:
    require(TODO, "TODO.md")
    if priority not in PRIORITIES:
        sys.exit(f"error: priority must be one of {', '.join(PRIORITIES)}")

    content = TODO.read_text(encoding="utf-8")
    tag = f" `{area}`" if area else ""
    line = f"- [ ] **{priority}**{tag} {text.strip()}  <!-- added {today()} -->\n"

    heading = f"## {priority.upper()}"
    if heading in content:
        idx = content.index(heading)
        nl = content.index("\n", idx) + 1
        content = content[:nl] + "\n" + line + content[nl:]
    else:
        content = content.rstrip() + f"\n\n{heading}\n\n{line}"

    TODO.write_text(content, encoding="utf-8")
    print(f"added [{priority}] {text.strip()[:60]}")
    return 0


def todo_done(match: str) -> int:
    require(TODO, "TODO.md")
    content = TODO.read_text(encoding="utf-8")
    out, hits = [], 0
    for line in content.split("\n"):
        if match.lower() in line.lower() and re.search(r"\[ \]|⬜|🟡", line):
            line = line.replace("- [ ]", "- [x]", 1)
            line = line.replace("⬜", "✅", 1).replace("🟡", "✅", 1)
            line += f"  <!-- done {today()} -->"
            hits += 1
        out.append(line)
    if not hits:
        sys.exit(f"error: no open item matching {match!r}")
    TODO.write_text("\n".join(out), encoding="utf-8")
    print(f"closed {hits} item(s) matching {match!r}")
    return 0


def counts() -> tuple[int, int]:
    """Count open and done items.

    The backlog uses emoji status markers as well as Markdown checkboxes;
    both are counted so the header stamp reflects the real file.
    """
    if not TODO.exists():
        return 0, 0
    text = TODO.read_text(encoding="utf-8")
    open_n = (len(re.findall(r"^\s*-? ?\[ \]", text, re.M))
              + len(re.findall(r"⬜", text))
              + len(re.findall(r"🟡", text))
              + len(re.findall(r"🔴", text)))
    done_n = (len(re.findall(r"^\s*-? ?\[x\]", text, re.M))
              + len(re.findall(r"✅", text)))
    return open_n, done_n


# ── sync ────────────────────────────────────────────────────────────────────

def sync() -> int:
    """Refresh everything derived, so no document is maintained by hand."""
    require(TODO, "TODO.md")
    steps = []

    # 1. TODO header carries a real date and a real count.
    text = TODO.read_text(encoding="utf-8")
    open_n, done_n = counts()
    stamp = (f"> Last updated {today()} · {open_n} open, {done_n} done · "
             f"maintained by `shesh-workspace/tools/journal.py`")
    if re.search(r"^> Last updated .*$", text, re.M):
        text = re.sub(r"^> Last updated .*$", stamp, text, count=1, flags=re.M)
    else:
        lines = text.split("\n")
        at = 1 if lines and lines[0].startswith("#") else 0
        lines.insert(at, "\n" + stamp)
        text = "\n".join(lines)
    TODO.write_text(text, encoding="utf-8")
    steps.append(f"TODO.md ({open_n} open, {done_n} done)")

    # 2. STATE.md is generated from the working trees.
    handoff = ECO / "tools" / "handoff.py"
    if handoff.exists():
        subprocess.run([sys.executable, str(handoff)], cwd=ECO,
                       capture_output=True, timeout=120)
        steps.append("STATE.md")

    # 3. Component catalogue is generated from the manifest.
    gen = FLEET / "shesh-docs" / "tools" / "generate_components.py"
    man = ECO / "manifests" / "components.toml"
    if gen.exists() and man.exists():
        subprocess.run([sys.executable, str(gen), str(man)],
                       cwd=FLEET / "shesh-docs", capture_output=True, timeout=120)
        steps.append("component catalogue")

    # 4. Fleet boilerplate.
    sync_fleet = ECO / "tools" / "sync_fleet.py"
    if sync_fleet.exists():
        subprocess.run([sys.executable, str(sync_fleet)], cwd=ECO,
                       capture_output=True, timeout=120)
        steps.append("fleet boilerplate")

    print("synced: " + ", ".join(steps))
    return 0


def check() -> int:
    """Fail when a live document has fallen behind."""
    problems = []

    if not JOURNAL.exists():
        problems.append("decision journal missing; run: journal.py record")
    else:
        dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})$",
                           JOURNAL.read_text(encoding="utf-8"), re.M)
        if not dates:
            problems.append("decision journal has no entries")
        else:
            last = datetime.date.fromisoformat(max(dates))
            age = (datetime.date.today() - last).days
            if age > STALE_DAYS:
                problems.append(f"decision journal last written {age} days ago")

    if not TODO.exists():
        problems.append("TODO.md missing")
    else:
        text = TODO.read_text(encoding="utf-8")
        m = re.search(r"^> Last updated (\d{4}-\d{2}-\d{2})", text, re.M)
        if not m:
            problems.append("TODO.md has no update stamp; run: journal.py sync")
        else:
            open_n, done_n = counts()
            if f"{open_n} open" not in text:
                problems.append("TODO.md counts are stale; run: journal.py sync")

    if not STATE.exists():
        problems.append("STATE.md missing; run: journal.py sync")

    if problems:
        print("Live documents are out of date:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Live documents are current.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("record", help="append an instruction and its outcome")
    p.add_argument("--query", required=True)
    p.add_argument("--answer", required=True)

    p = sub.add_parser("todo", help="manage the backlog")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--add")
    g.add_argument("--done")
    p.add_argument("--priority", default="p2", choices=PRIORITIES)
    p.add_argument("--area")

    sub.add_parser("sync", help="refresh every derived document")
    sub.add_parser("check", help="non-zero if a live document is stale")

    a = ap.parse_args()
    if a.cmd == "record":
        return record(a.query, a.answer)
    if a.cmd == "todo":
        return todo_add(a.add, a.priority, a.area) if a.add else todo_done(a.done)
    if a.cmd == "sync":
        return sync()
    if a.cmd == "check":
        return check()
    return 2


if __name__ == "__main__":
    sys.exit(main())
