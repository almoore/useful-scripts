#!/usr/bin/env bash
# Rotate session-handoff files in .claude/ to keep the last N sessions.
#
# Pattern (default N=3):
#   session-handoff.md     ← current / newest (becomes session-handoff-1.md)
#   session-handoff-1.md   ← previous       (becomes session-handoff-2.md)
#   session-handoff-2.md   ← oldest kept    (deleted)
#
# After rotation, session-handoff.md does not exist — the caller writes
# the new handoff into that path.
#
# Timestamped archive files (session-handoff-YYYY-MM-DD*.md) are left
# untouched.
#
# Usage:
#   rotate.sh                    # uses $CLAUDE_PROJECT_DIR/.claude or cwd/.claude
#   rotate.sh /path/to/.claude   # explicit dir
#   KEEP=5 rotate.sh             # keep last 5 (handoff + handoff-1..4)
#
# Always idempotent and silent on success. Errors go to stderr, exit 1.

set -euo pipefail

DIR="${1:-${CLAUDE_PROJECT_DIR:-$PWD}/.claude}"
KEEP="${KEEP:-3}"

if [ ! -d "$DIR" ]; then
    echo "rotate.sh: directory not found: $DIR" >&2
    exit 1
fi

if [ "$KEEP" -lt 2 ]; then
    echo "rotate.sh: KEEP must be >= 2 (got $KEEP)" >&2
    exit 1
fi

cd "$DIR"

OLDEST=$((KEEP - 1))

# Step 1: delete the oldest kept slot if it exists.
if [ -f "session-handoff-${OLDEST}.md" ]; then
    rm -f "session-handoff-${OLDEST}.md"
fi

# Step 2: shift each numbered file up by one (oldest → newest).
i=$((OLDEST - 1))
while [ "$i" -ge 1 ]; do
    src="session-handoff-${i}.md"
    dst="session-handoff-$((i + 1)).md"
    if [ -f "$src" ]; then
        mv "$src" "$dst"
    fi
    i=$((i - 1))
done

# Step 3: promote the current handoff to slot 1.
if [ -f "session-handoff.md" ]; then
    mv "session-handoff.md" "session-handoff-1.md"
fi

exit 0
