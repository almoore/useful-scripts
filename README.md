# useful-scripts

A collection of standalone utility scripts for DevOps workflows covering AWS, GCP, Kubernetes, Helm, Jira, and general automation. Scripts are self-contained and designed to run independently with standard CLI tools.

## Directory Structure

| Directory | Scripts | Description |
|-----------|---------|-------------|
| [aws/](aws/) | 8 | AWS utilities — IAM policy/role downloads, RDS queries, authentication |
| [bash/](bash/) | 67 | General bash utilities — git helpers, Docker tools, system diagnostics |
| [gcp/](gcp/) | 4 | Google Cloud Platform — GPU availability, GCS KMS re-encryption |
| [helm/](helm/) | 9 | Helm chart management — release upgrades, diffs, value extraction |
| [k8s/](k8s/) | 32 | Kubernetes utilities — secrets, events, pod management, backups |
| [python/](python/) | 50 | Python tools — Jira, Facebook, Terraform, YouTube, data conversion |
| [api-scripts/](api-scripts/) | 39 | Legacy API integrations — Stash, Salt, Jenkins, Bamboo |
| [expect/](expect/) | 2 | Expect-based SSH and MySQL automation |
| [images/](images/) | 3 | ImageMagick image processing — watermarks, effects |
| [archive/](archive/) | 1 | Legacy/outdated scripts kept for reference |

## Installation

Most scripts can be run directly. To set up all `~/bin` and shell dotfile symlinks on a new machine:

```bash
git clone https://github.com/almoore/useful-scripts.git
cd useful-scripts

# Preview what will be created
./setup-symlinks.sh check

# Create all symlinks
./setup-symlinks.sh install

# Or override the repo path if cloned elsewhere
./setup-symlinks.sh install -r /path/to/useful-scripts
```

See `./setup-symlinks.sh --help` for all options (`check`, `install`, `remove`, `list`).

### Python Dependencies

```bash
# Core dependencies (Pipfile)
pipenv install

# Jira scripts (not in Pipfile)
pip install jira atlassian-python-api keyring

# Legacy api-scripts
pip install -r api-scripts/requirements.txt
```

### External CLI Tools

Scripts assume these are available as needed: `kubectl`, `helm`, `aws`, `gcloud`, `jq`, `yq`, `exiftool`, `imagemagick`

## Shell Dotfile Symlinks

These files are symlinked into `~/` and sourced by `~/.bashrc`:

| Dotfile | Script | Description |
|---------|--------|-------------|
| `~/.bash_functions` | [bash/lib/bash_functions.sh](bash/lib/bash_functions.sh) | Utility functions: PATH deduplication, pyenv management |
| `~/.bash_tricks` | [bash/lib/bash-tricks.sh](bash/lib/bash-tricks.sh) | Useful bash aliases and shell shortcuts |

```bash
# In ~/.bashrc:
if [ -f ~/.bash_functions ]; then . ~/.bash_functions; fi
if [ -f ~/.bash_tricks ]; then . ~/.bash_tricks; fi
```

## ~/bin Symlinks

These scripts are symlinked from `~/bin` for direct command-line use. The symlinks point through `~/repos/me/useful-scripts/` (which is this same repo at an alternate path).

### AWS

| Command | Script |
|---------|--------|
| `aws-docker-login` | [bash/aws-docker-login.sh](bash/aws-docker-login.sh) |
| `aws-download-policies` | [aws/download-policies.sh](aws/download-policies.sh) |
| `aws-download-roles` | [aws/download-roles.sh](aws/download-roles.sh) |
| `aws-ssm-find` | [bash/aws-ssm-find.sh](bash/aws-ssm-find.sh) |

### Git

| Command | Script |
|---------|--------|
| `git-base` | [bash/git-base.sh](bash/git-base.sh) |
| `git-bump` | [bash/git-bump.sh](bash/git-bump.sh) |
| `git-jira-branch` | [python/git_jira_branch.py](python/git_jira_branch.py) |

### Kubernetes

| Command | Script |
|---------|--------|
| `k8s-check-certs` | [k8s/check-certs.sh](k8s/check-certs.sh) |
| `k8s-decode-certs` | [k8s/decode-certs.sh](k8s/decode-certs.sh) |
| `k8s-decode-secrets` | [k8s/decode-secret.py](k8s/decode-secret.py) |
| `k8s-delete-failed-pods` | [k8s/delete-failed-pods.sh](k8s/delete-failed-pods.sh) |
| `k8s-delete-pods-older-than-1-day` | [k8s/delete-pods-older-than-1-day.sh](k8s/delete-pods-older-than-1-day.sh) |
| `k8s-filter` | [k8s/k8s_filter.py](k8s/k8s_filter.py) |
| `k8s-filter-all-files` | [k8s/filter-all-files.sh](k8s/filter-all-files.sh) |
| `k8s-get-agents-yaml-ha` | [k8s/get_agents_yaml_ha.sh](k8s/get_agents_yaml_ha.sh) |
| `k8s-get-events-since` | [k8s/get-events-since.sh](k8s/get-events-since.sh) |
| `k8s-get-failed-pods` | [k8s/get-failed-pods.sh](k8s/get-failed-pods.sh) |
| `k8s-get-latest-events` | [k8s/get-latest-events.sh](k8s/get-latest-events.sh) |
| `k8s-get-not-running-pods` | [k8s/get-not-running-pods.sh](k8s/get-not-running-pods.sh) |
| `k8s-get-pod-by-node` | [k8s/get-pod-by-node.sh](k8s/get-pod-by-node.sh) |
| `k8s-get-release-pods` | [k8s/get-release-pods.sh](k8s/get-release-pods.sh) |
| `k8s-get-snapshot` | [k8s/get-snapshot.sh](k8s/get-snapshot.sh) |
| `k8s-get-taints` | [k8s/get-taints.sh](k8s/get-taints.sh) |
| `k8s-kill-kube-ns` | [k8s/kill-kube-ns.sh](k8s/kill-kube-ns.sh) |
| `k8s-list-containers-go-template` | [k8s/list-containers-go-template.sh](k8s/list-containers-go-template.sh) |
| `k8s-list-statefulset-state-go-template` | [k8s/list-statefulset-state-go-template.sh](k8s/list-statefulset-state-go-template.sh) |
| `k8s-nsenter` | [k8s/nsenter.sh](k8s/nsenter.sh) |
| `k8s-setup-aws-kubeconfig` | [k8s/setup-aws-kubeconfig.sh](k8s/setup-aws-kubeconfig.sh) |
| `k8s-split-resources` | [k8s/split-resources.py](k8s/split-resources.py) |

### Helm

| Command | Script |
|---------|--------|
| `hrs-values.py` | [helm/hrs-values.py](helm/hrs-values.py) |

### Python Utilities

| Command | Script |
|---------|--------|
| `bs` | [python/bs.py](python/bs.py) |
| `bs-pass` | [python/bs-pass.py](python/bs-pass.py) |
| `export-dotenv` | [python/export_dotenv.py](python/export_dotenv.py) |

### Other

| Command | Script |
|---------|--------|
| `clone_match_path` | [bash/clone_match_path.sh](bash/clone_match_path.sh) |
| `dockerfile-from-image` | [bash/dockerfile-from-image.sh](bash/dockerfile-from-image.sh) |
| `for_each_dir` | [bash/for_each_dir.sh](bash/for_each_dir.sh) |
| `x509-check` | [bash/x509-check.sh](bash/x509-check.sh) |
| `add_kustomization_to_current` | [k8s/add_kustomization_to_current.sh](k8s/add_kustomization_to_current.sh) |
| `add_kustomization_to_subdirs` | [k8s/add_kustomization_to_subdirs.sh](k8s/add_kustomization_to_subdirs.sh) |

## Conventions

- **Bash scripts**: `#!/usr/bin/env bash`, `set -e` or `set -euo pipefail`, 2-space indentation
- **Python scripts**: `#!/usr/bin/env python3`, argparse for CLI args, 4-space indentation, 80-char lines
- **Formatting**: Enforced via [.editorconfig](.editorconfig) — LF line endings, UTF-8, trailing whitespace trimmed
- **Credentials**: Managed via `keyring` and config files (e.g., `~/.atlassian-conf.json`), never hardcoded

## Notes

- `ws/` and `tmp/` directories are gitignored working/scratch space
- `.env*` files are gitignored
- Some Python scripts have companion `.md` docs in `python/`
- The `posts_to_pdf` library was extracted to its own repo: [almoore/storybound](https://github.com/almoore/storybound)
