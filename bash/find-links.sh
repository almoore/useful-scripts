#!/bin/sh
# set -x
BASEDIR=${BASEDIR:-$HOME}
FILE=$(realpath "${1}")
MAXDEPTH=${MAXDEPTH:-3}
find -L ${BASEDIR} -maxdepth ${MAXDEPTH} -xtype l -samefile ${FILE} 2>/dev/null
