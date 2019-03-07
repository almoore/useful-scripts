#!/usr/bin/env bash

set -euo pipefail

main() {
  local success=0 failure=0

  while true; do
    echo "=> Attemping"
    echo

    if script/ci/test; then
      ((++success))
    else
      ((++failure))
    fi

    echo
    echo "=> Results: failure=${failure} success=${success}"
  done
}

main "$@"
