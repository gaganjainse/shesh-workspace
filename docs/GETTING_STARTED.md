# Getting Started — Shesh on CachyOS/Hyprland

> For MSI Sword 16 HX B14VEKG (i7-14700HX, RTX 4050 6 GB, 1920×1200@144, 16 GB DDR5) but works on any Arch. You need CachyOS 260628 + Hyprland ≥0.55 + Quickshell.

## 0. One-command quick start (developer, no hardware)

```bash
git clone https://github.com/gaganjainse/shesh-ecosystem.git
cd shesh-ecosystem
make check        # ruff + 30 tests + license gate + regenerate locks — must be green
python -m pytest tests/ -q
```

## 1. Full install on CachyOS (MSI laptop)

### 1.1 Bootstrap the desktop (existing dotfiles)

This reuses the battle-tested end-4 base + Shesh overlay:

```bash
bash <(curl -s https://raw.githubusercontent.com/gaganjainse/shesh-desktop/main/tools/bootstrap.sh)
# Script does:
# - Installs Hyprland, Quickshell, matugen, greetd/regreet, pacman hooks
# - Clones shesh-desktop to ~/Workspace/shesh-desktop
# - Symlinks dots/ into the end-4 layout, custom/ overrides thin
# - Enables shesh systemd units (ambient, file watcher, hyprland-control)
```

Reboot, log into Hyprland, check:

```bash
hyprctl version
hyprctl monitors          # should show 1920x1200@144
wpctl status              # audio sinks/sources
```

See `docs/MANUAL_VERIFICATION.md` §0 for first-boot checklist.

### 1.2 Ollama + 6 GB model stack

```bash
sudo pacman -S ollama
systemctl --user enable --now ollama

ollama pull phi4-mini              # primary/planner/researcher/critic
ollama pull qwen2.5-coder:3b       # coder
ollama pull moondream2             # vision
ollama pull nomic-embed-text       # embeddings/RAG

# Optional: list loaded
ollama ps
```

`shesh-mind` budgets VRAM — one model resident at a time, 5.5 GB ceiling. Check `watch nvidia-smi`.

### 1.3 Rust + uv + Podman

```bash
# Rust (only if you touch SheshAOS kernel; otherwise CI has it)
# Do NOT install in sandbox — heavy (~1 GB)

# uv for Python
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version

# Rootless Podman
sudo pacman -S podman buildah
podman info  # should show rootless
podman run --rm alpine echo ok

# Distrobox for exotic runtimes
sudo pacman -S distrobox
```

See `docs/CONTAINERS_AND_VENV.md`.

### 1.4 Shesh components (pipx, not pip)

We use pipx for isolated MCP binaries:

```bash
# From shesh-ecosystem
python scripts/generate_mcp_config.py --channel canary
cat ~/.config/shesh/mcp/servers.json   # 9 servers

# Install each component (example)
for repo in shesh-audit shesh-mind shesh-memory shesh-orchestrator shesh-skills \
            shesh-system shesh-shell shesh-files shesh-backup shesh-phone \
            shesh-containers shesh-mcp-bundle shesh-calendar shesh-acp shesh-secrets; do
  echo "=== $repo ==="
  pipx install git+https://github.com/gaganjainse/$repo.git --force
done

# Verify
for s in shesh-{audit,system,shell,files,skills,memory,mind,harness,orchestrator,backup,phone,containers,secrets,calendar,acp}-mcp; do
  command -v "$s" && echo "ok  $s" || echo "MISSING $s"
done
```

If you prefer uv:

```bash
uv tool install git+https://github.com/gaganjainse/shesh-audit.git
```

### 1.5 Voice (shesh-voice / Newelle fork)

```bash
git clone https://github.com/gaganjainse/shesh-voice.git
cd shesh-voice
# Native build (not Flatpak)
meson setup build
meson compile -C build
sudo meson install -C build

# Overlay MCP config
mkdir -p ~/.config/Newelle
cp shesh-overlay/shesh-mcp-servers.json ~/.config/Newelle/mcp-servers.json

# Launch
newelle
# In Newelle settings:
# - Provider: Ollama -> phi4-mini (localhost:11434)
# - Wake word: openwakeword, phrase "hey shesh"
# - STT: faster-whisper
# - TTS: Piper
```

Check Muse's MCP panel — should show 9 servers green.

### 1.6 Secrets (no keys in config)

```bash
pipx install git+https://github.com/gaganjainse/shesh-secrets.git
shesh-secrets-mcp  # then in any MCP client:

# Env backend (simplest)
export MY_TOKEN=xxx
shesh-secrets-mcp -> get_secret("env:MY_TOKEN")

# gopass
gopass insert shesh/backup  # restic password
get_secret("gopass:shesh/backup")

# KeepassXC
# File (0600 only, refuses world-readable)
echo "secret" > ~/.config/shesh/my.key
chmod 600 ~/.config/shesh/my.key
get_secret("file:~/.config/shesh/my.key")
```

Never commit a key. Run `git secrets --scan` or `truffleHog`.

### 1.7 Backup (restic, real)

```bash
sudo pacman -S restic
restic -r /srv/shesh-backup init   # or gdrive/s3 via rclone

# Store password via shesh-secrets
# Configured in shesh-backup as env:RESTIC_PASSWORD or gopass:shesh/backup

shesh-backup-mcp -> run_backup
restic -r /srv/shesh-backup snapshots

# Test restore to temp dir before trusting
mkdir /tmp/restore-test
restic -r /srv/shesh-backup restore latest --target /tmp/restore-test
```

Set a systemd timer for daily:

```bash
systemctl --user enable --now shesh-backup.timer
```

### 1.8 Phone (Realme Narzo 90x, ADB)

```bash
sudo pacman -S android-tools
# On phone: Developer Options -> USB debugging ON

adb devices  # should list device
pipx install git+https://github.com/gaganjainse/shesh-phone.git
shesh-phone-mcp
# Try safe tap:
# tap at 500,500 — allowed (inside safe area)
# tap at 10,10 — denied (status bar protected)
```

### 1.9 Container sandbox

```bash
shesh-containers-mcp -> run_sandboxed(["echo","hi"])
# Should return "hi" with no network (--network=none) and --cap-drop=ALL
podman run --rm alpine echo ok  # manual check
```

---

## 2. Everyday use

### Voice

- Say "hey shesh" → speak goal: "organize my Downloads by type, allow"
- Newelle shows plan (planner), delegates to coder/researcher, critic approves, then asks confirmation for file moves.

### Memories & habits

```bash
shesh-memory-mcp -> recall("my backup habit")
shesh-memory-mcp -> semantic_search("how do I greet users?")
# Habits learned: check ~/.local/share/shesh/memory/habits.md
```

### Sessions (background)

```bash
shesh-orchestrator-mcp -> start_session(goal="refactor all ...", use_llm=true)
# Disconnect, work on other things
shesh-orchestrator-mcp -> get_session(id)
shesh-orchestrator-mcp -> list_sessions
shesh-orchestrator-mcp -> cancel_session(id)  # actually stops loop
```

### Traces

```bash
shesh-orchestrator-mcp -> recent_traces(limit=5)
cat ~/.local/share/shesh/traces/*.jsonl | jq .
```

---

## 3. Canary & promotion flow

```bash
# Daily canary (runs in CI): boots all 16 components in containers
bash scripts/e2e-canary.sh

# If green on your MSI, promote:
git checkout -b promote/canary-$(date +%Y%m%d)
make check
git add channels/ && git commit -m "chore: promote canary $(date -I)"
# Open PR -> merge -> stable after btrfs snapshot

# Switch channels (installer with snapshot+rollback):
curl -fsSL https://raw.githubusercontent.com/gaganjainse/shesh-ecosystem/main/tools/install.sh | bash -s -- --channel canary
# Installer does:
# btrfs subvolume snapshot / /@snapshots/pre-shesh-canary-$(date +%Y%m%d)
# pipx upgrade all shesh-* from canary.lock
# If boot fails -> select snapshot in grub-btrfs
```

---

## 4. Hardware checks (must on MSI)

Run through `docs/MANUAL_VERIFICATION.md` top-to-bottom. Key:

- Hyprland@144, NVIDIA MUX `nvidia-smi`, wake word, PipeWire `wpctl`, Quickshell render pink check, backup restore, phone safe-area, podman rootless, Newelle MCP green.

One-command health:

```bash
echo "=== Shesh health ===" && \
systemctl --user is-active ollama && \
bash ~/src/shesh-ecosystem/scripts/e2e-canary.sh && \
for s in shesh-{audit,system,shell,files,skills,memory,mind,harness,orchestrator,backup,phone,containers,secrets,calendar,acp}-mcp; do
  command -v "$s" >/dev/null && echo "ok  $s" || echo "MISSING  $s"
done && \
echo "=== done ==="
```

---

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: mcp` | `pipx install mcp fastmcp` and `pip install -e ./src/shesh-*` |
| Hyprland keybinds missing | `cd ~/Workspace/shesh-desktop && git pull && ./dots/.config/hypr/install.sh` |
| Quickshell pink placeholders | `quickshell --reload`, check QML log `journalctl --user -u quickshell` |
| Newelle MCP red | `cat ~/.config/shesh/mcp/servers.json`, verify `shesh-*-mcp` in PATH |
| Ollama OOM | `shesh-mind-mcp -> list_installed_models`, `ollama ps`, unload with `ollama stop` |
| Backup fails | `restic check`, password backend `shesh-secrets-mcp -> get_secret` |
| Podman rootless fails | `podman system migrate`, `loginctl enable-linger $USER` |
| Audit log tampered | `shesh-audit-mcp -> verify_integrity()` — shows broken hash chain |
| Workspace over budget | `rm -rf ~/.cargo ~/.rustup ~/.cache __pycache__ */__pycache__ .pytest_cache` |

---

## 6. Next steps

- Read `docs/SESSION_HANDOFF.md` for P1 list.
- Read ADRs in `docs/adr/` (15 decisions).
- Pick a todo from `TODO.md` — highest ⬜ not blocked.
- Run autopilot: `python -m tools.autopilot.cli run` — it loops: implement → gate → safe commit → push.

Welcome to Shesh — an agent that is a body, not a chatbot.
