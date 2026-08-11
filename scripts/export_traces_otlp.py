#!/usr/bin/env python3
"""Export local JSONL traces to OTLP (offline-first)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime


def jsonl_to_otlp(trace_dir: pathlib.Path) -> dict:
    spans = []
    for jf in trace_dir.glob("*.jsonl"):
        for line in jf.read_text(errors="ignore").splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            raw_time = ev.get("time", "2026-01-01T00:00:00")
            try:
                dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                start_ns = int(dt.timestamp() * 1e9)
            except Exception:
                start_ns = int(time.time() * 1e9)

            dur_ms = ev.get("duration_ms", 10)
            trace_id = ev.get("trace_id", "0" * 32)[:32].ljust(32, "0")
            span_id_raw = ev.get("span_id", raw_time[10:18] if len(raw_time) >= 18 else "0")
            span_id = span_id_raw.encode().hex()[:16].ljust(16, "0")[:16]

            span = {
                "traceId": trace_id,
                "spanId": span_id,
                "name": ev.get("tool", ev.get("action", "shesh.tool")),
                "startTimeUnixNano": str(start_ns),
                "endTimeUnixNano": str(start_ns + int(dur_ms * 1e6)),
                "attributes": [
                    {
                        "key": "shesh.actor",
                        "value": {"stringValue": str(ev.get("actor", "x"))},
                    },
                    {
                        "key": "shesh.tool",
                        "value": {"stringValue": str(ev.get("tool", ""))},
                    },
                    {
                        "key": "shesh.verdict",
                        "value": {"stringValue": str(ev.get("verdict", ""))},
                    },
                ],
                "status": {"code": 1 if ev.get("error") else 2},
            }
            spans.append(span)

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "shesh"}}
                    ]
                },
                "scopeSpans": [
                    {"scope": {"name": "shesh-orchestrator"}, "spans": spans}
                ],
            }
        ]
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Export traces to OTLP")
    ap.add_argument("--traces-dir", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--endpoint", help="OTLP HTTP endpoint")
    args = ap.parse_args()

    tdir = args.traces_dir
    if tdir is None:
        tdir = pathlib.Path.home() / ".local/share/shesh/traces"

    if not tdir.exists():
        print(f"No traces dir {tdir}, empty export", file=sys.stderr)
        otlp = {"resourceSpans": []}
    else:
        otlp = jsonl_to_otlp(tdir)

    payload = json.dumps(otlp, indent=2)

    if args.out:
        args.out.write_text(payload + "\n")
        count = 0
        try:
            rs = otlp.get("resourceSpans", [])
            if rs:
                count = len(rs[0].get("scopeSpans", [{}])[0].get("spans", []))
        except Exception:
            count = 0
        print(f"Wrote {count} spans to {args.out}")
    else:
        print(payload)

    if args.endpoint:
        try:
            import urllib.request

            req = urllib.request.Request(
                args.endpoint,
                data=payload.encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"POST {args.endpoint} -> {resp.status}")
        except Exception as e:
            print(f"OTLP export failed offline ok: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
