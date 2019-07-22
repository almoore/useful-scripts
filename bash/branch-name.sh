#!/usr/bin/env bash
NAME="$@"
echo $NAME | tr '[:upper:]' '[:lower:]' | sed 's/\ /-/g'
