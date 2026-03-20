#!/usr/bin/env bash
# List pods with NAME, STATUS, NODE, and NAMESPACE columns
# Usage: k8s-get-pod-by-node [kubectl args...]
#   Example: k8s-get-pod-by-node -n kube-system
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,4s/^# //p' "$0"; exit 0; }

kubectl get pod \
  -o=custom-columns="NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,NAMESPACE:.metadata.namespace" \
  "$@"
