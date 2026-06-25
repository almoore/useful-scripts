---
name: jira-read
description: >
  Search Jira Cloud issues via JQL (CCAOA tenant by default). Use when the
  user wants to list, find, query, or filter Jira tickets — phrasings like
  "all open tickets in X", "what's assigned to me", "tickets created this
  week", "everything tagged with Y", or a raw JQL string. Handles auth via
  the shared atlassian_auth helper and uses Jira Cloud REST v3. Do not
  invoke to fetch one specific ticket (use jira-get) or to create one
  (use jira-create).
---

# Jira — search via JQL

## When to invoke

Any of:
- User asks "show me / list / find all tickets where…".
- User wants tickets filtered by status / assignee / label / project / sprint / fixVersion.
- User pastes a raw JQL string.
- User asks for a count or backlog summary.

Do **not** invoke for:
- A single specific ticket by key → use `jira-get`.
- Creating a new ticket → use `jira-create`.

## Auth

Same as `jira-get` — `atlassian_auth.get_auth()` reads
`~/.atlassian-conf.json` and pulls the token from macOS keyring. One
Atlassian API token covers Jira and Confluence both.

## The fast path — `jira_search.py`

```bash
# Raw JQL (most flexible)
python3 ~/.claude/skills/jira-read/jira_search.py \
  --jql "project = CLOUDOPS and status = 'In Progress'"

# Common-case shortcuts (composed with AND, plus ORDER BY updated DESC)
python3 ~/.claude/skills/jira-read/jira_search.py \
  --project CLOUDOPS --status "In Progress" --assignee "currentUser()"

# Pick fields to return
python3 ~/.claude/skills/jira-read/jira_search.py \
  --jql "project = CLOUDOPS and resolution = Unresolved" \
  --fields summary,status,priority,updated,customfield_10020

# Bigger result cap (default 50)
python3 ~/.claude/skills/jira-read/jira_search.py --jql "..." --max-results 200

# JSON for further processing
python3 ~/.claude/skills/jira-read/jira_search.py --jql "..." --format json

# Non-default profile
python3 ~/.claude/skills/jira-read/jira_search.py --jql "..." --profile someother
```

Default output is a fixed-width table — `KEY [status] assignee summary`,
ordered by most-recently-updated. JSON output returns the raw v3 issue
dicts so you can pipe to `jq`.

## JQL building blocks worth remembering

```jql
project = CLOUDOPS
status = "In Progress"             -- quote multi-word values
statusCategory != Done             -- "open" filter that's workflow-agnostic
assignee = currentUser()           -- token holder
assignee in (alice, bob)
resolution = Unresolved
labels in ("dr", "rancher")
priority = Highest
created >= "2026-01-01"
updated >= -7d                     -- relative dates supported
sprint in openSprints()
"Epic Link" = CLOUDOPS-100         -- field names with spaces need quotes
parent = CLOUDOPS-100              -- new way to refer to epic parent
ORDER BY updated DESC, priority DESC
```

## Useful endpoints (raw HTTP)

```python
# v3 search — POST /rest/api/3/search/jql (paginated via nextPageToken)
requests.post(f"{url}/rest/api/3/search/jql",
              json={"jql": "...", "fields": ["summary","status"], "maxResults": 100},
              auth=auth)

# v3 deprecated-but-still-supported — GET /rest/api/3/search (paginated via startAt)
requests.get(f"{url}/rest/api/3/search",
             params={"jql": "...", "fields": "summary,status",
                     "startAt": 0, "maxResults": 100},
             auth=auth)
```

`jira_search.py` tries the newer POST endpoint first and falls back to the
GET form if the tenant doesn't expose it (some older Cloud tenants don't).

## Gotchas

- **JQL keywords are case-insensitive** but **values usually aren't**.
  `status = "In progress"` may return nothing while `status = "In Progress"`
  works. Use `jira-get` on a known ticket to confirm the exact workflow name.
- **Custom fields by ID, not name** in `--fields`. Sprint, Story Points,
  Epic Link all live under `customfield_*`. Use `jira-get --format json`
  once on a known ticket to map them.
- **Reconciliation lag.** Newly-created or edited issues sometimes don't
  appear in search for ~30s while the JQL index catches up.
- **maxResults caps at 100 per API call.** `jira_search.py` paginates
  internally up to `--max-results`. Default is 50 to keep latency low.
- **`assignee = currentUser()` resolves to the API token's owner**, not the
  current `git config user.email`. Pass an explicit accountId or display
  name in scripts where the caller may differ from the token owner.

## What to report back

For a list: total count, the JQL used, and a compact table with key /
status / assignee / summary. If asked to summarize a backlog, group by
status or assignee and flag anomalies (no assignee, stale "In Progress"
older than N days, priority/effort mismatches).
