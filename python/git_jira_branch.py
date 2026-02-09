#!/usr/bin/env python3
"""
Description: A util for creating git branch names from jira issue key and summary
Usage: run directly using python or add it to your path with a name like
       'git-jira-branch' and git will pick it up as a plugin. You can then run
       things like 'git jira-branch <issue key>' and it will create and checkout
       a branch.
"""
import os
import json
import argparse
import getpass
from subprocess import Popen, PIPE
import contextlib
import shutil
import tempfile
import re

try:
    from jira import JIRA, JIRAError
except ModuleNotFoundError:
    print("jira module not found please install it:\n\tpip install jira")
    exit(1)

try:
    import keyring
    HAS_KEYRING_PY = True
except ImportError:
    HAS_KEYRING_PY = False


def parse_args():
    user_base = os.path.expanduser('~')
    conf_path = os.path.join(user_base, '.atlassian-conf.json')
    parser = argparse.ArgumentParser()
    parser.add_argument('issue', help='The ticket number to start from')
    parser.add_argument('-p', '--prefix', help='Specify a prefix to use that will be joined with \'/\'')
    parser.add_argument('--conf', default=os.environ.get("GIT_JIRA_CONF", conf_path),
                        help='The location to read conf data from')
    parser.add_argument('--url', default=os.environ.get("JIRA_URL"),
                        help='The jira url')
    parser.add_argument('--profile', default=os.environ.get("JIRA_PROFILE", "default"),
                        help='The jira profile')
    parser.add_argument('--force-password', default=False, action='store_true',
                        help='Force prompting for password (useful when token has expired)')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='More verbose logging')
    parser.add_argument('-d', '--dry-run', default=False, action='store_true',
                        help='Show what would be done, without making changes')
    return parser.parse_args()


def copy(src, dest):
    shutil.copyfile(src, dest)


def save_json(path, data):
    with open(path,'w') as f:
        json.dump(data,f,indent=2)


def save_conf(conf_path, conf):
    # backup the file
    dir_name, file_name = os.path.split(conf_path)
    bk_name = os.path.join(tempfile.gettempdir(),file_name)
    if os.path.isfile(conf_path):
        print("Creating back copy of conf file")
        copy(conf_path, bk_name)
    try:
        save_json(conf_path, conf)
        print("Wrote conf file to {}".format(conf_path))
    except Exception as e:
        # print error and restore backup
        print('Got error while saving config {} ERROR: {}'.format(conf_path, e))
        if os.path.isfile(bk_name):
            print("Restoring file to previous state")
            copy(bk_name, conf_path)


def get_user_auth_input(conf):
    """
    Get the username and password from user input prompt
    :param conf: dict with current
    :return: conf with user input
    """
    if not conf.get('username'):
        conf['username'] = str(input('Enter your jira username: '))
    if not conf.get('password'):
        conf['password'] = getpass.getpass()
    return conf


def get_conf(conf_path):
    conf = {}
    try:
        with contextlib.suppress(FileNotFoundError):
            with open(conf_path) as fs:
                conf = json.load(fs)
    except ValueError:
        print('Decoding JSON has failed: ' + conf_path)
    return conf


def auth(args):
    full_conf = get_conf(conf_path=args.conf)
    conf = full_conf.get(args.profile, {})
    conf_orig = conf.copy()
    url = args.url
    if not conf.get("url"):
        conf["url"] = url
    if url is None and not conf.get("url"):
        conf["url"] = str(input('Enter your jira url: '))
    if args.force_password:
        conf.pop("password", None)
    if HAS_KEYRING_PY and conf.get("username") and not args.force_password:
        if args.verbose:
            print("Getting password from keyring {url}: {username}".format(**conf))
        conf["password"] = keyring.get_password(conf["url"], conf["username"])
    conf = get_user_auth_input(conf)
    if HAS_KEYRING_PY and conf.get("password"):
        keyring.set_password(conf["url"], conf["username"], conf["password"])
        _conf = { k: v for k, v in conf.items() if k != "password"}
        if conf_orig != _conf:
            full_conf[args.profile] = _conf
            save_conf(conf_path=args.conf, conf=full_conf)
    else:
        if conf_orig != conf:
            full_conf[args.profile] = conf
            save_conf(conf_path=args.conf, conf=full_conf)
    return conf


def run(command):
    """
    Create a generator to a shell command with async output yielded
    :param command:
    :return:
    """
    process = Popen(command, stdout=PIPE, shell=True)
    while True:
        line = process.stdout.readline().rstrip()
        if not line:
            break
        yield line.decode('utf-8')


def run_command(command, verbose=False, dry=False):
    """
    Get output from command printed to stdout
    :param command: the command to run in the shell
    :param verbose: print command before executing it
    :param dry: print command do not execute
    """
    if verbose or dry:
        print(command)
        if dry:
            return
    for line in run(command):
        print(line)


def normalize_dashes(text: str):
    """
    Change multiple dashes in a row to one
    :param text: input string
    :return: a string with the dashes replaced
    """
    while '--' in text:
        text = text.replace('--', '-')
    return text


def replace_multiple(main_string, replacements, new_string):
    """
    Replace a set of multiple sub strings with a new string in main string.
    :param main_string:
    :param replacements:
    :param new_string:
    :return:
    """
    # Iterate over the strings to be replaced
    for elem in replacements :
        # Check if string is in the main string
        if elem in main_string :
            # Replace the string
            main_string = main_string.replace(elem, new_string)
    return main_string


def create_slug(text: str, lower=True):
    s = normalize_dashes(re.sub('[^a-zA-Z0-9_-]', '-', text).strip('-'))
    if lower:
        s = s.lower()
    return s


def main():
    args = parse_args()
    conf = auth(args)
    try:
        jira = JIRA(server=conf["url"],
                    basic_auth=(conf["username"], conf["password"]))
        issue = jira.issue(args.issue)
        summary = str(issue.fields.summary)
        if args.dry_run:
            print("DRY RUN: Command that would be run...")
        if args.verbose:
            print("Got summary:", summary)
        slug = create_slug(summary)
        if args.verbose:
            print("Created slug:", slug)
        branch_name = "{id}-{desc}".format(id=issue, desc=slug)
        if args.prefix:
            branch_name = "{}/{}".format(args.prefix, branch_name)
        run_command("git branch {}".format(branch_name),
                    verbose=args.verbose, dry=args.dry_run)
        run_command("git checkout {}".format(branch_name),
                    verbose=args.verbose, dry=args.dry_run)
    except JIRAError as e:
        print(e.text)
        pass


if __name__ == '__main__':
    main()
