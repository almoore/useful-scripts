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

# Timestamp dates
MINUTES=20
S_DATE=$(date --utc +"%Y-%m-%dT%H:%M:%SZ" --date "-$MINUTES min")
E_DATE=$(date --utc +"%Y-%m-%dT%H:%M:%SZ")

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

cat << EOF >&2
Gathering events :
start date       : $S_DATE
end date         : $E_DATE
EOF

kubectl get events --all-namespaces --sort-by=lastTimestamp -o go-template-file --template $TMP
