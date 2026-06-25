---
name: jira-comment
description: >
  Add a comment to an existing Jira Cloud issue (CCAOA tenant by default).
  Use whenever the user asks you to comment on, add a note to, leave an
  update on, reply on, or "post to" a Jira ticket — phrasings like "add
  notes to PROJ-123", "comment on that ticket", "drop a status update on
  the Jira", or "leave a note for the team on DEVOPS-1". Wraps jira_comment.py,
  which posts via the v2 (wiki-markup) or v3 (ADF) comment API using the
  shared atlassian_auth helper. Do not invoke for reading an issue (use
  jira-get), searching (use jira-read), creating a new ticket (use
  jira-create), or editing description/status fields.
---

# Jira — add a comment

## When to invoke

Any of:
- User asks to "comment on / add a note to / leave an update on / reply on / post to" a specific Jira issue.
- User wrote a status update, summary, or findings and wants it attached to a ticket (very common after finishing a chunk of work — "add notes to DEVOPS-1").
- User pastes an issue key or `…/browse/<KEY>` URL alongside text to record.

Do **not** invoke for:
- Reading / summarizing an issue → `jira-get`.
- Searching across issues (JQL) → `jira-read`.
- Creating a new ticket → `jira-create`.
- Editing the description, transitioning status, or changing fields — no skill
  yet; drop to raw REST `PUT /rest/api/3/issue/{key}` or the transitions endpoint.

## Auth

Same `atlassian_auth` helper used by `jira-get` / `jira-create`:
`~/.atlassian-conf.json` (profile `default` → `https://ccaoa.atlassian.net`)
plus the API token from the macOS keyring. One token covers Jira and Confluence.

Search paths the script tries, in order:
1. `$DEVOPS_SCRIPTS_DIR/lib/atlassian_auth.py`
2. `/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/atlassian_auth.py`

## The fast path — `jira_comment.py`

```bash
SCRIPT=~/.claude/skills/jira-comment/jira_comment.py

# Literal body
python3 "$SCRIPT" DEVOPS-1 --body "Deployed v0.11.0 to dev; smoke tests green."

# Body from a file (good for long, formatted notes)
python3 "$SCRIPT" DEVOPS-1 --body-file notes.md

# Body piped on stdin ("-" also works as the file arg)
echo "Quick status note" | python3 "$SCRIPT" DEVOPS-1

# By URL (key auto-extracted)
python3 "$SCRIPT" https://ccaoa.atlassian.net/browse/DEVOPS-1 --body "..."

# Preview the payload without posting
python3 "$SCRIPT" DEVOPS-1 --body "..." --dry-run

# Restrict visibility to a group or project role (internal notes)
python3 "$SCRIPT" DEVOPS-1 --body "internal only" --visibility-role Administrators

# Non-default Atlassian profile
python3 "$SCRIPT" DEVOPS-1 --body "..." --profile someother
```

On success it prints the new comment id and a deep link
(`…/browse/<KEY>?focusedCommentId=<id>`).

## Body format — wiki (default) vs adf

`--format wiki` (default) posts the raw string to **v2**, which Jira renders as
**wiki markup**. This is the high-fidelity path for human-readable notes:

| Wiki markup | Renders as |
|---|---|
| `h3. Heading` | section heading |
| `*bold*` | **bold** |
| `_italic_` | _italic_ |
| `{{monospace}}` | `inline code` |
| `* item` / `# item` | bullet / numbered list |
| `{code}...{code}` | code block |
| `[text|url]` | link |

`--format adf` wraps **plaintext** into an ADF document and posts to **v3**
(blank lines → paragraphs, single newlines → line breaks). Use it when the body
contains literal `*`, `_`, `{`, or `[` that must NOT be interpreted as markup —
e.g. pasting raw log lines or code-ish text. It deliberately does no markdown
parsing, so headings/bullets written in the source won't render as such.

Rule of thumb: composing a status note for humans → **wiki**. Dumping
verbatim/unstructured text safely → **adf**.

## Composing good notes

- **Write wiki markup, not Markdown.** `h3.` not `###`, `{{x}}` not `` `x` ``,
  `*` bullets not `-`. Markdown `#`/`-`/backticks will render literally under
  the default wiki format. (This is the same v2 caveat as `jira-create`.)
- **Lead with what changed and the artifact** — commit SHA, version, PR, branch.
  A note that says "tagged {{v0.11.0}}, TFC will auto-publish" is worth more than
  "done".
- **Long notes: use `--body-file`.** Building a multi-section note inline with
  shell quoting is error-prone; write it to a temp file and pass `--body-file`.
- **`--dry-run` first** when the body has heavy formatting or shell-risky
  characters, to confirm the payload is what you intend before it's public.

## Useful endpoints (raw HTTP)

When the script doesn't cover it (editing or deleting a comment, paging existing
comments before adding one):

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

# v3 — add a comment with a full ADF body (rich formatting beyond the script)
requests.post(f"{url}/rest/api/3/issue/{key}/comment",
              json={"body": {"type": "doc", "version": 1, "content": [...]}},
              auth=auth)

# v2 — add a comment as a wiki-markup string (what --format wiki does)
requests.post(f"{url}/rest/api/2/issue/{key}/comment",
              json={"body": "h3. Title\n* point one"}, auth=auth)

# Edit an existing comment
requests.put(f"{url}/rest/api/3/issue/{key}/comment/{comment_id}",
             json={"body": {...}}, auth=auth)

# Delete a comment
requests.delete(f"{url}/rest/api/3/issue/{key}/comment/{comment_id}", auth=auth)

# List existing comments (e.g. to avoid duplicating a note)
requests.get(f"{url}/rest/api/3/issue/{key}/comment",
             params={"maxResults": 100}, auth=auth)
```

## Gotchas

- **Comments are public to the project by default.** Anyone with browse access
  sees them. For internal-only notes use `--visibility-group`/`--visibility-role`;
  the value must match an existing group/role name exactly or the API rejects it.
- **A comment is hard to un-send.** It notifies watchers immediately. Treat
  posting like sending mail — `--dry-run` if unsure, and confirm the target key.
- **Key vs URL.** The script resolves `PROJ-123`, `/browse/PROJ-123`, and
  `selectedIssue=PROJ-123`; anything else errors rather than guessing.
- **Stale read-back.** Reading the issue immediately after commenting may not
  show it for a few seconds (read-replica lag) — the printed comment id is the
  source of truth that it landed.

## What to report back

The comment id and the deep link the script prints. If the user asked to chain
("comment then transition", "note it and assign"), post the comment, report the
link, and confirm the next step rather than guessing it.
