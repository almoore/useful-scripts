#!/bin/bash
dir_name=${PWD##*/}
files=$(ls *.h)
for f in $files; do
    if ! grep "\b${f//\./\\\.}\b" ${dir_name}.vcxproj > /dev/null ; then
        nfound="$nfound $f"
    else
        found="$found $f"
    fi
done

if [ "$nfound" == "" ] ; then
    echo "All headers found"
else
    echo "Files not found in ${dir_name}.vcxproj:"
    echo "$nfound"
fi

unset nfound found
