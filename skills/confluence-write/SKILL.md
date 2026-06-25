---
name: confluence-write
description: >
  Create or update pages in Atlassian Confluence Cloud (CCAOA tenant by
  default). Use when the user asks you to write, draft, publish, post,
  create, update, edit, or "fix" a Confluence page. Two paths: hand a
  markdown file to the existing md_to_confluence.py CLI for whole-page
  writes, or do surgical raw-HTTP edits in storage format for in-place
  table-row / status-macro / single-section changes.
---

# Confluence — write

## When to invoke

Any of:
- User says "create / draft / publish / post / write a Confluence page".
- User says "update / edit / fix / append to" a Confluence page.
- User provides text/markdown and asks for it to land on Confluence.
- User asks for a targeted change (e.g. "add a row to the ADR register",
  "change the status macro on ADR-001 to ACCEPTED").

Pair with `confluence-read` when the task is to **edit** an existing page —
read first, plan the diff, then write.

## Before you write — confirm with the user

A `POST` or `PUT` to Confluence is visible to other humans and emails
watchers. Before any write, summarize what you're about to do and ask for
confirmation:

> "Going to **create** a page titled *X* under parent *Y* in space ENGR.
> Body is ~Z lines, includes a status macro and a register table. OK to
> publish?"

For updates, also state the page ID, the current version, and the diff
shape (e.g. "appending one row to the register table; everything else
unchanged"). Do not auto-publish from a fresh prompt.

## Path 1 — markdown → page via `md_to_confluence.py`

The user maintains `md_to_confluence.py` at
`/Users/alexmoore/repos/github.com/almoore/useful-scripts/python/md_to_confluence.py`.
Use it as the default for any whole-page create/update where the source is
markdown. It handles markdown → storage XHTML conversion, auth, version
bumping, and the create-vs-update branch.

```bash
# Always start with a dry-run to inspect the converted XHTML
python3 /Users/alexmoore/repos/github.com/almoore/useful-scripts/python/md_to_confluence.py \
    page.md --dry-run

# Create a new page (auto-selects the first H1 as title)
python3 .../md_to_confluence.py page.md \
    --space ENGR --parent-id 1532625010

# Override the title
python3 .../md_to_confluence.py page.md \
    --space ENGR --parent-id 1532625010 \
    --title "ADR-0002: Adopt PostgreSQL for billing"

# Update an existing page (pass the page ID; title defaults to file's H1)
python3 .../md_to_confluence.py page.md --page-id 1534328833 \
    --title "ADR-001: New infra for AppRunner workloads"
```

### Markdown features the converter supports
Headings (H1–H6), bold (`**x**`), italic (`*x*`), inline code (`` `x` ``),
links `[label](url)`, bullet lists (`-` / `*`), ordered lists (`1.`),
fenced code blocks (`` ```lang ``), tables with header row, blockquotes,
horizontal rules.

### Limitations to work around
The converter is intentionally narrow. If you need any of these, edit the
generated XHTML by hand before running (use `--dry-run`, redirect to a
file, edit, then re-run with a pre-converted body):

- **Nested lists** — indented bullets break the outer list. Flatten or
  manually edit.
- **Images** — `![alt](url)` partially matches the link regex and renders
  with a stray `!`. Strip the `!` or insert an `<ac:image>` block by hand.
- **Task lists** — `- [ ]` renders as a literal bullet with `[ ]` text.
- **Confluence-specific macros** — status lozenges, info/note/warning
  panels, ToC, expand sections, Jira smart links, intra-Confluence page
  links (`<ac:link>` + `<ri:page>`). The converter doesn't know about
  these. Insert them by editing the dry-run XHTML.
- **Title preservation on update** — the script always sends a title.
  Always pass `--title` on updates to avoid an accidental rename (renames
  break inbound `<ri:page ri:content-title=…>` links).
- **No `version.message`** — page history will show "(no message)" for
  every update. Cosmetic.

If the user wants you to *fix* `md_to_confluence.py` to remove one of
these limitations, do it — it's their script. Priority order, from the
review: (a) preserve title on update by fetching the current page when
`--title` is omitted, (b) wrap `<td>` contents in `<p>`, (c) add nested
list support, (d) accept `--message`, (e) retry-once on 409.

## Path 2 — surgical edits via raw HTTP

For targeted in-place changes (append a row to a register table, swap a
status macro, fix a typo in one paragraph), do not regenerate the page
from markdown — you'll lose macros the converter doesn't know about. Read
the current storage body, modify it as XML, write it back. v2 API:

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
page_id = "1532625010"

# 1. Read fresh — immediately before the write
cur = requests.get(
    f"{url}/wiki/api/v2/pages/{page_id}",
    params={"body-format": "storage"}, auth=auth, timeout=20,
).json()

body = cur["body"]["storage"]["value"]
new_body = body.replace(
    "<!-- INSERT NEW ROW HERE -->",
    "<tr><td><p>ADR-002</p></td><td><p>New thing</p></td></tr>",
)

# 2. PUT with version + 1
payload = {
    "id": page_id,
    "status": "current",
    "title": cur["title"],
    "body": {"representation": "storage", "value": new_body},
    "version": {
        "number": cur["version"]["number"] + 1,
        "message": "Add ADR-002 row to register",
    },
}
r = requests.put(f"{url}/wiki/api/v2/pages/{page_id}", json=payload, auth=auth, timeout=20)
r.raise_for_status()
print(f"updated to v{r.json()['version']['number']}")
```

A `409 Conflict` means someone (or you) bumped the version since you read.
Re-fetch and try again — do **not** blindly force.

## Storage-format snippets (for hand edits or macros)

Confluence storage format is XHTML with two extra namespaces: `ac:`
(macros / Atlassian elements) and `ri:` (resource identifiers). It is the
format the editor saves and what `body-format=storage` returns on read.
It round-trips losslessly. The other option, `atlas_doc_format` (ADF
JSON), is more verbose and only needed when manipulating a structured
tree — default to storage.

```xml
<!-- Headings, paragraphs -->
<h2>What this is</h2>
<p>Body with <strong>bold</strong>, <em>italics</em>, <code>code</code>.</p>

<!-- Lists -->
<ul><li>first</li><li>second</li></ul>
<ol><li>step one</li><li>step two</li></ol>

<!-- Code block -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">bash</ac:parameter>
  <ac:plain-text-body><![CDATA[
echo hello
  ]]></ac:plain-text-body>
</ac:structured-macro>

<!-- Info / Note / Warning panels -->
<ac:structured-macro ac:name="info"><ac:rich-text-body>
  <p>FYI box.</p>
</ac:rich-text-body></ac:structured-macro>
<ac:structured-macro ac:name="note"><ac:rich-text-body>
  <p>Watch out.</p>
</ac:rich-text-body></ac:structured-macro>
<ac:structured-macro ac:name="warning"><ac:rich-text-body>
  <p>Don't do this in prod.</p>
</ac:rich-text-body></ac:structured-macro>

<!-- Status lozenge -->
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="title">ACCEPTED</ac:parameter>
  <ac:parameter ac:name="colour">Green</ac:parameter>
</ac:structured-macro>
<!-- Colours: Grey · Red · Yellow · Green · Blue · Purple -->

<!-- Link to another Confluence page in the same space -->
<ac:link>
  <ri:page ri:content-title="ADR Template"/>
  <ac:link-body>ADR Template</ac:link-body>
</ac:link>

<!-- Link to a page in a different space -->
<ac:link>
  <ri:page ri:space-key="OPS" ri:content-title="Runbook: RDS failover"/>
  <ac:link-body>RDS failover runbook</ac:link-body>
</ac:link>

<!-- Jira issue smart link -->
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="key">PROJ-123</ac:parameter>
</ac:structured-macro>

<!-- Date -->
<time datetime="2026-06-15"/>

<!-- Table with header row -->
<table data-layout="default"><tbody>
  <tr><th><p>Col A</p></th><th><p>Col B</p></th></tr>
  <tr><td><p>cell</p></td><td><p>cell</p></td></tr>
</tbody></table>

<!-- Table of contents -->
<ac:structured-macro ac:name="toc"/>

<!-- Expand / collapse -->
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Click to see detail</ac:parameter>
  <ac:rich-text-body><p>Hidden content.</p></ac:rich-text-body>
</ac:structured-macro>
```

## API quick-reference

Confluence Cloud uses v1 (`/wiki/rest/api/...`) and v2 (`/wiki/api/v2/...`).
There is **no v3** — quietly use v2 if the user says "v3".

```python
# v2 — preferred for new code
GET  /wiki/api/v2/pages/{id}?body-format=storage
PUT  /wiki/api/v2/pages/{id}        # body needs id, status, title, body, version.number
POST /wiki/api/v2/pages              # body needs spaceId (numeric), title, body, parentId?

# v1 — what md_to_confluence.py uses (simpler space/parent resolution)
GET  /wiki/rest/api/content/{id}?expand=body.storage,version
PUT  /wiki/rest/api/content/{id}
POST /wiki/rest/api/content          # accepts space:{key:...} and ancestors:[{id:...}] directly

# Looking up a space's numeric ID for v2 POST:
GET  /wiki/api/v2/spaces?keys=ENGR    # -> results[0].id

# CQL search (v1 only — v2 has no equivalent yet)
GET  /wiki/rest/api/content/search?cql=space="ENGR" AND title="ADR Template"
```

## Gotchas

- **No v3.** Use v2; v1 for CQL and the existing md_to_confluence.py.
- **Storage XHTML must be well-formed.** A stray `<br>` (not `<br/>`) or
  an unclosed `<p>` returns `400`. Parse-check your generated body before
  sending.
- **Tables need `<p>` inside cells** (`<td><p>cell</p></td>`). Bare text
  renders but breaks later editor operations.
- **`ri:content-title` is case- and whitespace-sensitive.** Match the
  target page's title exactly or the link becomes broken.
- **Version bumps include silent saves** (someone publishing without
  edits). Always read fresh immediately before the write.
- **Restricted pages return 403** even on read. Programmatic write won't
  bypass restrictions — check the page's permissions in the UI.
- **Don't include the date in the title.** Renames break inbound
  `<ri:page>` links. Put dates in the body.
- **Watchers get emailed on publish.** For high-traffic spaces, ask
  whether to first save as `status=draft` before flipping to `current`.

## What to report back

After a successful create/update: title, page ID, new version number,
and the page URL. After a refused write (because the user didn't confirm
or a 4xx came back): say so plainly and surface the response body — do
not retry silently.
