#!python3
# This script writes out the 'dependencies' files in the salt states.
# It tries hard not to get rid of dependencies already there, but it
# scans the salt states to make sure dependent salt states are declared.
# Simply checkout ALL the salt states to a directory on your FS, like
# for example I have a directory called '~/Development/src/p-bitbucket.imovetv.com/salt'
# that has all the salt states checked out thereunto.
#
# With that directory as the PWD, run this script. It will write a 'dependencies' file
# out to those salt state repos which need one.

import os
import re
import pprint

root_path=os.getcwd()


find_sls = re.compile(r'\.sls$')

def find_modules(path):

    find_module = re.compile(r'^(?P<repository>[^/]+)/+(?P<raw_module>.+)/?$')

    repos_to_modules = {}
    modules_to_repos = {}

    for root, dirs, files in os.walk(path):
        sls_found = False
        for f in files:
            if find_sls.search(f):
                relative = os.path.relpath(root, path)
                stripped_relative = re.sub(r'^[.][/]+', '', relative)
                module_results = find_module.search(stripped_relative)
                if module_results:
                    repository = module_results.group('repository')
                    raw_module = module_results.group('raw_module')
                    module_name = re.sub(r'[/]+', '.', raw_module)

                    if repository in repos_to_modules:
                        repos_to_modules[repository].add(module_name)
                    else:
                        repos_to_modules[repository] = set([module_name])
                    modules_to_repos[module_name] = repository
    return {
        "repos_to_modules": repos_to_modules,
        "modules_to_repos": modules_to_repos
        }

def repo_depfile(repo):
    return os.path.join(repo, "dependencies")

# Cyclomatic complexity LOLZ :O w00t
def find_dependencies(repos, modules_to_repos, path):
    dependencies = {}
    find_include = re.compile(r'^include:')
    find_included = re.compile(r' +- (?P<module>[^\s]+)\s*$')
    find_jinja = re.compile(r'^\s*{%')

    for repo in repos:
        depfile = repo_depfile(repo)
        if os.access(depfile, os.R_OK|os.F_OK):
            with open(depfile, 'r', encoding='utf-8', errors='ignore') as df:
                dependencies[repo] = set(df.read().strip().splitlines())
        for root, dirs, files in os.walk(os.path.join(path, repo)):
            if os.path.basename(root) != "saltstack":
                for f in files:
                    p = os.path.join(root, f)
                    if find_sls.search(f) and os.access(p, os.R_OK|os.F_OK):
                        with open(p, 'r', encoding='utf-8', errors='ignore') as sls:
                            l = sls.readline()
                            while l != '':
                                if find_include.search(l):
                                    l = sls.readline()
                                    included_results = find_included.search(l)
                                    jinja_results = find_jinja.search(l)
                                    while l != '' and (jinja_results or included_results):
                                        if included_results:
                                            included_module = included_results.group('module')
                                            if included_module in modules_to_repos and \
                                              modules_to_repos[included_module] != repo:
                                              dep_repo = modules_to_repos[included_module]
                                              deb_name = 'salt-state-{repo}'.format(repo=dep_repo)
                                              if repo in dependencies:
                                                found_dep = False
                                                for dep in dependencies[repo]:
                                                  if deb_name in dep:
                                                    found_dep = True
                                                    break
                                                if not found_dep:
                                                  dependencies[repo].add(deb_name)
                                              else:
                                                dependencies[repo] = set([deb_name])
                                        l = sls.readline()
                                        included_results = find_included.search(l)
                                        jinja_results = find_jinja.search(l)
                                else:
                                    l = sls.readline()
    return dependencies


def write_depfiles(dependencies, path):
    for repo, deps in dependencies.items():
        with open(os.path.join(path, repo, 'dependencies'), 'w', encoding='utf-8') as depfile:
            for dep in sorted(deps):
                print(dep, file=depfile)

def main():
    path = os.getcwd()
    modules = find_modules(path)
    modules_to_repos = modules["modules_to_repos"]
    repos_to_modules = modules["repos_to_modules"]
    repos = list(repos_to_modules.keys())
    dependencies = find_dependencies(repos, modules_to_repos, path)
    pprint.pprint(dependencies)
    write_depfiles(dependencies, path)

if __name__ == "__main__":
    main()
