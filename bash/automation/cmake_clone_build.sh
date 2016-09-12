#!//usr/bin/env bash
S=$PWD
B=${S}/build
_github_user="almoore"
_github_url_base="github.com"
sdk_url="" # If there is need of an SDK or toolchain to source
SDK_PATH="" # SDK path if toolchain or package is preinstalled
project_base_url="" # Put common base url here
repos="" # Put a list of repos to clone from the common base ie "repo1 repo2 repo3"

set_git_url()
{
    if [ -z "$github_url_base" ] ; then
	github_url_base=$_github_url_base
	echo "Selected default - $github_url"
    fi
    github_url="${github_url_base}:${github_user}/"
}

usage()
{
    echo "$0 [options]"
    echo "Options:"
    echo " -h , --help       print this message"
    echo " -g , --giturl     set git server url"
    echo " -u , --username   set git user name"
    echo " -l , --local      install and use local artifacts"
}

local=0
while [ "$1" != "" ]; do
    case $1 in
        -g | --giturl )
            shift; github_url_base="$1";set_git_url
            ;;
        -u | --username )
            shift; username="$1";
            ;;
        -l | --local )
            shift; local=1;
            ;;
        *)
            echo "Unknown argument $1" >&2
            exit 1
            ;;
    esac
    shift
done


if which git > /dev/null ; then
    if [ ! -x "$username" ] ; then
        git config --global user.name "$username"
        sdk_url="https://${username}@${git_url}/sdk.git"
        project_base_url="https://${username}@${git_url}/${project}"
    fi
    git config --global color.ui auto
    git config --global credential.helper store
else
    echo -e '\e[0;31m'"git is not installed"'\e[0m'
    exit 0
fi

# get sdk if one is not installed
if [ ! -e ${SDK_PATH}* ] ; then
    git clone $sdk_url
fi

# fetch all native code
cd $S
for r in $repos; do
    git clone ${project_base_url}/${r}.git
done
# create build dirs
mkdir -p ${B}
cd ${B}
mkdir $repos

for r in $repos; do
    cd ${B}/${r}
    pwd
    if [ -e /usr/share/StorageCraftSDK* ] ; then
        cmake ${S}/$r -DCMAKE_BUILD_TYPE=Release -GNinja
    else
        cmake ${S}/$r -DCMAKE_BUILD_TYPE=Release -DSDK_DIR=${S}/sdk -GNinja
    fi
    succ_list_header="Sucessful builds:\n"
    fail_list_header="Failed builds:\n"
    if ! ninja ; then
        msg="failed build: $r"
        echo -e '\E[1;31m'"\033[1m${msg}\033[0m"   # Red
        fail_list="${fail_list} ${r}\n"
    else
        msg="successful build:$r"
        echo -e '\E[1;32m'"\033[1m${msg}\033[0m"   # Green
        succ_list="${succ_list} ${r}\n"
    fi

    if [ "$local" == "1" ] ; then
        if ! ninja install ; then
            msg="failed install: $r"
            echo -e '\E[1;31m'"\033[1m${msg}\033[0m"   # Red
            fail_list="${fail_list} ${r} install\n"
        fi
    fi
done

if [ ! -z "$succ_list" ] ; then
    echo -e '\n'$succ_list_header'\e[0;32m'${succ_list}'\e[0m'
fi
if [ ! -z "$fail_list" ] ; then
    echo -e '\n'$fail_list_header'\e[0;31m'${fail_list}'\e[0m'
fi
