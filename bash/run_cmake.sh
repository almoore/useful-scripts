#!/bin/bash
set -e -x

# This script is made to have less repetitive commands during the build process 
# This is done by selecting some default variables that are best left out 
# of the CMakeLists.txt

# NOTE: The SDK_DIR cmake variable needs to be changed to one you use 
# or implemented in you cmake files.

GEN="-GNinja"
S=${HOME}/repos
r=${PWD##*/}
build_type=Release
SOURCE_DIR=${S}/$r
BUILD_NOW=1
BUILD_DIR_SET_MANULALY=0

while [ "$1" != "" ] ; do
    case $1 in 
        --sdk | -S )
            shift
            SDK_DIR=$1
            ;;
        --make )
            GEN=""
            ;;
        --build )
            BUILD_NOW=1
            ;;
        --no-build | -N)
            BUILD_NOW=0
            ;;
        --build-dir)
            shift
            BUILD_DIR=$1
            BUILD_DIR_SET_MANULALY=1
            ;;
        -D* | -W* )
            options="$options $1"
            ;;
        --debug )
            build_type=Debug
            ;;
        --base-dir | -B )
            shift
            S=$1
            ;;
        --source-dir | -s )
            shift
            SOURCE_DIR=$1
            SOURCE_DIR_SET_MANUALLY=1
            ;;
        *)
            SOURCE_DIR=$1
            SOURCE_DIR_SET_MANUALLY=1
            ;;
        
    esac
shift
done

if [ -z ${SDK_DIR} ] ; then
    SDK_DIR=${S}/sdk
fi

options="$options -DCMAKE_BUILD_TYPE=${build_type} $GEN"

if [ ! -e /usr/share/SDK* ] ; then
    echo "Using : -DSDK_DIR=${SDK_DIR}"
    options="$options -DSDK_DIR=${SDK_DIR}"
fi  

if ! ls ${SOURCE_DIR}/CMakeLists.txt &> /dev/null ; then
    if [ "$SOURCE_DIR_SET_MANUALLY" == "1" ] ; then
        echo "$SOURCE_DIR does not seem to have a CMakeLists.txt in it." >&2
    else
        echo "$SOURCE_DIR does not seem to have a CMakeLists.txt in it."
        echo "Checking this directory or its parent have a CMakeLists.txt file."
        if ls CMakeLists.txt &> /dev/null ; then
        # Check to see if this is a sub directory with a CmakeLists file
            SOURCE_DIR=$PWD
        elif ls ../CMakeLists.txt> /dev/null ; then
            SOURCE_DIR=${PWD%/*} # could also use $(cd .. ; pwd)
        fi
    fi
fi

cmake ${SOURCE_DIR} ${options}

if [ $BUILD_NOW -eq 1 ] ; then
    if [ $BUILD_DIR_SET_MANUALLY -eq 1 ] ; then
        cmake --build $BUILD_DIR
    else
        cmake --build $PWD
    fi
fi
