#!/bin/bash
# List pods for a Helm release by name
# Usage: k8s-get-release-pods RELEASE_NAME
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }
REL_NAME="${1}"
if [ -z $REL_NAME ]; then
  echo "Usage: $(basename "$0") RELEASE_NAME" >&2
  exit 1
fi
kubectl get pods -l release=$REL_NAME -o jsonpath='{range .items[*]}{.metadata.name} {end}'
