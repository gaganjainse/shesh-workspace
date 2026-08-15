# Self-Hosted Update Mirror (P2 Future, now minimal)

> Future: self-hosted update mirror — P2

## Concept

- Instead of pulling component releases directly from GitHub (rate limited, needs internet), host a mirror on local network or VPS
- Mirror syncs via `tools/mirror_sync.py` from `manifests/components.toml` — fetches latest tags, verifies sigstore provenance, stores in `/srv/shesh-mirror/`
- Desktop installer `tools/install.sh --mirror http://mirror.local` installs from mirror, not GitHub

## Minimal Implementation (P2 done)

- Script `tools/mirror_sync.py` — fetches component repos, verifies SHA256 from locks, writes to local dir
- Config `~/.config/shesh/mirror.conf` — `mirror_url=http://mirror.local` or `file:///srv/shesh-mirror`

## Usage

```bash
# Sync mirror (run on mirror host)
python tools/mirror_sync.py --channel canary --out /srv/shesh-mirror

# Install from mirror (on MSI)
tools/install.sh --channel canary --mirror http://mirror.local

# Verify provenance
python scripts/sign_artifacts.py --check --artifacts /srv/shesh-mirror/*
```

## Status: P2 done minimal — docs + script placeholder, full mirror infra future
