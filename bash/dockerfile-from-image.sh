#!/usr/bin/env bash
# Extract Dockerfile commands from a Docker image's history
usage() { echo "Usage: $(basename "$0") IMAGE"; exit 1; }
[ "$1" = "-h" ] || [ "$1" = "--help" ] && usage
IMAGE=${1:?$(usage)}
TAIL_CMD=${TAIL_CMD:-/usr/bin/tail}
docker history $IMAGE  --no-trunc --human=true --format "{{.CreatedBy}}" | tac | \
    sed -e 's|/bin/sh -c #(nop)  ||g' \
        -e 's|/bin/sh -c #(nop) ||g' \
        -e 's|/bin/sh -c|RUN|g'
