#!/usr/bin/env python3
import os, json, contextlib

from jira import JIRA, User, utils
from atlassian import Jira


def get_conf(conf_path):
    conf = {}
    try:
        with contextlib.suppress(FileNotFoundError):
            with open(conf_path) as fs:
                conf = json.load(fs)
    except ValueError:
        print('Decoding JSON has failed: ' + conf_path)
    return conf


def get_all_user_in_group(jira, group):
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
    result = r['users']['items']
    return result


def get_user(jira, id, accountId=None, expand=None):
    """Get a user Resource from the server.

    :param id: ID of the user to get
    :param accountId: extra information to fetch inside each resource
    :param expand: extra information to fetch inside each resource
    """
    user = User(jira._options, jira._session)
    params = {}
    if accountId:
        params['accountId'] = accountId
    if expand is not None:
        params['expand'] = expand
    user.find(id, params=params)
    return user


def add_user_to_group(jira, accountId, group):
    """Add a user to an existing group.

    :param accountId: users account ID that will be added to specified group.
    :param group: Group that the user will be added to.
    :return: json response from Jira server for success or a value that evaluates as False in case of failure.
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


def setup_jira_client():
    profile = os.getenv('JIRA_PROFILE', 'default')
    user_base = os.path.expanduser('~')
    conf_path = os.path.join(user_base, '.atlassian-conf.json')
    full_conf = get_conf(conf_path=conf_path)
    conf = full_conf.get(profile, {})
    return JIRA(server=conf["url"], basic_auth=(conf["username"], conf["password"]))


def main():
    jira = setup_jira_client()
    group = 'deloitte'
    group_b = 'jira-sotware-users'

    users = get_all_user_in_group(jira, group)
    users_b = get_all_user_in_group(jira, group_b)
    for user in users:
        u = get_user(jira, user, accountId=user['accountId'])
        print(f"Found {u.displayName}: {u.self}")
        if user not in users_b and u.accountType == "atlassian":
            add_user_to_group(jira, u.accountId, group_b)
            print(f"Added user {u.displayName} to {group_b}")


if __name__ == "__main__":
    main()
