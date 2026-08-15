#!/bin/bash
# Session timer — adaptive cadence (15 min), self-healing.
# Parses the guard's JSON output precisely (no loose greps).
set -u
cd "$(dirname "$0")/.." || exit 1
INTERVAL="${SESSION_TICK_SECS:-900}"
echo "[timer] start, tick every ${INTERVAL}s"
while true; do
  ts=$(date -u +%H:%M:%S)
  out=$(python3 tools/session_guard.py --tick 2>&1)
  code=$?
  verdict=$(python3 - "$out" <<'PY'
import json, sys, re
raw = sys.argv[1]
# extract the JSON object printed by the guard
m = re.search(r'\{[^{}]*\}', raw)
attn = []
if m:
    try:
        d = json.loads(m.group(0))
        if d.get("need_password"): attn.append("NEED_PASSWORD")
        if d.get("workspace_mb", 0) > 100: attn.append("WORKSPACE>100MB")
        if d.get("file_count", 0) > 8000: attn.append("FILES>8000")
        if d.get("uncommitted", 0) > 0: attn.append(f"UNCOMMITTED={d.get('uncommitted')}")
    except Exception:
        pass
if "HOP RECOMMENDED" in raw: attn.append("HOP RECOMMENDED")
print(",".join(attn) if attn else "OK")
PY
)
  if [ $code -ne 0 ]; then
    echo "[$ts] tick exited $code: $out"
  elif [ "$verdict" = "OK" ]; then
    echo "[$ts] ok"
  else
    echo "[$ts] ATTENTION: $verdict"
  fi
  sleep "$INTERVAL"
done
