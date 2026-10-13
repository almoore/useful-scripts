#!/usr/bin/env python3
"""Show or change TF_CLI_ARGS targeting on a Terraform Enterprise workspace.

TF_CLI_ARGS is a workspace environment variable that silently scopes every run
in that workspace. Set once for a one-off `-target` operation and forgotten, it
freezes the workspace: plans look clean because most of the configuration is
never evaluated. Nothing in the run UI makes it obvious.

This prints the targeting state of a workspace, and can park it (rename to
X_TF_CLI_ARGS, the convention for "kept but inactive"), unpark it, clear it, or
set it from a file.

Exits 1 when targeting is active and --quiet-ok was not passed, so it can be
used as a pre-flight check before a release.

Credentials are read from ~/.terraform.d/credentials.tfrc.json or
~/.terraformrc, matching tfe-review.py.

Usage:
    tfe-targets CDIG/my-workspace --hostname tfe.example.com
    tfe-targets ws-AbC123 --hostname tfe.example.com
    tfe-targets https://tfe.example.com/app/CDIG/workspaces/my-workspace
    tfe-targets CDIG/my-workspace --park      # disable, keep the value
    tfe-targets CDIG/my-workspace --unpark    # re-enable a parked value
    tfe-targets CDIG/my-workspace --clear     # delete it entirely
    tfe-targets CDIG/my-workspace --set targets.txt
"""

import argparse
import json
import os
import re
import sys

import requests

DEFAULT_HOSTNAME = "app.terraform.io"
API_TIMEOUT = 30
ACTIVE = "TF_CLI_ARGS"
PARKED = "X_TF_CLI_ARGS"
# Both "-target foo" and "-target=foo" are valid; count either.
TARGET_RE = re.compile(r"-target[= ]")


def load_token(hostname):
    """Load the TFC/TFE API token for a hostname, or None."""
    creds = os.path.expanduser("~/.terraform.d/credentials.tfrc.json")
    if os.path.isfile(creds):
        try:
            with open(creds) as fh:
                data = json.load(fh)
            token = data.get("credentials", {}).get(hostname, {}).get("token")
            if token:
                return token
        except (json.JSONDecodeError, OSError):
            pass

    rc_path = os.path.expanduser("~/.terraformrc")
    if os.path.isfile(rc_path):
        try:
            with open(rc_path) as fh:
                content = fh.read()
            pattern = (r'credentials\s+"' + re.escape(hostname)
                       + r'"\s*\{[^}]*token\s*=\s*"([^"]+)"')
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)
        except OSError:
            pass
    return None


def api(hostname, token, path, method="GET", payload=None):
    """Authenticated TFC/TFE API call. None on 404 or empty body."""
    url = "https://{}{}".format(hostname, path)
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/vnd.api+json",
    }
    resp = requests.request(method, url, headers=headers, timeout=API_TIMEOUT,
                            data=json.dumps(payload) if payload else None)
    if resp.status_code == 404:
        return None
    if resp.status_code not in (200, 201, 204):
        print("Error: API {} on {} {}".format(resp.status_code, method, path),
              file=sys.stderr)
        print(resp.text[:400], file=sys.stderr)
        sys.exit(1)
    if not resp.content:
        return None
    return resp.json()


def resolve_workspace(hostname, token, target):
    """Return (hostname, workspace_id, label) from id, org/name, or URL."""
    if target.startswith("http"):
        match = re.match(
            r"https?://([^/]+)/app/([^/]+)/workspaces/([^/?#]+)", target)
        if not match:
            print("Error: could not parse a workspace from {}".format(target),
                  file=sys.stderr)
            sys.exit(1)
        hostname = match.group(1)
        target = "{}/{}".format(match.group(2), match.group(3))

    if target.startswith("ws-"):
        data = api(hostname, token, "/api/v2/workspaces/{}".format(target))
        if not data:
            print("Error: workspace {} not found".format(target),
                  file=sys.stderr)
            sys.exit(1)
        name = data["data"]["attributes"].get("name", target)
        return hostname, target, name

    if "/" not in target:
        print("Error: expected ws-ID, ORG/WORKSPACE, or a workspace URL",
              file=sys.stderr)
        sys.exit(1)
    org, name = target.split("/", 1)
    data = api(hostname, token,
               "/api/v2/organizations/{}/workspaces/{}".format(org, name))
    if not data:
        print("Error: workspace {}/{} not found".format(org, name),
              file=sys.stderr)
        sys.exit(1)
    return hostname, data["data"]["id"], name


def env_vars(hostname, token, ws_id):
    """Return {key: var} for the workspace's env-category variables."""
    data = api(hostname, token, "/api/v2/workspaces/{}/vars".format(ws_id))
    out = {}
    for var in (data or {}).get("data", []):
        attrs = var["attributes"]
        if attrs.get("category") == "env":
            out[attrs["key"]] = var
    return out


def describe(key, var):
    """One line describing a targeting variable."""
    value = var["attributes"].get("value") or ""
    count = len(TARGET_RE.findall(value))
    head = value[:60] + ("..." if len(value) > 60 else "")
    return "  {:<16} {:>5} chars  {:>4} targets  {}".format(
        key, len(value), count, head)


def rename(hostname, token, ws_id, var, new_key):
    api(hostname, token,
        "/api/v2/workspaces/{}/vars/{}".format(ws_id, var["id"]),
        method="PATCH",
        payload={"data": {"id": var["id"], "type": "vars",
                          "attributes": {"key": new_key}}})


def main():
    args = parse_args()
    token_host = args.hostname
    token = load_token(token_host)
    if not token and args.target.startswith("http"):
        match = re.match(r"https?://([^/]+)/", args.target)
        if match:
            token_host = match.group(1)
            token = load_token(token_host)
    if not token:
        print("Error: no API token found for {}".format(token_host),
              file=sys.stderr)
        sys.exit(1)

    hostname, ws_id, name = resolve_workspace(token_host, token, args.target)
    variables = env_vars(hostname, token, ws_id)
    active = variables.get(ACTIVE)
    parked = variables.get(PARKED)

    if args.park:
        if not active:
            print("{}: {} is not set, nothing to park".format(name, ACTIVE))
            return
        if parked:
            print("Error: {} already exists; clear or unpark it first".format(
                PARKED), file=sys.stderr)
            sys.exit(1)
        rename(hostname, token, ws_id, active, PARKED)
        print("{}: parked {} -> {}".format(name, ACTIVE, PARKED))
    elif args.unpark:
        if not parked:
            print("{}: {} is not set, nothing to unpark".format(name, PARKED))
            return
        if active:
            print("Error: {} already set; clear it first".format(ACTIVE),
                  file=sys.stderr)
            sys.exit(1)
        rename(hostname, token, ws_id, parked, ACTIVE)
        print("{}: unparked {} -> {}".format(name, PARKED, ACTIVE))
    elif args.clear:
        if not active:
            print("{}: {} is not set".format(name, ACTIVE))
            return
        api(hostname, token,
            "/api/v2/workspaces/{}/vars/{}".format(ws_id, active["id"]),
            method="DELETE")
        print("{}: deleted {} (runs are now untargeted)".format(name, ACTIVE))
    elif args.set:
        with open(args.set) as fh:
            value = fh.read().strip()
        attrs = {"key": ACTIVE, "value": value, "category": "env",
                 "sensitive": False}
        if active:
            api(hostname, token,
                "/api/v2/workspaces/{}/vars/{}".format(ws_id, active["id"]),
                method="PATCH",
                payload={"data": {"id": active["id"], "type": "vars",
                                  "attributes": attrs}})
            print("{}: updated {} ({} targets)".format(
                name, ACTIVE, len(TARGET_RE.findall(value))))
        else:
            api(hostname, token, "/api/v2/workspaces/{}/vars".format(ws_id),
                method="POST",
                payload={"data": {"type": "vars", "attributes": attrs}})
            print("{}: created {} ({} targets)".format(
                name, ACTIVE, len(TARGET_RE.findall(value))))

    variables = env_vars(hostname, token, ws_id)
    active = variables.get(ACTIVE)
    parked = variables.get(PARKED)
    print("\n{} ({})".format(name, ws_id))
    if not active and not parked:
        print("  no TF_CLI_ARGS set: runs are untargeted")
    if active:
        print(describe(ACTIVE, active))
    if parked:
        print(describe(PARKED, parked))

    # An empty TF_CLI_ARGS scopes nothing, so it is not a real freeze.
    scoping = bool(active) and bool(
        TARGET_RE.search(active["attributes"].get("value") or ""))
    if active and not scoping:
        print("\nNote: {} is set but contains no -target, so it does not "
              "scope runs.".format(ACTIVE))
    if scoping:
        print("\nWARNING: targeting is ACTIVE. Every run in this workspace "
              "is scoped by the value above,\n         so a clean plan does "
              "not mean the configuration is clean.")
        if not args.quiet_ok:
            sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show or change TF_CLI_ARGS targeting on a workspace.")
    parser.add_argument(
        "target", help="ws-ID, ORG/WORKSPACE, or a workspace URL")
    parser.add_argument(
        "--hostname", default=DEFAULT_HOSTNAME,
        help="TFC/TFE hostname (default: {})".format(DEFAULT_HOSTNAME))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--park", action="store_true",
                       help="rename TF_CLI_ARGS to X_TF_CLI_ARGS")
    group.add_argument("--unpark", action="store_true",
                       help="rename X_TF_CLI_ARGS back to TF_CLI_ARGS")
    group.add_argument("--clear", action="store_true",
                       help="delete TF_CLI_ARGS entirely")
    group.add_argument("--set", metavar="FILE",
                       help="set TF_CLI_ARGS from the contents of FILE")
    parser.add_argument("--quiet-ok", action="store_true",
                        help="exit 0 even when targeting is active")
    return parser.parse_args()


if __name__ == "__main__":
    main()
