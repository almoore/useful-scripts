#!/usr/bin/env python3
"""Summarize the TLS certificate(s) inside a Kubernetes TLS Secret.

Reads a Kubernetes Secret (YAML or JSON) from a file or stdin, base64-decodes
the requested data key (default ``tls.crt``), and prints a per-certificate
summary: subject CN, issuer CN, validity window, days remaining, and SANs.

Examples
--------
    kubectl get secret -n cattle-system tls-rancher-ingress -o yaml \\
        | k8s-decode-tls-secret
    k8s-decode-tls-secret secret.yaml --backend openssl
    k8s-decode-tls-secret --key ca.crt secret.json
"""

import argparse
import base64
import datetime as dt
import re
import subprocess
import sys

import yaml


def load_secret(source):
    """Return the parsed Secret dict from a path or file handle."""
    if hasattr(source, "read"):
        data = yaml.safe_load(source)
    else:
        with open(source, "r") as fh:
            data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SystemExit("Input is not a YAML/JSON object")
    return data


def extract_pem(secret, key):
    """Return PEM bytes for ``key`` from a Secret's data or stringData."""
    data = secret.get("data") or {}
    if key in data:
        return base64.b64decode(data[key])
    string_data = secret.get("stringData") or {}
    if key in string_data:
        return string_data[key].encode("utf-8")
    keys = sorted(set(data) | set(string_data))
    raise SystemExit(
        f"Key {key!r} not found in Secret. Available: {keys or '(none)'}"
    )


def split_pem(pem):
    """Yield each PEM block (as bytes) from a multi-cert PEM bundle."""
    pattern = re.compile(
        rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
        re.DOTALL,
    )
    for match in pattern.finditer(pem):
        yield match.group(0)


# --- Backends -------------------------------------------------------------

def summarize_python(pem_bundle):
    """Use the ``cryptography`` library to parse and summarize each cert."""
    from cryptography import x509
    from cryptography.x509.oid import ExtensionOID, NameOID

    summaries = []
    for pem in split_pem(pem_bundle):
        cert = x509.load_pem_x509_certificate(pem)

        def cn(name):
            attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
            return attrs[0].value if attrs else None

        try:
            ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
            dns = list(ext.get_values_for_type(x509.DNSName))
            ips = [str(ip) for ip in ext.get_values_for_type(x509.IPAddress)]
            sans = dns + ips
        except x509.ExtensionNotFound:
            sans = []

        summaries.append({
            "subject_cn": cn(cert.subject),
            "issuer_cn": cn(cert.issuer),
            "not_before": cert.not_valid_before_utc,
            "not_after": cert.not_valid_after_utc,
            "sans": sans,
        })
    return summaries


_OSSL_DATE_FMT = "%b %d %H:%M:%S %Y %Z"


def _parse_ossl_date(value):
    return dt.datetime.strptime(value.strip(), _OSSL_DATE_FMT).replace(
        tzinfo=dt.timezone.utc
    )


def _parse_ossl_subject_cn(line):
    # "subject=CN=foo, O=bar" or "subject= /CN=foo/O=bar"
    match = re.search(r"CN\s*=\s*([^,/]+)", line)
    return match.group(1).strip() if match else None


def summarize_openssl(pem_bundle):
    """Shell out to ``openssl x509`` for each cert in the bundle."""
    summaries = []
    for pem in split_pem(pem_bundle):
        result = subprocess.run(
            [
                "openssl", "x509", "-noout",
                "-subject", "-issuer", "-dates",
                "-ext", "subjectAltName",
            ],
            input=pem, capture_output=True, check=True,
        )
        out = result.stdout.decode("utf-8", errors="replace")

        subject_cn = issuer_cn = None
        not_before = not_after = None
        sans = []
        in_san = False

        for raw in out.splitlines():
            line = raw.strip()
            if line.startswith("subject="):
                subject_cn = _parse_ossl_subject_cn(line)
            elif line.startswith("issuer="):
                issuer_cn = _parse_ossl_subject_cn(line)
            elif line.startswith("notBefore="):
                not_before = _parse_ossl_date(line.split("=", 1)[1])
            elif line.startswith("notAfter="):
                not_after = _parse_ossl_date(line.split("=", 1)[1])
            elif "X509v3 Subject Alternative Name" in line:
                in_san = True
            elif in_san and line:
                # Lines look like "DNS:foo.example, DNS:bar.example, IP:1.2.3.4"
                for entry in line.split(","):
                    entry = entry.strip()
                    if entry.startswith(("DNS:", "IP:", "URI:", "email:")):
                        sans.append(entry.split(":", 1)[1])
                in_san = False

        summaries.append({
            "subject_cn": subject_cn,
            "issuer_cn": issuer_cn,
            "not_before": not_before,
            "not_after": not_after,
            "sans": sans,
        })
    return summaries


# --- Output ---------------------------------------------------------------

def print_summary(summaries, source_label):
    now = dt.datetime.now(tz=dt.timezone.utc)
    if not summaries:
        raise SystemExit("No PEM CERTIFICATE blocks found")

    for i, s in enumerate(summaries, start=1):
        days_left = None
        if s["not_after"] is not None:
            days_left = (s["not_after"] - now).days
        header = f"[{source_label}] cert {i}/{len(summaries)}"
        print(header)
        print(f"  Subject CN : {s['subject_cn'] or '(none)'}")
        print(f"  Issuer  CN : {s['issuer_cn'] or '(none)'}")
        print(f"  Not Before : {s['not_before']}")
        print(f"  Not After  : {s['not_after']}"
              + (f"  ({days_left} days remaining)" if days_left is not None
                 else ""))
        if s["sans"]:
            print(f"  SANs       : {', '.join(s['sans'])}")
        else:
            print("  SANs       : (none)")
        print()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Summarize the TLS cert(s) inside a Kubernetes Secret",
    )
    parser.add_argument(
        "file", nargs="?",
        help="Path to a Secret YAML/JSON file. If omitted, read stdin.",
    )
    parser.add_argument(
        "--backend", choices=("python", "openssl"), default="python",
        help="Decoder to use (default: python via cryptography library)",
    )
    parser.add_argument(
        "-k", "--key", default="tls.crt",
        help="Secret data key holding the PEM bundle (default: tls.crt)",
    )
    args = parser.parse_args(argv)

    if args.file:
        secret = load_secret(args.file)
        label = args.file
    else:
        if sys.stdin.isatty():
            parser.error("No input on stdin and no file argument given")
        secret = load_secret(sys.stdin)
        label = "stdin"

    pem_bundle = extract_pem(secret, args.key)

    if args.backend == "python":
        summaries = summarize_python(pem_bundle)
    else:
        summaries = summarize_openssl(pem_bundle)

    print_summary(summaries, label)


if __name__ == "__main__":
    main()
