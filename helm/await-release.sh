#!/usr/bin/env bash

# This script is a workaround for helm issues with timeouts
# helm install --wait should do everything this script does.

set -e

cleanup() {
    rm -f $TMP
}

trap_caught() {
    echo "caught signal exiting"
    exit 1
}
trap trap_caught SIGINT SIGTERM
trap cleanup EXIT

error() {
  echo "$*" >&2
}

usage() {
cat << EOF >&2
Collect data from a Kubernetes cluster using kubectl

Usage:
  ${0##*/} [flags]

Flags:
  -r, --release            the release to wait for
  -t, --timeout            the number of seconds to wait; defaults to 600
  -n, --namespace          the namespaces to search in; defaults to default
  -c, --context            the kubectl context to use; defaults to current-context

  --debug                  turn on debug logging

EOF
}

log() {
  local msg="${1}"
  if [ "${QUIET}" = false ]; then
    printf '%s\n' "${msg}"
  fi
}

parse_args() {
  debug=0
  while [ ! -z "${1}" ]; do
    case "${1}" in
      -r|--release)
        shift
        _release="${1}"
        ;;
      -t|--timeout)
        shift
        arg_timeout="${1}"
        ;;
      -n|--namespace)
        shift
        KUBE_NAMESPACE="${1}"
        ;;
      -c|--context)
        shift
        KUBE_CONTEXT="${1}"
        ;;
      --debug)
        debug=1
        ;;
      *)
        error "Unknown argument: ${1}"
        usage
        exit 1
        ;;
    esac
    shift
  done
  if [ -z "$arg_timeout" ]; then
    arg_timeout=600
  fi
  readonly timeout=$(date --utc +"%s" --date "+${arg_timeout} sec")
  readonly release="${_release}"
  if [ "${debug}" -ne 0 ]; then
      set -x
  fi
}

get_timestamp() {
    timestamp=$(date --utc +"%s")
    echo $timestamp
}

main() {
  local pod_status
  TMP="$(mktemp)"
  KUBE_CONTEXT=${KUBE_CONTEXT:-""}
  KUBE_NAMESPACE=${KUBE_NAMESPACE:-default}
  parse_args "$@"

  if [ -z "$KUBE_CONTEXT" ]; then
    KUBE_CONTEXT=$(kubectl config current-context)
  fi
  timestamp=$(get_timestamp)
  start=$timestamp
  while [ "$timestamp" -lt "$timeout" ]; do
    helm ls -q --kube-context "${KUBE_CONTEXT}" > "${TMP}"

    if ! grep -qF "${release}" "${TMP}" ; then
      echo "${release} not found. $(($timestamp - $start))/${arg_timeout} checks completed; retrying."
      cat "${TMP}" 2>&1
      echo 1>&2
      timestamp=$(get_timestamp)
      sleep 10
    else
      break
    fi
  done

  if [ "$timestamp" -ge "$timeout" ]; then
    error "${release} failed to appear."
    return 1
  fi

  while [ $timestamp -lt $timeout ]; do
    pending_pods="$(kubectl get pods \
      -l "release=${release}" \
      -o 'custom-columns=NAME:.metadata.name,STATUS:.status.phase' \
      -n "${KUBE_NAMESPACE}" \
      --context "${KUBE_CONTEXT}" \
      | tail -n +2 \
    )"

    if echo "${pending_pods}" | grep -qvF 'Running'; then
      echo "${release} pods not ready. $(($timestamp - $start))/${arg_timeout} checks completed; retrying."

      echo "${pending_pods}" | grep -vF 'Running' 1>&2
      echo 1>&2

      timestamp=$(get_timestamp)
      sleep 10
    else
      echo "All ${release} pods running. Done!"
      return 0
    fi
  done

  echo "Release ${release} did not complete in time" 1>&2
  return 1
}

main "$@"
