#!/usr/bin/env python3
"""Non-interactive GitHub HTTPS credential helper.

Git invokes this program only when it needs a username or password.  The
PAT is loaded through ``github_auth`` and is printed only to Git's stdin; it
is never placed in a remote URL, command line, or repository file.
"""

from __future__ import annotations

import pathlib
import sys

# Allow direct execution from the tools directory without installing a package.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import github_auth  # noqa: E402


def main() -> int:
    prompt = " ".join(sys.argv[1:]).lower()
    if "username" in prompt:
        print("x-access-token")
        return 0

    token = github_auth.load_pat()
    if not token:
        print("GitHub PAT unavailable", file=sys.stderr)
        return 1
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
