#!/usr/bin/env python3
"""
Jira group user management: list users in a group and add missing users
from one group to another.

Usage:
    python jira_tools.py --group-a deloitte --group-b jira-software-users
    python jira_tools.py --group-a deloitte --group-b jira-software-users --verbose
"""
import json
import argparse

from jira import JIRA, User, utils
from atlassian import Jira

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


def add_user_to_group(jira, accountId, group):
    """Add a user to an existing group.

    :param accountId: users account ID that will be added to specified group.
    :param group: Group that the user will be added to.
    :return: json response from Jira server for success or False on failure.
    """
    url = jira._options['server'] + '/rest/api/latest/group/user'
    x = {'groupname': group}
    y = {'accountId': accountId}

    payload = json.dumps(y)

    r = utils.json_loads(jira._session.post(url, params=x, data=payload))
    if 'name' not in r or r['name'] != group:
        return False
    else:
        return r


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage Jira group membership.",
    )
    parser.add_argument('--group-a', default='deloitte',
                        help='Source group to read users from.')
    parser.add_argument('--group-b', default='jira-software-users',
                        help='Target group to add missing users to.')
    parser.add_argument('--force-password', default=False, action='store_true',
                        help='Force prompting for password (useful when token has expired)')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='More verbose logging')
    return parser.parse_args()


def main():
    args = parse_args()
    jira = setup_jira_client(force_password=args.force_password, verbose=args.verbose)

    users = get_all_users_in_group(jira, args.group_a)
    users_b = get_all_users_in_group(jira, args.group_b)
    for user in users:
        u = get_user(jira, user, accountId=user['accountId'])
        print(f"Found {u.displayName}: {u.self}")
        if user not in users_b and u.accountType == "atlassian":
            add_user_to_group(jira, u.accountId, args.group_b)
            print(f"Added user {u.displayName} to {args.group_b}")


if __name__ == "__main__":
    main()
