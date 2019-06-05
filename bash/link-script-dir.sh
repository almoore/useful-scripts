#!/usr/bin/env bash

BASE=$PWD
GC="\033[1;32m"
EC="\033[1;0m"
DEST="$HOME/bin"

printgreen() {
    printf "${GC}%s${EC}\n" "$@";
}

if [ "$#" -lt 1 ]; then
  printgreen "Please supply a directory to link"
  exit 1
elif [ "$#" -eq 1 ]; then
  SRC="$(realpath $1)"
elif [ "$#" -eq 2 ]; then
  SRC="$(realpath $1)"
  DEST="$2"
fi

if [ ! -z "${SRC}" ]; then
    FILES=$(find ${SRC} -maxdepth 1 -type f)
fi

PREFIX="$(basename ${SRC})"

for f in $FILES; do
  FN="$(basename  -s '.sh' $f)"
  ln -sv "${f}" "${DEST}/${PREFIX}-${FN}"
done
