#!/usr/bin/env bash
# Print the unique EKS nodegroup names seen across all nodes in the current
# cluster (reads the eks.amazonaws.com/nodegroup label).
kubectl get node -o yaml | yq '.items[].metadata.labels["eks.amazonaws.com/nodegroup"]' -r | sort | uniq
