#!/usr/bin/env python3
"""Show OPA/Sentinel policy results for a Terraform Cloud/Enterprise run.

`tfe-review` summarizes plan changes but does not read the policy stage, so a
run that plans cleanly and then dies in post-plan looks like an unexplained
failure. This walks the run's task stages, finds each policy evaluation, and
prints the policy sets that did not fully pass along with the rule messages.

Only non-passing outcomes are expanded by default, since a policy set routinely
holds a dozen passing rules. Exits 2 when a mandatory policy failed, so it can
gate a script.

Credentials are read from ~/.terraform.d/credentials.tfrc.json or
~/.terraformrc, matching tfe-review.py.

Usage:
    tfe-policy run-ABC123 --hostname cps-terraform.anthem.com
    tfe-policy https://tfe.example.com/app/Org/workspaces/ws/runs/run-ABC123
    tfe-policy run-ABC123 --all      # include rules that passed
    tfe-policy run-ABC123 --quiet     # rule names only, no messages
"""

import argparse
import json
import os
import re
import sys

import requests

DEFAULT_HOSTNAME = "app.terraform.io"
API_TIMEOUT = 30


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


def api_get(hostname, token, path):
    """Authenticated GET against the TFC/TFE API. None on 404."""
    url = "https://{}{}".format(hostname, path)
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/vnd.api+json",
    }
    resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        print("Error: API {} on GET {}".format(resp.status_code, path),
              file=sys.stderr)
        sys.exit(1)
    return resp.json()


def split_target(target, hostname):
    """Return (hostname, run_id) from a run id or a run URL."""
    if target.startswith("http"):
        match = re.match(
            r"https?://([^/]+)/.*/runs/(run-[A-Za-z0-9]+)", target)
        if not match:
            print("Error: no run id found in {}".format(target),
                  file=sys.stderr)
            sys.exit(1)
        return match.group(1), match.group(2)
    if not target.startswith("run-"):
        print("Error: expected a run id or run URL, got {}".format(target),
              file=sys.stderr)
        sys.exit(1)
    return hostname, target


def find_evaluations(hostname, token, run_id):
    """Return [(stage, policy_evaluation_id)] for a run."""
    stages = api_get(hostname, token,
                     "/api/v2/runs/{}/task-stages".format(run_id))
    found = []
    for stage in (stages or {}).get("data", []):
        attrs = stage["attributes"]
        print("\ntask stage {}  stage={}  status={}".format(
            stage["id"], attrs.get("stage"), attrs.get("status")))
        rels = stage.get("relationships", {})
        evals = rels.get("policy-evaluations", {}).get("data") or []
        for item in evals:
            found.append((attrs.get("stage", "?"), item["id"]))
    return found


def print_legacy_checks(hostname, token, run_id):
    """Older TFE exposes /policy-checks instead of task stages."""
    checks = api_get(hostname, token,
                     "/api/v2/runs/{}/policy-checks".format(run_id))
    data = (checks or {}).get("data", [])
    for check in data:
        attrs = check["attributes"]
        print("\npolicy check {}: status={} result={}".format(
            check["id"], attrs.get("status"),
            json.dumps(attrs.get("result"))))
    if not data:
        print("\nNo policy evaluations on this run.")


def print_outcomes(hostname, token, pe_id, show_all, quiet):
    """Print policy-set outcomes. Returns the mandatory-failure count."""
    mandatory_failed = 0
    outcomes = api_get(
        hostname, token,
        "/api/v2/policy-evaluations/{}/policy-set-outcomes".format(pe_id))
    for outcome in (outcomes or {}).get("data", []):
        attrs = outcome["attributes"]
        counts = attrs.get("result-count") or {}
        failed = counts.get("mandatory-failed") or 0
        mandatory_failed += failed
        bad = (failed + (counts.get("advisory-failed") or 0)
               + (counts.get("errored") or 0))
        if not bad and not show_all:
            continue
        flag = "   << BLOCKING" if failed else ""
        print("\n  policy set: {}  {}{}".format(
            attrs.get("policy-set-name"), json.dumps(counts), flag))
        if attrs.get("error"):
            print("    error: {}".format(attrs["error"]))
        if not attrs.get("overridable", True):
            print("    overridable: false "
                  "(cannot be waived at run time)")
        for rule in (attrs.get("outcomes") or []):
            if rule.get("status") == "passed" and not show_all:
                continue
            print("    [{}/{}] {}".format(
                rule.get("status"), rule.get("enforcement_level"),
                rule.get("policy_name")))
            if rule.get("query"):
                print("        query: {}".format(rule["query"]))
            if quiet:
                continue
            for message in (rule.get("output") or []):
                print("        {}".format(message))
    return mandatory_failed


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show policy results for a TFC/TFE run.")
    parser.add_argument("target", help="run id (run-...) or full run URL")
    parser.add_argument(
        "--hostname", default=DEFAULT_HOSTNAME,
        help="TFC/TFE hostname (default: {})".format(DEFAULT_HOSTNAME))
    parser.add_argument("--all", action="store_true",
                        help="also show policy sets and rules that passed")
    parser.add_argument("--quiet", action="store_true",
                        help="omit the individual rule messages")
    return parser.parse_args()


def main():
    args = parse_args()
    hostname, run_id = split_target(args.target, args.hostname)

    token = load_token(hostname)
    if not token:
        print("Error: no API token found for {}".format(hostname),
              file=sys.stderr)
        sys.exit(1)

    run = api_get(hostname, token, "/api/v2/runs/{}".format(run_id))
    if not run:
        print("Error: run {} not found on {}".format(run_id, hostname),
              file=sys.stderr)
        sys.exit(1)
    attrs = run["data"]["attributes"]
    print("{}  status={}  {!r}".format(
        run_id, attrs.get("status"), attrs.get("message")))

    evaluations = find_evaluations(hostname, token, run_id)
    if not evaluations:
        print_legacy_checks(hostname, token, run_id)
        return

    mandatory_failed = 0
    for stage, pe_id in evaluations:
        detail = api_get(hostname, token,
                         "/api/v2/policy-evaluations/{}".format(pe_id))
        status = (detail or {}).get("data", {}).get(
            "attributes", {}).get("status")
        print("\npolicy evaluation {}  ({})  status={}".format(
            pe_id, stage, status))
        mandatory_failed += print_outcomes(
            hostname, token, pe_id, args.all, args.quiet)

    if mandatory_failed:
        print("\n{} mandatory policy failure(s): this run cannot be applied "
              "until the policy passes or is overridden.".format(
                  mandatory_failed))
        sys.exit(2)


if __name__ == "__main__":
    main()
