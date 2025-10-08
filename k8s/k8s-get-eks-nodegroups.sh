kubectl get node -o yaml | yq '.items[].metadata.labels["eks.amazonaws.com/nodegroup"]' -r | sort | uniq
