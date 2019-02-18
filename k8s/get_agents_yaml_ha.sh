#!/bin/bash
# Usage: ./get_agents_yaml_ha.sh cluster_name
# Needs to have KUBECONFIG environment variable set or ~/.kube/config pointing to the RKE Rancher cluster

# Check if jq exists
command -v jq >/dev/null 2>&1 || { echo "jq is not installed. Exiting." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is not installed. Exiting." >&2; exit 1; }

# Check if clustername is given
if [ -z "$1" ]; then
    echo "Usage: $0 [clustername]"
    exit 1
fi

case "$OSTYPE" in
  darwin*)  MD5=md5; SHA256SUM="shasum -a 256" ;;
  linux*)   MD5=md5sum; SHA256SUM=sha256sum ;;
  *)        echo "unsupported: $OSTYPE"; exit 1 ;;
esac

# Provide clustername as first argument
CLUSTERNAME=$1

# Validate that we are querying the correct etcd
if kubectl get cluster > /dev/null; then
  echo "'kubectl get cluster' returns clusters available"
else
  echo "'kubectl get cluster' returns error, this should be run using a kubeconfig pointing to the RKE cluster running Rancher"
  exit 1
fi

# Get clusters
CLUSTERINFO=$(kubectl get cluster --no-headers --output=custom-columns=Name:.spec.displayName,Driver:.status.driver,ClusterID:.metadata.name)

echo "Clusters found:"
echo "${CLUSTERINFO}"

# Get clusterid from clustername
CLUSTERID=$(echo "${CLUSTERINFO}" | awk -v CLUSTERNAME=$CLUSTERNAME '$1==CLUSTERNAME { print $3 }')

if [[ -z $CLUSTERID ]]; then
  echo "No CLUSTERID could be retrieved for $CLUSTERNAME, make sure you entered the correct clustername"
  exit 1
fi

# Get all needed settings
CACERTS=$(kubectl get setting cacerts -o json | jq -r .value)
if [ "x${CACERTS}" == "x" ]; then
  CACHECKSUM=""
else
  CACHECKSUM=$(echo "$CACERTS" | $SHA256SUM  | awk '{ print $1 }')
fi
SERVERURL=$(kubectl get setting server-url -o json | jq -r .value)
AGENTIMAGE=$(kubectl get settings agent-image -o json | jq -r .value)
TOKEN=$(kubectl get clusterregistrationtoken system -n $CLUSTERID -o json | jq -r .status.token)

# Getting correct values
B64TOKEN=$(echo -n $TOKEN | base64)
B64URL=$(echo -n $SERVERURL | base64)
TOKENKEY=$(echo -n $TOKEN | $MD5 | cut -c1-7)

#echo $B64TOKEN
#echo $B64URL
#echo $TOKENKEY

cat >./rancher-agents-$CLUSTERNAME.yml <<EOL
---
apiVersion: v1
kind: Namespace
metadata:
  name: cattle-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cattle
  namespace: cattle-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: cattle-admin-binding
  namespace: cattle-system
  labels:
    cattle.io/creator: "norman"
subjects:
- kind: ServiceAccount
  name: cattle
  namespace: cattle-system
roleRef:
  kind: ClusterRole
  name: cattle-admin
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: v1
kind: Secret
metadata:
  name: cattle-credentials-${TOKENKEY}
  namespace: cattle-system
type: Opaque
data:
  url: "${B64URL}"
  token: "${B64TOKEN}"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cattle-admin
  labels:
    cattle.io/creator: "norman"
rules:
- apiGroups:
  - '*'
  resources:
  - '*'
  verbs:
  - '*'
- nonResourceURLs:
  - '*'
  verbs:
  - '*'
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: cattle-cluster-agent
  namespace: cattle-system
spec:
  selector:
    matchLabels:
      app: cattle-cluster-agent
  template:
    metadata:
      labels:
        app: cattle-cluster-agent
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                - key: beta.kubernetes.io/os
                  operator: NotIn
                  values:
                    - windows
      serviceAccountName: cattle
      containers:
        - name: cluster-register
          imagePullPolicy: IfNotPresent
          env:
          - name: CATTLE_SERVER
            value: "${SERVERURL}"
          - name: CATTLE_CA_CHECKSUM
            value: "${CACHECKSUM}"
          - name: CATTLE_CLUSTER
            value: "true"
          - name: CATTLE_K8S_MANAGED
            value: "true"
          image: ${AGENTIMAGE}
          volumeMounts:
          - name: cattle-credentials
            mountPath: /cattle-credentials
            readOnly: true
      volumes:
      - name: cattle-credentials
        secret:
          secretName: cattle-credentials-${TOKENKEY}
---
apiVersion: extensions/v1beta1
kind: DaemonSet
metadata:
    name: cattle-node-agent
    namespace: cattle-system
spec:
  selector:
    matchLabels:
      app: cattle-agent
  template:
    metadata:
      labels:
        app: cattle-agent
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                - key: beta.kubernetes.io/os
                  operator: NotIn
                  values:
                    - windows
      hostNetwork: true
      serviceAccountName: cattle
      tolerations:
      - effect: NoExecute
        key: "node-role.kubernetes.io/etcd"
        value: "true"
      - effect: NoSchedule
        key: "node-role.kubernetes.io/controlplane"
        value: "true"
      containers:
      - name: agent
        image: ${AGENTIMAGE}
        imagePullPolicy: IfNotPresent
        env:
        - name: CATTLE_NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: CATTLE_SERVER
          value: "${SERVERURL}"
        - name: CATTLE_CA_CHECKSUM
          value: "${CACHECKSUM}"
        - name: CATTLE_CLUSTER
          value: "false"
        - name: CATTLE_K8S_MANAGED
          value: "true"
        - name: CATTLE_AGENT_CONNECT
          value: "true"
        volumeMounts:
        - name: cattle-credentials
          mountPath: /cattle-credentials
          readOnly: true
        - name: k8s-ssl
          mountPath: /etc/kubernetes
        - name: var-run
          mountPath: /var/run
        - name: run
          mountPath: /run
        securityContext:
          privileged: true
      volumes:
      - name: k8s-ssl
        hostPath:
          path: /etc/kubernetes
          type: DirectoryOrCreate
      - name: var-run
        hostPath:
          path: /var/run
          type: DirectoryOrCreate
      - name: run
        hostPath:
          path: /run
          type: DirectoryOrCreate
      - name: cattle-credentials
        secret:
          secretName: cattle-credentials-${TOKENKEY}
  updateStrategy:
    type: RollingUpdate
EOL

echo "You can now configure kubeconfig to your created/managed cluster and run kubectl apply -f rancher-agents-${CLUSTERNAME}.yml to restore cluster/node agents"