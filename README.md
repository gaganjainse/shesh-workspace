>  **Superseded & archived** — this workspace-meta repo duplicated docs that already live in [shesh-ecosystem](https://github.com/gaganjainse/shesh-ecosystem) (`docs/`). Credentials are no longer stored here either (see the rotated fine-grained-PAT flow in `secrets/README.md`).

# shesh-workspace — session state, secrets relay, and workspace protocols

This repo is intentionally **small**. The 2026-08-12 renovation removed every
duplicate it carried (tools, scripts, manifests, swarm workflows, Containerfile,
stale audit snapshots) because those have exactly one canonical home:

| Concern | Canonical home |
| --- | --- |
| Swarm tooling, gates, CI, locks, docs | [gaganjainse/shesh-ecosystem](https://github.com/gaganjainse/shesh-ecosystem) |
| Components (23) | `shesh-*` repos via `manifests/components.toml` |
| Kernel (Rust) | [gaganjainse/SheshAOS](https://github.com/gaganjainse/SheshAOS) |
| Product docs site | [gaganjainse/shesh-docs](https://github.com/gaganjainse/shesh-docs) |

What stays here:

- `secrets/` — the encrypted PAT relay (`github.pat.enc`, 200k-iteration
  PBKDF2 + Fernet; decrypt via `shesh-ecosystem/tools/secure_pat.py`). Never
  commit plaintext tokens.
- `docs/` — workspace/session protocols that govern chat-tab work
  (SESSION_PROTOCOL, SESSION_HOP_ALERT, SWARM_STARTUP_GUIDE, TRAVEL_MODE,
  WORKSPACE_SEPARATION).

If you found a tool here you need: it lives in **shesh-ecosystem** now.
Nothing in this repo should ever drift from canonical again — there is
nothing left here that can.
