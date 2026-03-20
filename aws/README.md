# AWS Utilities

Scripts for AWS IAM management, RDS queries, and authentication helpers.

## Scripts

| Script | Description |
|--------|-------------|
| `download-policies.sh` | Download all IAM policies for the current AWS account to local directory structure |
| `download-roles.sh` | Download all IAM roles and their associated inline policies to local files |
| `assume-web-identity.sh` | Assume an AWS role using OIDC web identity tokens and export temporary credentials |
| `update-ssh-userdata.sh` | Cloud-init MIME multipart userdata template with SSH key provisioning for EC2 |
| `get-rds-versions.py` | List default PostgreSQL engine versions for each major version from AWS RDS |
| `get-rds-running-db-versions.py` | Query RDS for running database instances and their versions (table/JSON output) |
| `find_r6_instances.py` | Find r6-class instance types in Terraform files and suggest r7 equivalents |
| `rds-maintenance-report.py` | Generate RDS Aurora maintenance reports with pending actions; publish to Confluence |

## ~/bin Symlinks

```
aws-download-policies -> aws/download-policies.sh
aws-download-roles    -> aws/download-roles.sh
```

## Prerequisites

- AWS CLI configured with appropriate profiles
- Python 3 with `boto3` for Python scripts
- `rds-maintenance-report.py` additionally requires `atlassian-python-api` and `keyring`
