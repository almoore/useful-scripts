#!/usr/bin/env python3
from git_jira_branch import *
from atlassian import Jira
from jira import JIRA, User
import sys
sys.argv.append('')
args = parse_args()
profile = 'default'
full_conf = get_conf(conf_path=args.conf)
conf = full_conf.get(args.profile, {})

jira = JIRA(server=conf["url"], basic_auth=(conf["username"], conf["password"]))
group = 'jira-software-users'

def get_all_user_in_group(group)
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

def add_user_to_group(self, username, group):
    """Add a user to an existing group.

    :param username: Username that will be added to specified group.
    :param group: Group that the user will be added to.
    :return: json response from Jira server for success or a value that evaluates as False in case of failure.
    """
    url = self._options['server'] + '/rest/api/latest/group/user'
    x = {'groupname': group}
    y = {'name': username}

    payload = json.dumps(y)

    r = json_loads(self._session.post(url, params=x, data=payload))
    if 'name' not in r or r['name'] != group:
        return False
    else:
        return r

users = get_all_user_in_group(group)
for user in users:
    u = get_user(jira, user, accountId=user['accountId'])
    print(u)





# Atlassian jira
jira = Jira(url=conf["url"], username=conf["username"], password=conf["password"])
jira.get_all_users_from_group(group)
