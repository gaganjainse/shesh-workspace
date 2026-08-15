#!/usr/bin/env bash
# install-shesh-stack.sh — Shesh Brain/Mind/Soma MCP stack (desktop-agnostic).
#
# Installs the shesh-core monorepo + the kept service repos into a shared venv,
# wires MCP client configs, systemd user units, and (optionally) Ollama models.
# Idempotent; safe to re-run. Runs after `setup install` (which already created
# the venv and installed Ollama/models on the desktop) OR standalone.
#
# Usage:
#   bash install-shesh-stack.sh [--skip-ai] [--no-sysupgrade] [--channel canary] [--dry-run]
#   --skip-ai       skip Ollama + model pulls (MCP servers still install)
#   --no-sysupgrade skip `pacman -Syu` (bootstrap already upgraded)
#   --channel       stable|canary|devel (default canary — matches the desktop)
set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()  { echo -e "${GREEN}[OK]${NC}   $*"; }
info(){ echo -e "${BLUE}[..]${NC}   $*"; }
warn(){ echo -e "${YELLOW}[!!]${NC}   $*"; }
die() { echo -e "${RED}[FATAL]${NC} $*" >&2; exit 1; }

SKIP_AI=0; NOSYS=0; DRY=0; CHANNEL="canary"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-ai) SKIP_AI=1; shift;;
    --no-sysupgrade) NOSYS=1; shift;;
    --channel) CHANNEL="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    -h|--help) cat <<'EOF'
install-shesh-stack.sh — install the Shesh MCP stack (desktop-agnostic)
  --skip-ai        skip Ollama + model pulls
  --no-sysupgrade  skip `pacman -Syu`
  --channel        stable|canary|devel (default canary)
  --dry-run        print actions only
EOF
      exit 0;;
    *) warn "unknown arg $1"; shift;;
  esac
done

SRC="${HOME}/src"
ECO="${SRC}/shesh-ecosystem"
COMP="${SRC}/components"
VENV="${XDG_STATE_HOME:-$HOME/.local/state}/shesh/.venv"
BIN_LINK="${HOME}/.local/bin"

run() { if [[ $DRY -eq 1 ]]; then info "[dry-run] $*"; else "$@"; fi; }

info "== Preflight =="
[[ $EUID -eq 0 ]] && die "run as your normal user"
command -v sudo >/dev/null || die "sudo required"
grep -qiE 'arch|cachyos' /etc/os-release || warn "not Arch/CachyOS — steps may differ"

info "== 1. Base tooling =="
[[ $NOSYS -eq 0 ]] && run sudo pacman -Syu --noconfirm
run sudo pacman -S --noconfirm --needed git curl base-devel
if ! command -v uv >/dev/null 2>&1; then
  run bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
  export PATH="$HOME/.local/bin:$PATH"
fi
# The installer above verifies artifact checksums internally; belt-and-braces:
uv --version >/dev/null 2>&1 || die "uv install failed verification" 
ok "uv: $(uv --version 2>/dev/null || echo 'restart shell to load uv')"

info "== 2. Clone ecosystem + component repos =="
run mkdir -p "$SRC"
if [[ -d "$ECO/.git" ]]; then
  run git -C "$ECO" pull --ff-only || warn "ecosystem pull failed — continuing with existing checkout"
else
  run git clone https://github.com/gaganjainse/shesh-ecosystem.git "$ECO"
fi
run bash "$ECO/scripts/fetch-components.sh" "$COMP" "$ECO/manifests/components.toml"

info "== 3. Shared venv (reuses setup's ~/.local/state/shesh/.venv if present) =="
if [[ ! -x "$VENV/bin/python" ]]; then
  run uv venv "$VENV"
fi
ok "venv: $VENV"

info "== 4. Install components (editable) =="
if [[ -d "$COMP" ]]; then
  for d in "$COMP"/shesh-*; do
    [[ -d "$d" && ! -L "$d" ]] || continue   # skip symlinks (shared-repo aliases)
    [[ -f "$d/pyproject.toml" ]] || continue
    info "installing $(basename "$d")"
    run uv pip install --python "$VENV/bin/python" -e "$d"
  done
else
  warn "components dir missing — fetch-components.sh may need network"
fi

info "== 5. Symlink console scripts into ~/.local/bin (MCP clients resolve them) =="
run mkdir -p "$BIN_LINK"
if [[ -d "$VENV/bin" ]]; then
  for s in "$VENV"/bin/shesh-*; do
    [[ -f "$s" ]] || continue
    run ln -sf "$s" "$BIN_LINK/$(basename "$s")"
  done
fi

info "== 6. MCP client configs (channel: $CHANNEL) =="
run python3 "$ECO/scripts/generate_mcp_config.py" --channel "$CHANNEL"

info "== 7. systemd user units (absolute venv paths) =="
UNIT_DIR="$HOME/.config/systemd/user"
run mkdir -p "$UNIT_DIR"
write_unit() { # name, exec, desc
  local name="$1" exec_cmd="$2" desc="$3"
  local f="$UNIT_DIR/$name"
  if [[ $DRY -eq 1 ]]; then info "[dry-run] write unit $name"; return; fi
  cat > "$f" <<UNIT
[Unit]
Description=$desc
After=network-online.target

[Service]
ExecStart=$exec_cmd
EnvironmentFile=-%h/.config/shesh/ollama/env
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
UNIT
}
if [[ -d "$VENV/bin" ]]; then
  for s in "$VENV"/bin/shesh-*-mcp; do
    [[ -f "$s" ]] || continue
    bn="$(basename "$s")"
    write_unit "$bn.service" "$s" "Shesh MCP server: $bn"
  done
fi
run systemctl --user daemon-reload
if [[ -d "$UNIT_DIR" ]]; then
  for u in "$UNIT_DIR"/shesh-*-mcp.service; do
    [[ -f "$u" ]] || continue
    run systemctl --user enable "$(basename "$u")"
  done
fi

# shesh-mcp.target — the desktop's Settings → Shesh master switch toggles this.
info "== 7b. shesh-mcp.target + automation tools =="
TARGET="$UNIT_DIR/shesh-mcp.target"
if [[ $DRY -eq 1 ]]; then
  info "[dry-run] write shesh-mcp.target"
else
  {
    echo "[Unit]"
    echo "Description=Shesh MCP servers (Brain/Mind/Soma)"
    echo "Documentation=https://github.com/gaganjainse/shesh-ecosystem"
    echo "After=graphical-session.target"
    for u in "$UNIT_DIR"/shesh-*-mcp.service; do
      [[ -f "$u" ]] || continue
      echo "Wants=$(basename "$u")"
    done
    echo ""
    echo "[Install]"
    echo "WantedBy=graphical-session.target"
  } > "$TARGET"
  ok "shesh-mcp.target written"
fi
if [[ $DRY -eq 1 ]]; then
  info "[dry-run] systemctl --user enable shesh-mcp.target"
elif systemctl --user enable shesh-mcp.target >/dev/null 2>&1; then
  ok "shesh-mcp.target enabled"
else
  warn "shesh-mcp.target enable failed (no user bus here?); unit files are still installed"
fi

DESKTOP="${SHESH_DESKTOP:-$HOME/Workspace/shesh-desktop}"
if [[ -d "$DESKTOP/tools" ]]; then
  # shesh-power: system script + udev rule (root) + user service
  if [[ -f "$DESKTOP/tools/automation/shesh-power.sh" ]]; then
    run sudo install -Dm755 "$DESKTOP/tools/automation/shesh-power.sh" /usr/local/bin/shesh-power.sh
    if [[ -f "$DESKTOP/tools/automation/99-shesh-power.rules" ]]; then
      run sudo install -Dm644 "$DESKTOP/tools/automation/99-shesh-power.rules" /etc/udev/rules.d/99-shesh-power.rules
      run sudo udevadm control --reload-rules 2>/dev/null || warn "udevadm reload failed (rule installed; takes effect after reboot)"
    fi
    if [[ -f "$DESKTOP/tools/automation/shesh-power.service" ]]; then
      run cp "$DESKTOP/tools/automation/shesh-power.service" "$UNIT_DIR/"
    fi
    ok "shesh-power installed (system script + udev rule + user service)"
  fi
  # shesh-ambient: python package + user units
  if [[ -f "$DESKTOP/tools/shesh-ambient/pyproject.toml" ]]; then
    run uv pip install --python "$VENV/bin/python" -e "$DESKTOP/tools/shesh-ambient"
    for f in "$DESKTOP"/tools/shesh-ambient/units/*; do
      [[ -f "$f" ]] || continue
      run cp "$f" "$UNIT_DIR/"
    done
    ok "shesh-ambient installed (package + timer/service)"
  fi
  # mcp-bundle upstreams (filesystem/fetch/git) — the bundle proxies these
  if command -v uvx >/dev/null 2>&1; then
    run uv tool install mcp-server-fetch mcp-server-git
    ok "mcp-bundle upstreams: fetch + git installed"
  else
    warn "uvx missing — fetch/git MCP bundles skipped"
  fi
  if command -v npx >/dev/null 2>&1; then
    run npm install -g @modelcontextprotocol/server-filesystem
    ok "mcp-bundle upstreams: filesystem installed"
  else
    warn "npx missing — filesystem MCP bundle skipped (install nodejs)"
  fi
else
  warn "shesh-desktop not found at $DESKTOP — automation tools (power/ambient) skipped"
fi

info "== 8. Ollama model stack (6GB VRAM) =="
if [[ $SKIP_AI -eq 0 ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    run sudo pacman -S --noconfirm --needed ollama
    run systemctl enable --now ollama 2>/dev/null || run sudo systemctl enable --now ollama
  fi
  MODELS=(phi4-mini qwen2.5-coder:3b moondream2 nomic-embed-text)
  for m in "${MODELS[@]}"; do
    run ollama pull "$m"
  done
  ok "models pulled: ${MODELS[*]}"

  # Ollama auth: force loopback binding + API-key proxy (Caddy) in front.
  run sudo pacman -S --noconfirm --needed caddy
  if [[ -f "$DESKTOP/tools/ollama-auth/setup-ollama-auth.sh" ]]; then
    run bash "$DESKTOP/tools/ollama-auth/setup-ollama-auth.sh"
    ok "ollama auth proxy installed (127.0.0.1:11435, key required)"
  else
    warn "setup-ollama-auth.sh not found in shesh-desktop — raw ollama stays loopback-only"
  fi
fi

info "== 9. Verification =="
[[ $DRY -eq 1 ]] && { info "[dry-run] verification skipped"; exit 0; }
fails=0
check() { if "$@" >/dev/null 2>&1; then ok "$*"; else warn "FAILED: $*"; fails=$((fails+1)); fi; }
check "$VENV/bin/python" -c "import tomllib"
check uv --version
for c in "$BIN_LINK"/shesh-*-mcp; do
  [[ -e "$c" ]] && check test -x "$c"
done
[[ -f "$UNIT_DIR/shesh-mcp.target" ]] && check test -f "$UNIT_DIR/shesh-mcp.target"
[[ -x /usr/local/bin/shesh-power.sh ]] && check test -x /usr/local/bin/shesh-power.sh
[[ -f /etc/udev/rules.d/99-shesh-power.rules ]] && check test -f /etc/udev/rules.d/99-shesh-power.rules
[[ $SKIP_AI -eq 0 ]] && check ollama list
if [[ $fails -gt 0 ]]; then die "$fails verification step(s) failed — see above"; fi
ok "Shesh stack installed. MCP config: ~/.config/shesh/mcp/servers.json"
