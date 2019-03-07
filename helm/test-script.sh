#!/usr/bin/env bash

set -euo pipefail

main() {
  local release="${1:-}" test_output
  test_output="$(mktemp)"

  if [ -z "${release}" ]; then
    echo "USAGE: ${0} RELEASE" 1>&2
    return 1
  fi

  kubectl delete pod \
    -l "release=${release},app=smoke-test" \
    -n "${KUBE_NAMESPACE}" \
    --context "${KUBE_CONTEXT}" &> /dev/null

  # FIXME: This is a work around for https://github.com/kubernetes/helm/issues/2166
  set +e
  helm test "${release}" --timeout 600 --kube-context "${KUBE_CONTEXT}" > "${test_output}"
  set -e

  if grep -qF 'PASSED' "${test_output}"; then
    cat "${test_output}"

    kubectl delete pod \
      -l "release=${release},app=smoke-test" \
      -n "${KUBE_NAMESPACE}" \
      --context "${KUBE_CONTEXT}" &> /dev/null

    return 0
  else
    echo "${release} test failed! Capturing logs and cleaning up"
    echo
    cat "${test_output}"

    while read -r pod; do
      echo "${pod} Logs:"
      echo
      kubectl logs "${pod}" -n "${KUBE_NAMESPACE}" --context "${KUBE_CONTEXT}"
      kubectl delete pod "${pod}" -n "${KUBE_NAMESPACE}" --context "${KUBE_CONTEXT}"
      echo
    done < <(kubectl get pod \
      --show-all \
      -o "custom-columns=NAME:.metadata.name" \
      -l "release=${release},app=smoke-test" \
      -n "${KUBE_NAMESPACE}" \
      --context "${KUBE_CONTEXT}" \
      | tail -n +2)

    return 1
  fi
}

main "$@"
