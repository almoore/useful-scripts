#!/bin/bash
REL_NAME="${1}"
if [ -z $REL_NAME ]; then
  echo "Must give a release name" >&2
  exit 1
fi
kubectl get pods -l release=$REL_NAME -o jsonpath='{range .items[*]}{.metadata.name} {end}'
