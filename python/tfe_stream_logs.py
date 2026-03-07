#!/usr/bin/env python3
"""Stream Terraform Cloud/Enterprise run logs with formatted output.

Fetches plan and apply logs from TFC/TFE and streams them with optional
formatting: raw, cli (terraform-like), pretty (annotated + colored), or json.

Usage:
    tfe_stream_logs.py https://app.terraform.io/app/Org/workspaces/ws/runs/run-XXX
    tfe_stream_logs.py https://app.terraform.io/app/Org/workspaces/ws/runs/run-XXX --mode pretty
    tfe_stream_logs.py run-XXX --base-url https://app.terraform.io --follow
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

CRED_FILE = Path.home() / ".terraform.d" / "credentials.tfrc.json"


# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------

class Color:
    """ANSI color codes, disabled when not writing to a terminal."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def red(self, t: str) -> str:       return self._wrap("31", t)
    def green(self, t: str) -> str:     return self._wrap("32", t)
    def yellow(self, t: str) -> str:    return self._wrap("33", t)
    def blue(self, t: str) -> str:      return self._wrap("34", t)
    def magenta(self, t: str) -> str:   return self._wrap("35", t)
    def cyan(self, t: str) -> str:      return self._wrap("36", t)
    def dim(self, t: str) -> str:       return self._wrap("2", t)
    def bold(self, t: str) -> str:      return self._wrap("1", t)
    def bold_red(self, t: str) -> str:  return self._wrap("1;31", t)
    def bold_green(self, t: str) -> str: return self._wrap("1;32", t)
    def bold_yellow(self, t: str) -> str: return self._wrap("1;33", t)


# Global, set in main()
C = Color(enabled=False)


# ---------------------------------------------------------------------------
# Credential + API helpers
# ---------------------------------------------------------------------------

def load_token_for_host(host: str) -> str:
    if not CRED_FILE.exists():
        raise SystemExit(f"Missing credentials file: {CRED_FILE}")
    data = json.loads(CRED_FILE.read_text())
    token = (data.get("credentials", {}).get(host, {}) or {}).get("token")
    if not token:
        raise SystemExit(f"No token for host '{host}' in {CRED_FILE}")
    return token


def parse_run_id(run_url: str) -> str:
    m = re.search(r"(run-[A-Za-z0-9]+)", run_url)
    if not m:
        raise SystemExit("Could not find run-XXXX in the run URL")
    return m.group(1)


def api_get(sess: requests.Session, base: str, path: str):
    r = sess.get(base + path)
    r.raise_for_status()
    return r.json()


def rel_id(run_data: dict, name: str):
    rel = (run_data.get("relationships", {}) or {}).get(name, {})
    return (rel.get("data", {}) or {}).get("id")


def attr(obj_data: dict, *names):
    attrs = (obj_data.get("attributes", {}) or {})
    for n in names:
        v = attrs.get(n)
        if v:
            return v
    return None


# ---------------------------------------------------------------------------
# Action/severity → color mapping
# ---------------------------------------------------------------------------

ACTION_SYMBOLS = {
    "create": ("+", "green"),
    "update": ("~", "yellow"),
    "delete": ("-", "red"),
    "remove": ("x", "magenta"),
    "read":   (">", "dim"),
    "noop":   (".", "dim"),
}


def _color_action(action: str, text: str) -> str:
    """Colorize text based on a terraform action."""
    _, color = ACTION_SYMBOLS.get(action, ("?", "dim"))
    return getattr(C, color)(text)


def _action_symbol(action: str) -> str:
    """Return a colored symbol for an action."""
    sym, color = ACTION_SYMBOLS.get(action, ("?", "dim"))
    return getattr(C, color)(sym)


# ---------------------------------------------------------------------------
# Line emitter — dispatches by event type
# ---------------------------------------------------------------------------

class RefreshTracker:
    """Collapses refresh_start/refresh_complete into a counter in cli mode."""

    def __init__(self):
        self.count = 0
        self.last_addr = ""

    def tick(self, addr: str):
        self.count += 1
        self.last_addr = addr

    def flush(self):
        if self.count > 0:
            msg = C.dim(f"  Refreshing state... ({self.count} resources, last: {self.last_addr})")
            print(f"\r{msg}", flush=True)
            self.count = 0
            self.last_addr = ""


# Global tracker for cli mode refresh collapsing
_refresh = RefreshTracker()


def _extract_addr(obj: dict) -> str | None:
    """Extract resource address from hook or change fields."""
    # hook.resource.addr (refresh_start, refresh_complete, apply_start, apply_complete)
    addr = (obj.get("hook") or {}).get("resource", {}).get("addr")
    if addr:
        return addr
    # change.resource.addr (planned_change, resource_drift)
    addr = (obj.get("change") or {}).get("resource", {}).get("addr")
    return addr


def _extract_action(obj: dict) -> str | None:
    """Extract action from change field."""
    return (obj.get("change") or {}).get("action")


def emit_line(line: str, mode: str, *, show_ts: bool = False, show_level: bool = False):
    """Format and print a single log line.

    Modes:
      raw    — print line as-is
      cli    — terraform-like human output (collapses refresh, highlights changes)
      pretty — annotated with type/addr tags + color
      json   — passthrough ndjson
    """
    if mode == "raw":
        print(line, flush=True)
        return

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        # Non-JSON preamble lines (e.g. "Terraform v1.9.8", "Initializing...")
        if mode == "json":
            print(json.dumps({"text": line}, ensure_ascii=False), flush=True)
        else:
            _refresh.flush()
            print(C.dim(line), flush=True)
        return

    if mode == "json":
        print(json.dumps(obj, ensure_ascii=False), flush=True)
        return

    ts = obj.get("@timestamp") or obj.get("timestamp") or ""
    lvl = obj.get("@level") or obj.get("level") or ""
    typ = obj.get("type", "")
    msg = obj.get("@message") or obj.get("message") or ""
    addr = _extract_addr(obj)
    action = _extract_action(obj)

    # Optional prefix
    pfx_parts = []
    if show_ts and ts:
        pfx_parts.append(C.dim(ts[:19]))  # trim to second precision
    if show_level and lvl:
        if lvl == "error":
            pfx_parts.append(C.bold_red(lvl.upper()))
        elif lvl == "warn":
            pfx_parts.append(C.bold_yellow(lvl.upper()))
        else:
            pfx_parts.append(C.dim(lvl.upper()))
    pfx = (" ".join(pfx_parts) + " ") if pfx_parts else ""

    # --- Dispatch by type ---

    if mode == "cli":
        _emit_cli(obj, typ, msg, addr, action, pfx)
    elif mode == "pretty":
        _emit_pretty(obj, typ, msg, addr, action, pfx)


def _emit_cli(obj: dict, typ: str, msg: str, addr: str | None, action: str | None, pfx: str):
    """CLI mode: mimic terraform CLI output with color."""

    if typ in ("refresh_start", "refresh_complete"):
        _refresh.tick(addr or "?")
        return  # collapsed; flushed on next non-refresh event

    # Flush any pending refresh counter before printing
    _refresh.flush()

    if typ == "version":
        ver = obj.get("terraform", "")
        print(pfx + C.bold(f"Terraform v{ver}"), flush=True)

    elif typ == "planned_change":
        sym = _action_symbol(action or "noop")
        reason = (obj.get("change") or {}).get("reason", "")
        reason_str = f" ({reason.replace('_', ' ')})" if reason else ""
        colored_msg = _color_action(action or "noop", f"{addr}: Plan to {action}{reason_str}")
        print(pfx + f"  {sym} {colored_msg}", flush=True)

    elif typ == "resource_drift":
        colored_msg = C.yellow(f"{addr}: Drift detected ({action})")
        print(pfx + f"  ~ {colored_msg}", flush=True)

    elif typ == "change_summary":
        counts = obj.get("changes", {})
        add = counts.get("add", 0)
        change = counts.get("change", 0)
        remove = counts.get("remove", 0)
        parts = []
        if add:
            parts.append(C.bold_green(f"{add} to add"))
        else:
            parts.append(f"{add} to add")
        if change:
            parts.append(C.bold_yellow(f"{change} to change"))
        else:
            parts.append(f"{change} to change")
        if remove:
            parts.append(C.bold_red(f"{remove} to destroy"))
        else:
            parts.append(f"{remove} to destroy")
        print(pfx + C.bold(f"\nPlan: {', '.join(parts)}."), flush=True)

    elif typ == "outputs":
        outputs = obj.get("outputs", {})
        changed = {k: v for k, v in outputs.items() if v.get("action") != "noop"}
        if changed:
            print(pfx + C.bold(f"\nOutputs: {len(outputs)} ({len(changed)} changing)"), flush=True)
            for name, info in changed.items():
                sym = _action_symbol(info.get("action", "noop"))
                print(f"  {sym} {name}", flush=True)
        else:
            print(pfx + C.dim(f"Outputs: {len(outputs)} (no changes)"), flush=True)

    elif typ == "diagnostic":
        diag = obj.get("diagnostic", {})
        severity = diag.get("severity", "")
        summary = diag.get("summary", msg)
        detail = diag.get("detail", "")
        if severity == "error":
            print(pfx + C.bold_red(f"Error: {summary}"), flush=True)
            if detail:
                # Show first 3 lines of detail
                for dl in detail.strip().splitlines()[:3]:
                    print(pfx + C.red(f"  {dl}"), flush=True)
        elif severity == "warning":
            print(pfx + C.yellow(f"Warning: {summary}"), flush=True)
            if detail:
                for dl in detail.strip().splitlines()[:2]:
                    print(pfx + C.dim(f"  {dl}"), flush=True)
        else:
            print(pfx + msg, flush=True)

    elif typ in ("apply_start", "apply_complete"):
        # Data source reads — show but dimmed
        hook = obj.get("hook", {})
        act = hook.get("action", "")
        if act == "read":
            print(pfx + C.dim(f"  {msg}"), flush=True)
        # skip non-read apply_start/complete (resource state operations)

    else:
        # Fallback: print the message
        if msg:
            print(pfx + msg, flush=True)


def _emit_pretty(obj: dict, typ: str, msg: str, addr: str | None, action: str | None, pfx: str):
    """Pretty mode: structured tags with color."""

    if typ in ("refresh_start", "refresh_complete"):
        tag = C.dim(f"[{typ}]")
        print(f"{pfx}{tag} {C.dim(addr or msg)}", flush=True)
        return

    if typ == "version":
        print(pfx + C.bold(f"[version] Terraform v{obj.get('terraform', '?')}"), flush=True)

    elif typ == "planned_change":
        reason = (obj.get("change") or {}).get("reason", "")
        reason_str = f" ({reason.replace('_', ' ')})" if reason else ""
        tag_color = {"create": "green", "update": "yellow", "delete": "red",
                     "remove": "magenta"}.get(action or "", "dim")
        tag = getattr(C, tag_color)(f"[{action}]")
        body = _color_action(action or "noop", f"{addr}{reason_str}")
        print(f"{pfx}{tag} {body}", flush=True)

    elif typ == "resource_drift":
        tag = C.yellow(f"[drift:{action}]")
        print(f"{pfx}{tag} {C.yellow(addr or msg)}", flush=True)

    elif typ == "change_summary":
        counts = obj.get("changes", {})
        add, change, remove = counts.get("add", 0), counts.get("change", 0), counts.get("remove", 0)
        parts = []
        if add:    parts.append(C.green(f"+{add}"))
        if change: parts.append(C.yellow(f"~{change}"))
        if remove: parts.append(C.red(f"-{remove}"))
        summary = " ".join(parts) if parts else "no changes"
        print(f"{pfx}{C.bold('[summary]')} {summary}", flush=True)

    elif typ == "outputs":
        outputs = obj.get("outputs", {})
        changed = [k for k, v in outputs.items() if v.get("action") != "noop"]
        tag = C.cyan("[outputs]")
        if changed:
            print(f"{pfx}{tag} {len(outputs)} total, changing: {', '.join(changed)}", flush=True)
        else:
            print(f"{pfx}{tag} {C.dim(f'{len(outputs)} (unchanged)')}", flush=True)

    elif typ == "diagnostic":
        diag = obj.get("diagnostic", {})
        severity = diag.get("severity", "")
        summary = diag.get("summary", msg)
        detail = diag.get("detail", "")
        if severity == "error":
            tag = C.bold_red("[error]")
            print(f"{pfx}{tag} {C.red(summary)}", flush=True)
            if detail:
                for dl in detail.strip().splitlines()[:3]:
                    print(f"{pfx}        {C.dim(dl)}", flush=True)
        elif severity == "warning":
            tag = C.bold_yellow("[warn]")
            print(f"{pfx}{tag}  {C.yellow(summary)}", flush=True)
            if detail:
                for dl in detail.strip().splitlines()[:2]:
                    print(f"{pfx}        {C.dim(dl)}", flush=True)
        else:
            print(f"{pfx}[diag] {msg}", flush=True)

    elif typ in ("apply_start", "apply_complete"):
        hook = obj.get("hook", {})
        act = hook.get("action", "")
        elapsed = hook.get("elapsed_seconds")
        if typ == "apply_complete" and act == "read":
            dur = f" ({elapsed}s)" if elapsed else ""
            print(f"{pfx}{C.dim(f'[read]')} {C.dim(f'{addr}{dur}')}", flush=True)
        elif typ == "apply_start" and act == "read":
            print(f"{pfx}{C.dim('[read]')} {C.dim(f'{addr}: reading...')}", flush=True)
        else:
            tag = C.dim(f"[{typ}]")
            print(f"{pfx}{tag} {C.dim(addr or msg)}", flush=True)

    else:
        tag = C.dim(f"[{typ or 'log'}]")
        body = addr or msg
        print(f"{pfx}{tag} {body}", flush=True)


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

def stream_log_url(log_url: str, mode: str, show_ts: bool = False, show_level: bool = False):
    """Stream log from a pre-signed URL, emitting each line."""
    with requests.get(log_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            emit_line(line, mode, show_ts=show_ts, show_level=show_level)
    # Flush any remaining refresh counter
    _refresh.flush()


def wait_for_log_url(sess, base, kind, obj_id, follow, poll_sec):
    """Poll until the log URL is available.

    kind: 'plans' or 'applies'
    """
    path = f"/api/v2/{kind}/{obj_id}"
    while True:
        data = api_get(sess, base, path)["data"]
        log_url = attr(data, "log-read-url", "log_read_url", "log-read-url-v2", "log_read_url_v2")
        if log_url:
            return log_url
        if not follow:
            return None
        status = attr(data, "status") or "unknown"
        print(C.dim(f"  Waiting for {kind[:-1]} log... (status: {status})"), file=sys.stderr, flush=True)
        time.sleep(poll_sec)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global C

    ap = argparse.ArgumentParser(
        description="Stream Terraform Cloud/Enterprise run logs",
    )
    ap.add_argument("run_url", help="TFC run URL or run-XXXX ID")
    ap.add_argument("--base-url", default=None,
                    help="TFC/TFE base URL (inferred from run_url if a full URL)")
    ap.add_argument("--mode", choices=["raw", "cli", "pretty", "json"], default="cli",
                    help="raw=exact; cli=terraform-like; pretty=annotated; json=ndjson (default: cli)")
    ap.add_argument("--show-ts", action="store_true",
                    help="Show timestamps in cli/pretty modes")
    ap.add_argument("--show-level", action="store_true",
                    help="Show log level in cli/pretty modes")
    ap.add_argument("--no-color", action="store_true",
                    help="Disable colored output")
    ap.add_argument("--follow", action="store_true",
                    help="Poll until log URLs exist (useful when run is queued)")
    ap.add_argument("--poll-sec", type=int, default=2,
                    help="Polling interval in seconds (default: 2)")
    ap.add_argument("--plan-only", action="store_true",
                    help="Only stream plan logs, skip apply")
    args = ap.parse_args()

    # Color: enabled for tty unless --no-color or mode=raw/json
    use_color = (
        not args.no_color
        and args.mode in ("cli", "pretty")
        and sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
    )
    C = Color(enabled=use_color)

    # Parse URL
    u = urlparse(args.run_url)
    if u.scheme and u.netloc:
        base = f"{u.scheme}://{u.netloc}"
        host = u.netloc
    elif args.base_url:
        bu = urlparse(args.base_url)
        base = f"{bu.scheme}://{bu.netloc}"
        host = bu.netloc
    else:
        raise SystemExit("Provide a full URL or use --base-url with a run ID")

    run_id = parse_run_id(args.run_url)
    token = load_token_for_host(host)

    sess = requests.Session()
    sess.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json",
    })

    run = api_get(sess, base, f"/api/v2/runs/{run_id}")["data"]
    plan_id = rel_id(run, "plan")
    apply_id = rel_id(run, "apply")

    if plan_id:
        header = f"--- Streaming PLAN logs for {run_id} ---"
        print(C.bold(header) if args.mode != "raw" else header, file=sys.stderr, flush=True)
        plan_log = wait_for_log_url(sess, base, "plans", plan_id, args.follow, args.poll_sec)
        if plan_log:
            stream_log_url(plan_log, args.mode, args.show_ts, args.show_level)
        else:
            print(C.dim("(no plan log URL yet)"), file=sys.stderr, flush=True)

    if apply_id and not args.plan_only:
        header = f"--- Streaming APPLY logs for {run_id} ---"
        print(C.bold(header) if args.mode != "raw" else header, file=sys.stderr, flush=True)
        apply_log = wait_for_log_url(sess, base, "applies", apply_id, args.follow, args.poll_sec)
        if apply_log:
            stream_log_url(apply_log, args.mode, show_ts=args.show_ts, show_level=args.show_level)
        else:
            print(C.dim("(no apply log URL yet)"), file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
