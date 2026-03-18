# GCP Utilities

Scripts for Google Cloud Platform operations — GPU availability queries and GCS object management.

## Scripts

| Script | Description |
|--------|-------------|
| `gcp-get-gpu-availability.py` | Query Compute Engine for GPU availability across regions and zones |
| `gcp_switch.sh` | Switch between local GCP configurations with bash completion |
| `update-objects.sh` | Re-encrypt GCS objects with new KMS encryption keys |
| `update-objects-async.sh` | Async version — re-encrypt GCS objects with new KMS keys using semaphore locking |

## Prerequisites

- `gcloud` CLI configured with appropriate projects
- Python 3 with `google-api-python-client` for `gcp-get-gpu-availability.py`
