#!/bin/sh
package=$1
script_name=${0##*/} 
script_path=${0%/*}
if [ -z $package ] ; then
    echo "Usage: $script_name <package name>"
    echo
    exit 1
fi
apt-cache depends ${package} | awk '/Depends/ {print $2}' | sort -u
