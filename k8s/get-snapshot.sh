#!/bin/bash
#
# Uses kubectl to collect cluster information.
# Dumps:

_PREV_CONTEXT=$(kubectl config current-context)
CONTEXT=${K8S_CONTEXT:-$_PREV_CONTEXT}
debug=0
build=1
date=$(date +"%Y%m%d%H%M%S")
prefix=$date

error() {
  echo "$*" >&2
}

usage() {
cat << EOF >&2
USAGE: ${0##*/} [options]
  options:
  -n | --namespaces NAMESPACES
  -k | --kinds KINDS
  --prefix PREFIX
  --debug
EOF
}

log() {
  local msg="${1}"
  if [ "${QUIET}" = false ]; then
    printf '%s\n' "${msg}"
  fi
}

parse_args() {
  while [ -n "${1}" ]; do
    case "${1}" in
      -n | --namespaces)
        shift
        NAMESPACES="$NAMESPACES $1"
        ;;
      -k | --kinds)
        shift
        KINDS="$1"
        ;;
      --prefix |
        shift
        prefix="${1}"
        ;;
      -d | --output-directory)
        shift
        local out_dir="${1}"
        ;;
      -z|--archive)
        local should_archive=true
        ;;
      -q|--quiet)
        local quiet=true
        ;;
      --debug)
        debug=1
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

  readonly OUT_DIR="${out_dir:k8s-backup/$prefix}"
  readonly SHOULD_ARCHIVE="${should_archive:-false}"
  readonly QUIET="${quiet:-false}"
  readonly SHOULD_CHECK_LOGS_FOR_ERRORS="${should_check_logs_for_errors:-false}"
  readonly LOG_DIR="${OUT_DIR}/logs"
  readonly RESOURCES_FILE="${OUT_DIR}/resources.yaml"
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
  kubectl logs --namespace="${namespace}" "${pod}" "${container}" \
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
    kubectl logs --namespace="${namespace}" \
        --previous "${pod}" "${container}" \
        > "${log_previous_file}"
  fi
}

copy_core_dumps_if_istio_proxy() {
  local namespace="${1}"
  local pod="${2}"
  local container="${3}"
  local got_core_dump=false

  if [ "${got_core_dump}" = true ]; then
    return 254
  fi
}

# Run functions on each container. Each argument should be a function which
# takes 3 args: ${namespace} ${pod} ${container}.
# If any of the called functions returns error, tap_containers returns
# immediately with that error.
tap_containers() {
  local functions=( "$@" )

  local namespaces
  namespaces=$(kubectl get \
      namespaces -o=jsonpath="{.items[*].metadata.name}")
  for namespace in ${namespaces}; do
    local pods
    pods=$(kubectl get --namespace="${namespace}" \
        pods -o=jsonpath='{.items[*].metadata.name}')
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
  kubectl get --all-namespaces --export \
      all,jobs,ingresses,endpoints,customresourcedefinitions,configmaps,secrets,events \
      -o yaml > "${RESOURCES_FILE}"
}

dump_istio_custom_resource_definitions() {
  log "Retrieving istio resource configurations"

  local istio_resources
  # Trim to only first field; join by comma; remove last comma.
  istio_resources=$(kubectl get customresourcedefinitions \
      --no-headers 2> /dev/null \
      | cut -d ' ' -f 1 \
      | tr '\n' ',' \
      | sed 's/,$//')

  if [ ! -z "${istio_resources}" ]; then
    kubectl get "${istio_resources}" --all-namespaces -o yaml \
        > "${ISTIO_RESOURCES_FILE}"
  fi
}

dump_resources() {
  dump_kubernetes_resources
  dump_istio_custom_resource_definitions

  mkdir -p "${OUT_DIR}"
  kubectl cluster-info dump > "${OUT_DIR}/cluster-info.dump.txt"
  kubectl describe pods -n istio-system > "${OUT_DIR}/istio-system-pods.txt"
  kubectl get events --all-namespaces -o wide > "${OUT_DIR}/events.txt"
}

dump_pilot_url(){
  local pilot_pod=$1
  local url=$2
  local dname=$3
  local outfile

  outfile="${dname}/$(basename "${url}")"

  log "Fetching ${url} from pilot"
  kubectl -n istio-system exec -i -t "${pilot_pod}" -c istio-proxy -- \
      curl "http://localhost:8080/${url}" > "${outfile}"
}

dump_pilot() {
  local pilot_pod
  pilot_pod=$(kubectl -n istio-system get pods -l istio=pilot \
      -o jsonpath='{.items[*].metadata.name}')

  if [ ! -z "${pilot_pod}" ]; then
    local pilot_dir="${OUT_DIR}/pilot"
    mkdir -p "${pilot_dir}"

    dump_pilot_url "${pilot_pod}" debug/configz "${pilot_dir}"
    dump_pilot_url "${pilot_pod}" debug/endpointz "${pilot_dir}"
    dump_pilot_url "${pilot_pod}" debug/adsz "${pilot_dir}"
    dump_pilot_url "${pilot_pod}" metrics "${pilot_dir}"
  fi
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
  if [ "${debug}" -ne 0 ]; then
      set -x
  fi

  if [ "$_PREV_CONTEXT" != "$CONTEXT" ] ; then
      kubectl config use-context $CONTEXT
  fi

  if [ -z "$NAMESPACES" ]; then
      NAMESPACES=$(kubectl get namespace -o name | xargs -n1 basename)
  fi

  if [ -z "$KINDS" ]; then
      KINDS=all,jobs,ingresses,endpoints,customresourcedefinitions,configmaps,secrets,events,pvc
  fi
  mkdir -p $${OUT_DIR}
  cd $${OUT_DIR}
  touch manifest.txt
}

main() {
  local exit_code=0
  parse_args "$@"
  setup_output
  check_prerequisites kubectl
  dump_time
  for ns in $NAMESPACES; do
    log "Getting namespace ${ns}"
    mkdir -p $ns
    prev=""
    for n in $(kubectl get $KINDS -o name -n $ns); do
      kind=$(dirname $n)
      item=$(basename $n)
      if [ "$prev" != "$kind" ]; then
        prev=$kind
        log -e "\t${kind}"
        mkdir -p ${ns}/${kind}
      fi
      echo ${ns}/${n}.yaml >> manifest.txt
      kubectl get $kind $item -n ${ns} -o yaml | k8s-filter > ${ns}/${n}.yaml
    done
  done

  return ${exit_code}
}

main "$@"
