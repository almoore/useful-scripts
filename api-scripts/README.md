API Scripts
===========

# Purpose

The main purpose of this repo is to share work that has been done for the
different API's such as stash, salt, jenkins, bamboo, etc.

# Setup

Most of the packages that are to be install are python packages but that might
change. So to support that a general bash script has been added to centralize
the installation and versions. The tests/packages.sh script is there to test
and install packages that would need to be installed.


# Scripts

## hooks
Meant for configuring hooks or gathering data about those hooks.
## jenkins
Working with jenkins. For doing things like
  * Adding a default Jenkinsfile
  * Doing something to many repos
  * Checking dependencies
  * Adding a config file for a jenkins job

## packages
Setup of this repo and installation of packages
## salt
  * salt-api calls used from jenkins such as pepper calls and curl calls
  * api-test script for running common commands that would show that the salt api is funcional

## util
There is another README in that directory that has more details about the scripts in there. 

[VIEW UTIL README](./util/README.md)
