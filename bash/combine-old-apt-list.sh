#!/usr/bin/env bash

cd /etc/apt/sources.list.d/
combine_files() {
    fn="${1}"
    gp="${2}"
    touch ${fn}
    # Grab all the dist upgrade files and make them one
    for f in $(grep trusty -l *.${gp}); do
        if [ "$f" != "$fn" ]; then
            echo "# from $f" >> ${fn}
            cat $f >> ${fn}
            echo "" >> ${fn}
            rm $f
        fi
    done
}

clean_saves() {
    for f in *.save; do
        list_name=$(basename -s .save $f)
        if [ ! -f $list_name ]; then
            rm $f
        fi
    done
}

combine_files trusty.list.distUpgrade distUpgrade
combine_files trusty.list list

clean_saves
