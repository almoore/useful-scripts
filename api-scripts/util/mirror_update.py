#/usr/bin/env python
import stashy
import json
import getpass
import os

conf = {}
conf_path = '.conf.json'
print_configs = False

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
    print'Decoding JSON has failed: ',conf_path
    
# Set defaults
# Get user input if needed
if not conf.get('username'):
    conf['username'] = str(raw_input('Enter your stash username: '))
if not conf.get('password'):
    conf['password'] = getpass.getpass()

conf['clone_type'] = conf.get('clone_type','ssh')
conf['enable_all'] = conf.get('enable_all',True)
conf['project'] = conf.get('project','salt')

# Save config
save_conf()

todo_list = []
stash = stashy.connect("http://p-bitbucket.imovetv.com", conf['username'],conf['password'])
bitbucket = stashy.connect("http://p-bitbucket.imovetv.com", conf['username'],conf['password'])

def jp(data):
    print(json.dumps(data,indent=4))

def names(data):
    ret = []
    for d in data:
        ret += [d['name']]
    return ret

def get_todo_list():
    repo_names = names(list(stash.projects['salt'].repos))
    b_repo_names = names(list(bitbucket.projects['salt'].repos))
    return [n for n in repo_names if n not in b_repo_names]

todo_list = get_todo_list()

def create_new_repos(repo_list):
    for r in repo_list:
        bitbucket.projects['salt'].repos.create(r)

def set_default_branch(branch='dev'):
    repo_names = names(list(bitbucket.projects['salt'].repos))
    for name in repo_names:
        bitbucket.projects['salt'].repos[name].default_branch = branch

