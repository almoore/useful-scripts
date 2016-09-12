#!/usr/bin/env bash
S=$PWD
git_ext=".git"
RED='\E[1;31m'
GREEN='\E[1;32m'
YELLOW='\E[1;33m'
NORMAL='\E[0m'

DIST_NAME="$(lsb_release -i -s)"
if [ "$DIST_NAME" == "CentOS" ] ; then
    RELEASE=$(lsb_release -r -s | awk -F . '{print $1}')
    sudo yum install -y libxml2-devel libxslt-devel
else
    RELEASE=$(lsb_release -r -s)
    sudo apt-get install -y libxml2-dev libxslt1-dev
fi
DIST=${DIST_NAME}${RELEASE}
cd ${HOME}/python27/bin
export PATH=${PWD}:$PATH
mkdir -p /vagrant/resources/${DIST}
cd  /vagrant/resources/${DIST}
pip wheel lxml


