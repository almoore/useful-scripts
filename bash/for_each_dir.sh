#!/bin/bash
#set -e

BASE=$PWD
GC="\033[1;32m"
EC="\033[1;0m"

if [ -z "${DIRS}" ]; then 
    DIRS=$(find ${PWD} -maxdepth 1 -type d)
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
