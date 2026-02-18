#!/usr/bin/env python3
"""
RDS Aurora PostgreSQL Maintenance & Lifecycle Report

Queries AWS for pending maintenance actions, Health lifecycle events,
cluster versions, and RDS event logs. Outputs a report to stdout (markdown)
or publishes directly to Confluence.

Usage:
    # Print markdown report to stdout
    ./rds-maintenance-report.py --profile grindr-prod-admin

    # Write markdown to a file
    ./rds-maintenance-report.py --profile grindr-prod-admin -o report.md

    # Publish to Confluence
    ./rds-maintenance-report.py --profile grindr-prod-admin --confluence --space SRE

    # Check events for a specific cluster (last 14 days)
    ./rds-maintenance-report.py --profile grindr-prod-admin --cluster chat-preview-service

    # Check events with custom duration (in minutes, max 14 days = 20160)
    ./rds-maintenance-report.py --profile grindr-prod-admin --cluster chat-preview-service --duration 4320
"""

import argparse
import base64
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone


def aws_cli(args, profile, region=None):
    """Run an AWS CLI command and return parsed JSON."""
    cmd = ["aws"] + args + ["--profile", profile, "--output", "json"]
    if region:
        cmd += ["--region", region]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: aws {' '.join(args[:3])}...: {result.stderr.strip()[:300]}", file=sys.stderr)
        return None
    return json.loads(result.stdout) if result.stdout.strip() else None


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def get_all_clusters(profile):
    """Get all Aurora PostgreSQL clusters with version info."""
    data = aws_cli([
        "rds", "describe-db-clusters",
        "--query", "DBClusters[?Engine==`aurora-postgresql`].{Cluster:DBClusterIdentifier,Version:EngineVersion,MaintenanceWindow:PreferredMaintenanceWindow,AutoUpgrade:AutoMinorVersionUpgrade,Instances:DBClusterMembers[*].DBInstanceIdentifier}",
    ], profile)
    return data or []


def get_pending_maintenance(profile):
    """Get all pending maintenance actions."""
    data = aws_cli(["rds", "describe-pending-maintenance-actions"], profile)
    return data.get("PendingMaintenanceActions", []) if data else []


def get_cluster_events(profile, cluster_id, duration=20160):
    """Get RDS events for a specific cluster."""
    data = aws_cli([
        "rds", "describe-events",
        "--source-identifier", cluster_id,
        "--source-type", "db-cluster",
        "--duration", str(duration),
    ], profile)
    return data.get("Events", []) if data else []


def get_health_events(profile):
    """Get all RDS scheduled change Health events."""
    data = aws_cli([
        "health", "describe-events",
        "--filter", "eventTypeCategories=scheduledChange,services=RDS",
    ], profile, region="us-east-1")
    return data.get("events", []) if data else []


def get_health_event_details(profile, event_arn):
    """Get details for a specific Health event."""
    data = aws_cli([
        "health", "describe-event-details",
        "--event-arns", event_arn,
    ], profile, region="us-east-1")
    if data and data.get("successfulSet"):
        return data["successfulSet"][0]
    return None


def get_health_affected_entities(profile, event_arn):
    """Get affected entities for a Health event."""
    data = aws_cli([
        "health", "describe-affected-entities",
        "--filter", f"eventArns={event_arn}",
    ], profile, region="us-east-1")
    return data.get("entities", []) if data else []


# ---------------------------------------------------------------------------
# Report: cluster events
# ---------------------------------------------------------------------------

def build_cluster_events_report(profile, cluster_id, duration):
    """Build a markdown report of events for a specific cluster."""
    events = get_cluster_events(profile, cluster_id, duration)
    lines = [f"# RDS Events: {cluster_id}\n"]
    lines.append(f"Last {duration} minutes ({duration / 1440:.1f} days)\n")

    if not events:
        lines.append("No events found.\n")
        return "\n".join(lines)

    lines.append("| Time (UTC) | Category | Message |")
    lines.append("|---|---|---|")
    for e in events:
        ts = e.get("Date", "")[:19].replace("T", " ")
        cats = ", ".join(e.get("EventCategories", [])) or "-"
        msg = e.get("Message", "")
        lines.append(f"| {ts} | {cats} | {msg} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report: full maintenance report
# ---------------------------------------------------------------------------

def build_full_report(profile):
    """Build the full maintenance & lifecycle markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# RDS Aurora PostgreSQL Maintenance Report\n"]
    lines.append(f"Generated: {now}\n")

    # --- Clusters by version ---
    clusters = get_all_clusters(profile)
    by_version = defaultdict(list)
    for c in clusters:
        by_version[c["Version"]].append(c["Cluster"])

    lines.append(f"## Cluster Inventory ({len(clusters)} clusters)\n")
    lines.append("| Version | Count | Clusters |")
    lines.append("|---|---|---|")
    for ver in sorted(by_version.keys()):
        names = sorted(by_version[ver])
        display = ", ".join(names[:5])
        if len(names) > 5:
            display += f", ... (+{len(names) - 5} more)"
        lines.append(f"| {ver} | {len(names)} | {display} |")
    lines.append("")

    # --- Pending engine upgrades ---
    pending = get_pending_maintenance(profile)
    engine_upgrades = []
    os_patches = 0
    for item in pending:
        resource = item["ResourceIdentifier"].split(":")[-1]
        resource_type = item["ResourceIdentifier"].split(":")[5]
        for detail in item.get("PendingMaintenanceActionDetails", []):
            desc = detail.get("Description", "")
            match = re.match(r"Upgrade to Aurora PostgreSQL (\S+)", desc)
            if match and resource_type == "cluster":
                engine_upgrades.append({
                    "cluster": resource,
                    "target": match.group(1),
                    "auto_apply": detail.get("AutoAppliedAfterDate", ""),
                    "forced_apply": detail.get("ForcedApplyDate", ""),
                })
            elif "Operating System" in desc:
                os_patches += 1

    by_target = defaultdict(list)
    for u in engine_upgrades:
        by_target[u["target"]].append(u)

    lines.append(f"## Pending Engine Version Upgrades ({len(engine_upgrades)} clusters)\n")
    if engine_upgrades:
        lines.append("| Target Version | Clusters | Has Forced Date? |")
        lines.append("|---|---|---|")
        for target in sorted(by_target.keys()):
            items = by_target[target]
            names = ", ".join(sorted(i["cluster"] for i in items[:5]))
            if len(items) > 5:
                names += f", ... (+{len(items) - 5} more)"
            has_forced = any(i["forced_apply"] for i in items)
            forced_str = "YES" if has_forced else "No"
            lines.append(f"| {target} | {names} | {forced_str} |")
        lines.append("")
    else:
        lines.append("No pending engine upgrades.\n")

    lines.append(f"## Pending OS Patches\n")
    lines.append(f"{os_patches} instance-level OS patches pending (no forced dates).\n")

    # --- Health lifecycle events ---
    health_events = get_health_events(profile)
    active_events = [e for e in health_events if e.get("statusCode") in ("upcoming", "open")]

    lines.append(f"## AWS Health Lifecycle Events\n")
    lines.append(f"Total events: {len(health_events)} | Active: {len(active_events)}\n")

    if active_events:
        for event in sorted(active_events, key=lambda x: x.get("startTime", "")):
            arn = event["arn"]
            status = event["statusCode"]
            start = event["startTime"][:10]
            region = event["region"]

            details = get_health_event_details(profile, arn)
            desc_text = ""
            metadata = {}
            if details:
                desc_text = details.get("eventDescription", {}).get("latestDescription", "")
                metadata = details.get("eventMetadata", {})

            title = metadata.get("deprecated_versions", event["eventTypeCode"])
            # Extract first paragraph as summary
            summary = desc_text.split("\n\n")[0][:300] if desc_text else "No description"

            entities = get_health_affected_entities(profile, arn)
            pending_entities = [e for e in entities if e.get("statusCode") != "RESOLVED"]
            resolved_entities = [e for e in entities if e.get("statusCode") == "RESOLVED"]

            lines.append(f"### [{status.upper()}] {title}\n")
            lines.append(f"- **Start date:** {start}")
            lines.append(f"- **Region:** {region}")
            lines.append(f"- **Affected resources:** {len(entities)} total, {len(resolved_entities)} resolved, {len(pending_entities)} pending")
            lines.append(f"- **Summary:** {summary}")
            lines.append("")

            if pending_entities:
                lines.append("**Pending resources (not yet resolved):**\n")
                for e in sorted(pending_entities, key=lambda x: x["entityValue"]):
                    name = e["entityValue"].split(":")[-1]
                    lines.append(f"- `{name}`")
                lines.append("")

    # --- Risk assessment ---
    lines.append("## Risk Assessment\n")

    # Check for clusters on known deprecated versions
    deprecated_16x = ["16.1", "16.2", "16.3"]
    at_risk = []
    for ver, names in by_version.items():
        if ver in deprecated_16x:
            for n in names:
                at_risk.append((n, ver, "16.1/16.2/16.3 past end-of-support (Nov 30, 2025) — forced upgrade imminent"))
        major = ver.split(".")[0]
        if major == "13":
            for n in names:
                at_risk.append((n, ver, "PG13 end-of-standard-support Feb 28, 2026"))

    if at_risk:
        lines.append("| Cluster | Current Version | Risk |")
        lines.append("|---|---|---|")
        for name, ver, risk in sorted(at_risk):
            lines.append(f"| {name} | {ver} | {risk} |")
        lines.append("")
    else:
        lines.append("No clusters on immediately at-risk versions.\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Confluence publishing
# ---------------------------------------------------------------------------

def markdown_to_confluence_html(md):
    """Convert markdown report to Confluence storage format HTML."""
    html_lines = []
    in_table = False
    table_header_done = False

    for line in md.split("\n"):
        # Headers
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        # Table rows
        elif line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            # Skip separator rows
            if all(re.match(r"^-+$", c) for c in cells):
                table_header_done = True
                continue
            if not in_table:
                html_lines.append("<table><thead>")
                in_table = True
                table_header_done = False
            if not table_header_done:
                html_lines.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
            else:
                if "</thead>" not in html_lines[-1] and "<tbody>" not in "\n".join(html_lines[-3:]):
                    html_lines.append("</thead><tbody>")
                # Convert backticks to <code>
                cells = [re.sub(r"`([^`]+)`", r"<code>\1</code>", c) for c in cells]
                html_lines.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        else:
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False
                table_header_done = False
            # List items
            if line.startswith("- **"):
                content = line[2:]
                content = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", content)
                content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
                html_lines.append(f"<ul><li>{content}</li></ul>")
            elif line.startswith("- `"):
                content = line[2:]
                content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
                html_lines.append(f"<ul><li>{content}</li></ul>")
            elif line.startswith("- "):
                html_lines.append(f"<ul><li>{line[2:]}</li></ul>")
            elif line.strip():
                line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
                line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
                html_lines.append(f"<p>{line}</p>")

    if in_table:
        html_lines.append("</tbody></table>")

    return "\n".join(html_lines)


def publish_to_confluence(md_content, space_key, title=None):
    """Publish markdown content to Confluence as a new page."""
    try:
        import keyring
    except ImportError:
        print("ERROR: 'keyring' package required for Confluence publishing. Install with: pip install keyring", file=sys.stderr)
        sys.exit(1)

    email = "alex.moore@team.grindr.com"
    token = keyring.get_password("https://grindr.atlassian.net", email)
    if not token:
        print("ERROR: No Atlassian API token found in keychain.", file=sys.stderr)
        sys.exit(1)

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    base_url = "https://grindr.atlassian.net/wiki"

    # Look up space ID
    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        f"{base_url}/api/v2/spaces?keys={space_key}&limit=5",
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req)
        space_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR looking up space: HTTP {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        sys.exit(1)

    results = space_data.get("results", [])
    if not results:
        print(f"ERROR: Space '{space_key}' not found.", file=sys.stderr)
        sys.exit(1)

    space_id = results[0]["id"]

    if not title:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title = f"RDS Aurora PostgreSQL Maintenance Report — {now}"

    body_html = markdown_to_confluence_html(md_content)

    payload = json.dumps({
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": body_html},
    })

    req = urllib.request.Request(
        f"{base_url}/api/v2/pages",
        data=payload.encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        web_link = data.get("_links", {}).get("webui", "")
        print(f"Published to Confluence: {base_url}{web_link}")
    except urllib.error.HTTPError as e:
        print(f"ERROR publishing: HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="RDS Aurora PostgreSQL Maintenance & Lifecycle Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--profile", required=True, help="AWS CLI profile to use")
    parser.add_argument("--cluster", help="Show events for a specific cluster instead of the full report")
    parser.add_argument("--duration", type=int, default=20160, help="Event lookback in minutes (default: 20160 = 14 days)")
    parser.add_argument("-o", "--output", help="Write markdown to file instead of stdout")
    parser.add_argument("--confluence", action="store_true", help="Publish report to Confluence")
    parser.add_argument("--space", default="SRE", help="Confluence space key (default: SRE)")
    parser.add_argument("--title", help="Custom Confluence page title")

    args = parser.parse_args()

    if args.cluster:
        report = build_cluster_events_report(args.profile, args.cluster, args.duration)
    else:
        report = build_full_report(args.profile)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    elif not args.confluence:
        print(report)

    if args.confluence:
        publish_to_confluence(report, args.space, args.title)


if __name__ == "__main__":
    main()
