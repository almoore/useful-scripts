#!/usr/bin/env python3
"""
Shared Jira authentication utilities.

Handles reading config from ~/.atlassian-conf.json, keyring integration,
and interactive credential prompts. Used by git_jira_branch.py,
jira_reassign_children.py, jira_tools.py, and jira_uses_list.py.

Config file format (~/.atlassian-conf.json):
    {
        "default": {
            "url": "https://your-org.atlassian.net",
            "username": "you@example.com"
        }
    }

Passwords are stored/retrieved via the system keyring when available.
"""
import os
import json
import getpass
import contextlib
import shutil
import tempfile

try:
    from jira import JIRA
except ModuleNotFoundError:
    print("jira module not found please install it:\n\tpip install jira")
    exit(1)

try:
    import keyring
    HAS_KEYRING_PY = True
except ImportError:
    HAS_KEYRING_PY = False

DEFAULT_CONF_PATH = os.path.join(os.path.expanduser('~'), '.atlassian-conf.json')


def get_conf(conf_path):
    """Load the full config dict from a JSON file."""
    conf = {}
    try:
        with contextlib.suppress(FileNotFoundError):
            with open(conf_path) as fs:
                conf = json.load(fs)
    except ValueError:
        print('Decoding JSON has failed: ' + conf_path)
    return conf


def save_conf(conf_path, conf):
    """Save config to JSON file with backup/restore on failure."""
    dir_name, file_name = os.path.split(conf_path)
    bk_name = os.path.join(tempfile.gettempdir(), file_name)
    if os.path.isfile(conf_path):
        shutil.copyfile(conf_path, bk_name)
    try:
        with open(conf_path, 'w') as f:
            json.dump(conf, f, indent=2)
    except Exception as e:
        print('Got error while saving config {} ERROR: {}'.format(conf_path, e))
        if os.path.isfile(bk_name):
            shutil.copyfile(bk_name, conf_path)


def get_user_auth_input(conf):
    """Prompt for username and/or password if not already set."""
    if not conf.get('username'):
        conf['username'] = str(input('Enter your jira username: '))
    if not conf.get('password'):
        conf['password'] = getpass.getpass()
    return conf


def auth(args):
    """Authenticate using config file, keyring, and interactive prompts.

    Expects args to have: conf, profile, url, force_password, verbose.
    Returns a dict with url, username, password.
    """
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
        if getattr(args, 'verbose', False):
            print("Getting password from keyring {url}: {username}".format(**conf))
        conf["password"] = keyring.get_password(conf["url"], conf["username"])
    conf = get_user_auth_input(conf)
    if HAS_KEYRING_PY and conf.get("password"):
        keyring.set_password(conf["url"], conf["username"], conf["password"])
        _conf = {k: v for k, v in conf.items() if k != "password"}
        if conf_orig != _conf:
            full_conf[args.profile] = _conf
            save_conf(conf_path=args.conf, conf=full_conf)
    else:
        if conf_orig != conf:
            full_conf[args.profile] = conf
            save_conf(conf_path=args.conf, conf=full_conf)
    return conf


def setup_jira_client(force_password=False, verbose=False, profile=None,
                      conf_path=None):
    """Quick setup: load config, authenticate, return a JIRA client.

    Simpler alternative to auth() that doesn't require an argparse namespace.
    """
    profile = profile or os.getenv('JIRA_PROFILE', 'default')
    conf_path = conf_path or DEFAULT_CONF_PATH
    full_conf = get_conf(conf_path=conf_path)
    conf = full_conf.get(profile, {})
    if force_password:
        conf.pop("password", None)
    if HAS_KEYRING_PY and conf.get("username") and not force_password:
        if verbose:
            print("Getting password from keyring {url}: {username}".format(**conf))
        conf["password"] = keyring.get_password(conf["url"], conf["username"])
    conf = get_user_auth_input(conf)
    if HAS_KEYRING_PY and conf.get("password"):
        keyring.set_password(conf["url"], conf["username"], conf["password"])
    return JIRA(server=conf["url"], basic_auth=(conf["username"], conf["password"]))


def add_auth_arguments(parser):
    """Add common Jira auth arguments to an argparse parser."""
    parser.add_argument('--conf', default=os.environ.get("GIT_JIRA_CONF", DEFAULT_CONF_PATH),
                        help='The location to read conf data from')
    parser.add_argument('--url', default=os.environ.get("JIRA_URL"),
                        help='The jira url')
    parser.add_argument('--profile', default=os.environ.get("JIRA_PROFILE", "default"),
                        help='The jira profile')
    parser.add_argument('--force-password', default=False, action='store_true',
                        help='Force prompting for password (useful when token has expired)')
