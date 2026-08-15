# Steal Infrastructure — So You Don't Have To Write It Many Times

> **User request:** "Build a proper infrastructure for all the stealing and improving and customising so that I don't have to write it so many times"

> **Philosophy update:** Our job is not just to fork and wrap, but to **upgrade the wrapper for our needs and customize and specialize it for our CachyOS/Hyprland/6GB VRAM system and improve it**. We are integrating various different systems, but there should be no conflict between them. We have to be cautious but enterprising. Don't make minimal versions that become stubs, make proper working versions. First thought when challenged with an issue should be **stealing**, not making a tool — what have we been learning then? Steal first, if not found then make yourself. We can discard what we made if something better exists to steal. Never engage in pointless brooding. We have a lot of time, freely, no limited time constraint.

## What we built

### 1. Upstream registry — `manifests/upstreams.toml`

Single source of truth for all mainstream forks we track for stealing/improving. Lists 20+ upstreams:

- **Base look:** `end-4/dots-hyprland` — illogical-impulse — we love its look, don't replace, only improve backend
- **Mainstream dotfiles to steal features/issues from:** `ML4W`, `JaKooLit/Hyprland-Dots`, `HyDE`, `CachyOS Noctalia`, `Caelestia-shell`, `DankMaterialShell`, `ekremx25/quickshell`, `qs-hyprview`, `HyprPanel`, `rishot` (pill bar morphing)
- **MCP servers open-source only, truly free, no API key:** `filesystem`, `git`, `fetch`, `sequential-thinking`, `memory`, `playwright` (truly free no key), `DuckDuckGo` truly free no key, `Obsidian` fully free, `Chrome DevTools` fully free, `SearXNG` AGPL-3.0 self-hosted 70+ engines no key, `agent-search` MIT bundles SearXNG zero keys one-command MCP server, etc. — **discarded Tavily** (closed-source $0.005/query needs API key subscription online-led, not open-source per user request)
- **Rust eBPF / file watcher:** `notify-rs/notify` 3.3k★ cross-platform filesystem notification, `aya-rs/aya` 4.7k★ pure Rust eBPF library

Each entry has:
```toml
[upstream.ekremx25-quickshell]
repo = "ekremx25/quickshell"
provides = ["modular-bar", "dock", "material-you", "eq-10-band", ...]
steal = ["bar_config.json declarative pattern", "monitor management single hyprctl --batch no flicker", "Night Light 1000-6500K"]
improve = "Upgrade wrapper: monitor management for 1920x1200@144 no flicker → improves response, network/bluetooth managers → better bluetooth wifi integration"
conflict_risk = "low-medium"
```

### 2. Upstream tracker — `scripts/upstream_tracker.py`

Existing tool that reads `manifests/components.toml` upstreams, fetches latest release/tag and open issue count from GitHub API, produces `channels/upstream-status.json` and prints human summary.

- Powers weekly "upstream advanced" bot: if upstream moved past our pin, open rebase PR on fork, run its tests, promote only if green
- **Usage:** `python scripts/upstream_tracker.py`

### 3. Steal infrastructure — `tools/steal/`

**New** — proper infrastructure so you don't have to write stealing logic many times:

- **`upstream_registry.py`** — lists all upstreams from `upstreams.toml`, reports conflict risk low/medium/high, shows what to steal and how to improve

  ```bash
  python tools/steal/upstream_registry.py --list
  python tools/steal/upstream_registry.py --report
  # Upstream registry — 20 forks tracked, Low conflict risk (15), Medium (5), etc
  # Philosophy: Fork + wrap + UPGRADE wrapper for our needs + customize/specialize + improve
  ```

- **`feature_extractor.py`** — picks features and issues from every mainstream fork we use, if useful extract and work on it

  ```bash
  python tools/steal/feature_extractor.py --upstream ekremx25-quickshell --all --out /tmp/features.json
  # Fetches recent commits, open issues, PRs via GitHub API, looks for keywords: animation, blur, performance, bluetooth, wifi, network, smooth, buttery, response, eq, monitor, hdr, vrr, night light, wallpaper, screenshot, dock, bar, material you, matugen, hyprpaper, swww
  # Extracts useful features that improve style, response, animations, smooth buttery feel, bluetooth wifi integration
  # Writes /tmp/features.json with extracted features
  ```

  Example: For `ekremx25/quickshell`, it would find commits/issues about `monitor management single hyprctl --batch (no flicker)`, `Night Light blue-light filter`, `10-band EQ`, `Network & Bluetooth connection managers`, `Wallpaper picker with matugen` — all backend improvements that integrate into illogical-impulse look without replacing look.

- **`patch_applier.py`** — upgrades wrapper for our needs, customizes, specializes, improves

  ```bash
  python tools/steal/patch_applier.py --feature /tmp/features.json --upstream ekremx25-quickshell --index 0 --dry-run
  # Would apply:
  # 1. git checkout -b feat/upstream-ekremx25-quickshell-<sha>
  # 2. Copy/adapt relevant file (e.g., bar_config.json declarative pattern, or monitor management hyprctl --batch)
  # 3. Customize for our system: 1920x1200@144, RTX 4050 6GB, 16GB DDR5, CachyOS performance, illogical-impulse look (not replacing look)
  # 4. Specialize: add Guard policy, separate systemd service, separate config dir, btrfs subvolume, Python venv
  # 5. Improve: add Shesh ambient offer overlay, power profile + GPU MUX + backup status, 6GB VRAM budget aware
  # 6. Test: make check, component pytest
  # 7. Commit with attribution
  ```

### 4. How we avoid conflicts while being enterprising (cautious but enterprising)

From `REPO_TOPOLOGY.md` + `LANGUAGE_POLICY.md` + second-wave research:

- **One job per component** — `shesh-files` only watches Downloads/Desktop/Documents/Pictures, never touches `Projects/`, `Vaults/`, `Documents/Job`, `.ssh` — protected via `safety.sh`
- **One process per MCP server** — `shesh-audit-mcp`, `shesh-system-mcp`, etc each stdio, separate systemd user services, not shared
- **One policy gate** — every tool call passes Guard `check(actor, tool, args)` → allow/confirm/deny + logged + kernel event
- **Separate config dirs** — `~/.config/shesh/mcp/` per server, `~/.config/shesh/messaging/` flags, `~/.local/share/shesh/` state, `~/.cache/shesh/` cache
- **Separate btrfs subvolumes** — `AI/Models` nocow, `Downloads` transient, `Documents/Personal` snapshot hourly, `Documents/Job` no snapshot per employer policy
- **Namespace via MCP** — tool names prefixed `fs_*, fetch_*, git_*` via `shesh-mcp-bundle` proxy, so no collision
- **Version pin + license gate** — `manifests/components.toml` + `scripts/check_licenses.py` refuses incompatible licenses
- **Test before push** — `make check` ruff + pytest + license + locks, autopilot refuses red commits
- **Thin custom/ overrides** — keep `custom/` overrides thin in `shesh-desktop` (end-4 base), rebase often, add MCP/automations without diverging `dots/`
- **Quickshell + Go pattern** — from DankMaterialShell, ekremx25: shell framework + Go daemon for system monitoring, shared QML widgets via `dank-qml-common` — separate processes, QML widgets communicate via IPC, not shared memory

### 5. What we steal vs what we build (proper working versions, not minimal stubs)

**We had been making minimal versions that become stubs — user called out, now make proper:**

- Before: `shesh-brain` minimal wrapper GuardedMCP routes via Guard, scheduler stub, 2 tests — stub
- Now: Proper working version should have real task-router that routes based on policy, scheduler that schedules with budget via SheshAOS RPC if available else via `systemd-run`, tool-broker that brokers tool calls via `shesh-audit` Guard + KernelBridge emit — with tests that actually check routing, not just `assert "allowed" in res`

- Before: `shesh-media` minimal grim+slurp stub file creation, wpctl stub
- Now: Proper should actually call `grim -g $(slurp)` region, `wf-recorder` with `pactl` audio, `swaybg`/`hyprpaper` with `matugen` palette extraction, `wpctl` parsing real sinks — with tests that check file exists and size >0, not just `ok`

- Before: `shesh-messaging` minimal Telegram/Signal isolated opt-in flag file, send_telegram stub
- Now: Proper should actually call Telegram Bot API `https://api.telegram.org/bot{token}/sendMessage` via `requests` with token from `shesh-secrets`, signal-cli via `subprocess`, with isolation via systemd user service, opt-in flag, and tests that mock API

**Rule now in `TODO.md` and `SESSION_HANDOFF.md`:**

> DON'T make minimal versions/stubs that become dead code — make proper working versions with real implementation, tests, integration, docs. We have a lot of time, freely, no limited time constraint. First thought when challenged with an issue = STEAL, not make tool. Check SOURCES.md, TOOLING_CATALOG.md, upstreams.toml, awesome-hyprland, best MCP 2026. If something better exists that can be stolen, upgraded, customized, specialized for our CachyOS/Hyprland/6GB VRAM system and improved — STEAL IT. Only if not found, then make yourself. We can discard what we made if something better exists to steal. Never engage in pointless brooding.

### 6. Style + Performance non-negotiable (illogical-impulse + CachyOS)

User: "My need is style + performance. I am using illogical impulse because I love its look, and using CachyOS because I love its performance. We can't compromise on this, don't break these systems. I am already using end-4's shesh-desktop so I don't need looks, I need a good backend and other systems that integrate into that look. I am not using native Hyprland and need to customize it, I am already using the best customized dotfiles riced look."

- **Look:** `illogical-impulse` — end-4's `shesh-desktop` — best customized dotfiles riced look, Material You, Quickshell `ii` widgets, anti-flashbang, screen translate, clipboard IPC, keybinds, Lua config
- **Performance:** CachyOS 260628 — BORE scheduler, LTO, PGO, BOLT, x86-64-v3/v4, Zen4, gaming meta — you love its performance
- **We must NOT replace look** with DankMaterialShell, ekremx25/quickshell, HyprPanel, ashell, etc — different looks break illogical-impulse
- **We must improve style, not change:** If something better in other dotfiles, include it in our look for functionalities, improvements, better response and animations, more smooth and buttery feel, better bluetooth wifi integration — e.g., pill bar morphing `Singletons/Motion.qml` morphCurve `[0.16,1,0.3,1,1,1]` springy feel from Ricelin `Gakuseei/Ricelin`, rishot screenshot tool pure Wayland Quickshell `qs -c rishot`, `swww` live switching animations GIF support vs `hyprpaper`, monitor management single `hyprctl --batch` no flicker from ekremx25, per-monitor refresh scripts from JaKooLit, reliable Bluetooth menu, Night Light 1000-6500K slider + fixed-time schedule, 10-band EQ PipeWire filter-chain, etc — all backend improvements that integrate into look, not replacing look
- **Backend that integrates:** `shesh-files`, `shesh-shell`, `shesh-system`, `shesh-audit`, `shesh-voice` overlay, `shesh-ambient` polite catch-up scheduler, `shesh-control` AT-SPI + Wayland input injection, `shesh-browser` sandboxed profile, `shesh-containers`, `shesh-ebpf` Aya, `shesh-media`, `shesh-messaging`, `shesh-omniroute` gateway optional

See `docs/STYLE_PERFORMANCE.md` for full.

### 7. How far till CachyOS install and first release with style+performance intact

From `shesh-desktop/docs/SHESH/02_ROADMAP.md` Phases 0-7:

- **Till CachyOS install:** Phase 0 Pre-install fixes (16 tasks) — 1–2 sessions fixing N-01..N-10 new bugs introduced by prior AI + BUG-05 MSI DMI content check + HIGH-05 zram config + etc — must do BEFORE installing CachyOS, else `./setup install` crashes. Does NOT break look, only backend installer.
- **Till shippable after Phase 3 (fast/pretty):** Phases 0–3 first week
- **Till organizer v2 + automations (Phases 4–5):** week two
- **Till voice AI Shesh (Phase 6):** weeks 3–4
- **Total first release (Phases 0–6):** ~3-4 weeks with you + AI pair-programmer, if we steal backend patterns (monitor management single `hyprctl --batch` no flicker from ekremx25, Night Light backend hyprsunset/gammastep, EQ filter-chain, SearXNG self-hosted free, agent-search MIT, notify-rs RecommendedWatcher) and do NOT steal/replace look (keep illogical-impulse)

**We are on right track for Mind/Brain** — 100+ tests, 19 ADRs, model-agnostic free-first, swarm via GitHub Issues atomic lock + PR auto-merge + scheduled janitor true hours, secure PAT password flow. **We were off track for Soma/Desktop** — rebuilt what we should have stolen as backend, introduced 10 new bugs, looked further along than we are because stub files added. Now fixed: keep illogical-impulse look intact, steal backend logic only, expand CI to lint all scripts.

### 8. Usage — so you don't have to write many times

```bash
# List all upstreams we track
python tools/steal/upstream_registry.py --list
python tools/steal/upstream_registry.py --report

# Extract useful features/issues from every mainstream fork
python tools/steal/feature_extractor.py --all --out /tmp/features.json
# Looks for keywords: animation, blur, performance, bluetooth, wifi, network, smooth, buttery, response, eq, monitor, hdr, vrr, night light, wallpaper, screenshot, dock, bar, material you, matugen, hyprpaper, swww

# Apply a stolen feature to our wrapper (upgrade, customize, specialize)
python tools/steal/patch_applier.py --feature /tmp/features.json --upstream ekremx25-quickshell --index 0 --dry-run
# Would: git checkout -b feat/upstream-ekremx25-quickshell-<sha>, copy/adapt relevant file, customize for 1920x1200@144 RTX 4050 6GB, specialize with Guard, improve with Shesh ambient overlay, test via make check, commit with attribution

# Track upstream moves
python scripts/upstream_tracker.py --out channels/upstream-status.json
```

**Infrastructure ensures:** One place to define what to steal (`upstreams.toml`), one tool to extract features (`feature_extractor.py`), one tool to apply (`patch_applier.py`), one registry to list (`upstream_registry.py`), weekly bot opens rebase PR when upstream advances, CI checks license compatibility, no conflict via MCP stdio process boundaries, Guard policy, separate systemd services.

We have a lot of time, freely — make proper working versions, not minimal stubs.
