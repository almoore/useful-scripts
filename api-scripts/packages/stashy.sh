#!/bin/sh

# Using the api library https://github.com/RisingOak/stashy
STASHY_VERSION=${STASHY_VERSION:="0.3"}

pip install stashy==${STASHY_VERSION} -e git+https://github.com/cosmin/stashy.git
