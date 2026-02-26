#!/usr/bin/env python3
"""
Description: A utility for reassigning child issues from a Jira epic or parent issue
Usage: run directly using python or add it to your path

Examples:
    # Assign all children of an epic to yourself (default)
    jira_reassign_children.py PROJ-123

    # Assign to a specific user
    jira_reassign_children.py PROJ-123 --assignee jdoe

    # Unassign all children
    jira_reassign_children.py PROJ-123 --unassign

    # Filter by status, then assign
    jira_reassign_children.py PROJ-123 --status "To Do" --assignee jdoe

    # Preview changes without applying
    jira_reassign_children.py PROJ-123 --dry-run --verbose
"""
import argparse

try:
    from jira import JIRA, JIRAError
except ModuleNotFoundError:
    print("jira module not found please install it:\n\tpip install jira")
    exit(1)

from jira_auth import auth, add_auth_arguments


def parse_args():
    parser = argparse.ArgumentParser(
        description='Reassign child issues from a Jira epic or parent issue'
    )
    parser.add_argument('parent', help='The parent issue or epic key (e.g., PROJ-123)')

    assignee_group = parser.add_mutually_exclusive_group()
    assignee_group.add_argument('--assignee',
                                help='Target assignee username or accountId')
    assignee_group.add_argument('--unassign', default=False, action='store_true',
                                help='Remove assignee from child issues')

    parser.add_argument('--status',
                        help='Only reassign issues with this status (e.g., "To Do")')
    parser.add_argument('--issue-type',
                        help='Only reassign issues of this type (e.g., "Story")')
    parser.add_argument('--current-assignee',
                        help='Only reassign issues currently assigned to this user')

    add_auth_arguments(parser)
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='More verbose logging')
    parser.add_argument('-d', '--dry-run', default=False, action='store_true',
                        help='Show what would be done, without making changes')
    return parser.parse_args()


def get_child_issues(jira, parent_key, args):
    """
    Fetch child issues using multiple strategies for Jira version compatibility.
    Tries: parent field (Cloud), Epic Link (older), and direct subtasks.
    :param jira: JIRA client
    :param parent_key: parent issue key (e.g., PROJ-123)
    :param args: parsed args for verbose flag
    :return: deduplicated list of child issue objects
    """
    all_children = []
    seen_keys = set()

    def add_issues(issues):
        for issue in issues:
            if issue.key not in seen_keys:
                seen_keys.add(issue.key)
                all_children.append(issue)

    # Strategy 1: parent field (Jira Cloud / newer)
    try:
        jql = 'parent = {}'.format(parent_key)
        if args.verbose:
            print("Searching: {}".format(jql))
        children = jira.search_issues(jql, maxResults=1000)
        add_issues(children)
        if args.verbose:
            print("Found {} issues via 'parent' field".format(len(children)))
    except JIRAError as e:
        if args.verbose:
            print("'parent' field search failed: {}".format(e.text))

    # Strategy 2: Epic Link (older Jira versions)
    try:
        jql = '"Epic Link" = {}'.format(parent_key)
        if args.verbose:
            print("Searching: {}".format(jql))
        children = jira.search_issues(jql, maxResults=1000)
        add_issues(children)
        if args.verbose:
            print("Found {} issues via 'Epic Link' field".format(len(children)))
    except JIRAError as e:
        if args.verbose:
            print("'Epic Link' search failed: {}".format(e.text))

    # Strategy 3: direct subtasks from parent issue
    try:
        parent_issue = jira.issue(parent_key)
        if hasattr(parent_issue.fields, 'subtasks') and parent_issue.fields.subtasks:
            if args.verbose:
                print("Found {} subtasks on {}".format(
                    len(parent_issue.fields.subtasks), parent_key))
            for subtask in parent_issue.fields.subtasks:
                if subtask.key not in seen_keys:
                    full_subtask = jira.issue(subtask.key)
                    seen_keys.add(subtask.key)
                    all_children.append(full_subtask)
    except JIRAError as e:
        if args.verbose:
            print("Subtask retrieval failed: {}".format(e.text))

    if args.verbose:
        print("Total unique children found: {}".format(len(all_children)))

    return all_children


def apply_filters(issues, args):
    """
    Filter issues by status, issue type, and/or current assignee.
    :param issues: list of JIRA issue objects
    :param args: parsed args with filter values
    :return: filtered list of issues
    """
    filtered = issues

    if args.status:
        filtered = [i for i in filtered if str(i.fields.status) == args.status]
        if args.verbose:
            print("After status filter '{}'  : {} issues".format(args.status, len(filtered)))

    if args.issue_type:
        filtered = [i for i in filtered if str(i.fields.issuetype) == args.issue_type]
        if args.verbose:
            print("After type filter '{}'    : {} issues".format(args.issue_type, len(filtered)))

    if args.current_assignee:
        def matches_assignee(issue):
            assignee = issue.fields.assignee
            if not assignee:
                return False
            return (getattr(assignee, 'name', None) == args.current_assignee or
                    getattr(assignee, 'accountId', None) == args.current_assignee)

        filtered = [i for i in filtered if matches_assignee(i)]
        if args.verbose:
            print("After assignee filter '{}': {} issues".format(
                args.current_assignee, len(filtered)))

    return filtered


def get_target_assignee(jira, args):
    """
    Determine target assignee from CLI flags.
    --unassign returns None, --assignee returns the value,
    default returns the authenticated user.
    :param jira: JIRA client
    :param args: parsed args
    :return: assignee identifier or None
    """
    if args.unassign:
        if args.verbose:
            print("Will unassign issues (remove assignee)")
        return None

    if args.assignee:
        if args.verbose:
            print("Will assign issues to: {}".format(args.assignee))
        return args.assignee

    # Default: assign to current user
    current_user = jira.myself()
    assignee = current_user.get('name') or current_user.get('accountId')
    if args.verbose:
        display = current_user.get('displayName', assignee)
        print("Will assign issues to current user: {} ({})".format(display, assignee))
    return assignee


def reassign_issues(jira, issues, assignee, args):
    """
    Reassign a list of issues to the target assignee.
    :param jira: JIRA client
    :param issues: list of JIRA issue objects
    :param assignee: target assignee string or None to unassign
    :param args: parsed args for verbose/dry-run
    :return: dict with success and failed counts
    """
    results = {'success': 0, 'failed': 0, 'errors': []}

    for issue in issues:
        current = 'Unassigned'
        if issue.fields.assignee:
            current = getattr(issue.fields.assignee, 'displayName',
                              getattr(issue.fields.assignee, 'name', 'Unknown'))

        if assignee is None:
            action_desc = "unassign"
        else:
            action_desc = "assign to {}".format(assignee)

        if args.dry_run:
            print("DRY RUN: Would {} {} [{}] (currently: {})".format(
                action_desc, issue.key, issue.fields.summary, current))
            results['success'] += 1
            continue

        try:
            jira.assign_issue(issue.key, assignee)
            results['success'] += 1
            if args.verbose:
                print("{}: {} (was: {})".format(issue.key, action_desc, current))
            else:
                print("{}: {}".format(issue.key, action_desc))
        except JIRAError as e:
            results['failed'] += 1
            error_msg = "{}: {}".format(issue.key, e.text)
            results['errors'].append(error_msg)
            print("ERROR: {}".format(error_msg))

    return results


def print_summary(issues, results, args):
    """Print a summary of the reassignment operation."""
    prefix = "Would reassign" if args.dry_run else "Reassigned"
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print("Total issues: {}".format(len(issues)))
    print("{}: {}".format(prefix, results['success']))
    if results['failed'] > 0:
        print("Failed: {}".format(results['failed']))
        for error in results['errors']:
            print("  - {}".format(error))
    print("=" * 50)


def main():
    args = parse_args()
    conf = auth(args)

    try:
        jira = JIRA(server=conf["url"],
                    basic_auth=(conf["username"], conf["password"]))
    except JIRAError as e:
        print("Failed to connect to Jira: {}".format(e.text))
        exit(1)

    # Verify parent issue exists
    try:
        parent_issue = jira.issue(args.parent)
        if args.verbose:
            print("Parent: {} - {}".format(parent_issue.key,
                                           parent_issue.fields.summary))
    except JIRAError as e:
        print("Failed to fetch parent issue '{}': {}".format(args.parent, e.text))
        exit(1)

    # Fetch children
    children = get_child_issues(jira, args.parent, args)
    if not children:
        print("No child issues found for {}".format(args.parent))
        exit(0)

    print("Found {} child issue(s) for {}".format(len(children), args.parent))

    # Apply filters
    filtered = apply_filters(children, args)
    if not filtered:
        print("No issues match the specified filters")
        exit(0)

    if len(filtered) != len(children):
        print("{} issue(s) after filtering".format(len(filtered)))

    # Determine target assignee
    target = get_target_assignee(jira, args)

    if args.dry_run:
        print("\nDRY RUN MODE - No changes will be made\n")

    # Reassign
    results = reassign_issues(jira, filtered, target, args)

    # Summary
    print_summary(filtered, results, args)

    if results['failed'] > 0:
        exit(1)


if __name__ == '__main__':
    main()
