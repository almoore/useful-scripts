#!/usr/bin/env bash
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

# Grab repo name
REPO=${1}
shift
# Create path
REPO_PATH=$(dirname ${REPO#*://})
REPO_NAME=$(basename -s .git $REPO)
FULL_PATH=/repos/$REPO_PATH/$REPO_NAME
mkdir -p $FULL_PATH
# Clone repo
git clone $REPO $FULL_PATH "$@"

