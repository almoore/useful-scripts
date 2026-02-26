#!/usr/bin/env python3
"""
List all users in a Jira group.

Usage:
    python jira_uses_list.py --group jira-software-users
    python jira_uses_list.py --group jira-software-users --verbose
"""
import argparse

from jira import User

from jira_auth import setup_jira_client


def get_all_users_in_group(jira, group):
    """Fetch all users in a Jira group, handling pagination."""
    params = {'groupname': group, 'expand': "users"}
    r = jira._get_json('group', params=params)
    size = r['users']['size']
    end_index = r['users']['end-index']

    while end_index < size - 1:
        params = {'groupname': group, 'expand': "users[%s:%s]" % (
            end_index + 1, end_index + 50)}
        r2 = jira._get_json('group', params=params)
        for user in r2['users']['items']:
            r['users']['items'].append(user)
        end_index = r2['users']['end-index']
        size = r['users']['size']
    return r['users']['items']


def get_user(jira, user_id, accountId=None, expand=None):
    """Get a user Resource from the server."""
    user = User(jira._options, jira._session)
    params = {}
    if accountId:
        params['accountId'] = accountId
    if expand is not None:
        params['expand'] = expand
    user.find(user_id, params=params)
    return user


def parse_args():
    parser = argparse.ArgumentParser(
        description="List all users in a Jira group.",
    )
    parser.add_argument('--group', default='jira-software-users',
                        help='Jira group name to list users from.')
    parser.add_argument('--force-password', default=False, action='store_true',
                        help='Force prompting for password.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='More verbose logging.')
    return parser.parse_args()


def main():
    args = parse_args()
    jira = setup_jira_client(force_password=args.force_password, verbose=args.verbose)

    users = get_all_users_in_group(jira, args.group)
    print(f"Found {len(users)} user(s) in group '{args.group}':")
    for user in users:
        u = get_user(jira, user, accountId=user['accountId'])
        print(f"  {u.displayName} ({u.accountId})")


if __name__ == "__main__":
    main()
