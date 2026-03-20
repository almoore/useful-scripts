#!/usr/bin/env bash
# List all pods in Failed status
# Usage: k8s-get-failed-pods [kubectl args...]
#   Example: k8s-get-failed-pods -n production
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }
set -x
kubectl get pod --field-selector 'status.phase==Failed' "$@"
