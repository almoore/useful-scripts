#!/bin/bash

cleanup() {
    rm -f $TMP
}

trap_caught() {
    echo "caught signal exiting"
    exit 1
}
trap trap_caught SIGINT SIGTERM
trap cleanup EXIT

usage() {
cat << EOF >&2
Collect events since a specified time from a Kubernetes cluster using kubectl

Usage:
  ${0##*/} [options]

Options:
  -n, --namespace          the namespaces to search in
  -l, --selector           selector (label query) to filter on
  --all-namespace          get events from all namespaces
  --debug                  turn on debug logging
  -h,--help                print this message and exit

EOF
}


parse_args() {
  OPTS=()
  DEBUG=0
  while [ -n "${1}" ]; do
    case "${1}" in
      -n|--namespace)
        OPTS+=( ${1} )
        shift
        NAMESPACE="$1"
        OPTS+=( ${1} )
        ;;
      -l|--selector)
        OPTS+=( ${1} )
        shift
        local selector="$1"
        OPTS+=( ${1} )
        ;;
      --all-namespace)
        OPTS+=( ${1} )
        ;;
      --debug)
        DEBUG=1
        OPTS+=( ${1} )
        ;;
      -h|--help)
        usage
        exit
        ;;
      *)
        if [ -z "${minutes}" ]; then
          local minutes="${1}"
        fi
        usage
        exit 1
        ;;
    esac
    shift
  done

  readonly SELECTOR="${selector:-''}"
  # Timestamp dates
  readonly MINUTES="${minutes:-20}"
  readonly S_DATE=$(date --utc +"%Y-%m-%dT%H:%M:%SZ" --date "-$MINUTES min")
  readonly E_DATE=$(date --utc +"%Y-%m-%dT%H:%M:%SZ")
}

setup_tempate() {
TMP=$(mktemp)
cat << TEMPLATE > $TMP
{{- /* "LAST_TIMESTAMP\t\tNAME\t\tKIND\t\tREASON\tMESSAGE" */ -}}
{{range .items}}
{{- if gt .lastTimestamp "$S_DATE" }}
{{- .lastTimestamp}}  {{- .involvedObject.name}}{{"\t"}}{{.involvedObject.kind}}{{"\t"}}{{.reason}}{{"\t"}}{{.message}}
{{- "\n"}}
{{- end}}
{{- end}}
TEMPLATE
}

get_events() {
cat << EOF >&2
Gathering events :
start date       : $S_DATE
end date         : $E_DATE
EOF
kubectl get events \
  --sort-by=lastTimestamp \
  "${OPTS[@]}" \
  -o go-template-file --template $TMP
}

main(){
  parse_args "$@"
  setup_tempate
  get_events
}

main "$@"
