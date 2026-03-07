#!/usr/bin/env python3
"""Review Terraform Cloud/Enterprise run plans.

Fetches plan output from the TFC/TFE API, parses resource changes,
flags destroys or errors, and prints a concise summary.

Credentials are read from ~/.terraform.d/credentials.tfrc.json or ~/.terraformrc.

Usage:
    tfc-review.py run-KVUv2g2NFuLePErU
    tfc-review.py MyOrg/my-workspace
    tfc-review.py https://app.terraform.io/app/MyOrg/workspaces/my-workspace/runs/run-ABC123
    tfc-review.py                          # interactive: prompt for org/workspace
"""

import argparse
import json
import os
import re
import sys

import requests

DEFAULT_HOSTNAME = "app.terraform.io"
API_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

def load_token(hostname: str) -> str | None:
    """Load TFC/TFE API token for the given hostname.

    Checks ~/.terraform.d/credentials.tfrc.json first, then ~/.terraformrc.
    """
    # Path 1: JSON credentials file
    creds_path = os.path.expanduser("~/.terraform.d/credentials.tfrc.json")
    if os.path.isfile(creds_path):
        try:
            with open(creds_path) as f:
                data = json.load(f)
            token = data.get("credentials", {}).get(hostname, {}).get("token")
            if token:
                return token
        except (json.JSONDecodeError, OSError):
            pass

    # Path 2: HCL-style ~/.terraformrc
    rc_path = os.path.expanduser("~/.terraformrc")
    if os.path.isfile(rc_path):
        try:
            with open(rc_path) as f:
                content = f.read()
            # Match: credentials "hostname" { token = "..." }
            pattern = (
                r'credentials\s+"'
                + re.escape(hostname)
                + r'"\s*\{[^}]*token\s*=\s*"([^"]+)"'
            )
            m = re.search(pattern, content, re.DOTALL)
            if m:
                return m.group(1)
        except OSError:
            pass

    return None


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(hostname: str, token: str, path: str, accept: str | None = None) -> requests.Response:
    """Make an authenticated GET request to the TFC/TFE API."""
    url = f"https://{hostname}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json",
    }
    if accept:
        headers["Accept"] = accept
    resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    if resp.status_code != 200:
        print(f"Error: API {resp.status_code} on GET {path}", file=sys.stderr)
        try:
            detail = resp.json()
            for err in detail.get("errors", []):
                print(f"  {err.get('title', '')}: {err.get('detail', '')}", file=sys.stderr)
        except Exception:
            print(f"  {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)
    return resp


def get_workspace_id(hostname: str, token: str, org: str, workspace: str) -> str:
    """Fetch the workspace ID for org/workspace."""
    resp = api_get(hostname, token, f"/api/v2/organizations/{org}/workspaces/{workspace}")
    return resp.json()["data"]["id"]


def list_runs(hostname: str, token: str, workspace_id: str) -> list[dict]:
    """List recent runs for a workspace."""
    resp = api_get(hostname, token, f"/api/v2/workspaces/{workspace_id}/runs?page[size]=10")
    return resp.json()["data"]


def get_run(hostname: str, token: str, run_id: str) -> dict:
    """Fetch a run with its included plan."""
    resp = api_get(hostname, token, f"/api/v2/runs/{run_id}?include=plan")
    return resp.json()


def get_plan_json(hostname: str, token: str, plan_id: str) -> dict | None:
    """Fetch the structured JSON plan output. Returns None if unavailable."""
    url = f"https://{hostname}/api/v2/plans/{plan_id}/json-output"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError):
        return None


def get_plan_log(hostname: str, token: str, plan_id: str) -> str | None:
    """Fetch the raw plan log text."""
    try:
        url = f"https://{hostname}/api/v2/plans/{plan_id}/log"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def parse_target(target: str) -> dict:
    """Parse the target argument into its components.

    Returns a dict with keys: run_id, org, workspace, hostname.
    """
    result = {"run_id": None, "org": None, "workspace": None, "hostname": None}

    # Run ID: run-XXXXX
    if re.match(r'^run-[A-Za-z0-9]+$', target):
        result["run_id"] = target
        return result

    # TFC URL
    url_m = re.match(
        r'https?://([^/]+)/app/([^/]+)/workspaces/([^/]+)(?:/runs/(run-[A-Za-z0-9]+))?',
        target,
    )
    if url_m:
        result["hostname"] = url_m.group(1)
        result["org"] = url_m.group(2)
        result["workspace"] = url_m.group(3)
        result["run_id"] = url_m.group(4)  # may be None
        return result

    # Org/Workspace
    if "/" in target:
        parts = target.split("/", 1)
        result["org"] = parts[0]
        result["workspace"] = parts[1]
        return result

    # Bare workspace name (needs --org)
    result["workspace"] = target
    return result


# ---------------------------------------------------------------------------
# Plan parsing — JSON output
# ---------------------------------------------------------------------------

def parse_json_plan(json_plan: dict) -> dict:
    """Parse structured JSON plan output into our standard format."""
    result = {
        "status": "planned",
        "adds": 0,
        "changes": 0,
        "destroys": 0,
        "created_resources": [],
        "changed_resources": [],
        "destroyed_resources": [],
        "resource_details": {},
        "warnings": [],
    }

    resource_changes = json_plan.get("resource_changes", [])
    for rc in resource_changes:
        address = rc.get("address", "unknown")
        change = rc.get("change", {})
        actions = change.get("actions", [])

        if actions == ["create"]:
            result["adds"] += 1
            result["created_resources"].append(address)
            _extract_json_details(result, address, change, "create")
        elif actions == ["delete"]:
            result["destroys"] += 1
            result["destroyed_resources"].append(address)
        elif actions == ["delete", "create"] or actions == ["create", "delete"]:
            result["destroys"] += 1
            result["adds"] += 1
            result["destroyed_resources"].append(address)
            result["created_resources"].append(address)
            _extract_json_details(result, address, change, "replace")
        elif actions == ["update"]:
            result["changes"] += 1
            result["changed_resources"].append(address)
            _extract_json_details(result, address, change, "update")
        elif actions == ["no-op"] or actions == ["read"]:
            continue

    if result["adds"] == 0 and result["changes"] == 0 and result["destroys"] == 0:
        result["status"] = "no_changes"

    return result


KEY_ATTRS = {
    "instance_class", "engine", "engine_version", "node_type",
    "instance_type", "cluster_identifier", "identifier", "name",
    "ami", "availability_zone",
}


def _extract_json_details(result: dict, address: str, change: dict, action: str):
    """Extract key attribute details from JSON change data."""
    details = []
    before = change.get("before") or {}
    after = change.get("after") or {}

    if action == "create" or action == "replace":
        for attr in KEY_ATTRS:
            val = after.get(attr)
            if val is not None:
                details.append(f"{attr} = {val}")
    elif action == "update":
        for attr in sorted(set(list(before.keys()) + list(after.keys()))):
            bv = before.get(attr)
            av = after.get(attr)
            if bv != av and av is not None and bv is not None:
                # Only show scalar changes for key attrs or short values
                if attr in KEY_ATTRS or (isinstance(av, str) and len(str(av)) < 60):
                    details.append(f"{attr}: {bv!r} -> {av!r}")
            if len(details) >= 5:
                break

    if details:
        result["resource_details"][address] = details


# ---------------------------------------------------------------------------
# Plan parsing — raw log text (fallback)
# ---------------------------------------------------------------------------

def _is_structured_log(log: str) -> bool:
    """Check if the log is Structured Run Output (JSON Lines)."""
    for line in log.splitlines()[:10]:
        line = line.strip()
        if line and line.startswith("{"):
            try:
                json.loads(line)
                return True
            except json.JSONDecodeError:
                continue
    return False


def _parse_structured_log(log: str) -> dict:
    """Parse Structured Run Output (JSON Lines) from TFC."""
    result = {
        "status": "unknown",
        "adds": 0,
        "changes": 0,
        "destroys": 0,
        "created_resources": [],
        "changed_resources": [],
        "destroyed_resources": [],
        "removed_resources": [],  # removed from state (not actually destroyed)
        "resource_details": {},
        "warnings": [],
        "errors": [],
    }

    for line in log.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry_type = entry.get("type", "")

        if entry_type == "change_summary":
            counts = entry.get("changes", {})
            result["adds"] = counts.get("add", 0)
            result["changes"] = counts.get("change", 0)
            result["destroys"] = counts.get("remove", 0)
            result["status"] = "planned"

        elif entry_type == "planned_change":
            change = entry.get("change", {})
            action = change.get("action", "")
            addr = change.get("resource", {}).get("addr", "unknown")

            if action == "create":
                if addr not in result["created_resources"]:
                    result["created_resources"].append(addr)
            elif action == "delete":
                if addr not in result["destroyed_resources"]:
                    result["destroyed_resources"].append(addr)
            elif action == "remove":
                if addr not in result["removed_resources"]:
                    result["removed_resources"].append(addr)
            elif action == "update":
                if addr not in result["changed_resources"]:
                    result["changed_resources"].append(addr)
            # "read" actions are skipped

        elif entry_type == "diagnostic":
            diag = entry.get("diagnostic", {})
            severity = diag.get("severity", "")
            summary = diag.get("summary", "")
            if severity == "warning" and summary:
                if summary not in result["warnings"]:
                    result["warnings"].append(summary)
            elif severity == "error" and summary:
                if summary not in result["errors"]:
                    result["errors"].append(summary)

    if result["adds"] == 0 and result["changes"] == 0 and result["destroys"] == 0:
        if result["status"] != "planned":
            result["status"] = "no_changes"

    if result["errors"] and result["status"] == "unknown":
        result["status"] = "failed"

    return result


def parse_log_plan(log: str) -> dict:
    """Parse raw plan log text into structured data.

    Handles both Structured Run Output (JSON Lines) and traditional
    human-readable plan text (mirrors atlantis-review.py logic).
    """
    # Detect and handle Structured Run Output
    if _is_structured_log(log):
        return _parse_structured_log(log)

    result = {
        "status": "unknown",
        "adds": 0,
        "changes": 0,
        "destroys": 0,
        "created_resources": [],
        "changed_resources": [],
        "destroyed_resources": [],
        "resource_details": {},
        "warnings": [],
    }

    # Strip ANSI escape codes
    clean = re.sub(r'\x1b\[[0-9;]*m', '', log)

    # Extract plan counts
    m = re.search(r'Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy', clean)
    if m:
        result["adds"] = int(m.group(1))
        result["changes"] = int(m.group(2))
        result["destroys"] = int(m.group(3))
        result["status"] = "planned"

    if "No changes" in clean or "0 to add, 0 to change, 0 to destroy" in clean:
        result["status"] = "no_changes"

    if "Error:" in clean and result["status"] == "unknown":
        result["status"] = "failed"

    # Resource action pattern
    res_pattern = r'#\s+(\S+)\s+will be'

    seen = set()
    for rm in re.finditer(res_pattern + r' destroyed', clean):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["destroyed_resources"].append(name)

    seen = set()
    for rm in re.finditer(res_pattern + r' created', clean):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["created_resources"].append(name)

    seen = set()
    for rm in re.finditer(res_pattern + r' updated in-place', clean):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["changed_resources"].append(name)

    # Also catch replace (destroy + create)
    seen_replace = set()
    for rm in re.finditer(r'#\s+(\S+)\s+must be replaced', clean):
        name = rm.group(1)
        if name not in seen_replace:
            seen_replace.add(name)
            if name not in result["destroyed_resources"]:
                result["destroyed_resources"].append(name)
            if name not in result["created_resources"]:
                result["created_resources"].append(name)

    # Attribute changes — TFC uses ~ prefix for changes (not !)
    resource_sections = re.split(r'(?=\n\s*#\s+\S+\s+(?:will be|must be) )', clean)
    for section in resource_sections:
        rm = re.search(r'#\s+(\S+)\s+(?:will be|must be) (\S+)', section)
        if not rm:
            continue
        res_name = rm.group(1)
        details = []

        if "will be created" in section:
            for attr_m in re.finditer(
                r'\+\s+(instance_class|engine|engine_version|node_type|'
                r'instance_type|cluster_identifier|identifier|name|ami)\s+'
                r'=\s+"?([^"\n]+)"?',
                section,
            ):
                details.append(f"{attr_m.group(1)} = {attr_m.group(2).strip()}")

        if "will be updated" in section:
            # TFC uses ~ for changed attrs
            for attr_m in re.finditer(r'[~!]\s+(\w+)\s+=\s+(.+)', section):
                attr_name = attr_m.group(1).strip()
                attr_value = attr_m.group(2).strip()
                details.append(f"{attr_name}: {attr_value}")
                if len(details) >= 5:
                    break

        if details and res_name not in result["resource_details"]:
            result["resource_details"][res_name] = details

    # Warnings
    for wm in re.finditer(r'Warning:\s*(.+)', clean):
        w = wm.group(1).strip()
        if w not in result["warnings"]:
            result["warnings"].append(w)

    return result


# ---------------------------------------------------------------------------
# Merge JSON + log results
# ---------------------------------------------------------------------------

def merge_plans(json_plan: dict | None, log_plan: dict | None) -> dict:
    """Merge JSON and log plan data. JSON is preferred for resources; log for warnings."""
    if json_plan and not log_plan:
        return json_plan
    if not json_plan and log_plan:
        return log_plan
    if not json_plan and not log_plan:
        return {
            "status": "unknown", "adds": 0, "changes": 0, "destroys": 0,
            "created_resources": [], "changed_resources": [], "destroyed_resources": [],
            "resource_details": {}, "warnings": [], "errors": [],
        }

    # Use JSON for resource data (more accurate), log for warnings/errors
    merged = dict(json_plan)
    if log_plan.get("warnings"):
        merged["warnings"] = log_plan["warnings"]
    if log_plan.get("errors"):
        merged["errors"] = log_plan["errors"]
    return merged


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_review(org: str, workspace: str, run_id: str, run_data: dict, plan: dict):
    """Print the formatted review."""
    attrs = run_data.get("data", {}).get("attributes", {})
    status = attrs.get("status", "unknown")
    message = attrs.get("message", "")
    created_at = attrs.get("created-at", "")

    print(f"## TFC Run — {org}/{workspace}")
    print(f"Run: {run_id} | Status: {status} | {created_at}")
    if message:
        print(f"Message: {message}")
    print()

    print("### Plan Summary")

    if plan["status"] == "no_changes":
        print("**Status: NO CHANGES**")
        print()
        return

    if plan["status"] == "failed":
        print("**Status: FAILED**")
        print()
        return

    total = plan["adds"] + plan["changes"] + plan["destroys"]
    status_label = "CLEAN" if plan["destroys"] == 0 else "CONCERNS"
    print(f"**Status: {status_label}**")
    print(f"**Resources:** {plan['adds']} to add, {plan['changes']} to change, {plan['destroys']} to destroy")
    print()

    # Created resources
    if plan["created_resources"]:
        print("**Creating:**")
        for r in plan["created_resources"]:
            details = plan["resource_details"].get(r, [])
            if details:
                print(f"  + {r} ({', '.join(details)})")
            else:
                print(f"  + {r}")
        print()

    # Changed resources
    if plan["changed_resources"]:
        print("**Changing:**")
        for r in plan["changed_resources"]:
            details = plan["resource_details"].get(r, [])
            if details:
                for d in details:
                    print(f"  ~ {r}: {d}")
            else:
                print(f"  ~ {r}")
        print()

    # Destroyed resources
    if plan["destroyed_resources"]:
        print("**DESTROYING:**")
        for r in plan["destroyed_resources"]:
            print(f"  - {r}")
        print()

    # Removed from state (not actually destroyed)
    removed = plan.get("removed_resources", [])
    if removed:
        print(f"**Removing from state:** ({len(removed)} resources)")
        for r in removed:
            print(f"  x {r}")
        print()

    # Errors (from structured log)
    errors = plan.get("errors", [])
    if errors:
        unique_errors = list(dict.fromkeys(errors))  # dedupe preserving order
        print(f"**Errors:** ({len(unique_errors)} unique)")
        for e in unique_errors[:5]:
            print(f"  - {e}")
        if len(unique_errors) > 5:
            print(f"  - ... and {len(unique_errors) - 5} more")
        print()

    # Warnings
    unique_warnings = []
    seen = set()
    for w in plan["warnings"]:
        key = w.split(":")[0] if ":" in w else w
        if key not in seen:
            seen.add(key)
            unique_warnings.append(w)
    if unique_warnings:
        print(f"**Warnings:** ({len(plan['warnings'])} total, {len(unique_warnings)} unique)")
        for w in unique_warnings[:5]:
            print(f"  - {w}")
        if len(unique_warnings) > 5:
            print(f"  - ... and {len(unique_warnings) - 5} more")
        print()

    # Verdict
    if errors:
        print(f"**Verdict:** Plan has {len(errors)} error(s) — review carefully.")
    elif plan["destroys"] > 0:
        print(f"**Verdict:** {plan['destroys']} resource(s) will be destroyed — review carefully before applying.")
    else:
        print("**Verdict:** Plan looks clean. Ready to apply.")
    print()


def pick_run_interactive(hostname: str, token: str, org: str, workspace: str) -> str:
    """List recent runs and let user pick one."""
    ws_id = get_workspace_id(hostname, token, org, workspace)
    runs = list_runs(hostname, token, ws_id)

    if not runs:
        print("No runs found for this workspace.", file=sys.stderr)
        sys.exit(0)

    print(f"Recent runs for {org}/{workspace}:")
    for i, run in enumerate(runs):
        attrs = run["attributes"]
        rid = run["id"]
        status = attrs.get("status", "?")
        msg = (attrs.get("message") or "")[:60]
        created = (attrs.get("created-at") or "")[:10]
        print(f"  {i+1:>2}. {rid}  {status:<16} {created}  {msg}")
    print()

    try:
        choice = input("Enter number or run ID: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    # By number
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(runs):
            return runs[idx]["id"]
        print("Invalid selection.", file=sys.stderr)
        sys.exit(1)

    # By run ID
    if choice.startswith("run-"):
        return choice

    print("Invalid selection.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_file_review(plan: dict, source: str):
    """Print review for a locally-parsed log file (no run metadata)."""
    print(f"## TFC Plan Review — {source}")
    print()
    print("### Plan Summary")

    if plan["status"] == "no_changes":
        print("**Status: NO CHANGES**")
        print()
        return

    if plan["status"] == "failed":
        print("**Status: FAILED**")
        print()

    if plan["status"] == "unknown" and not plan["adds"] and not plan["changes"] and not plan["destroys"]:
        errors = plan.get("errors", [])
        if not errors:
            print("**Status: UNKNOWN** (no plan summary found in log)")
            print()
            return

    total = plan["adds"] + plan["changes"] + plan["destroys"]
    status_label = "CLEAN" if plan["destroys"] == 0 else "CONCERNS"
    print(f"**Status: {status_label}**")
    print(f"**Resources:** {plan['adds']} to add, {plan['changes']} to change, {plan['destroys']} to destroy")
    print()

    if plan["created_resources"]:
        print("**Creating:**")
        for r in plan["created_resources"]:
            details = plan["resource_details"].get(r, [])
            if details:
                print(f"  + {r} ({', '.join(details)})")
            else:
                print(f"  + {r}")
        print()

    if plan["changed_resources"]:
        print("**Changing:**")
        for r in plan["changed_resources"]:
            details = plan["resource_details"].get(r, [])
            if details:
                for d in details:
                    print(f"  ~ {r}: {d}")
            else:
                print(f"  ~ {r}")
        print()

    if plan["destroyed_resources"]:
        print("**DESTROYING:**")
        for r in plan["destroyed_resources"]:
            print(f"  - {r}")
        print()

    removed = plan.get("removed_resources", [])
    if removed:
        print(f"**Removing from state:** ({len(removed)} resources)")
        for r in removed:
            print(f"  x {r}")
        print()

    errors = plan.get("errors", [])
    if errors:
        unique_errors = list(dict.fromkeys(errors))
        print(f"**Errors:** ({len(unique_errors)} unique)")
        for e in unique_errors[:5]:
            print(f"  - {e}")
        if len(unique_errors) > 5:
            print(f"  - ... and {len(unique_errors) - 5} more")
        print()

    unique_warnings = []
    seen = set()
    for w in plan["warnings"]:
        key = w.split(":")[0] if ":" in w else w
        if key not in seen:
            seen.add(key)
            unique_warnings.append(w)
    if unique_warnings:
        print(f"**Warnings:** ({len(plan['warnings'])} total, {len(unique_warnings)} unique)")
        for w in unique_warnings[:5]:
            print(f"  - {w}")
        if len(unique_warnings) > 5:
            print(f"  - ... and {len(unique_warnings) - 5} more")
        print()

    if errors:
        print(f"**Verdict:** Plan has {len(errors)} error(s) — review carefully.")
    elif plan["destroys"] > 0:
        print(f"**Verdict:** {plan['destroys']} resource(s) will be destroyed — review carefully before applying.")
    else:
        print("**Verdict:** Plan looks clean. Ready to apply.")
    print()


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

def stream_and_review(hostname: str, token: str, run_id: str, json_output: bool):
    """Stream plan logs from TFC, print them live, then review."""
    import time

    run_data = get_run(hostname, token, run_id)
    run_attrs = run_data["data"]["attributes"]

    # Get plan ID
    plan_id = None
    for included in run_data.get("included", []):
        if included["type"] == "plans":
            plan_id = included["id"]
            break
    if not plan_id:
        plan_rel = run_data["data"]["relationships"].get("plan", {}).get("data", {})
        plan_id = plan_rel.get("id")
    if not plan_id:
        print("Error: Could not find plan ID for this run.", file=sys.stderr)
        sys.exit(1)

    # Poll for log URL
    log_url = None
    for _ in range(60):  # up to 2 min
        resp = api_get(hostname, token, f"/api/v2/plans/{plan_id}")
        plan_attrs = resp.json()["data"]["attributes"]
        log_url = plan_attrs.get("log-read-url") or plan_attrs.get("log_read_url")
        plan_status = plan_attrs.get("status", "")
        if log_url:
            break
        if plan_status in ("errored", "canceled", "force_canceled"):
            print(f"Plan {plan_status}, no log available.", file=sys.stderr)
            sys.exit(1)
        print(f"Waiting for plan log... (status: {plan_status})", file=sys.stderr)
        time.sleep(2)

    if not log_url:
        print("Error: Timed out waiting for plan log URL.", file=sys.stderr)
        sys.exit(1)

    # Stream and collect
    collected_lines = []
    print(f"--- Streaming plan for {run_id} ---", file=sys.stderr)
    with requests.get(log_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if line is None:
                continue
            print(line, flush=True)
            collected_lines.append(line)

    print(f"\n--- End of plan log ---\n", file=sys.stderr)

    # Now review
    full_log = "\n".join(collected_lines)
    plan = parse_log_plan(full_log)

    if json_output:
        json.dump(plan, sys.stdout, indent=2)
        print()
    else:
        # Extract org/workspace for the header
        org, workspace = _resolve_org_workspace(hostname, token, run_data)
        print()
        print_review(org, workspace, run_id, run_data, plan)


def _resolve_org_workspace(hostname: str, token: str, run_data: dict) -> tuple[str, str]:
    """Resolve org and workspace names from run data."""
    org = "unknown"
    workspace = "unknown"
    ws_rel = run_data["data"]["relationships"].get("workspace", {})
    ws_data = ws_rel.get("data", {})
    if ws_data.get("id"):
        ws_resp = api_get(hostname, token, f"/api/v2/workspaces/{ws_data['id']}")
        ws_attrs = ws_resp.json()["data"]["attributes"]
        workspace = ws_attrs.get("name", "unknown")
        ws_org = ws_resp.json()["data"]["relationships"].get("organization", {}).get("data", {}).get("id")
        org = ws_org or "unknown"
    return org, workspace


def main():
    parser = argparse.ArgumentParser(
        description="Review Terraform Cloud/Enterprise run plans",
    )
    parser.add_argument(
        "target", nargs="?", default=None,
        help="Run ID, org/workspace, or TFC URL (omit for interactive)",
    )
    parser.add_argument(
        "--hostname", default=DEFAULT_HOSTNAME,
        help=f"TFC/TFE hostname (default: {DEFAULT_HOSTNAME})",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output raw parsed data as JSON",
    )
    parser.add_argument(
        "--log-only", action="store_true",
        help="Skip JSON plan endpoint, parse raw log only",
    )
    parser.add_argument(
        "--org", default=None,
        help="Default organization (so you can pass just a workspace name)",
    )
    parser.add_argument(
        "--file", dest="file", default=None,
        help="Parse a local log file instead of fetching from API",
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream plan logs live from TFC, then review",
    )
    args = parser.parse_args()

    # --file mode: parse local log file, no API needed
    if args.file:
        try:
            with open(args.file) as f:
                log = f.read()
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
        plan = parse_log_plan(log)
        if args.json_output:
            json.dump(plan, sys.stdout, indent=2)
            print()
        else:
            print_file_review(plan, os.path.basename(args.file))
        return

    # Parse target
    if args.target:
        parsed = parse_target(args.target)
    else:
        parsed = {"run_id": None, "org": None, "workspace": None, "hostname": None}

    hostname = parsed["hostname"] or args.hostname
    org = parsed["org"] or args.org
    workspace = parsed["workspace"]
    run_id = parsed["run_id"]

    # Load token
    token = load_token(hostname)
    if not token:
        print(f"Error: No API token found for {hostname}.", file=sys.stderr)
        print(f"Run `terraform login {hostname}` to authenticate.", file=sys.stderr)
        sys.exit(1)

    # If we have only a run ID (no org/workspace), fetch the run directly
    if run_id and not org:
        pass  # We can fetch the run by ID alone

    # If we have org/workspace but no run ID, list runs interactively
    if org and workspace and not run_id:
        run_id = pick_run_interactive(hostname, token, org, workspace)

    # If we have nothing, prompt for org/workspace
    if not run_id and not (org and workspace):
        try:
            if not org:
                org = input("Organization: ").strip()
            if not workspace:
                workspace = input("Workspace: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not org or not workspace:
            print("Organization and workspace are required.", file=sys.stderr)
            sys.exit(1)
        run_id = pick_run_interactive(hostname, token, org, workspace)

    # --stream mode: stream logs live, then review
    if args.stream:
        stream_and_review(hostname, token, run_id, args.json_output)
        return

    # Fetch run data
    run_data = get_run(hostname, token, run_id)
    run_attrs = run_data["data"]["attributes"]

    # Extract org/workspace from run relationships if not already known
    if not org or not workspace:
        org, workspace = _resolve_org_workspace(hostname, token, run_data)

    # Get plan ID from included resources
    plan_id = None
    for included in run_data.get("included", []):
        if included["type"] == "plans":
            plan_id = included["id"]
            break

    if not plan_id:
        # Try from relationships
        plan_rel = run_data["data"]["relationships"].get("plan", {}).get("data", {})
        plan_id = plan_rel.get("id")

    if not plan_id:
        print("Error: Could not find plan ID for this run.", file=sys.stderr)
        sys.exit(1)

    # Fetch plan data
    json_plan_data = None
    log_plan_data = None

    if not args.log_only:
        raw_json = get_plan_json(hostname, token, plan_id)
        if raw_json:
            json_plan_data = parse_json_plan(raw_json)

    raw_log = get_plan_log(hostname, token, plan_id)
    if raw_log:
        log_plan_data = parse_log_plan(raw_log)

    plan = merge_plans(json_plan_data, log_plan_data)

    # Output
    if args.json_output:
        json.dump(plan, sys.stdout, indent=2)
        print()
    else:
        print_review(org, workspace, run_id, run_data, plan)


if __name__ == "__main__":
    main()
