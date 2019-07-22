#!/usr/bin/env bash
#
# Uses kubectl to collect cluster information.
# Dumps:

_PREV_CONTEXT=$(kubectl config current-context)
CONTEXT=${K8S_CONTEXT:-$_PREV_CONTEXT}
DEBUG=0
DUMP_ALL_RESOURCES=0
DUMP_BY_NAMESPACE=0
date=$(date +"%Y%m%d%H%M%S")
prefix=$date

set -e

usage() {
cat << EOF >&2
Collect data from a Kubernetes cluster using kubectl

Usage:
  ${0##*/} [options]

Options:
  -n, --namespaces         space seperated list of namespaces to search
  -k, --kinds              comma seperated list of kinds of object to restrict
                              the dump to example: configmaps,secrets,events,pods
  -l, --selector           selector (label query) to filter on
  -a, --all                if present, collects from all namespace and kinds
  -R, --by-resource        if present, dump by resource and kind
  -p, --prefix             the prefix to write to; defaults to date string
  -d, --output-directory   directory to output files; defaults to
                              "k8s-backup/<prefix-dir>"
  -z, --archive            if present, archives and removes the output
                              directory
  -q, --quiet              if present, do not log
  --error-if-nasty-logs    if present, exit with 255 if any logs
                              contain errors
  --debug                  turn on debug logging

EOF
}

run() {
    if [ "VERBOSE" == 1 ]; then
        printf "+%b\n" "$@" 1>&2
    fi
    "$@"
}

log() {
  local msg="${1}"
  if [ "${QUIET}" = false ]; then
    printf "%b\n" "${msg}"
  fi
}

error_out() {
  local msg="${1}"
  RED='\E[1;31m'
  RESET='\E[0m'
  printf "${RED}%b ${RESET}\n" "${msg}" >&2
}

parse_args() {
  while [ -n "${1}" ]; do
    case "${1}" in
      -n|--namespaces)
        shift
        DUMP_BY_NAMESPACE=1
        NAMESPACES="$NAMESPACES $1"
        ;;
      -k|--kinds)
        shift
        KINDS="$1"
        ;;
      -l|--selector)
        shift
        local selector="$1"
        ;;
      -p|--prefix)
        shift
        prefix="${1}"
        ;;
      -d|--output-directory)
        shift
        local out_dir="${1}"
        ;;
      -z|--archive)
        local should_archive=true
        ;;
      -a|--all)
        DUMP_ALL_RESOURCES=1
        ;;
      -R|--by-resource)
        DUMP_BY_NAMESPACE=1
        ;;
      -L|--no-logs)
        NO_LOGS=1
        ;;
      -q|--quiet)
        local quiet=true
        ;;
      -v|--verbose)
        local verbose=0
        ;;
      --debug)
        DEBUG=1
        ;;
      --error-if-nasty-logs)
        local should_check_logs_for_errors=true
        ;;
      *)
        usage
        exit
        ;;
    esac
    shift
  done

  if [ "${DUMP_ALL_RESOURCES}" == 1 ]; then
    KINDS=""
    NAMESPACES=""
  fi
  readonly OUT_DIR=${out_dir:-${PWD}/k8s-backup/$prefix}
  readonly SHOULD_ARCHIVE=${should_archive:-false}
  readonly QUIET=${quiet:-false}
  if [ "$QUIET" == true ]; then
      readonly VERBOSE=0
  else
      readonly VERBOSE=${verbose:-0}
  fi
  readonly SHOULD_CHECK_LOGS_FOR_ERRORS=${should_check_logs_for_errors:-false}
  readonly LOG_DIR="${OUT_DIR}/logs"
  readonly RESOURCES_FILE="${OUT_DIR}/resources.yaml"
  readonly CUSTOM_RESOURCES_FILE="${OUT_DIR}/custom-resources.yaml"
  readonly SELECTOR=$(if [ -n "${selector}" ]; then echo "-l ${selector}"; fi)
}

check_prerequisites() {
  local prerequisites=$*
  for prerequisite in ${prerequisites}; do
    if ! command -v "${prerequisite}" > /dev/null; then
      error "\"${prerequisite}\" is required. Please install it."
      return 1
    fi
  done
}

dump_time() {
  mkdir -p "${OUT_DIR}"
  date -u > "${OUT_DIR}/DUMP_TIME"
}

dump_logs_for_container() {
  local namespace="${1}"
  local pod="${2}"
  local container="${3}"

  log "Retrieving logs for ${namespace}/${pod}/${container}"

  mkdir -p "${LOG_DIR}/${namespace}/${pod}"
  local log_file_head="${LOG_DIR}/${namespace}/${pod}/${container}"

  local log_file="${log_file_head}.log"
  run kubectl logs --namespace="${namespace}" "${pod}" "${container}" \
      > "${log_file}"

  local filter="?(@.name == \"${container}\")"
  local json_path='{.status.containerStatuses['${filter}'].restartCount}'
  local restart_count
  restart_count=$(kubectl get --namespace="${namespace}" \
      pod "${pod}" -o=jsonpath="${json_path}")
  if [ "${restart_count}" -gt 0 ]; then
    log "Retrieving previous logs for ${namespace}/${pod}/${container}"

    local log_previous_file
    log_previous_file="${log_file_head}_previous.log"
    run kubectl logs --namespace="${namespace}" \
        --previous "${pod}" "${container}" \
        > "${log_previous_file}"
  fi
}

# Run functions on each container. Each argument should be a function which
# takes 3 args: ${namespace} ${pod} ${container}.
# If any of the called functions returns error, tap_containers returns
# immediately with that error.
tap_containers() {
  local functions=( "$@" )

  if [ -z "$NAMESPACES" ]; then
      NAMESPACES=$(kubectl get \
      namespaces -o=jsonpath="{.items[*].metadata.name}")
  fi
  for namespace in ${NAMESPACES}; do
    local pods
    pods=$(kubectl get --namespace="${namespace}" \
        pods ${SELECTOR} -o=jsonpath='{.items[*].metadata.name}')
    for pod in ${pods}; do
      local containers
      containers=$(kubectl get --namespace="${namespace}" \
          pod "${pod}" -o=jsonpath='{.spec.containers[*].name}')
      for container in ${containers}; do

        for f in "${functions[@]}"; do
          "${f}" "${namespace}" "${pod}" "${container}" || return $?
        done

      done
    done
  done

  return 0
}

dump_kubernetes_resources() {
  log "Retrieving kubernetes resource configurations"

  mkdir -p "${OUT_DIR}"
  # Only works in Kubernetes 1.8.0 and above.
  run kubectl get --all-namespaces \
      ${KINDS} \
      -o yaml > "${RESOURCES_FILE}"
}

dump_custom_resource_definitions() {
  log "Retrieving custom resource configurations"

  local custom_resources
  # Trim to only first field; join by comma; remove last comma.
  custom_resources=$(kubectl get customresourcedefinitions \
      --no-headers 2> /dev/null \
      | cut -d ' ' -f 1 \
      | tr '\n' ',' \
      | sed 's/,$//')

  if [ ! -z "${custom_resources}" ]; then
    run kubectl get "${custom_resources}" --all-namespaces -o yaml \
        > "${CUSTOM_RESOURCES_FILE}"
  fi
}

dump_resources() {
  dump_kubernetes_resources
  dump_custom_resource_definitions

  mkdir -p "${OUT_DIR}"
  run kubectl cluster-info dump > "${OUT_DIR}/cluster-info.dump.txt"
  run kubectl describe --all-namespaces pods  > "${OUT_DIR}/all-pods.txt"
  run kubectl get events --all-namespaces -o wide > "${OUT_DIR}/events.txt"
}

archive() {
  local parent_dir
  parent_dir=$(dirname "${OUT_DIR}")
  local dir
  dir=$(basename "${OUT_DIR}")

  pushd "${parent_dir}" > /dev/null || exit
  tar -czf "${dir}.tar.gz" "${dir}"
  popd > /dev/null || exit

  log "Wrote ${parent_dir}/${dir}.tar.gz"
}

check_logs_for_errors() {
  log "Searching logs for errors."
  grep -R --include "${LOG_DIR}/*.log" --ignore-case -e 'segmentation fault'
}

setup_output() {
  if [ "${DEBUG}" -ne 0 ]; then
      set -x
  fi

  if [ "$_PREV_CONTEXT" != "$CONTEXT" ] ; then
      run kubectl config use-context $CONTEXT
  fi

  if [ -z "$NAMESPACES" ]; then
      NAMESPACES=$(kubectl get \
      namespaces -o=jsonpath="{.items[*].metadata.name}")
  fi

  if [ -z "$KINDS" ]; then
      KINDS=all,jobs,ingresses,endpoints,customresourcedefinitions,configmaps,secrets,events,pvc
  fi
  if [ -z ${OUT_DIR} ]; then
      error_out "Output Directory not set"
  fi
  mkdir -p ${OUT_DIR}
  cd ${OUT_DIR}
  touch manifest.txt
}

dump_by_namespace_and_kind() {
  local namespace
  local skip_replicaset
  _rs=$(echo $KINDS | grep -E -q "(\brs\b|replicaset)" || skip_replicaset=1 )
  for namespace in $NAMESPACES; do
    log "Getting namespace ${namespace}"
    mkdir -p $namespace
    prev=""
    for n in $(kubectl get $KINDS -o name -n ${namespace} ${SELECTOR}); do
      kind=$(dirname $n)
      item=$(basename $n)
      if [ "${skip_replicaset}" == 1 ] && echo ${kind} | grep -q replicaset ; then
        continue
      fi
      if [ "$prev" != "$kind" ]; then
        prev=$kind
        log "\t${kind}"
        mkdir -p ${namespace}/${kind}
      fi
      echo ${namespace}/${n}.yaml >> manifest.txt
      run kubectl get $kind $item -n ${namespace} -o yaml > ${namespace}/${n}.yaml
    done
  done
}

main() {
  local exit_code=0
  run parse_args "$@"
  run setup_output
  run check_prerequisites kubectl
  run dump_time
  if [ "${DUMP_ALL_RESOURCES}" -eq 1 ]; then
    run dump_resources
  fi
  if [ "${DUMP_BY_NAMESPACE}" -eq 1 ]; then
    run dump_by_namespace_and_kind
  fi
  if [ "$NO_LOGS" != 1 ]; then
      run tap_containers dump_logs_for_container
      exit_code=$?
  fi
  if [ "${SHOULD_CHECK_LOGS_FOR_ERRORS}" = true ]; then
    if ! check_logs_for_errors; then
      exit_code=255
    fi
  fi

  if [ "${SHOULD_ARCHIVE}" = true ] ; then
    archive
    rm -r "${OUT_DIR}"
  fi
  log "Wrote to ${OUT_DIR}"

  return ${exit_code}
}

main "$@"
