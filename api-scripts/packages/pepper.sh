#!/bin/sh

# Using the api library https://github.com/saltstack/pepper
PEPPER_VERSION=${PEPPER_VERSION:="0.5.0"}

pip install pepper==${PEPPER_VERSION}
