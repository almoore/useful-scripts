#!/usr/bin/env bash
# Display detailed information from an X.509 certificate file
usage() { echo "Usage: $(basename "$0") CERT_FILE"; exit 1; }
[ "$1" = "-h" ] || [ "$1" = "--help" ] && usage
openssl x509 -noout -text -in ${1:?$(usage)}
