#!/usr/bin/env bash
# Print the container image of every container in every pod across all
# namespaces (space-separated) using a go-template.
kubectl get pods --all-namespaces -o go-template --template="{{range .items}}{{range .spec.containers}}{{.image}} {{end}}{{end}}"
