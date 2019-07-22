set -x
kubectl get node  -o=custom-columns=NAME:.metadata.name,TAINT:.spec.taints
