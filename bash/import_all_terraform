#!/usr/bin/env bash
PROVIDER=${1:-aws}
PROFILE=${2}
RESOURCES=$(terraformer import $PROVIDER list | xargs | sed 's/ /,/g')
terraformer import $PROVIDER --profile="$PROFILE" -r $RESOURCES
