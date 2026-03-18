# Kubernetes Utilities

Scripts for Kubernetes cluster management — secret decoding, event filtering, pod management, resource backup, and certificate inspection.

## ~/bin Symlinks

The largest set of symlinks — most scripts are available as `k8s-*` commands:

```
k8s-check-certs                        -> k8s/check-certs
k8s-decode-certs                       -> k8s/decode-certs.sh
k8s-decode-secrets                     -> k8s/decode-secret.py
k8s-delete-failed-pods                 -> k8s/delete-failed-pods.sh
k8s-delete-pods-older-than-1-day       -> k8s/delete-pods-older-than-1-day
k8s-filter                             -> k8s/k8s_filter.py
k8s-filter-all-files                   -> k8s/filter-all-files.sh
k8s-get-agents-yaml-ha                 -> k8s/get_agents_yaml_ha.sh
k8s-get-events-since                   -> k8s/get-events-since.sh
k8s-get-failed-pods                    -> k8s/get-failed-pods.sh
k8s-get-latest-events                  -> k8s/get-latest-events.sh
k8s-get-not-running-pods               -> k8s/get-not-running-pods.sh
k8s-get-pod-by-node                    -> k8s/get-pod-by-node.sh
k8s-get-release-pods                   -> k8s/get-release-pods.sh
k8s-get-snapshot                       -> k8s/get-snapshot.sh
k8s-get-taints                         -> k8s/get-taints.sh
k8s-kill-kube-ns                       -> k8s/kill-kube-ns.sh
k8s-list-containers-go-template        -> k8s/list-containers-go-template.sh
k8s-list-statefulset-state-go-template -> k8s/list-statefulset-state-go-template.sh
k8s-nsenter                            -> k8s/nsenter
k8s-setup-aws-kubeconfig               -> k8s/setup-aws-kubeconfig.sh
k8s-split-resources                    -> k8s/split-resources.py
add_kustomization_to_current           -> k8s/add_kustomization_to_current
add_kustomization_to_subdirs           -> k8s/add_kustomization_to_subdirs
```

## Scripts

### Secrets & Certificates

| Script | Description |
|--------|-------------|
| `decode-secret.py` | Decode base64-encoded Kubernetes secret values to readable output |
| `decode-certs.sh` | Decode and display certificate details from Kubernetes secrets |
| `check-certs` | Verify certificate expiration dates |
| `extract-helm-secret.py` | Extract and decompress Helm release data from Kubernetes secrets |

### Pod Management

| Script | Description |
|--------|-------------|
| `get-failed-pods.sh` | List pods in Failed status |
| `get-not-running-pods.sh` | List pods not in Running status |
| `get-release-pods.sh` | List all pods for a Helm release by release name |
| `get-pod-by-node.sh` | List pods with their node assignments |
| `delete-failed-pods.sh` | Delete pods in Failed status |
| `delete-pods-older-than-1-day` | Delete pods older than 1 day |
| `nsenter` | Enter the namespace of a running container for debugging |

### Events & Monitoring

| Script | Description |
|--------|-------------|
| `get-events-since.sh` | Get events since a specified time with namespace/selector filtering |
| `get-latest-events.sh` | Get latest events sorted by timestamp |

### Cluster Info

| Script | Description |
|--------|-------------|
| `get-taints.sh` | Display taints on Kubernetes nodes |
| `get-snapshot.sh` | Collect comprehensive snapshot of cluster resources and state |
| `list-containers-go-template.sh` | List all containers across pods using go template |
| `list-statefulset-state-go-template.sh` | Display StatefulSet pod state using go template |
| `k8s-get-eks-nodegroups.sh` | List EKS node groups and their instances |
| `get_agents_yaml_ha.sh` | Generate HA agent YAML for Rancher RKE clusters |

### Resource Filtering & Splitting

| Script | Description |
|--------|-------------|
| `k8s_filter.py` | Filter Kubernetes YAML to remove metadata preventing clean restore |
| `filter-all-files.sh` | Filter all YAML files in a directory to remove Kubernetes metadata |
| `split-resources.py` | Split multi-document YAML into directory structure by kind/namespace |
| `split-custom-resources.py` | Split multi-document YAML with custom resources into directories |
| `split_docs.py` | Load and split YAML documents into separate files by kind/name |

### Backup & Restore

| Script | Description |
|--------|-------------|
| `kube_backup.py` | Backup Kubernetes resources by namespace and kind with filtering |
| `correlate_backup_objects.sh` | Correlate backup objects with live Kubernetes resources |

### Setup

| Script | Description |
|--------|-------------|
| `setup-aws-kubeconfig.sh` | Configure kubeconfig for AWS EKS cluster access |
| `add_kustomization_to_current` | Add `kustomization.yaml` to current directory |
| `add_kustomization_to_subdirs` | Add `kustomization.yaml` to all subdirectories |
| `kill-kube-ns.sh` | Forcefully terminate all resources in a Kubernetes namespace |

### Helm Integration

| Script | Description |
|--------|-------------|
| `helm-diff-update.py` | Show helm diff before updating releases with color-coded output |

## Prerequisites

- `kubectl` configured with appropriate contexts
- `jq` and `yq` for JSON/YAML processing
- Python 3 with `pyyaml` for Python scripts
