"""
Shared Atlassian authentication utilities for CAB scripts.

Uses ~/.atlassian-conf.json for config and system keyring for password storage.
Compatible with the auth pattern from useful-scripts/python/jira_auth.py.

Config file format (~/.atlassian-conf.json):
    {
        "default": {
            "url": "https://your-org.atlassian.net",
            "username": "you@example.com",
            "jira_server_id": "BP8Q-WXN6-SKX3-NB5M"
        }
    }
"""

import contextlib
import getpass
import json
import os
import shutil
import sys
import tempfile

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

DEFAULT_CONF_PATH = os.path.join(os.path.expanduser("~"), ".atlassian-conf.json")


def get_conf(conf_path=DEFAULT_CONF_PATH):
    """Load the full config dict from a JSON file."""
    conf = {}
    try:
        with contextlib.suppress(FileNotFoundError):
            with open(conf_path) as fs:
                conf = json.load(fs)
    except ValueError:
        print(f"Decoding JSON has failed: {conf_path}", file=sys.stderr)
    return conf


def save_conf(conf_path, conf):
    """Save config to JSON file with backup/restore on failure."""
    _, file_name = os.path.split(conf_path)
    bk_name = os.path.join(tempfile.gettempdir(), file_name)
    if os.path.isfile(conf_path):
        shutil.copyfile(conf_path, bk_name)
    try:
        with open(conf_path, "w") as f:
            json.dump(conf, f, indent=2)
    except Exception as e:
        print(f"Error saving config {conf_path}: {e}", file=sys.stderr)
        if os.path.isfile(bk_name):
            shutil.copyfile(bk_name, conf_path)


def get_auth(profile=None, conf_path=None, force_password=False):
    """Authenticate using config file, keyring, and interactive prompts.

    Returns (base_url, username, password) tuple suitable for requests auth.
    """
    profile = profile or os.getenv("JIRA_PROFILE", "default")
    conf_path = conf_path or DEFAULT_CONF_PATH
    full_conf = get_conf(conf_path=conf_path)
    conf = full_conf.get(profile, {})
    conf_orig = conf.copy()

    if not conf.get("url"):
        conf["url"] = input("Enter your Atlassian URL: ").strip()
    if force_password:
        conf.pop("password", None)
    if HAS_KEYRING and conf.get("username") and not force_password:
        conf["password"] = keyring.get_password(conf["url"], conf["username"])
    if not conf.get("username"):
        conf["username"] = input("Enter your Atlassian username: ").strip()
    if not conf.get("password"):
        conf["password"] = getpass.getpass("Enter your Atlassian API token: ")

    # Persist to keyring and config (without password in config file)
    if HAS_KEYRING and conf.get("password"):
        keyring.set_password(conf["url"], conf["username"], conf["password"])
        save_data = {k: v for k, v in conf.items() if k != "password"}
        if conf_orig != save_data:
            full_conf[profile] = save_data
            save_conf(conf_path=conf_path, conf=full_conf)
    elif conf_orig != conf:
        full_conf[profile] = conf
        save_conf(conf_path=conf_path, conf=full_conf)

    return conf["url"], conf["username"], conf["password"]


def get_jira_server_id(base_url, auth, profile=None, conf_path=None,
                       space_key=None, page_body=None):
    """Get the Jira server ID used in Confluence Jira macros.

    Checks config first. If not found, tries to extract from the provided
    page_body, then falls back to searching the given space (or any space)
    for a page with a Jira macro. Caches the result in config.
    """
    import re
    import requests

    profile = profile or os.getenv("JIRA_PROFILE", "default")
    conf_path = conf_path or DEFAULT_CONF_PATH
    full_conf = get_conf(conf_path=conf_path)
    conf = full_conf.get(profile, {})

    # Return cached value if present
    if conf.get("jira_server_id"):
        return conf["jira_server_id"]

    # Try extracting from the provided page body first
    if page_body:
        match = re.search(r'ac:name="serverId">([^<]+)<', page_body)
        if match:
            server_id = match.group(1)
            conf["jira_server_id"] = server_id
            full_conf[profile] = conf
            save_conf(conf_path=conf_path, conf=full_conf)
            print(f"Cached jira_server_id: {server_id}", file=sys.stderr)
            return server_id

    # Discover by searching for a page with a Jira macro
    print("Discovering Jira server ID from Confluence...", file=sys.stderr)
    cql = 'macro = "jira"'
    if space_key:
        cql += f' and space = "{space_key}"'
    resp = requests.get(
        f"{base_url}/wiki/rest/api/content/search",
        params={"cql": cql, "limit": 1, "expand": "body.storage"},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        print("Error: Could not find any Confluence page with a Jira macro.", file=sys.stderr)
        print("Set jira_server_id manually in ~/.atlassian-conf.json", file=sys.stderr)
        sys.exit(1)

    body = results[0].get("body", {}).get("storage", {}).get("value", "")
    match = re.search(r'ac:name="serverId">([^<]+)<', body)
    if not match:
        print("Error: Found a page with Jira macro but could not extract serverId.", file=sys.stderr)
        sys.exit(1)

    server_id = match.group(1)

    # Cache in config
    conf["jira_server_id"] = server_id
    full_conf[profile] = conf
    save_conf(conf_path=conf_path, conf=full_conf)
    print(f"Cached jira_server_id: {server_id}", file=sys.stderr)

    return server_id


def add_auth_arguments(parser):
    """Add common auth arguments to an argparse parser."""
    parser.add_argument(
        "--conf", default=os.environ.get("GIT_JIRA_CONF", DEFAULT_CONF_PATH),
        help="Config file path (default: ~/.atlassian-conf.json)",
    )
    parser.add_argument(
        "--profile", default=os.environ.get("JIRA_PROFILE", "default"),
        help="Config profile name (default: default)",
    )
    parser.add_argument(
        "--force-password", default=False, action="store_true",
        help="Force prompting for password (useful when token has expired)",
    )
