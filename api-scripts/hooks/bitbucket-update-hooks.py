#!/usr/bin/env python
import stashy
import json
import getpass
import os
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--name', help='The name of the repos to create.')
parser.add_argument('--project', action='store', default='SALT', help='The project of the repos (default=SALT).')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging.')
parser.add_argument('-K', '--keep-configs', action='store_false', help='Keep configs and do not force overwrite them.')
args = parser.parse_args()

conf = {}
USER_BASE = os.path.expanduser('~')
conf_path = os.path.join(USER_BASE,'.atlassian-conf.json')
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
    print('Decoding JSON has failed: {}'.format(conf_path))

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

bitbucket = stashy.connect("http://p-bitbucket.imovetv.com", conf['username'],conf['password'])

def jp(data):
    print(json.dumps(data,indent=4))

def print_hook(repo_name, hook_key, project='salt'):
    settings = bitbucket.projects[project].repos[repo_name].settings.hooks[hook_key].settings()
    jp(settings)

def get_hook(repo_name, hook_key, project='salt'):
    settings = bitbucket.projects[project].repos[repo_name].settings.hooks[hook_key].settings()
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
    "branchOptions": "",
    "cloneType": "ssh"
}

def set_hook(repo_name, hook_key, project='salt', **kwargs):
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
    return bitbucket.projects[project].repos[repo_name].settings.hooks[hook_key].configure(hook_dict)

def set_jenkins_hooks(names=[], clone_type='ssh', overwrite=False, project='salt'):
    changes = []
    for repo in bitbucket.projects[project].repos.list():
        name = repo.get('name')
        clone_link = ""
        if name in names:
            for link in repo['links']['clone']:
                if link['name'] == clone_type:
                    clone_link = link['href']

            for hook in bitbucket.projects[project].repos[name].settings.hooks.list():
                details = hook['details']
                update_config = not hook['configured']
                if hook['configured'] and overwrite:
                    update_config = True
                if details['name'] == 'Bitbucket Server Webhook to Jenkins' and details['type'] == 'POST_RECEIVE' and update_config:
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
                    hook = bitbucket.projects[project].repos[name].settings.hooks[details['key']].enable()
                    hook['settings'] = ret_set
                    print("Post change vals:")
                    jp(hook)
                    changes.append(hook)
    return changes

def get_disabled(project='salt'):
    repos = []
    for repo in bitbucket.projects[project].repos.list():
        name = repo.get('name')
        links = repo['links']['self']
        for hook in bitbucket.projects[project].repos[name].settings.hooks.list():
            details = hook['details']
            if details['name'] == 'Bitbucket Server Webhook to Jenkins' and details['type'] == 'POST_RECEIVE' and not hook['enabled']:
                link = links[0]['href']
                repos.append({'name': name, 'link': link})
    return repos

def get_repo_configs(repo_name="", project='salt'):
    # Gather the repos
    repos = []
    repo_configs = []
    if repo_name:
        repos = [ bitbucket.projects[project].repos[repo_name].get() ]
    else:
        repos = bitbucket.projects['salt'].repos.list()
    if args.verbose:
        print("REPOS")
        jp(repos)
    for repo in repos:
        if args.verbose:
            print("REPO CONFIG")
            jp(repo)
        name = repo.get('name')
        links = repo['links']['self']
        for hook in bitbucket.projects[project].repos[name].settings.hooks.list():
            details = hook['details']
            if args.verbose:
                print("Found hook for {} ( {} )".format(name, details['name']))
            if details['name'] == 'Bitbucket Server Webhook to Jenkins' and details['type'] == 'POST_RECEIVE':
                hook_config = get_hook(name, details['key'], project=project)
                repo_configs.append({'name': name, 'config': hook_config })
    return repo_configs


def run():
    if args.verbose:
        print(args)
        #exit()
    if args.name:
        repo_configs = get_repo_configs(args.name, args.project)
    else:
        print("Gathering repo configs...")
        repo_configs = get_repo_configs(args.project)
    print("Found ({}) configs in project".format(len(repo_configs)))
    if print_configs:
        print("Here are the repo configs: ")
        jp(repo_configs)

    update_list = []
    for repo in repo_configs:
        if args.verbose:
            print("Filtering config files.")
        config = repo.get('config', {} )
        is_empty = type(config) is unicode
        if is_empty or not config.get('gitRepoUrl','').startswith(conf['clone_type']):
            if args.verbose:
                print("Added ({})".format(repo['name']))
            update_list.append(repo['name'])

    if conf['enable_all']:
        disabled = get_disabled(args.project)
        for repo in disabled:
            if repo['name'] not in update_list:
                update_list.append(repo['name'])
    if len(update_list):
        print("Here is the list of repos being updated.")
        jp(update_list)
        set_jenkins_hooks(update_list, overwrite=args.keep_configs)
    else:
        print("No repo hooks need to be updated.")

if __name__ == '__main__':
    run()
