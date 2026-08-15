#!/usr/bin/env python3
"""Export local trace JSONL to an OpenTelemetry-compatible endpoint.

Shesh records spans to ~/.local/share/shesh/traces/traces.jsonl. This script
reads them and translates them to OTLP JSON over HTTP. It is optional —
the system works fully offline without it.

Usage:
  python scripts/export_traces_otlp.py --endpoint http://localhost:4318/v1/traces
  python scripts/export_traces_otlp.py --since 2026-08-10
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, UTC
from pathlib import Path

TRACE_PATH = Path.home() / ".local" / "share" / "shesh" / "traces" / "traces.jsonl"


def load_spans_from(path: Path, since: str | None) -> list[dict]:
    if not path.exists():
        return []
    cutoff = 0.0
    if since:
        cutoff = datetime.fromisoformat(since).timestamp()
    out = []
    for line in path.read_text().splitlines():
        try:
            s = json.loads(line)
        except json.JSONDecodeError:
            continue
        if s.get("start", 0) >= cutoff:
            out.append(s)
    return out


def _to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def load_spans(since: str | None) -> list[dict]:
    return load_spans_from(TRACE_PATH, since)


def to_otlp(spans: list[dict]) -> dict:
    """Translate our span records into an OTLP resourceSpans payload."""
    return {
        "resourceSpans": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": "shesh"}},
            ]},
            "scopeSpans": [{
                "scope": {"name": "shesh.orchestrator"},
                "spans": [{
                    "name": s.get("name", "unknown"),
                    "traceId": format(abs(hash(s.get("id", ""))), "032x"),
                    "spanId": format(abs(hash(s.get("id", "") + "span")), "016x"),
                    "kind": 1,  # internal
                    "startTimeUnixNano": int(s.get("start", time.time()) * 1e9),
                    "endTimeUnixNano": int((s.get("start", 0) +
                                           s.get("duration_ms", 0) / 1000) * 1e9),
                    "status": {"code": 2 if s.get("status") == "error" else 1},
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in s.get("attributes", {}).items()
                    ],
                } for s in spans],
            }],
        }],
    }


def export(endpoint: str, spans: list[dict]) -> int:
    if not spans:
        print("no spans to export")
        return 0
    body = json.dumps(to_otlp(spans)).encode()
    req = urllib.request.Request(
        endpoint, data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"exported {len(spans)} spans: {r.status}")
        return 0 if r.status < 300 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://localhost:4318/v1/traces")
    ap.add_argument("--since", help="ISO datetime; only spans after this time")
    ap.add_argument("--traces", type=Path, default=TRACE_PATH,
                    help="trace JSONL to read (default: the live shesh trace path)")
    ap.add_argument("--out", type=Path,
                    help="offline mode: write the OTLP JSON payload here instead of POSTing")
    args = ap.parse_args()
    spans = load_spans_from(args.traces, args.since)
    if args.out:
        payload = to_otlp(spans)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote OTLP payload ({len(spans)} spans) to {args.out}")
        return 0
    return export(args.endpoint, spans)


if __name__ == "__main__":
    raise SystemExit(main())
