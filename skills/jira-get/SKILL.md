---
name: jira-get
description: >
  Fetch a single Jira Cloud issue by key or URL (CCAOA tenant by default).
  Use when the user asks you to read, look at, summarize, inspect, or pull
  the details of a Jira ticket — anything starting with `PROJ-123` or a
  URL like https://ccaoa.atlassian.net/browse/PROJ-123. Handles auth via
  the shared atlassian_auth helper and prefers Jira Cloud REST v3 (ADF).
  Do not invoke for Confluence pages (use confluence-read), JQL / multi-
  issue search (use jira-read), or creating a new ticket (use jira-create).
---

# Jira — get one issue

## When to invoke

Any of:
- User pastes a `*.atlassian.net/browse/<KEY>` URL.
- User mentions an issue key in `<PROJECT>-<num>` form (e.g. `CLOUDOPS-1234`).
- User asks to "read / summarize / look at / pull / fetch / show me" a specific Jira ticket.

Do **not** invoke for:
- "Find me all tickets where…" / any JQL → use `jira-read`.
- Creating a new ticket → use `jira-create`.
- Adding a comment / note to a ticket → use `jira-comment`.
- Confluence pages → use `confluence-read`.

## Auth

Credentials come from the shared `atlassian_auth` helper. The helper reads
`~/.atlassian-conf.json` (profile `default` → `https://ccaoa.atlassian.net`)
and pulls the API token from the macOS keyring. One Atlassian API token
covers both Jira and Confluence — same credentials as `confluence-read`.

Search paths the helper script tries, in order:
1. `$DEVOPS_SCRIPTS_DIR/lib/atlassian_auth.py`
2. `/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/atlassian_auth.py`

## The fast path — `jira_get.py`

```bash
# By key
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234

# By URL (key auto-extracted)
python3 ~/.claude/skills/jira-get/jira_get.py \
  https://ccaoa.atlassian.net/browse/CLOUDOPS-1234

# Include comments / subtasks / changelog
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --comments
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --subtasks
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --changelog

# Force a specific output format
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --format text   # default — ADF rendered to plaintext
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --format json
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --format adf    # raw ADF tree for description

# Non-default Atlassian profile
python3 ~/.claude/skills/jira-get/jira_get.py CLOUDOPS-1234 --profile someother
```

Default output: a header (key, summary, type, status, priority, assignee,
reporter, parent, labels, components, fixVersions, created, updated)
followed by the description rendered ADF → plaintext.

## Useful endpoints (when you need raw HTTP)

Jira Cloud exposes both **v2** (`/rest/api/2/...`, wiki-markup bodies) and
**v3** (`/rest/api/3/...`, ADF JSON bodies). Prefer v3 for new code. Unlike
Confluence Cloud, Jira's v3 is real — use it.

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

# v3 — single issue, ADF description + HTML-rendered side-by-side
requests.get(f"{url}/rest/api/3/issue/{key}",
             params={"expand": "renderedFields,changelog,subtasks,names"},
             auth=auth)

# v3 — comments (separate endpoint, not in the issue payload)
requests.get(f"{url}/rest/api/3/issue/{key}/comment",
             params={"maxResults": 100}, auth=auth)

# v3 — transitions (which workflow steps are available next)
requests.get(f"{url}/rest/api/3/issue/{key}/transitions", auth=auth)

# v3 — attachments are inline under fields.attachment in the issue payload
```

`expand` notes:
- `renderedFields` — adds HTML-rendered versions next to ADF source. Cheap.
- `changelog` — every status/field/assignee change. Can be large on old tickets.
- `subtasks` — full subtask payloads. Otherwise you only get keys.
- `names` — pretty names for custom-field IDs (`customfield_10020` → "Sprint").

## Resolving keys from input

Issue keys look like `<PROJECT>-<number>` with the project all caps. URLs:
- `…/browse/<KEY>` — the canonical form.
- `…/jira/.../boards/N?selectedIssue=<KEY>` — board view, key in the query.

`jira_get.py` parses both, and falls back to a regex match on any
`[A-Z][A-Z0-9_]+-\d+` token in the input.

## Gotchas

- **ADF, not wiki markup.** v3 returns description/comments as ADF JSON.
  The helper converts to plaintext for human review — round-tripping
  through wiki markup will lose formatting.
- **Custom fields are opaque IDs** (`customfield_10020`) unless you pass
  `expand=names`. CCAOA's `Sprint`, `Story Points`, `Epic Link` all live
  under `customfield_*`. Use `--format json` once to map them.
- **Stale data after a write.** If a value was just changed in the UI and
  the read shows the old version, retry once — Jira's read replicas can
  lag a few seconds.

## What to report back

For a single issue: key, summary, type, status, assignee, parent, a short
description summary, and any concrete observations (stale assignee, missing
description, unanswered comments, conflicting parent vs. fixVersion).
With `--subtasks`, flag open subtasks blocking the parent. With
`--comments`, surface the most recent action item or decision.
