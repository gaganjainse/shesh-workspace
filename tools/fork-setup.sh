#!/usr/bin/env bash
# scripts/fork-setup.sh
# Creates local clones of every upstream we depend on, under sources/upstream/,
# and registers our forks under sources/forks/.
#
# This is the rolling-release intake layer (① in REPO_TOPOLOGY.md): we track
# upstream default branches so we can cherry-pick/rebase our patches weekly.
#
# Usage: scripts/fork-setup.sh [--shallow]
#
# Prerequisites: gh (GitHub CLI, authenticated) OR git over https.
# Nothing is pushed; this only clones/configures remotes locally.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHALLOW=()
[[ "${1:-}" == "--shallow" ]] && SHALLOW=(--depth 1)

mkdir -p "$ROOT/sources/upstream" "$ROOT/sources/forks"

# repo:dir:fork-owner (your GitHub account)
# Format: "upstream/repo  directory  gaganjainse"
REPOS=(
  "qwersyk/Newelle                    upstream/newelle           gaganjainse/newelle"
  "end-4/dots-hyprland               upstream/dots-hyprland     gaganjainse/dots-hyprland"
  "ollama/ollama                     upstream/ollama            gaganjainse/ollama"
  "89luca89/distrobox                 upstream/distrobox         gaganjainse/distrobox"
  "containers/podman                  upstream/podman            gaganjainse/podman"
)

clone_or_update() {
  local upstream="$1" dir="$2" fork="$3"
  local path="$ROOT/sources/$dir"
  if [[ -d "$path/.git" ]]; then
    echo "==> updating $dir"
    git -C "$path" fetch --all --quiet
  else
    echo "==> cloning $upstream -> $dir"
    git clone "${SHALLOW[@]}" "https://github.com/${upstream}.git" "$path"
    # Point 'origin' at our fork (assumes it exists on GitHub); keep 'upstream' tracking source.
    if command -v gh >/dev/null && gh repo view "$fork" >/dev/null 2>&1; then
      if git -C "$path" remote get-url upstream >/dev/null 2>&1; then
        echo "    upstream remote already configured; leaving remotes as-is"
      else
        git -C "$path" remote rename origin upstream
        git -C "$path" remote add origin "https://github.com/${fork}.git"
      fi
    fi
  fi
}

for entry in "${REPOS[@]}"; do
  # shellcheck disable=SC2086
  clone_or_update $entry
done

echo
echo "Upstreams cloned under sources/upstream/. Next:"
echo "  1. On GitHub, fork each repo listed above (gh repo fork --clone=false <repo>)."
echo "  2. Create a 'shesh' branch in each fork carrying our patches."
echo "  3. Run: scripts/upstream_tracker.py  to see what moved."
