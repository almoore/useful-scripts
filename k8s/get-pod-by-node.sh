#!/usr/bin/env bash

kubectl get pod \
  -o=custom-columns="NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,NAMESPACE:.metadata.namespace" \
  "$@"
