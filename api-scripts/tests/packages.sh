#!/usr/bin/env bash

set -e

# Stashy
export STASHY_VERSION="0.3"
bash packages/stashy.sh

# Gitpython
export GITPYTHON_VERSION="2.1.1"
bash packages/gitpython.sh

export PEPPER_VERSION="0.5.0"
bash packages/pepper.sh

export PYTHON_JENKINS_VERSION="0.4.13"
bash packages/python-jenkins.sh
