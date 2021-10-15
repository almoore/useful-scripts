#!/usr/bin/env bash
set -eEo pipefail
#set -x
swapname() {
  echo $1 | tr "/" "\n" | sed s#.yaml## | tac | tr "\n" "/" |sed 's#/$#.yaml#'
}

for i in $(find -type d -name \*.apps -o -name \*.batch); do
  o=$(echo $i|xargs basename -s .apps |xargs basename -s .batch)
  mv -v $i $o
done

# Cleanup directories that are redundant
RM_DIRS="
pod
endpoints
event
replicaset
redisfailover.databases.spotahome.com
"
rm -rf $RM_DIRS

# Remove helm managed files
grep -rl "app.kubernetes.io/managed-by: Helm" && rm $(grep -rl "app.kubernetes.io/managed-by: Helm")

DIRS="
configmap
daemonset
deployment
statefulset
endpoints
service
job
cronjob
serviceaccount
"

for d in $DIRS; do
  if [ -d $d ]; then
    for f in $(find $d -type f); do
      out=$(swapname $f)
      mkdir -p $(dirname $out)
      mv -v $f $out
    done
    rmdir $d
  fi
done