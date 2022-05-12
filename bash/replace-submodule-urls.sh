#!/usr/bin/env sh
BASE=$(git rev-parse --show-toplevel)
ls ${BASE}/.git/modules/*/config  ${BASE}/.gitmodules | xargs sed -i 's#ssh://git@#https://#g'
