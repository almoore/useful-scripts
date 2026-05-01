#!/usr/bin/env python3
"""
Description: Create a Jira issue from the command line.
Usage: run directly using python or add it to your path

Examples:
    # Minimal: summary on argv, description from stdin
    echo "Long description here" | jira_create_issue.py PROJ "Short summary"

    # Description from a file
    jira_create_issue.py PROJ "Short summary" --description-file ticket.txt

    # Description as a literal string
    jira_create_issue.py PROJ "Short summary" --description "One line desc"

    # Pick issue type, labels, assignee
    jira_create_issue.py PROJ "Short summary" --description-file t.txt \\
        --issue-type Task --label dr --label rancher --assignee jdoe

    # Attach to an epic / parent
    jira_create_issue.py PROJ "Short summary" --description-file t.txt \\
        --parent PROJ-456

    # Discover valid issue types for a project
    jira_create_issue.py PROJ --list-issue-types
"""
import argparse
import sys

try:
    from jira import JIRA, JIRAError
except ModuleNotFoundError:
    print("jira module not found please install it:\n\tpip install jira")
    exit(1)

from jira_auth import auth, add_auth_arguments


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create a Jira issue from the command line.'
    )
    parser.add_argument('project', help='Project key (e.g., CLOUDOPS)')
    parser.add_argument('summary', nargs='?',
                        help='Short summary line (required unless --list-issue-types)')

    desc_group = parser.add_mutually_exclusive_group()
    desc_group.add_argument('--description',
                            help='Issue description as a literal string')
    desc_group.add_argument('--description-file',
                            help='Path to a file containing the description '
                                 '(use "-" for stdin)')

    parser.add_argument('--issue-type', default='Task',
                        help='Issue type (default: Task)')
    parser.add_argument('--label', action='append', default=[],
                        help='Add a label (repeatable)')
    parser.add_argument('--assignee',
                        help='Assignee accountId or username')
    parser.add_argument('--parent',
                        help='Parent issue key (epic or parent task)')
    parser.add_argument('--priority',
                        help='Priority name (e.g., High, Medium)')
    parser.add_argument('--component', action='append', default=[],
                        help='Add a component by name (repeatable)')
    parser.add_argument('--list-issue-types', default=False, action='store_true',
                        help='List valid issue types for the project and exit')
    parser.add_argument('--dry-run', default=False, action='store_true',
                        help='Print the payload without creating the issue')
    parser.add_argument('--verbose', default=False, action='store_true',
                        help='Print extra information')

    add_auth_arguments(parser)
    return parser.parse_args()


def read_description(args):
    if args.description is not None:
        return args.description
    if args.description_file == '-':
        return sys.stdin.read()
    if args.description_file:
        with open(args.description_file) as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ''


def list_issue_types(jira, project_key):
    meta = jira.createmeta(projectKeys=project_key, expand='projects.issuetypes')
    if not meta.get('projects'):
        print(f'No project found with key {project_key}', file=sys.stderr)
        return 1
    for proj in meta['projects']:
        for it in proj['issuetypes']:
            print(it['name'])
    return 0


def build_fields(args, description):
    fields = {
        'project': {'key': args.project},
        'summary': args.summary,
        'issuetype': {'name': args.issue_type},
    }
    if description:
        fields['description'] = description
    if args.label:
        fields['labels'] = args.label
    if args.assignee:
        # Cloud expects accountId; fall back to name for older Jira instances.
        fields['assignee'] = {'accountId': args.assignee} \
            if len(args.assignee) > 20 and '-' in args.assignee \
            else {'name': args.assignee}
    if args.parent:
        fields['parent'] = {'key': args.parent}
    if args.priority:
        fields['priority'] = {'name': args.priority}
    if args.component:
        fields['components'] = [{'name': c} for c in args.component]
    return fields


def main():
    args = parse_args()
    conf = auth(args)
    jira = JIRA(server=conf['url'], basic_auth=(conf['username'], conf['password']))

    if args.list_issue_types:
        return list_issue_types(jira, args.project)

    if not args.summary:
        print('summary is required (or pass --list-issue-types)', file=sys.stderr)
        return 2

    description = read_description(args)
    fields = build_fields(args, description)

    if args.dry_run:
        import json
        print(json.dumps(fields, indent=2))
        return 0

    try:
        issue = jira.create_issue(fields=fields)
    except JIRAError as e:
        print(f'JIRA error ({e.status_code}): {e.text}', file=sys.stderr)
        return 1

    print(issue.key)
    if args.verbose:
        print(f'{conf["url"].rstrip("/")}/browse/{issue.key}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
