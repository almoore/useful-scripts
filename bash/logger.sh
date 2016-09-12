#!/bin/bash

logger1()
{
    local log_file="$1"
    shift
    # Log everything to one file
    touch $log_file
    tail -f $log_file & 
    tailpid=$!
    ${@} &> $log_file 
    local error_code=$?
    kill $tailpid
    wait $tailpid 2>/dev/null
    return $error_code
}

logger2()
{
    local log_file="$1"
    # Change log_file extenstion for error log using shortest search from back 
    local error_file="${log_file%.*}_error.log"
    shift
    # Log stdout and stderr to seperate files
    ${@} > >(tee $log_file) 2> >(tee $error_file >&2)
    local error_code=$?
    return $error_code
}

mkdir "logger1"
cd logger1
logger1 "${@}"
cd -

mkdir "logger2"
cd logger2
logger2 "${@}"
cd -
