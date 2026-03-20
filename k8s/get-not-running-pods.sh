#!/usr/bin/env bash
# List all pods that are not in Running state
# Usage: k8s-get-not-running-pods [kubectl args...]
#   Example: k8s-get-not-running-pods -A
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }
kubectl get pod --field-selector 'status.phase!=Running' "$@"