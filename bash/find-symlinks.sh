#!/bin/sh
# set -x
BASEDIR="${1:-.}"
find -L ${BASEDIR} -xtype l
