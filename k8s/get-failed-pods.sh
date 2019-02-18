kubectl get pod --field-selector 'status.phase==Failed' "$@"
