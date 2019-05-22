#!/bin/bash

get_os_type() {
    case "$OSTYPE" in
        darwin* )
        OS_STRING="darwin"
        ;;
        linux-gnu|freebsd*)
        OS_STRING="linux"
        ;;
        cygwin | msys | mingw | win32 )
        OS_STRING="window"
        ;;
        * )
        echo "OSTYPE=$OSTYPE unknow not able to proceed"
        exit 1
        ;;
    esac
}

get_os_type
echo "Found os type: $OSTYPE os family: $OS_STRING"
