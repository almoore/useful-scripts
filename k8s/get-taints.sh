#!/usr/bin/env bash
# Display taints on Kubernetes nodes
# Usage: k8s-get-taints
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,3s/^# //p' "$0"; exit 0; }
set -x
kubectl get node  -o=custom-columns=NAME:.metadata.name,TAINT:.spec.taints
