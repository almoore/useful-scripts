#!/usr/bin/env python
import stashy
import json
import getpass
import os
import re
import requests
import base64
import argparse
import logging

parser = argparse.ArgumentParser()
parser.add_argument('--name', action='store', help='The name of the repo to update permissions on.')
parser.add_argument('--match', action='store', default="", help='A regex to match the name of the repo to update permissions on.')
parser.add_argument('--project', action='store', default='SALT', help='The project of the repos (default=SALT).')
parser.add_argument('--branch', action='store', default=None, help='The branch to use for the default reviewers (default=prod).')
parser.add_argument('--default-branch', action='store', default='dev', help='The default branch for the the repo(s) (default=dev).')
parser.add_argument('--release-branch', action='store', default='prod', help='The release branch for the the repo(s) to create pull request requirements for (default=prod).')
parser.add_argument('--default-review-file', action='store', help='The file path for the default reviewers. (default=prod_default_reviewers.json)')
parser.add_argument('--no-default-reviewers', action='store_true', help='Disable setting the default reviewers ')
parser.add_argument('--no-default-branch', action='store_true', help='Disable changing the default branch')
parser.add_argument('--delete-permissions', action='store_true', help='Delete permisions and start fresh')
parser.add_argument('--get-default-reviewers', action='store_true', help='Print the default reviewers and exit')
parser.add_argument('--debug', action='store_true', help='Print debug info')
parser.add_argument('-v', dest='verbose', default=0, action='count', help='Increment output verbosity; may be specified multiple times')
args = parser.parse_args()

logger = logging.getLogger('bitbucket-update-permissions')

USER_BASE = os.path.expanduser('~')
conf_path = os.path.join(USER_BASE,'.atlassian-conf.json')
conf = {}
print_configs = False
base_url = "http://p-bitbucket.imovetv.com"

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

def delete_permissions(name, project="SALT"):
    template_url = base_url + "/rest/branch-permissions/2.0/projects/{}/repos/{}/restrictions"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    logger.debug("Calling {}".format(url))
    response = requests.request("GET", url, auth=(conf['username'],conf['password']), headers=headers)
    if response.ok:
        data = response.json()
        for r in data.get('values',[]):
            id_url = "{}/{}".format(url,r['id'])
            logger.debug("Calling DELETE {}".format(id_url))
            response = requests.request("DELETE", id_url, auth=(conf['username'],conf['password']), headers=headers)
            logger.debug("RESPONSE:" + response.text)
    else:
        logger.warn("Failed delete permissions: {}".format(response.reason))

def set_branch_perms(name, project="SALT", branches=None, release_branch='master'):
    if branches is None:
        branches = ["dev","qa","beta","prod"]
    template_url = base_url + "/rest/branch-permissions/2.0/projects/{}/repos/{}/restrictions"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
        }
    loop_index = 0
    for branch in branches:
        loop_index += 1
        payload_dict = {
            "id": loop_index,
            "type": "no-deletes",
            "matcher": {
                "id": "refs/heads/" + branch,
                "displayId": branch,
                "type": {
                    "id": "BRANCH",
                    "name": "Branch"
                },
                "active": True
            },
            "users": [],
            "groups": []
        }
        payload = json.dumps(payload_dict)
        logger.info("SETTING branch permissions for {} branch {}...".format( name, branch ))
        response = requests.request("POST", url, auth=(conf['username'],conf['password']), data=payload, headers=headers)
        logger.debug("RESPONSE:")
        jp(json.loads(response.text))
        # Add the changes to prod branch
        if branch == release_branch:
            payload_dict = {
                "id": loop_index + 1,
                "type": "fast-forward-only",
                "matcher": {
                    "id": "refs/heads/{}".format(release_branch),
                    "displayId": release_branch,
                    "type": {
                        "id": "BRANCH",
                        "name": "Branch"
                    },
                    "active": True
                },
                "users": [],
                "groups": []
            }
            payload = json.dumps(payload_dict)
            logger.info("SETTING branch permissions for {} branch {}...".format( name, branch ))
            response = requests.request("POST", url, auth=(conf['username'],conf['password']), data=payload, headers=headers)
            logger.debug("RESPONSE:")
            jp(json.loads(response.text))
            payload_dict = {
                "id": loop_index + 2,
                "type": "pull-request-only",
                "matcher": {
                    "id": "refs/heads/{}".format(release_branch),
                    "displayId": release_branch,
                    "type": {
                        "id": "BRANCH",
                        "name": "Branch"
                    },
                    "active": True
                },
                "users": [],
                "groups": []
            }
            payload = json.dumps(payload_dict)
            response = requests.request("POST", url, auth=(conf['username'],conf['password']), data=payload, headers=headers)
            logger.debug("RESPONSE:")
            jp(json.loads(response.text))


def save_json(file_name):
    with open(conf_path,'w') as conf_file:
        json.dump(conf,conf_file,indent=2)

def save_conf():
    save_json(conf_path)

# Read the conf file
try:
    if(os.path.exists(conf_path)):
        with open(conf_path,'r') as conf_file:
            conf = json.load(conf_file)
except ValueError:
    # Json probably invalid
    # do something here if needed
    logger.error('Decoding JSON has failed: ' + conf_path)

# Set defaults
# Get user input if needed
if not conf.get('username'):
    conf['username'] = str(raw_input('Enter your bitbucket username: '))

if not conf.get('password'):
    conf['password'] = getpass.getpass()

conf['clone_type'] = conf.get('clone_type','ssh')
conf['enable_all'] = conf.get('enable_all',True)
conf['project'] = conf.get('project','salt')

# Save config
save_conf()

bitbucket = stashy.connect(base_url, conf['username'],conf['password'])

def jp(data, log_level=logging.DEBUG):
    logger.log(level=log_level, msg=json.dumps(data,indent=4))

def set_pull_requests_settings(name, project="SALT"):
    template_url = base_url + "/rest/api/1.0/projects/{}/repos/{}/settings/pull-requests"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    payload_dict = {
        "unapproveOnUpdate": True
    }
    payload = json.dumps(payload_dict)
    logger.debug("SETTING pull-request Unapprove On Update for {} ...".format( name ))
    response = requests.request("POST", url, auth=(conf['username'],conf['password']), data=payload, headers=headers)
    logger.debug("RESPONSE:")
    jp(json.loads(response.text))

def check_reviewer_entry(entry, default_reviewers):
    reviewers = entry['reviewers']
    for item in reviewers:
        try:
            del item['links']
        except:
            pass
    if reviewers == default_reviewers:
        return True
    for reviewer in default_reviewers:
        if not reviewer in reviewers:
            logger.debug(reviewer)
            return False
    return True


def check_reviewers(name, project="SALT"):
    template_url = base_url + "/rest/default-reviewers/1.0/projects/{}/repos/{}/conditions"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    file_name = os.path.join(__location__, 'prod_default_reviewers.json')
    default_reviewers = []
    try:
        if os.path.exists(file_name):
            with open(file_name,'r') as conf_file:
                data = json.load(conf_file)
                default_reviewers = data.get('reviewers', [])
        else:
            logger.error("File not found {}".format(file_name) )
    except ValueError:
        # Json probably invalid
        # do something here if needed
        logger.error('Decoding JSON has failed: ' + file_name)
    response = requests.request("GET", url, auth=(conf['username'],conf['password']), headers=headers)
    if response.ok:
        data = response.json()
        for entry in data:
            if not check_reviewer_entry(entry, default_reviewers):
                return False
        return True
    else:
        return False


def get_default_reviewers(name, project="SALT"):
    template_url = base_url + "/rest/default-reviewers/1.0/projects/{}/repos/{}/conditions"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    reviewers = {}
    response = requests.request("GET", url, auth=(conf['username'],conf['password']), headers=headers)
    if response.ok:
        reviewers = response.json()
    return reviewers

def get_reviewer_list(name, project="SALT"):
    template_url = base_url + "/rest/default-reviewers/1.0/projects/{}/repos/{}/conditions"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    reviewers = []
    response = requests.request("GET", url, auth=(conf['username'],conf['password']), headers=headers)
    if response.ok:
        for item in response.json():
            if 'reviewers' in  item:
                reviewers.append(item)
    return reviewers


def delete_non_matching_reviewers(name, project='SALT', reviewers=None):
    template_url = base_url + "/rest/default-reviewers/1.0/projects/{}/repos/{}/condition/{}"
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    if reviewers is None:
        try:
            file_name = os.path.join(__location__, 'prod_default_reviewers.json')
            if os.path.exists(file_name):
                with open(file_name,'r') as conf_file:
                    data = json.load(conf_file)
                    reviewers = data.get('reviewers', [])
            else:
                logger.error("File not found {}".format(file_name) )
        except:
            # Json probably invalid
            # do something here if needed
            logger.error('Decoding JSON has failed: ' + file_name)
    rl = get_reviewer_list(name=name,project=project)
    logger.debug('Found {} enteries for reviewers in {}'.format(len(rl), name))
    match_found = False
    for r in rl:
        match = check_reviewer_entry(r, reviewers)
        # Remove duplicate enteries
        if not match or match_found and match:
            url = template_url.format(project,name, r['id'])
            logger.debug("running delete on {}".format(url))
            response = requests.request("DELETE", url, auth=(conf['username'],conf['password']), headers=headers)
            logger.debug('response.ok = {}'.format(response.ok))
        else:
            match_found = True


def set_default_reviewers(name, project="SALT", file_name=None):
    template_url = base_url + "/rest/default-reviewers/1.0/projects/{}/repos/{}/condition"
    url = template_url.format(project,name)
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    payload_dict = {}
    if file_name is None:
        file_name = os.path.join(__location__, 'prod_default_reviewers.json')
    try:
        if os.path.exists(file_name):
            with open(file_name,'r') as conf_file:
                payload_dict = json.load(conf_file)
        else:
            logger.error("File not found {}".format(file_name) )
    except ValueError:
        # Json probably invalid
        # do something here if needed
        logger.error('Decoding JSON has failed: ' + file_name)
    rl = get_reviewer_list(name=name, project=project)
    if len(rl) == 0:
        if payload_dict:
            # only do this if payload is valid
            payload = json.dumps(payload_dict)
            logger.info("SETTING default-reviewers for {} ...".format( name ))
            response = requests.request("POST", url, auth=(conf['username'],conf['password']), data=payload, headers=headers)
            if response.ok:
                logger.debug("RESPONSE:")
                jp(json.loads(response.text))
            else:
                logger.error("Got back a response of {}".format(response.status_code))
                logger.error("Reason {}".format(response.reason))
    if len(rl) > 1:
        logger.debug("calling delete_non_matching_reviewers")
        delete_non_matching_reviewers(name=name, project=project, reviewers=payload_dict)


def set_default_branch(name, project="SALT", branch="dev"):
    repo = bitbucket.projects[project].repos[name]
    branches  = [ b["displayId"] for b in repo.branches() ]
    if branch in branches:
        repo.default_branch = branch


def get_repo_list(project="salt", match=""):
    repos = []
    for repo in bitbucket.projects[project].repos.list():
        if match == "" or re.match(match, repo.get('name')): 
            repos.append(repo.get('name'))
    return repos


def run():
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    if args.verbose:
        logger.setLevel(max(logging.ERROR - (args.verbose * 10), 1))
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.info("Gathering repos...")
    repo_list = []
    if args.project and args.name:
        try:
            repo_list.append(bitbucket.projects[args.project].repos[args.name].get().get('name'))
            jp(repo_list)
        except Exception as e:
            logger.error(e)
            pass
    else:
        repo_list = get_repo_list(args.project, args.match)
    branches = None
    if args.branch is not None:
        branches = [ args.branch ]
    logger.info("Found ({}) configs in project".format(len(repo_list)))
    #jp(repo_list)
    if args.name and args.name in repo_list:
        if args.delete_permissions:
            delete_permissions(args.name, project=args.project)
        if args.get_default_reviewers:
            jp(get_default_reviewers(args.name, project=args.project), log_level=logging.INFO)
            exit()
        set_branch_perms(args.name, project=args.project, branches=branches, release_branch=args.release_branch)
        if not args.no_default_branch:
            set_default_branch(args.name, project=args.project, branch=args.default_branch)
        if not args.no_default_reviewers:
            set_default_reviewers(args.name, project=args.project)
    else:
        for repo in repo_list:
            logger.debug("Starting on repo " + repo)
            if args.delete_permissions:
                delete_permissions(repo, project=args.project)
            set_branch_perms(repo, project=args.project, branches=branches, release_branch=args.release_branch)
            if not args.no_default_branch:
                set_default_branch(repo, project=args.project, branch=args.default_branch)
            if not args.no_default_reviewers:
                set_default_reviewers(repo, project=args.project)

if __name__ == '__main__':
    run()
