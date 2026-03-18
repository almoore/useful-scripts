# Helm Utilities

Scripts for Helm chart management — release upgrades, diffs, testing, and value extraction.

## ~/bin Symlinks

```
hrs-values.py -> helm/hrs-values.py
```

## Scripts

| Script | Description |
|--------|-------------|
| `up.sh` | Helm upgrade/install release with diff, dry-run, and values management |
| `diff-up.sh` | Show helm diff before upgrading a release with context and dry-run options |
| `await-release.sh` | Wait for a Helm release to be fully deployed and healthy |
| `clean-releases.sh` | Delete Helm releases and associated Kubernetes resources |
| `test-script.sh` | Run helm test on a release and clean up test pods |
| `loop.sh` | Repeatedly run a test script and track success/failure counts |
| `hrs-values.py` | Extract and dump `spec.values` from a Helm Release resource YAML |
| `decode-configmap-data.py` | Decode and extract data from base64-encoded Helm ConfigMap releases |

## Prerequisites

- `helm` (v3) and `kubectl` configured
- `helm-diff` plugin for `diff-up.sh`
- Python 3 with `pyyaml` for Python scripts
