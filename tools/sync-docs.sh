#!/usr/bin/env bash
# Sync all docs to the shesh-docs repo (mdbook) — properly organised.
#
# Architecture: the book tree under src/ is a PURE PROJECTION of canonical
# sources. All real work — the explicit mirror map, fissions (Manual
# Verification → task chapters, OmniRoute study → free providers), generated
# pages (manifest/models/components), link translation, and the orphan sweep
# that deletes anything neither generated nor declared book-owned — lives in
# tools/book_build.py. This wrapper only prepares the checkout and calls it.
#
# Failure policy: REQUIRED sources abort the sync loudly (book_build exits
# non-zero; set -e propagates); OPTIONAL sources print SKIPPED lines. No copy
# may fail invisibly — that is how stale docs happen.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_REPO="${DOCS_REPO:-/tmp/shesh-docs}"
export DOCS_REPO
export SRC_ROOT="${SRC_ROOT:-$(cd "$ROOT/.." && pwd)/src}"

echo "Syncing docs to $DOCS_REPO ..."

# Clone docs repo if not exists
if [ ! -d "$DOCS_REPO" ]; then
    echo "Cloning shesh-docs to $DOCS_REPO"
    git clone --depth 1 https://github.com/gaganjainse/shesh-docs.git "$DOCS_REPO"
fi

python3 "$ROOT/tools/book_build.py" "$@"

echo "Sync complete — $(find "$DOCS_REPO/src" -type f | wc -l) files in $DOCS_REPO/src"
if command -v mdbook >/dev/null 2>&1; then
    (cd "$DOCS_REPO" && mdbook build) && echo "mdbook build: PASS"
else
    echo "NOTE: mdbook not installed locally; CI runs the render gate"
fi
echo "Next: commit + push inside $DOCS_REPO (agents use the graft-safe push loop)."
