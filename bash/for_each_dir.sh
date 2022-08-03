#!/bin/bash
#set -e
#set -x

BASE=$PWD
GC="\033[1;32m"
EC="\033[1;0m"

if [ -z "${DIRS}" ]; then
    DIRS=$(find -L ${PWD} -maxdepth 1 -type d | grep -v -E "(.idea)"| sort)
fi

printgreen() {
    printf "${GC}%s$@:${EC}\n";
}

for d in $DIRS; do
    if [ "${d}" != "${BASE}" ];then
        cd "${d}"
        printgreen "${d}"
        "$@"
    fi
done
