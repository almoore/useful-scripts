#!/bin/bash
# Pipe every *.yaml under the current directory through k8s-filter to strip
# server-managed metadata (resourceVersion, uid, etc.) so the manifests can be
# re-applied to a different cluster.
TMP=$(mktemp)
for f in $(find -name \*.yaml); do
  cp $f $TMP
  cat $TMP | k8s-filter > $f
done

rm $TMP
