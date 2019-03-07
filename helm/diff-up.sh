#!/bin/sh
_PREV_CONTEXT=$(kubectl config current-context)
CONTEXT=${K8S_CONTEXT:-$_PREV_CONTEXT}
debug=0
build=1
date=$(date +"%Y%m%d%H%M%S")
prefix=$date
FLAGS=()
valueFiles=()

usage() {
cat << EOF
USAGE: ${0##*/} [flags] [RELEASE] [CHART]

Examples:
  ${0##*/} my-release stable/postgresql --values values.yaml

Flags:
      --allow-unreleased         enables diffing of releases that are not yet deployed via Helm
  -C, --context int              output NUM lines of context around changes (default -1)
      --detailed-exitcode        return a non-zero exit code when there are changes
      --devel                    use development versions, too. Equivalent to version '>0.0.0-0'. If --version is set, this is ignored.
  -h, --help                     help for upgrade
      --home string              location of your Helm config. Overrides $HELM_HOME (default "/home/amoore/.helm")
      --namespace string         namespace to assume the release to be installed into (default "default")
      --reset-values             reset the values to the ones built into the chart and merge in any new values
      --reuse-values             reuse the last release's values and merge in any new values
      --set stringArray          set values on the command line (can specify multiple or separate values with commas: key1=val1,key2=val2)
      --set-file stringArray     set values from respective files specified via the command line (can specify multiple or separate values with commas: key1=path1,key2=path2)
      --set-string stringArray   set STRING values on the command line (can specify multiple or separate values with commas: key1=val1,key2=val2)
      --suppress stringArray     allows suppression of the values listed in the diff output
  -q, --suppress-secrets         suppress secrets in the output
      --tls                      enable TLS for request
      --tls-ca-cert string       path to TLS CA certificate file (default "$HELM_HOME/ca.pem")
      --tls-cert string          path to TLS certificate file (default "$HELM_HOME/cert.pem")
      --tls-key string           path to TLS key file (default "$HELM_HOME/key.pem")
      --tls-verify               enable TLS for request and verify remote
  -f, --values valueFiles        specify values in a YAML file (can specify multiple) (default overrides/values-<release-name>.yaml)
      --version string           specify the exact chart version to use. If this is not specified, the latest version is used

  --debug
EOF
}


while [ -n "${1}" ]; do
    case "${1}" in
        -f | --values)
            valueFiles+=( "${1}" )
            shift
            valueFiles+=( "${1}" )
            ;;
        --debug)
            debug=1
            ;;
        -h | --help)
            usage
            exit
            ;;
      --allow-unreleased | --detailed-exitcode | --reset-values | \
      --reuse-values | -q| --suppress-secrets| --tls | --tls-verify )
          FLAGS+=( "${1}" )
        ;;
        -*)
          FLAGS+=( "${1}" )
          shift
          FLAGS+=( "${1}" )
        ;;
        *)
          if [ -z "${_name}" ]; then
            _name="${1}"
          else
            _path="${1}"
          fi
        ;;
    esac
    shift
done

if [ "${debug}" -ne 0 ]; then
    set -x
fi

if [ -z "${_name}" ]; then
  echo "The release name must be specified"
  exit 1
fi
# Normalize the name by removeing '/' that are not allowed
_name=$(echo "${_name}" | sed "s:/::g")

if [ "${#valueFiles[@]}" -eq 0 ]; then
  valueFiles+=( -f overrides/values-"${_name}".yaml)
fi

if [ -z "${_path}" ]; then
  _path="${_name}"
fi

echo "running helm diff upgrade ${FLAGS[@]} ${_name} ${_path} ${valueFiles[@]}"
helm diff upgrade "${FLAGS[@]}" "${_name}" "${_path}" "${valueFiles[@]}"
