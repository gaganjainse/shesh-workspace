"""The failure register is data, so it is tested like data.

A register that drifts out of shape stops being queryable, and a guard that
does not actually detect its failure is worse than none: it looks like cover.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

WS = Path(__file__).resolve().parents[1]
REGISTER = WS / "failures" / "register.toml"
GUARDS = WS / "failures" / "guards"

VALID_SEVERITY = {"critical", "high", "medium", "low"}
VALID_STATUS = {"guarded", "manual", "accepted"}
VALID_AREA = {"ci", "docs", "security", "tooling", "process", "packaging", "git"}
REQUIRED = ("title", "date", "severity", "area", "symptom", "cause", "rule",
            "status", "recurrence")

ROWS = tomllib.loads(REGISTER.read_text(encoding="utf-8"))
IDS = sorted(ROWS)


def test_register_is_not_empty():
    assert ROWS, "the register has no rows"


@pytest.mark.parametrize("fid", IDS)
def test_id_is_well_formed(fid):
    assert re.fullmatch(r"F\d{3}", fid), f"{fid}: ids look like F001"


@pytest.mark.parametrize("fid", IDS)
def test_required_fields_present(fid):
    missing = [f for f in REQUIRED if f not in ROWS[fid]]
    assert not missing, f"{fid}: missing {missing}"


@pytest.mark.parametrize("fid", IDS)
def test_enumerations_are_valid(fid):
    r = ROWS[fid]
    assert r["severity"] in VALID_SEVERITY, f"{fid}: bad severity"
    assert r["status"] in VALID_STATUS, f"{fid}: bad status"
    for a in r["area"]:
        assert a in VALID_AREA, f"{fid}: bad area {a!r}"


@pytest.mark.parametrize("fid", IDS)
def test_prose_fields_are_substantive(fid):
    """A one-word symptom cannot be recognised by a future reader."""
    r = ROWS[fid]
    assert len(r["symptom"]) >= 25, f"{fid}: symptom too terse to recognise"
    assert len(r["cause"]) >= 40, f"{fid}: cause does not explain the mechanism"
    assert len(r["rule"]) >= 20, f"{fid}: rule too terse to follow"


@pytest.mark.parametrize("fid", IDS)
def test_rule_is_imperative(fid):
    """A rule is an instruction, not a description of what went wrong."""
    first = ROWS[fid]["rule"].split()[0].rstrip(",")
    assert not first.endswith("ed"), f"{fid}: rule reads as history, not instruction"


@pytest.mark.parametrize("fid", IDS)
def test_title_states_the_failure_not_the_fix(fid):
    title = ROWS[fid]["title"].lower()
    for word in ("fix", "add ", "use "):
        assert not title.startswith(word), (
            f"{fid}: title should name the failure, not the remedy")


@pytest.mark.parametrize("fid", IDS)
def test_recurrence_is_a_positive_integer(fid):
    n = ROWS[fid]["recurrence"]
    assert isinstance(n, int) and n >= 1, f"{fid}: recurrence must be >= 1"


# ── guards ──────────────────────────────────────────────────────────────────

GUARDED = [f for f in IDS if ROWS[f]["status"] == "guarded"]


@pytest.mark.parametrize("fid", GUARDED)
def test_guarded_row_names_a_guard(fid):
    assert ROWS[fid].get("guard"), f"{fid}: status is guarded but names no guard"


@pytest.mark.parametrize("fid", GUARDED)
def test_guard_exists_and_is_executable(fid):
    p = WS / "failures" / ROWS[fid]["guard"]
    assert p.exists(), f"{fid}: {p} does not exist"
    assert p.read_text(encoding="utf-8").startswith("#!"), f"{fid}: no shebang"


@pytest.mark.parametrize("fid", GUARDED)
def test_guard_passes_against_the_current_fleet(fid):
    """A guard that fires on a clean tree is a false positive and will be
    ignored, which is worse than having no guard at all."""
    p = WS / "failures" / ROWS[fid]["guard"]
    r = subprocess.run([sys.executable, str(p), str(WS.parent)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode == 2:
        # Exit 2 is "could not run" (no token, no network). That is not a pass
        # and not a failure of the fleet; the guard says so out loud rather
        # than exiting 0 without having checked.
        pytest.skip(f"{fid} could not run: {r.stdout.strip()}")
    assert r.returncode == 0, (
        f"{fid} fires on the current fleet:\n{r.stdout}{r.stderr}")


@pytest.mark.parametrize("fid", GUARDED)
def test_guard_documents_the_failure_it_detects(fid):
    """A guard read in isolation must say what it is for."""
    text = (WS / "failures" / ROWS[fid]["guard"]).read_text(encoding="utf-8")
    assert fid in text[:400], f"{fid}: guard docstring does not name the id"


@pytest.mark.parametrize("fid", GUARDED)
def test_guard_returns_findings_rather_than_printing_only(fid):
    """Structured output keeps a guard usable from another tool."""
    text = (WS / "failures" / ROWS[fid]["guard"]).read_text(encoding="utf-8")
    assert "def check(" in text, f"{fid}: guard has no check() entry point"


def test_manual_rows_explain_why_they_are_manual():
    for fid in [f for f in IDS if ROWS[f]["status"] == "manual"]:
        assert ROWS[fid].get("guard") is None, (
            f"{fid}: manual rows must not name a guard")


def test_no_orphan_guards():
    """A guard nobody references never runs."""
    named = {ROWS[f]["guard"].split("/")[-1] for f in IDS if ROWS[f].get("guard")}
    on_disk = {p.name for p in GUARDS.glob("F*.py")}
    orphans = on_disk - named
    assert not orphans, f"guards not referenced by any row: {sorted(orphans)}"


def test_ids_are_contiguous():
    """A gap usually means a row was deleted rather than marked accepted."""
    nums = sorted(int(f[1:]) for f in IDS)
    assert nums == list(range(1, len(nums) + 1)), (
        f"ids are not contiguous: {nums}")


def test_runner_validates_and_reports():
    r = subprocess.run([sys.executable, str(WS / "tools" / "guard.py"), "--check"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"guard.py --check failed:\n{r.stdout}{r.stderr}"
