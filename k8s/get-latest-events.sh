#!/usr/bin/env bash
# Display Kubernetes events sorted by timestamp
# Usage: k8s-get-latest-events [kubectl args...]
#   Example: k8s-get-latest-events -n production
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }
kubectl get events --sort-by='{.lastTimestamp}' "$@"
