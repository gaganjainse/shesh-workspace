#!/usr/bin/env bash
# scripts/bootstrap_workspace.sh — idempotent "proper workspace" setup.
#
# Survives Arena sandbox snapshots and fresh machines alike. Safe to re-run.
# Covers everything that silently dies between sessions:
#   - pip deps (ruff, pytest, cryptography) — snapshots drop site-packages
#   - git identity + PAT auth — snapshots drop .git/config
#   - plain PAT decrypt — needs GITHUB_PAT_PASSWORD (or it just tells you)
#
# Usage:
#   bash scripts/bootstrap_workspace.sh                 # full setup
#   GITHUB_PAT_PASSWORD=… bash scripts/bootstrap_workspace.sh   # + PAT decrypt
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "== pip toolchain =="
python3 -m pip install --quiet --upgrade ruff pytest cryptography || {
    echo "pip failed — check network"; exit 1; }

echo "== rust toolchain =="            # SheshAOS workspace builds need stable + fmt + clippy
export PATH="$HOME/.cargo/bin:$PATH"
if ! command -v cargo >/dev/null 2>&1; then
    curl -sSf --proto '=https' --tlsv1.2 https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable
    export PATH="$HOME/.cargo/bin:$PATH"
fi
rustup component list --installed 2>/dev/null | grep -q rustfmt || {
    echo "   adding rustfmt + clippy components"
    rustup component add rustfmt clippy >/dev/null; }
cargo --version

echo "== git identity =="
if ! git config user.name >/dev/null 2>&1; then
    name="$(git log --format='%an' -50 2>/dev/null | grep -iv -e 'actions' -e '\[bot\]' | head -1 || true)"
    email="$(git log --format='%ae' -50 2>/dev/null | grep -iv -e 'actions' -e '\[bot\]' | grep -v noreply | head -1 || true)"
    git config user.name "${name:-shesh-dev}"
    git config user.email "${email:-shesh-dev@localhost}"
fi
echo "   $(git config user.name) <$(git config user.email)>"

echo "== git HTTPS auth (PAT never stored in config) =="
# Snapshot restores strip exec bits (files land 0600 rw-) — re-assert before git auth matters.
for f in "$HOME/.git-cred-shesh" "$HOME/shesh-ecosystem/tools/git_askpass.py"; do
    if [ -e "$f" ]; then chmod +x "$f"; fi
done
if [ -f "$HOME/.config/shesh/github.pat" ]; then
    # shellcheck disable=SC2016 # the helper body is installed VERBATIM into
    # git config; $ escapes below must not expand in this script.
    git config credential.helper '!f() { echo username='"${GITHUB_ACTOR:-gaganjainse}"'; echo "password=$(tr -d \"\\n\" < \"$HOME/.config/shesh/github.pat\")"; }; f'
    echo "   credential.helper -> reads ~/.config/shesh/github.pat (0600)"
else
    echo "   no plain PAT yet — skipping credential helper"
fi

echo "== PAT =="
if [ -f "$HOME/.config/shesh/github.pat" ]; then
    echo "   plain PAT present"
elif [ -f "$HOME/.config/shesh/github.pat.enc" ] && [ -n "${GITHUB_PAT_PASSWORD:-}" ]; then
    GITHUB_PAT_PASSWORD="$GITHUB_PAT_PASSWORD" python3 tools/secure_pat.py --prompt
else
    echo "   enc present: $([ -f "$HOME/.config/shesh/github.pat.enc" ] && echo yes || echo no)"
    echo "   set GITHUB_PAT_PASSWORD to decrypt, or GITHUB_PAT / gh auth login"
fi

echo "== gate =="
make check 2>&1 | tail -1
echo "bootstrap OK — daemons: tools/swarm/daemon.sh start [component] (set SHESH_WORKER_EXECUTOR for workers)"
