---
name: jira-create
description: >
  Create a new Jira Cloud issue (CCAOA tenant by default). Use when the
  user asks you to file, open, log, create, draft, or "make a Jira" for
  a new ticket, bug, task, or epic. Wraps the existing jira_create_issue.py
  CLI in useful-scripts; for "epic + N tasks" bulk creation, points to
  jira_create_epic_with_tasks.py in the same directory. Handles auth via
  the shared atlassian_auth helper. Do not invoke for reading (use
  jira-get) or searching (use jira-read).
---

# Jira — create issue

## When to invoke

Any of:
- User asks to "create / file / open / draft / log / make / cut a Jira ticket for X".
- User describes a bug or task and asks for a ticket to track it.
- User wants to bulk-create an epic plus several child tasks.

Do **not** invoke for:
- Reading an existing issue → use `jira-get`.
- Searching → use `jira-read`.
- Adding a comment / note to an existing issue → use `jira-comment`.
- Updating an existing issue (transition, edit fields) — no skill yet;
  drop to raw REST `PUT /rest/api/3/issue/{key}` or the transitions endpoint.

## Auth

Same `atlassian_auth` / `jira_auth` helpers used elsewhere.
`~/.atlassian-conf.json` + macOS-keyring token. The `jira_create_issue.py`
script wires the auth itself; you just pass `--profile` if you need a non-default profile.

## The fast path — `jira_create_issue.py`

The script already exists in useful-scripts. Do not reimplement.

```bash
SCRIPT=/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/jira_create_issue.py

# Minimal — summary on argv, description piped on stdin
echo "Long description here" | python3 "$SCRIPT" CLOUDOPS "Short summary"

# Description from a file
python3 "$SCRIPT" CLOUDOPS "Short summary" --description-file ticket.txt

# Description as a literal string
python3 "$SCRIPT" CLOUDOPS "Short summary" --description "One line desc"

# Pick issue type, labels, assignee, priority
python3 "$SCRIPT" CLOUDOPS "Short summary" --description-file t.txt \
    --issue-type Task --label dr --label rancher \
    --assignee jdoe --priority High

# Attach to an epic / parent
python3 "$SCRIPT" CLOUDOPS "Short summary" --description-file t.txt \
    --parent CLOUDOPS-456

# Discover valid issue types for a project before committing
python3 "$SCRIPT" CLOUDOPS --list-issue-types

# Dry-run — print the JSON payload without creating
python3 "$SCRIPT" CLOUDOPS "Short summary" --description-file t.txt --dry-run

# Verbose — also print the browse URL after the new key
python3 "$SCRIPT" CLOUDOPS "Short summary" --description-file t.txt --verbose
```

The script prints the new issue key on success (e.g. `CLOUDOPS-1234`).
Exit codes: `0` success, `1` API/JIRAError, `2` missing required arg.

## Before creating

- **`--list-issue-types` once per unfamiliar project.** Projects vary on
  whether they expose `Task` vs `Story` vs `Sub-task` vs custom types.
  Default is `Task`.
- **`--dry-run` first when the description has formatting.** The script
  posts via the `jira` Python package against v2, which expects **wiki
  markup** (`h1.`, `*`, `{code}`) — not Markdown. If the user wrote
  Markdown, either convert or accept that formatting will flatten.
- **Verify `--parent` exists** when chaining to an epic. Most workflows
  will surface a JIRAError on a bad parent; some silently drop it. A
  quick `jira-get <parent>` confirms.
- **Assignee format.** Cloud expects `accountId` (long opaque string,
  contains `-`); the script falls back to `name` for legacy when the
  value looks short. If you have a display name, look up the accountId
  via `jira-read --jql "..." --fields assignee --format json` first.

## Bulk create — `jira_create_epic_with_tasks.py`

Same directory:
`/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/jira_create_epic_with_tasks.py`

For "create an epic and N tasks under it" workflows. Read its `--help`
before invoking; it consumes a spec describing the epic + children. Use
this rather than looping `jira_create_issue.py` N times — it's faster
and keeps the parent-link wiring consistent.

## Useful endpoints (raw HTTP, v3)

For cases the wrapper script doesn't cover (ADF descriptions, transitions,
linking after create):

```python
import sys, os
for p in (
    os.path.join(os.environ.get("DEVOPS_SCRIPTS_DIR", ""), "lib"),
    "/Users/alexmoore/repos/github.com/almoore/useful-scripts/python",
):
    if p and os.path.isdir(p):
        sys.path.insert(0, p)
from atlassian_auth import get_auth
import requests

url, user, token = get_auth()
auth = (user, token)

# v3 — create with ADF description
requests.post(f"{url}/rest/api/3/issue",
              json={"fields": {
                  "project": {"key": "CLOUDOPS"},
                  "summary": "...",
                  "issuetype": {"name": "Task"},
                  "description": {  # ADF document
                      "type": "doc", "version": 1,
                      "content": [{"type": "paragraph",
                                   "content": [{"type": "text", "text": "..."}]}],
                  },
              }},
              auth=auth)

# Discover createmeta (valid fields, types, required) for a project
requests.get(f"{url}/rest/api/3/issue/createmeta",
             params={"projectKeys": "CLOUDOPS",
                     "expand": "projects.issuetypes.fields"},
             auth=auth)

# Transition after create (e.g. set "In Progress")
requests.post(f"{url}/rest/api/3/issue/{key}/transitions",
              json={"transition": {"id": "<transition_id>"}},
              auth=auth)

# Link to another issue (blocks / is blocked by / relates to)
requests.post(f"{url}/rest/api/3/issueLink",
              json={"type": {"name": "Blocks"},
                    "inwardIssue": {"key": "CLOUDOPS-1"},
                    "outwardIssue": {"key": "CLOUDOPS-2"}},
              auth=auth)
```

Use raw v3 + ADF only when you need formatting fidelity Markdown→ADF that
the wrapper's wiki-markup path can't produce.

## What to report back

The new issue key (e.g. `CLOUDOPS-1234`) and the browse URL. If the user
asked you to chain — "create then assign", "create then link to PR" —
return the key and ask before proceeding to the next step rather than
guessing the follow-on values.
