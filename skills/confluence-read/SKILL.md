---
name: confluence-read
description: >
  Read pages from Atlassian Confluence Cloud (CCAOA tenant by default).
  Use when the user asks you to review, summarize, fetch, audit, or inspect
  a Confluence page or its children — anything starting with a URL like
  https://ccaoa.atlassian.net/wiki/spaces/.../pages/... or a page ID.
  Handles auth via the shared atlassian_auth helper and prefers the v2 REST
  API. Confluence Cloud has no v3 — do not look for one.
---

# Confluence — read

## When to invoke

Any of:
- User pastes a `*.atlassian.net/wiki/spaces/<KEY>/pages/<id>/...` URL.
- User asks to "review / summarize / audit / look at / pull / read" a Confluence page.
- User mentions a page title and a space (e.g. "the ADR home page in ENGR").
- User wants to walk a tree of pages (parent + children + grandchildren).

Do **not** invoke for Jira tickets — use Jira tooling instead.

## Auth

Credentials come from the shared `atlassian_auth` helper. The helper reads
`~/.atlassian-conf.json` (profile `default` → `https://ccaoa.atlassian.net`)
and pulls the API token from the macOS keyring.

Search paths the helper script tries, in order:
1. `$DEVOPS_SCRIPTS_DIR/lib/atlassian_auth.py`
2. `/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/atlassian_auth.py`

If neither is importable, prompt the user to either set `DEVOPS_SCRIPTS_DIR`
or to point you at the file.

## The fast path — `cf_get.py`

```bash
# Whole page by URL or numeric ID (auto-detected)
python3 ~/.claude/skills/confluence-read/cf_get.py \
  "https://ccaoa.atlassian.net/wiki/spaces/ENGR/pages/1532625010/Architecture+Decision+Records+ADRs"

# Force a specific output format
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --format storage
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --format view
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --format text   # readable plaintext (default)

# Include children
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --children

# Recurse one level deep (children of children)
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --children --depth 2

# Non-default Atlassian profile
python3 ~/.claude/skills/confluence-read/cf_get.py 1532625010 --profile someother
```

Output is structured: a header (title / id / spaceId / version / lastEdited)
followed by the body in the chosen format. With `--children`, the
helper appends a tree summary at the end.

## Useful endpoints (when you need raw HTTP)

Confluence Cloud uses v1 (`/wiki/rest/api/...`) and v2 (`/wiki/api/v2/...`).
There is **no v3**. Prefer v2 for content; fall back to v1 only when v2
doesn't expose what you need (some search/CQL features, comments expansion,
storage-format conversion endpoints).

```python
import sys, os
# Make atlassian_auth importable
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

# v2 — single page (preferred)
requests.get(f"{url}/wiki/api/v2/pages/{page_id}",
             params={"body-format": "storage"}, auth=auth)
# body-format: "storage" | "view" | "atlas_doc_format" | "anonymous_export_view"

# v2 — children of a page
requests.get(f"{url}/wiki/api/v2/pages/{page_id}/children",
             params={"limit": 100}, auth=auth)

# v2 — search pages in a space by title (CQL fallback is v1)
# v1 CQL is the right tool for "find a page by title"
requests.get(f"{url}/wiki/rest/api/content/search",
             params={"cql": 'space = "ENGR" and title = "ADR Template"',
                     "expand": "body.storage,version"},
             auth=auth)

# v2 — comments on a page (footer or inline)
requests.get(f"{url}/wiki/api/v2/pages/{page_id}/footer-comments", auth=auth)
requests.get(f"{url}/wiki/api/v2/pages/{page_id}/inline-comments", auth=auth)

# v2 — attachments
requests.get(f"{url}/wiki/api/v2/pages/{page_id}/attachments", auth=auth)
```

`body-format` notes:
- `storage` — the XHTML-ish source the editor saves. Best for round-tripping
  and for inspecting macros (`ac:structured-macro`, `ri:page` links, etc.).
- `view` — rendered HTML, good for human review.
- `atlas_doc_format` — the new ADF JSON. Only use when you specifically need
  to manipulate the ADF tree.

## Resolving URLs to IDs

Page URLs come in two common shapes:
- `…/wiki/spaces/<KEY>/pages/<ID>/<slug>` — ID is the second path segment after `pages`.
- `…/wiki/display/<KEY>/<title>?…&pageId=<ID>` — older form, ID is in the query.

`cf_get.py` parses both. For anything stranger, fall back to a CQL title
search in the right space.

## Gotchas

- **No v3.** The user may say "v3" out of habit — quietly use v2.
- The `view` body has inline JS/CSS. When summarizing for the user, strip
  tags or use `--format text`. Don't paste full `view` HTML back at them.
- `version-at-save` on `<ri:page>` links pins the link target — it does not
  break the link if the target moves, but it's worth knowing when you see it.
- `most-recent-version` of a page can lag behind a save by a few seconds;
  if a write was just made and the read shows the old version, retry once.
- For pages with thousands of children, paginate via the `cursor` value in
  the `_links.next` response field.

## What to report back

For a single page: title, ID, space, version, last-edited timestamp, a
content summary, and any concrete issues (broken links, stale placeholders,
inconsistent conventions). For a tree, also report the child titles and
flag any orphans / mismatched numbering.
