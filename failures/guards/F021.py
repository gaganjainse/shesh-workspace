#!/usr/bin/env python3
"""F021: a verified: date that means nobody ran anything.

A verified: date on a hardware claim comes from tools/hwverify.py evidence,
not from reading. A skipped probe is not a pass.

A page that asserts hardware behaviour must either carry evidence from a real
run or say plainly that it has not been verified on hardware. This guard fails
when a hardware-claiming page carries a bare `verified:` stamp and no evidence
file backs it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Pages whose claims are about physical behaviour, not source structure.
HARDWARE_WORDS = re.compile(
    r"\b(nvidia|gpu|vram|refresh rate|144 ?hz|hyprland|monitor|microphone|"
    r"wake word|adb|phone|bluetooth|brightness|pipewire|pulseaudio|mux)\b", re.I)
STAMP = re.compile(r"^verified:\s*(\S+)", re.M)
EVIDENCE_NAMES = ("hardware-verification.json", "hwverify.json")


def _evidence(fleet: Path) -> dict | None:
    for repo in fleet.iterdir():
        for name in EVIDENCE_NAMES:
            for cand in (repo / name, repo / "evidence" / name,
                         repo / "docs" / name):
                if cand.is_file():
                    try:
                        return json.loads(cand.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
    return None


def check(fleet: Path) -> list[str]:
    findings: list[str] = []
    ev = _evidence(fleet)
    passed = set()
    if ev:
        passed = {r["id"] for r in ev.get("results", []) if r.get("status") == "pass"}

    for repo in sorted(p for p in fleet.iterdir() if (p / ".git").is_dir()):
        # An archive records the system as it was. Its stamps are part of the
        # record, and editing them to look current would falsify it. The whole
        # repository is exempt, not just paths named "archive" inside it.
        if repo.name.endswith("-docs-archive"):
            continue
        for doc in sorted(repo.rglob("*.md")):
            rel = doc.relative_to(fleet)
            parts = set(rel.parts)
            if parts & {"archive", "history", "attic", ".git"}:
                continue
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            m = STAMP.search(text)
            if not m:
                continue
            if not HARDWARE_WORDS.search(text):
                continue  # a source-level claim; the stamp is honest
            # A hardware page must either disclaim, or be backed by evidence.
            hw = re.search(r"^hardware_verified:\s*(\S+)", text, re.M)
            if hw and hw.group(1).strip().lower() in ("no", "false", "none", '"no"'):
                continue  # honestly declared source-level only
            if re.search(r"not (?:been )?(?:hardware[- ])?verified|"
                         r"source[- ]level only|no hardware run", text, re.I):
                continue
            if hw and passed:
                continue  # dated and backed by an evidence file
            if hw and not passed:
                findings.append(
                    f"{rel}: sets hardware_verified: {hw.group(1)} but no "
                    f"hwverify evidence file with passing probes was found")
                continue
            findings.append(
                f"{rel}: claims hardware behaviour and stamps "
                f"verified: {m.group(1)}, but no hwverify evidence file backs "
                f"it. Run tools/hwverify.py --json, or say the page is "
                f"source-level only.")
    return findings


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = check(root)
    for f in found[:20]:
        print(f"  {f}")
    if len(found) > 20:
        print(f"  ... and {len(found) - 20} more")
    sys.exit(1 if found else 0)
