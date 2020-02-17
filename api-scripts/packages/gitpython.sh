#!/bin/sh

# Using the git library http://gitpython.readthedocs.io/en/stable/intro.html
GITPYTHON_VERSION=${GITPYTHON_VERSION:="2.1.1"}

pip install gitpython==${GITPYTHON_VERSION}
