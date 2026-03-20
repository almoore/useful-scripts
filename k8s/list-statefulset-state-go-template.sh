#!/usr/bin/env bash
# Show replica status for a StatefulSet by application name
# Usage: k8s-list-statefulset-state-go-template APP_NAME
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n '2,3s/^# //p' "$0"; exit 0; }
APP=${1:?MUST SUPPLY APP NAME}
kubectl get statefulset -l app=$APP -o go-template --template='{{range .items}}{{.status.replicas}}/{{.spec.replicas}}{{printf "\n"}}{{end}}'
