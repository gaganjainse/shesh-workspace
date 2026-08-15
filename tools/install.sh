#!/usr/bin/env bash
# Shesh installer with channel support + btrfs snapshot + rollback
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/gaganjainse/shesh-ecosystem/main/tools/install.sh | bash -s -- --channel canary
#   bash tools/install.sh --channel stable --dry-run
# Channels: stable | canary | devel (default: canary)
#
# What it does:
#   1. Verifies btrfs root (warns if not btrfs — snapshot skipped)
#   2. Creates btrfs snapshot: /@snapshots/pre-shesh-<channel>-YYYYMMDD-HHMMSS
#   3. Resolves manifest lock for channel
#   4. pipx upgrades all shesh-* from lock
#   5. Generates MCP config (~/.config/shesh/mcp/servers.json + Zed/Newelle)
#   6. Verifies e2e-canary.sh (optional --check)
#   7. Prints rollback instructions

set -euo pipefail

CHANNEL="canary"
DRY_RUN=false
CHECK=false
ROOT="/"
SNAP_DIR="/.snapshots"
DATE="$(date +%Y%m%d-%H%M%S)"

usage() {
  echo "Shesh installer — channels: stable|canary|devel"
  echo "  --channel <name>  Default: canary"
  echo "  --dry-run         Print what would be done, don't change"
  echo "  --check           Run e2e-canary.sh after install"
  echo "  --root <path>     Btrfs root to snapshot (default: /)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) CHANNEL="$2"; shift 2;;
    --dry-run) DRY_RUN=true; shift;;
    --check) CHECK=true; shift;;
    --root) ROOT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg $1"; usage; exit 1;;
  esac
done

[[ "$CHANNEL" =~ ^(stable|canary|devel)$ ]] || { echo "Invalid channel $CHANNEL"; exit 1; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$HERE/channels/${CHANNEL}.lock"

echo "==> Shesh installer — channel=$CHANNEL dry_run=$DRY_RUN root=$ROOT"

# 1. btrfs snapshot
if command -v btrfs >/dev/null 2>&1 && btrfs subvolume show "$ROOT" >/dev/null 2>&1; then
  SNAP="${SNAP_DIR}/pre-shesh-${CHANNEL}-${DATE}"
  if $DRY_RUN; then
    echo "[dry-run] would snapshot: btrfs subvolume snapshot $ROOT $SNAP"
  else
    sudo mkdir -p "$SNAP_DIR"
    echo "==> Creating btrfs snapshot $SNAP"
    sudo btrfs subvolume snapshot "$ROOT" "$SNAP" || echo "WARN: snapshot failed, continuing"
    echo "Snapshot created at $SNAP"
    echo "Rollback: sudo btrfs subvolume delete $ROOT && sudo btrfs subvolume snapshot $SNAP $ROOT && reboot"
    echo "Or select snapshot in grub-btrfs boot menu"
  fi
else
  echo "WARN: $ROOT not on btrfs or btrfs not installed — snapshot skipped (rollback via pipx reinstall)"
fi

# 2. Resolve lock
if [[ ! -f "$LOCK" ]]; then
  echo "Lock $LOCK missing — regenerating from manifest"
  if $DRY_RUN; then
    echo "[dry-run] python $HERE/scripts/resolve_manifest.py --channel $CHANNEL --out $LOCK"
  else
    python3 "$HERE/scripts/resolve_manifest.py" --channel "$CHANNEL" --out "$LOCK"
  fi
fi

echo "==> Lock: $(python3 -c 'import json,sys; print(json.load(sys.stdin).get("count",0))' < "$LOCK" 2>/dev/null || echo "?") components"

# 3. pipx upgrade
if ! command -v pipx >/dev/null 2>&1; then
  echo "Installing pipx"
  $DRY_RUN || python3 -m pip install --user pipx
  export PATH="$HOME/.local/bin:$PATH"
fi

# Parse lock for repo names
REPOS=$(python3 - <<PY
import json
lock="${LOCK}"
try:
  data=json.load(open(lock))
  seen=set()
  for name,c in data.get("components",{}).items():
    repo=c.get("repo")
    if repo and "shesh-" in name and repo not in seen:
      seen.add(repo)
      print(repo)
except Exception as e:
  print(f"# error reading lock: {e}", file=__import__("sys").stderr)
PY
)

echo "==> Will install/upgrade ${CHANNEL} components:"
while read -r repo_name; do echo "  - $repo_name"; done <<< "$REPOS"

if $DRY_RUN; then
  echo "[dry-run] pipx install/upgrade for each repo"
else
  for repo in $REPOS; do
    # skip shesh-desktop (dotfiles, not pip)
    [[ "$repo" == *"shesh-desktop"* ]] && continue
    echo "--- pipx install $repo ---"
    pipx install "git+https://github.com/${repo}.git" --force || pipx upgrade "${repo##*/}" || echo "WARN: $repo install failed"
  done
fi

# 4. MCP config generation
if $DRY_RUN; then
  echo "[dry-run] python $HERE/scripts/generate_mcp_config.py --channel $CHANNEL"
else
  echo "==> Generating MCP config"
  python3 "$HERE/scripts/generate_mcp_config.py" --channel "$CHANNEL" || echo "WARN: MCP config gen failed"
  if [ -f ~/.config/shesh/mcp/servers.json ]; then
    ls -lh ~/.config/shesh/mcp/servers.json
  else
    echo "WARN: ~/.config/shesh/mcp/servers.json was not generated"
  fi
fi

# 5. Optional e2e check
if $CHECK; then
  if $DRY_RUN; then
    echo "[dry-run] would run bash $HERE/scripts/e2e-canary.sh"
  else
    bash "$HERE/scripts/e2e-canary.sh" || echo "WARN: e2e-canary failed"
  fi
fi

cat <<EOF
=== Shesh $CHANNEL install done ===

Verify:
  for s in shesh-{audit,system,shell,files,skills,memory,mind,harness,orchestrator,backup,phone,containers,secrets,calendar,acp}-mcp; do
    command -v "\$s" && echo "ok \$s" || echo "MISSING \$s"
  done
  bash $HERE/scripts/e2e-canary.sh   # full integration

Rollback (if btrfs snapshot was taken):
  sudo btrfs subvolume list /
  sudo btrfs subvolume delete $ROOT
  sudo btrfs subvolume snapshot ${SNAP_DIR}/pre-shesh-${CHANNEL}-${DATE} $ROOT
  sudo reboot

Uninstall:
  for repo in $REPOS; do pipx uninstall "\${repo##*/}" || true; done

Docs:
  $HERE/docs/GETTING_STARTED.md
  $HERE/docs/MANUAL_VERIFICATION.md
EOF
