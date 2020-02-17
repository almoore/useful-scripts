#!/usr/bin/env bash

usage () {
read -r -d '' USAGE << EOU
A simple wrapper script that searches the jq results.

USAGE:
   ${0##*/} [OPTIONS] QUERY_STRING [FILE]

OPTIONS:
  --debug        Turn on debug output

JQ OPTIONS:

$(get_jq_options)

For more advanced filters see the jq(1) manpage ("man jq")
and/or https://stedolan.github.io/jq
EOU
echo -e "$USAGE\n"
}

get_jq_options() {
  jq --help | grep -E '^  (\-[-A-Za-z]+)( a [v,f])*'
}

setup() {
  DEBUG=0
  COMMAND=()
  # parse args
  while [ "$1" != "" ] ; do
    case $1 in
      --debug )
        DEBUG=1
        ;;
      -h | --help )
        usage
        exit
        ;;
      --arg | --argjson | --slurpfile | --rawfile )
         COMMAND+=( "${1}" "${2}" "${3}" )
         shift
         shift
        ;;
      -* )
         COMMAND+=( "${1}" )
        ;;
      * )
          if [[ -z "${_QUERY}" ]]; then
            export _QUERY="${1}"
          elif [[ -z "${FILE}" ]]; then
            FILE="${1}"
          else
            echo "Error: Unrecognized option"
            usage
            exit 1
          fi
        ;;
      esac
  shift
  done

  if [[ -z "$_QUERY" ]]; then
      usage
      exit 1
  fi
}

main() {
    setup "$@"
    if [[ "$DEBUG" = 1 ]]; then
        set -x
    fi
    if [[ -z "${COMMAND[@]}" ]]; then
        COMMAND=( . )
    fi
    _PATHS=$(jq -r '[path(..)|map(if type=="number" then "["+tostring+"]" else tostring end)|join(".")|split(".[]")|join("[]")]|unique|map("."+.)|.[]' ${FILE})
    for p in ${_PATHS}; do
        echo "Query ${p}"
#        read -r -d '' CMD << EOC
        jq "${COMMAND[@]}" "${FILE}" | jq "select(${p} | contains(env._QUERY))"
#EOC
#        echo "$CMD"
    done
}

main "$@"
