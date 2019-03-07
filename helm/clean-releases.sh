#!/usr/bin/env bash

set -euo pipefail

main() {
  local kinds=( Service Deployment Pod Secret ConfigMap )
  local counter=0 attempts=30

  for release in "$@"; do
    echo "--> Deleting release ${release}"

    if helm ls --kube-context "${KUBE_CONTEXT}" | grep -qF "${release}"; then
      echo "==> Found helm release; deleting with --purge"
      helm delete "${release}" --purge  --kube-context "${KUBE_CONTEXT}"
    else
      echo "==> No release found; deleting manually"

      for kind in "${kinds[@]}"; do
        echo "==> Deleting any dangling ${kind}"

        kubectl delete "${kind}" \
          -l "release=${release}" \
          -n "${KUBE_NAMESPACE}" \
          --force \
          --grace-period 0 \
          --context "${KUBE_CONTEXT}" 2>/dev/null
      done
    fi

    echo "--> Awaiting resource deleting confirmation"
    for kind in "${kinds[@]}"; do
      counter=0

      while [ $counter -lt $attempts ]; do
        pending_resources="$(kubectl get "${kind}" \
          -o wide \
          -l "release=${release}" \
          -n "${KUBE_NAMESPACE}" \
          --context "${KUBE_CONTEXT}" 2>/dev/null
        )"

        if [ -n "${pending_resources}" ]; then
          echo "${release} ${kind} still running. ${counter}/${attempts} tests completed; retrying."
          echo "${pending_resources}" 1>&2
          echo 1>&2

          # NOTE: The pre-increment usage. This makes the arithmatic expression
          # always exit 0. The post-increment form exits non-zero when counter
          # is zero. More information here: http://wiki.bash-hackers.org/syntax/arith_expr#arithmetic_expressions_and_return_codes
          ((++counter))
          sleep 10
        else
          break
        fi
      done

      if [ $counter -eq $attempts ]; then
        echo "${release} ${kind} failed to delete in time.";
        return 1
      fi
    done

    echo "--> Awaiting helm confirmation"
    counter=0

    while [ $counter -lt $attempts ]; do
      if helm ls --all --kube-context "${KUBE_CONTEXT}" | grep -qF "${release}"; then
        echo "${release} still in tiller. ${counter}/${attempts} checks completed; retrying."

        # NOTE: The pre-increment usage. This makes the arithmatic expression
        # always exit 0. The post-increment form exits non-zero when counter
        # is zero. More information here: http://wiki.bash-hackers.org/syntax/arith_expr#arithmetic_expressions_and_return_codes
        ((++counter))
        sleep 10
      else
        break
      fi
    done

    if [ $counter -eq $attempts ]; then
      echo "${release} failed to purge from tiller delete in time.";
      return 1
    fi
  done
}

main "$@"
