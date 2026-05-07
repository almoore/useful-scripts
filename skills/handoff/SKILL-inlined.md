---
name: handoff
description: >
  Write a session handoff to .claude/session-handoff.md so the next Claude
  Code session can pick up where this one left off. File rotation is fully
  automated — never ask the user about it.
---

# Session Handoff

> Self-contained variant: the rotation script is embedded as a heredoc, so
> this single SKILL.md is all you need (no separate `rotate.sh` to install).

## Step 1 — Rotate (silent, no user interaction)

Run the embedded rotation script via a single Bash call. It deletes the
oldest, shifts the rest up, and frees `.claude/session-handoff.md` for
the new write. Do NOT discuss rotation with the user, do NOT ask which
files to keep, and do NOT run mv/rm yourself.

If `$CLAUDE_PROJECT_DIR` isn't set, the script falls back to
`$PWD/.claude`. Override either by passing the directory as the first
argument or by setting `KEEP=N` to keep more than the default 3 slots.

```bash
bash -s -- <<'ROTATE_HANDOFF_EOF'
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
# Always idempotent and silent on success. Errors go to stderr, exit 1.

set -euo pipefail

DIR="${1:-${CLAUDE_PROJECT_DIR:-$PWD}/.claude}"
KEEP="${KEEP:-3}"

if [ ! -d "$DIR" ]; then
    echo "rotate: directory not found: $DIR" >&2
    exit 1
fi

if [ "$KEEP" -lt 2 ]; then
    echo "rotate: KEEP must be >= 2 (got $KEEP)" >&2
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
ROTATE_HANDOFF_EOF
```

The script is silent on success. Only mention it if it exits non-zero.

## Step 2 — Gather context

In parallel:
- `git status` and `git log -10 --oneline` to catch every file touched and
  every commit made this session.
- Read `.claude/session-handoff-1.md` (the handoff that just got rotated out
  of the active slot) to preserve any pending items that didn't get resolved
  this session.

## Step 3 — Write the new handoff

Write to `.claude/session-handoff.md`. Cover:

- **Session summary** — one paragraph: what was the focus, what shifted
- **Files modified this session** — table: file | one-line change | commit (if any)
- **Commits this session** — short hash + subject line
- **Current state** — positions, balances, in-progress work, branch state
- **First actions next session** — the exact next step, ordered, with file paths
  and commands ready to copy
- **Pending from prior sessions** — items lifted from `session-handoff-1.md`
  that are still unresolved
- **Gotchas / learnings** — non-obvious things discovered, with commit refs
- **Market state at handoff** (if a trading session) — key prices and dates

Use the date and time from the UserPromptSubmit hook context, not your
training cutoff.

## Step 4 — Confirm and stop

Brief one-line confirmation: "Handoff written to .claude/session-handoff.md".
Do not summarize what you wrote — the user can read the file.
