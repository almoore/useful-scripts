#!/bin/bash

_PREV_CONTEXT=$(kubectl config current-context)
CONTEXT=${K8S_CONTEXT:-$_PREV_CONTEXT}
debug=0
build=1
date=$(date +"%Y%m%d%H%M%S")
prefix=$date

usage() {
cat << EOF
USAGE: $0 [options]
  options:
  -n | --namespaces NAMESPACES
  -k | --kinds KINDS
  --prefix PREFIX
  --debug
EOF
}

while [ -n "${1}" ]
do
    case "${1}" in
        -n | --namespaces)
            shift
            NAMESPACES="$NAMESPACES $1"
            ;;
        -k | --kinds)
            shift
            KINDS="$1"
            ;;
        --prefix)
            shift
            prefix="${1}"
            ;;
        --debug)
            debug=1
            ;;
        *)
            usage
            exit
            shift
            ;;
    esac
    shift
done
if [ "${debug}" -ne 0 ]; then
    set -x
fi

if [ "$_PREV_CONTEXT" != "$CONTEXT" ] ; then
    kubectl config use-context bitsy-central
fi

mkdir -p $prefix
cd $prefix
touch manifest.txt

if [ -z "$NAMESPACES" ]; then 
    NAMESPACES=$(kubectl get namespace -o name | xargs -n1 basename)
fi

if [ -z "$KINDS" ]; then 
    KINDS=ingress,configmap,all,pvc,secret,all
fi


for ns in $NAMESPACES; do
    echo "Getting namespace ${ns}"
    mkdir -p $ns
    prev=""
    for n in $(kubectl get $KINDS -o name -n $ns); do
        kind=$(dirname $n)
        item=$(basename $n)
        if [ "$prev" != "$kind" ]; then
            prev=$kind
            echo -e "\t${kind}"
            mkdir -p ${ns}/${kind}
        fi
        echo ${ns}/${n}.yaml >> manifest.txt
        kubectl get $kind $item -n ${ns} -o yaml > ${ns}/${n}.yaml
    done
done
