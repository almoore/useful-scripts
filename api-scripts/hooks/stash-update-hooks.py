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
conf['project'] = conf.get('project', 'salt')

# Save config
save_conf()

stash = stashy.connect("http://p-bitbucket.imovetv.com:7990", conf['username'],conf['password'])

def jp(data):
    print(json.dumps(data,indent=4))

def print_hook(repo_name,hook_key):
    settings = stash.projects['salt'].repos[repo_name].settings.hooks[hook_key].settings()
    jp(settings)

def get_hook(repo_name,hook_key):
    settings = stash.projects['salt'].repos[repo_name].settings.hooks[hook_key].settings()
    return settings


hook_settings_list = [
    "ignoreCommitters",
    "branchOptionsBranches",
    "gitRepoUrl",
    "jenkinsBase",
    "branchOptions",
]

hook_settings_defaults = {
    "ignoreCommitters": "",
    "branchOptionsBranches": "",
    "gitRepoUrl": "",
    "jenkinsBase": "http://p-gp2-devopsjenkins-1.imovetv.com",
    "branchOptions": ""
}

def set_hook(repo_name,hook_key,**kwargs):
    # READ MOD WRITE
    hook_dict = hook_settings_defaults
    current = get_hook(repo_name,hook_key)
    if current:
        hook_dict = current
    for key in hook_settings_list:
        if key in kwargs.keys():
            hook_dict[key] = kwargs[key]
    if 'debug' in kwargs and kwargs['debug']:
        jp(hook_dict)
    return stash.projects['salt'].repos[repo_name].settings.hooks[hook_key].configure(hook_dict)

def set_jenkins_hooks(names=[], clone_type='ssh', overwrite=False):
    changes = []
    for repo in stash.projects['salt'].repos.list():
        name = repo.get('name')
        clone_link = ""
        if name in names:
            for link in repo['links']['clone']:
                if link['name'] == clone_type:
                    clone_link = link['href']

            for hook in stash.projects['salt'].repos[name].settings.hooks.list():
                details = hook['details']
                update_config = not hook['configured']
                if hook['configured'] and overwrite:
                    update_config = True
                if details['name'] == 'Stash Webhook to Jenkins' and details['type'] == 'POST_RECEIVE' and update_config:
                    print("Adding hook to: " + name)
                    print("Current vals:")
                    jp(hook)
                    # Setup the the hook
                    ret_set = set_hook(name,details['key'],
                        jenkinsBase = "http://p-gp2-devopsjenkins-1.imovetv.com",
                        gitRepoUrl = clone_link
                    )
                    # Update the local keys and enable
                    print("\nEnabling the hook...")
                    hook = stash.projects['salt'].repos[name].settings.hooks[details['key']].enable()
                    hook['settings'] = ret_set
                    print("Post change vals:")
                    jp(hook)
                    changes.append(hook)
    return changes

def get_disabled():
    repos = []
    for repo in stash.projects['salt'].repos.list():
        name = repo.get('name')
        links = repo['links']['self']
        for hook in stash.projects['salt'].repos[name].settings.hooks.list():
            details = hook['details']
            if details['name'] == 'Stash Webhook to Jenkins' and details['type'] == 'POST_RECEIVE' and not hook['enabled']:
                link = links[0]['href']
                repos.append({'name': name, 'link': link})
    return repos

def get_repo_configs():
    repos = []
    for repo in stash.projects['salt'].repos.list():
        name = repo.get('name')
        links = repo['links']['self']
        for hook in stash.projects['salt'].repos[name].settings.hooks.list():
            details = hook['details']
            if details['name'] == 'Stash Webhook to Jenkins' and details['type'] == 'POST_RECEIVE':
                hook_config = get_hook(name,details['key'])
                repos.append({'name': name, 'config': hook_config })
    return repos



print("Gathering repo configs...")
repo_configs = get_repo_configs()
print("Found ({}) configs in project".format(len(repo_configs)))
if print_configs:
    print("Here are the repo configs: ")
    jp(repo_configs)

update_list = []
for repo in repo_configs:
    config = repo.get('config', {} )
    is_empty = type(config) is unicode
    if is_empty or not config.get('gitRepoUrl','').startswith(conf['clone_type']):
        update_list.append(repo['name'])

if conf['enable_all']:
    disabled = get_disabled()
    for repo in disabled:
        if repo['name'] not in update_list:
            update_list.append(repo['name'])

set_jenkins_hooks(update_list, overwrite=True)
