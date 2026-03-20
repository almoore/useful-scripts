#!/usr/bin/env bash
# Delete all pods in Failed status
# Usage: k8s-delete-failed-pods [kubectl args...]
#   Example: k8s-delete-failed-pods -n production
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }
set -x
kubectl get pod --field-selector 'status.phase==Failed' -o json "$@" | kubectl delete -f -
