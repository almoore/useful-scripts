#!/usr/bin/env bash

usage () {
read -r -d '' USAGE << EOU
Script that searches the ssm parameter names for a string using

USAGE:
   aws-ssm-find STRING
EOU
echo -e "$USAGE" >&2
}

setup() {
  DEBUG=0
  # parse args
  while [ "$1" != "" ] ; do
    case $1 in
      -p | --path )
        shift
        _PATH=$1
        ;;
      --debug )
        DEBUG=1
        ;;
      --region )
        shift
        REGION="--region $1"
        ;;
      -h | --help )
        usage
        exit
        ;;
      * )
          export _QUERY="$1"
        ;;
      esac
  shift
  done

  if [ -z "$_QUERY" -a -z "$_PATH" ]; then
      usage
      exit 1
  fi
}

main() {
    setup "$@"
    if [ "$DEBUG" = 1 ]; then
        set -x
    fi
    echo "Sending query to aws secretmanager ..." >&2
    TMP=$(mktemp)
    
    aws secretsmanager list-secrets $REGION > $TMP
    if [ -z "$_QUERY" ]; then
        cat $TMP | jq '.'
    else
        cat $TMP | jq '.SecretList | map(select(.Name | contains(env._QUERY))) | { Parameters: . }'
    fi        
    rm $TMP
}

main "$@"
