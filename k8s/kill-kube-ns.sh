#!/bin/bash
# Force-delete a stuck Kubernetes namespace by clearing its finalizers via the
# API server's /finalize subresource. Use only when normal `kubectl delete ns`
# has been hanging in Terminating phase.

###############################################################################
# Copyright (c) 2018 Red Hat Inc
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0
#
# SPDX-License-Identifier: EPL-2.0
###############################################################################

set -eo pipefail

die() { echo "$*" 1>&2 ; exit 1; }

need() {
	which "$1" &>/dev/null || die "Binary '$1' is missing but required"
}

# checking pre-reqs

need "jq"
need "curl"
need "kubectl"

PROJECT="$1"
shift

test -n "$PROJECT" || die "Missing arguments: kill-ns <namespace> (set CONFIRM=yes to skip prompt for batch use)"

CONTEXT=$(kubectl config current-context)

PHASE=$(kubectl get ns "$PROJECT" -o jsonpath='{.status.phase}' 2>/dev/null) \
    || die "Namespace '$PROJECT' not found in context '$CONTEXT'"

META_FINALIZERS=$(kubectl get ns "$PROJECT" -o jsonpath='{.metadata.finalizers}')
SPEC_FINALIZERS=$(kubectl get ns "$PROJECT" -o jsonpath='{.spec.finalizers}')

echo "Context:             $CONTEXT"
echo "Namespace:           $PROJECT (phase: $PHASE)"
echo "spec.finalizers:     ${SPEC_FINALIZERS:-<none>}"
echo "metadata.finalizers: ${META_FINALIZERS:-<none>}"

if [ -n "$META_FINALIZERS" ] && [ "$META_FINALIZERS" != "[]" ] && [ "$META_FINALIZERS" != "null" ]; then
    echo
    echo "NOTE: metadata.finalizers is non-empty. /finalize only mutates spec.finalizers."
    echo "      If the namespace stays Terminating after this run, also clear metadata with:"
    echo "        kubectl patch ns $PROJECT --type=merge -p '{\"metadata\":{\"finalizers\":[]}}'"
fi
echo

if [ "$CONFIRM" != "yes" ]; then
    if [ "$PHASE" = "Terminating" ]; then
        PROMPT="Force-finalize stuck namespace '$PROJECT' on '$CONTEXT'? [y/N] "
    else
        PROMPT="Namespace '$PROJECT' is '$PHASE' (not yet Terminating). Delete + force-finalize on '$CONTEXT'? [y/N] "
    fi
    read -r -p "$PROMPT"
    [[ "$REPLY" =~ ^[Yy]$ ]] || die "Aborted."
fi

if [ "$PHASE" != "Terminating" ]; then
    echo "Initiating delete (graceful)..."
    kubectl delete ns "$PROJECT" --wait=false
    # give the API server a moment to flip phase to Terminating before the /finalize PUT
    for _ in 1 2 3 4 5; do
        sleep 1
        PHASE=$(kubectl get ns "$PROJECT" -o jsonpath='{.status.phase}' 2>/dev/null) || { echo "Namespace gone — clean exit."; exit 0; }
        [ "$PHASE" = "Terminating" ] && break
    done
fi

kubectl proxy &>/dev/null &
PROXY_PID=$!
killproxy () {
	kill $PROXY_PID
}
trap killproxy EXIT

sleep 1 # give the proxy a second

echo "Getting namespaced api-resources in $PROJECT"
#kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n "$PROJECT"
for o in $(kubectl api-resources --verbs=list --namespaced -o name); do
    echo "Get kind $o"
    kubectl get --show-kind --ignore-not-found -n "$PROJECT" $o
done

kubectl get namespace "$PROJECT" -o json | jq 'del(.spec.finalizers[] | select(. == "kubernetes"))' | curl -s -k -H "Content-Type: application/json" -X PUT -o /dev/null --data-binary @- http://localhost:8001/api/v1/namespaces/$PROJECT/finalize && echo "Killed namespace: $PROJECT"


# proxy will get killed by the trap

