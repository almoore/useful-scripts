APP=${1:?MUST SUPPLY APP NAME}
kubectl get statefulset -l app=$APP -o go-template --template='{{range .items}}{{.status.replicas}}/{{.spec.replicas}}{{printf "\n"}}{{end}}'
