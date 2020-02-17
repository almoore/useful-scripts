#!/usr/bin/env python
import stashy
import json
import getpass 
import os
import requests
import base64
import argparse
import shutil
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('name', help='The name of the repos to create.')
parser.add_argument('-d', '--delete', action='store_true', help='Delete Repo.')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging.')
parser.add_argument('-n', '--new', action='store_true', help='Fail if the repo already exists.')
parser.add_argument('-p', '--project', help='Set the project to use.')
args = parser.parse_args()

USER_BASE = os.path.expanduser('~')
conf_path = os.path.join(USER_BASE,'.atlassian-conf.json')
conf = {}
print_configs = False

def copy(src,dest):
    shutil.copyfile(src, dest)

def save_json(path,data):
    with open(path,'w') as f:
        json.dump(data,f,indent=2)

def save_config():
    # backup the file
    dir_name, file_name = os.path.split(conf_path)
    bk_name = os.path.join(tempfile.gettempdir(),file_name)
    if(os.path.isfile(conf_path)):
        copy(conf_path,bk_name)
    try:
        save_json(conf_path, conf)
    except Exception as e:
        # print error and restore backup
        print('Got error while saving config {} ERROR: {}'.format(conf_path,e))
        if(os.path.isfile(bk_name)):
            print("Restoring file to previous state")
            copy(bk_name,conf_path)

def jp(data):
    print(json.dumps(data,indent=4))

# Read the conf file
try:
    if(os.path.exists(conf_path)):
        with open(conf_path,'r') as conf_file:
            conf = json.load(conf_file)
except ValueError:
    # Json probably invalid
    # do something here if needed
    print('Decoding JSON has failed: ' + conf_path)
# Set defaults
# Get user input if needed
if not conf.get('username'):
    conf['username'] = str(raw_input('Enter your bitbucket username: '))
if not conf.get('password'):
    conf['password'] = getpass.getpass()
conf['clone_type'] = conf.get('clone_type','ssh')
conf['enable_all'] = conf.get('enable_all',True)
conf['project'] = conf.get('project','salt')
if args.project:
    conf['project'] = args.project
# Save config
save_config()

def get_repo_list(bitbucket,project='salt'):
    repos = []
    for repo in bitbucket.projects[project].repos.list():
        repos.append(repo.get('name'))
    return repos

def run():
    bitbucket = stashy.connect("http://p-bitbucket.imovetv.com", conf['username'],conf['password'])
    if args.verbose:
        print("Args",args)
    repo_list = get_repo_list(bitbucket,project=conf['project'])
    if args.delete:
        print("Deleting repo {}".format(args.name))
        bitbucket.projects[conf['project']].repos[args.name].delete()
    elif args.name in repo_list:
        print("Repos name ({}) already exists".format(args.name))
        if args.new:
            print("New flag set failing ...")
            exit(1)
    else:
        print("Creating repo {}".format(args.name))
        bitbucket.projects[conf['project']].repos.create(args.name)

if __name__ == '__main__':
    run()
