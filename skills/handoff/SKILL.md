---
name: handoff
description: >
  Write a session handoff to .claude/session-handoff.md so the next Claude
  Code session can pick up where this one left off. File rotation is fully
  automated — never ask the user about it.
---

# Session Handoff

## Step 1 — Rotate (silent, no user interaction)

Run the rotation script. It deletes the oldest, shifts the rest up, and frees
`.claude/session-handoff.md` for the new write. Do NOT discuss rotation with
the user, do NOT ask which files to keep, and do NOT run mv/rm yourself.

```bash
bash "$HOME/.claude/skills/handoff/rotate.sh"
```

If `$CLAUDE_PROJECT_DIR` isn't set, pass the project's `.claude/` directory
explicitly: `bash "$HOME/.claude/skills/handoff/rotate.sh" /path/to/.claude`.

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
