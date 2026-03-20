#!/bin/bash
# NOTE: Requires GNU sed (gsed on macOS: brew install gnu-sed)

usage() {
    echo "clone_match_path REPO [GIT-OPTIONS]"
}

trap_caught() {
    echo "Some signal caught. Stopping"
    usage
    exit 1
}

trap trap_caught SIGTSTP
trap trap_caught SIGQUIT
trap trap_caught SIGTERM
trap trap_caught INT


URL=$1
RP=$(echo $URL | sed -e 's#^.*://##' -e 's#.git$##' | sed -e 's#^.*@##' -e 's#:[0-9]*/#/#' | sed 's#:#/#')
CP=~/repos/$RP

git clone $URL $CP
