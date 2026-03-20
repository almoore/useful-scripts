#!/usr/bin/env bash
# Delete pods created more than 1 day ago
# Usage: k8s-delete-pods-older-than-1-day [kubectl args...]
#   Example: k8s-delete-pods-older-than-1-day -n staging
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }

set -x
date=$(type -p gdate || type -p date)
TIME=$($date -d 'yesterday' -Ins --utc |sed 's/+0000/Z/')
PODS=$(kubectl get pods -o go-template --template '{{range .items}}{{.metadata.name}} {{.metadata.creationTimestamp}}{{"\n"}}{{end}}' "${@}")
FILTERED_PODS=$(echo "$PODS" | awk '$2 <= "'$TIME'" { print $1 }')
for p in $FILTERED_PODS; do
    kubectl delete pod $p "${@}"
done
