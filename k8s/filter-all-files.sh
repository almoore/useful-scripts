#!/bin/bash
TMP=$(mktemp)
for f in $(find -name \*.yaml); do
  cp $f $TMP
  cat $TMP | k8s-filter > $f
done

rm $TMP
