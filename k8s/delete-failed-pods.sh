kubectl get pod --field-selector 'status.phase==Failed' -o json "$@" | kubectl delete -f -
