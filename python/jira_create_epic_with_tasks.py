#!/usr/bin/env python3
"""
Create a Jira Epic and a list of child Tasks linked to it, in one run.

Usage:
    jira_create_epic_with_tasks.py PROJECT \\
        --epic-summary "Big initiative summary" \\
        --epic-description-file epic.md \\
        --children-file children.yaml \\
        --assignee <accountId>

Children file format (YAML or JSON; YAML preferred):

    - summary: "Child task summary 1"
      description: |
        Multi-line task description.
        Wiki markup is allowed.
      # Optional per-child overrides (else inherits from CLI defaults):
      labels: [extra-label]
      components: [Backend]
      assignee: <accountId>            # override CLI --assignee for this one
      priority: High

    - summary: "Child task summary 2"
      description-file: child2.md      # alternative to inline description

Assignee handling:
    --assignee accepts a Jira accountId (24-char hex on Jira Cloud).
    Apply to Epic + all children unless overridden per-child.
    If --assignee is omitted, the script does not set assignee (leaves blank
    or default per project).

Auth:
    Uses jira_auth.py (same module as jira_create_issue.py). Standard auth
    flags from add_auth_arguments() are accepted.

Examples:
    # Dry-run, prints both Epic and Task payloads
    jira_create_epic_with_tasks.py CLOUDOPS \\
        --epic-summary "Upgrade flux apiVersions" \\
        --epic-description-file ./epic.md \\
        --children-file ./children.yaml \\
        --assignee 5e6677b2308ac10ced39e744

    # Real create — drop --dry-run when you've reviewed
    jira_create_epic_with_tasks.py CLOUDOPS \\
        --epic-summary "..." --epic-description-file ./e.md \\
        --children-file ./c.yaml --assignee <id> --create
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from jira import JIRA, JIRAError
except ModuleNotFoundError:
    print("jira module not found. Install with: pip install jira", file=sys.stderr)
    sys.exit(1)

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except ModuleNotFoundError:
    YAML_AVAILABLE = False

from jira_auth import auth, add_auth_arguments


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Jira Epic and child Tasks linked to it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("project", help="Project key (e.g., CLOUDOPS)")
    parser.add_argument("--epic-summary", required=True,
                        help="Epic summary line")
    epic_desc = parser.add_mutually_exclusive_group()
    epic_desc.add_argument("--epic-description",
                           help="Epic description as a literal string")
    epic_desc.add_argument("--epic-description-file",
                           help="Path to file containing the Epic description")
    parser.add_argument("--epic-issuetype", default="Epic",
                        help="Epic issue type (default: Epic)")
    parser.add_argument("--epic-label", action="append", default=[],
                        help="Add a label to the Epic only (repeatable)")
    parser.add_argument("--epic-component", action="append", default=[],
                        help="Add a component to the Epic only (repeatable)")
    parser.add_argument("--epic-priority",
                        help="Priority name on the Epic (e.g., High)")

    parser.add_argument("--children-file", required=True,
                        help="Path to YAML or JSON file describing child tasks")
    parser.add_argument("--child-issuetype", default="Task",
                        help="Child issue type (default: Task)")
    parser.add_argument("--child-label", action="append", default=[],
                        help="Default label applied to every child (repeatable; "
                             "merged with per-child labels)")

    parser.add_argument("--assignee",
                        help="Default assignee accountId (Jira Cloud) or "
                             "username (Server). Applies to Epic + all children "
                             "unless overridden per-child.")
    parser.add_argument("--label", action="append", default=[],
                        help="Default label applied to BOTH Epic and every child "
                             "(repeatable)")

    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="(default) Print the payloads without creating issues")
    parser.add_argument("--create", action="store_false", dest="dry_run",
                        help="Actually create the issues (overrides --dry-run)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print extra information including Jira URLs")

    add_auth_arguments(parser)
    return parser.parse_args()


def load_children(path):
    """Load children list from a YAML or JSON file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"children file not found: {path}")
    text = p.read_text()
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if not YAML_AVAILABLE:
            raise RuntimeError(
                "PyYAML required to parse YAML children files. "
                "Install with: pip install pyyaml"
            )
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        # Try YAML first, fall back to JSON
        if YAML_AVAILABLE:
            try:
                data = yaml.safe_load(text)
            except Exception:
                data = json.loads(text)
        else:
            data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(
            f"children file must contain a list at the top level, got {type(data).__name__}"
        )
    return data


def assignee_field(account_id_or_name):
    """Build an assignee field block.

    On Jira Cloud, accountId is required. On older Server installs, name works.
    Heuristic: long-ish hex strings (>= 20 chars, no whitespace) are treated
    as accountId; else as name. Caller can override by passing a dict directly.
    """
    if account_id_or_name is None:
        return None
    if isinstance(account_id_or_name, dict):
        return account_id_or_name
    if len(account_id_or_name) >= 20 and " " not in account_id_or_name:
        return {"accountId": account_id_or_name}
    return {"name": account_id_or_name}


def resolve_description(child, key_inline="description", key_file="description-file"):
    """Resolve description from inline or file reference in a child entry."""
    if key_inline in child and child[key_inline]:
        return child[key_inline]
    file_key = key_file if key_file in child else "description_file"
    if file_key in child and child[file_key]:
        return Path(child[file_key]).read_text()
    return ""


def build_epic_fields(args, description):
    fields = {
        "project": {"key": args.project},
        "summary": args.epic_summary,
        "issuetype": {"name": args.epic_issuetype},
    }
    if description:
        fields["description"] = description
    labels = list(args.label) + list(args.epic_label)
    if labels:
        fields["labels"] = labels
    if args.epic_component:
        fields["components"] = [{"name": c} for c in args.epic_component]
    if args.epic_priority:
        fields["priority"] = {"name": args.epic_priority}
    a = assignee_field(args.assignee)
    if a:
        fields["assignee"] = a
    return fields


def build_child_fields(args, child, epic_key=None):
    summary = child.get("summary")
    if not summary:
        raise ValueError("each child entry must have a 'summary' key")
    fields = {
        "project": {"key": args.project},
        "summary": summary,
        "issuetype": {"name": child.get("issuetype", args.child_issuetype)},
    }
    description = resolve_description(child)
    if description:
        fields["description"] = description

    # Labels: defaults from CLI + per-child
    labels = list(args.label) + list(args.child_label) + list(child.get("labels", []))
    if labels:
        fields["labels"] = sorted(set(labels))

    # Components per-child
    components = child.get("components", [])
    if components:
        fields["components"] = [{"name": c} for c in components]

    # Priority per-child
    priority = child.get("priority")
    if priority:
        fields["priority"] = {"name": priority}

    # Assignee: per-child override > CLI default
    child_assignee = child.get("assignee", args.assignee)
    a = assignee_field(child_assignee)
    if a:
        fields["assignee"] = a

    if epic_key:
        fields["parent"] = {"key": epic_key}

    return fields


def main():
    args = parse_args()
    children = load_children(args.children_file)

    # Epic description
    if args.epic_description:
        epic_desc = args.epic_description
    elif args.epic_description_file:
        epic_desc = Path(args.epic_description_file).read_text()
    else:
        epic_desc = ""

    epic_fields = build_epic_fields(args, epic_desc)

    if args.dry_run:
        print("=" * 72)
        print("DRY RUN — no issues will be created (use --create to commit)")
        print("=" * 72)
        print("\n--- EPIC payload ---")
        print(json.dumps(epic_fields, indent=2))
        print(f"\n--- {len(children)} CHILD payloads (parent will be filled at create time) ---")
        for i, c in enumerate(children, 1):
            cf = build_child_fields(args, c, epic_key="<EPIC-KEY-AFTER-CREATE>")
            print(f"\n[{i}] {cf['summary']}")
            print(f"    issuetype: {cf['issuetype']['name']}")
            print(f"    labels: {cf.get('labels', [])}")
            if "assignee" in cf:
                print(f"    assignee: {cf['assignee']}")
            if "priority" in cf:
                print(f"    priority: {cf['priority']}")
            if "components" in cf:
                print(f"    components: {cf['components']}")
        print(f"\nWould create: 1 Epic + {len(children)} children")
        return 0

    conf = auth(args)
    jira = JIRA(server=conf["url"], basic_auth=(conf["username"], conf["password"]))

    try:
        epic = jira.create_issue(fields=epic_fields)
    except JIRAError as e:
        print(f"FAILED to create Epic ({e.status_code}): {e.text}", file=sys.stderr)
        return 1
    epic_url = f"{conf['url'].rstrip('/')}/browse/{epic.key}"
    print(f"Created Epic: {epic.key}  {epic_url if args.verbose else ''}")

    failures = []
    created = []
    for i, c in enumerate(children, 1):
        try:
            cf = build_child_fields(args, c, epic_key=epic.key)
        except ValueError as e:
            print(f"  [{i}] SKIP (bad config): {e}", file=sys.stderr)
            failures.append((i, str(e)))
            continue
        try:
            issue = jira.create_issue(fields=cf)
            created.append(issue.key)
            child_url = f"{conf['url'].rstrip('/')}/browse/{issue.key}"
            print(f"  [{i}] {issue.key}: {cf['summary']}"
                  + (f"  {child_url}" if args.verbose else ""))
        except JIRAError as e:
            print(f"  [{i}] FAILED ({e.status_code}): {e.text}", file=sys.stderr)
            failures.append((i, e.text))

    print(f"\nSummary: {epic.key} + {len(created)} children created"
          + (f" ({len(failures)} failed)" if failures else ""))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
