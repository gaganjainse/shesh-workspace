# github_auth.py + git_askpass.py — PAT loading without leaks

Status: living · last verified 2026-08-13
Sources: `tools/github_auth.py`, `tools/git_askpass.py`

Two small loaders, one contract: GitHub credentials are resolved at call time,
never stored in repo files, never printed.

## Resolution order (github_auth.py)

1. `GITHUB_PAT` / `GH_TOKEN` environment variables.
2. `~/.config/shesh/github.pat` — **must be mode 600**, a world-readable file
   is refused loudly (that failure, not the token, is what gets logged).
3. `gh auth login` session, if the GitHub CLI is authenticated.

## git_askpass.py

Git-native half: set `GIT_ASKPASS=tools/git_askpass.py` (plus
`GIT_TERMINAL_PROMPT=0`) and every `git fetch/push` over HTTPS is answered
from the same secure file — no credentials in remote URLs, no
`.git-credentials` on disk.

## Verified

- `make check` covers the loader; refusals and redaction are unit-tested.
- The fleet CI checkouts pass `persist-credentials: false` so runner-side
  tokens are not written to disk either (see [SECURITY](../../SECURITY.md)).
