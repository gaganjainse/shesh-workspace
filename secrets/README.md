# Secrets — Encrypted PAT

This file `github.pat.enc` is the GitHub PAT encrypted with password via PBKDF2HMAC 200k + Fernet.

- **File:** `secrets/github.pat.enc` — JSON {salt, token, kdf} — 600 perms, safe to commit because encrypted, needs password to decrypt
- **Password:** User provides via ask_user UI (e.g., Gagan#2003) — never committed, never logged
- **Decrypt:** `python tools/secure_pat.py --prompt` or `GITHUB_PAT_PASSWORD="..." python tools/secure_pat.py --prompt` → writes `~/.config/shesh/github.pat` 600

**Flow for new clean workspace (foolproof):**
1. Fetch encrypted file from GitHub: `curl -s https://raw.githubusercontent.com/gaganjainse/shesh-workspace/main/secrets/github.pat.enc -o ~/.config/shesh/github.pat.enc && chmod 600 ~/.config/shesh/github.pat.enc`
2. Prompt for password via ask_user UI → decrypt → plain 600
3. `tools/github_auth.py --check` loads it

**Security:** Encrypted file is safe to commit (needs password), plain file is gitignored (.config/shesh/ in .gitignore), auto-deleted on handoff.

**If password compromised (e.g., in transcript), re-encrypt with new password:**
```bash
python tools/secure_pat.py --store "$(cat ~/.config/shesh/github.pat)" --password "NEW_STRONG_PASSWORD_NOT_IN_CHAT"
cp ~/.config/shesh/github.pat.enc secrets/github.pat.enc
git add secrets/github.pat.enc && git commit -m "chore: re-encrypt PAT with new password" && git push
```
