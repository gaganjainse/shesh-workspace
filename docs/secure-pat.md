# secure_pat.py — password-encrypted GitHub PAT at rest

Status: living · last verified 2026-08-13
Source: `tools/secure_pat.py` · Loader: [github-auth](github-auth.md)

The PAT never sits in a repo, transcript, or world-readable file. It is stored
encrypted under a password only the owner knows.

## Layout

| File | Mode | Purpose |
|---|---|---|
| `~/.config/shesh/github.pat.enc` | 600 | encrypted PAT (PBKDF2HMAC, 200k iterations, Fernet) — survives sessions |
| `~/.config/shesh/github.pat` | 600 | decrypted plain PAT, deleted on handoff |

## Flow

1. New session: guard detects `enc` present, `plain` missing → `NEED_PASSWORD`.
2. The agent asks for the password through the UI (never in a chat message).
3. `secure_pat.py` decrypts to the plain file, mode 600.
4. `tools/github_auth.py` / `tools/git_askpass.py` load from there, redacted.

## Commands

```bash
python tools/secure_pat.py --prompt        # decrypt via hidden password prompt
python tools/secure_pat.py --handoff       # delete plain, keep enc
python tools/github_auth.py --check        # verify load + redaction
```

## Rules

- Never echo the PAT or password; tools print redacted length only.
- The plain file existing world-readable is treated as compromise: rotate.
- Rotation after the 2026-08-11/12 transcript exposures remains an **owner
  action** tracked in TODO.md.
