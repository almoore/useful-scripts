# Python Utilities

Python scripts for Jira integration, Facebook data export, Terraform helpers, YouTube downloading, data conversion, and more.

## ~/bin Symlinks

```
bs              -> python/bs.py
bs-pass         -> python/bs-pass.py
export-dotenv   -> python/export_dotenv.py
git-jira-branch -> python/git_jira_branch.py
```

## Shared Modules (libraries, not CLI tools)

| Module | Description | Used By |
|--------|-------------|---------|
| `jira_auth.py` | Jira authentication via config file + keyring + interactive prompts | `git_jira_branch.py`, `jira_reassign_children.py`, `jira_tools.py`, `jira_uses_list.py` |
| `facebook_auth.py` | Facebook OAuth 2.0 with browser flow and token persistence | Facebook scripts |
| `atlassian_auth.py` | Atlassian authentication via config file and keyring | `cab-add.py`, `cab-read.py`, `atlantis-review.py` |
| `run_command.py` | Subprocess wrapper with real-time output streaming | Various |
| `date_compare.py` | Date parsing and timezone conversion utilities | Various |
| `history.py` | Readline command history read/save | Various |
| `add_fileserver_root.py` | Salt configuration module for fileserver roots | Salt integration |

## Scripts

### Jira

| Script | Description |
|--------|-------------|
| `git_jira_branch.py` | Create git branch names from Jira issue key and summary |
| `jira_reassign_children.py` | Reassign child issues from a Jira parent/epic with filtering |
| `jira_tools.py` | Jira group management — list and sync group members |
| `jira_uses_list.py` | List all users in a Jira group with pagination |

### Facebook

| Script | Description | Docs |
|--------|-------------|------|
| `facebook_profile_csv.py` | Fetch user timeline posts and export to CSV with pagination | [docs](facebook_profile_csv.md) |
| `facebook_download_photos.py` | Download photos from Facebook posts via Graph API | |
| `facebook_photo_to_wordpress.py` | Convert Facebook photos to WordPress posts | [docs](facebook_photo_to_wordpress.md) |
| `facebook_user_id.py` | Get Facebook user ID by username from Graph API | |
| `facebook_json_export_to_pdf.py` | Convert Facebook JSON export to PDF books with date filtering | |
| `check_facebook_rate_limit.py` | Check Facebook Graph API rate limit status | |

### Terraform

| Script | Description |
|--------|-------------|
| `atlantis-review.py` | Review Atlantis plan output from GitHub PR with resource summaries |
| `tfe-review.py` | Review Terraform Cloud/Enterprise run plans with change summaries |
| `tfe_stream_logs.py` | Stream TFC/TFE run logs with multiple format options |
| `terraform_import_route53.py` | Generate terraform import commands for Route53 records |
| `terraform_extract_targets.py` | Extract Terraform resource names and generate `-target` arguments |

### Atlassian / Confluence

| Script | Description |
|--------|-------------|
| `cab-add.py` | Add rows to weekly Confluence CAB (Change Advisory Board) review page |
| `cab-read.py` | Read and display weekly Confluence CAB review page |

### YouTube

| Script | Description |
|--------|-------------|
| `download-youtube-audio.py` | Download YouTube videos as MP3 audio with configurable bitrate |
| `download-youtube-video.py` | Download YouTube videos in highest available resolution |

### Google

| Script | Description | Docs |
|--------|-------------|------|
| `google_docs_to_csv.py` | Fetch Google Docs from Drive folder and convert tables to CSV/JSON | [docs](google_docs_to_csv.md) |
| `google_docs_to_pdf.py` | Convert Google Docs to PDF with images and formatting | |
| `create_gdoc.py` | Create Google Docs programmatically with formatted content | |
| `gdrive_download_and_embed_image.py` | Download images from Google Drive and embed in documents | |

### WordPress

| Script | Description |
|--------|-------------|
| `wordpress_media_upload.py` | Upload images to WordPress.com via REST API |
| `wordpress_flask_app.py` | Flask OAuth app for WordPress.com authorization |

### Data Conversion

| Script | Description |
|--------|-------------|
| `y2j.py` | YAML to JSON converter with query support |
| `export_dotenv.py` | Export `.env` file variables as shell export statements |
| `remove-colors.py` | Strip ANSI color codes from log files |
| `serialize_fix.py` | Fix PHP serialized string length encoding |

### Docker / Registry

| Script | Description |
|--------|-------------|
| `get_all_docker_images.py` | List all Docker images from a registry with pagination |

### Fun

| Script | Description |
|--------|-------------|
| `bs.py` | Corporate bullshit generator — random management-speak sentences |
| `bs-pass.py` | Corporate bullshit generator — meaningless buzzword passwords |

### Other

| Script | Description |
|--------|-------------|
| `check_compression.py` | Detect file compression type (gzip, bzip2, zip) using magic bytes |
| `get-auth0-users.py` | Query Auth0 for users and filter by account age |
| `list-all-github-repos.py` | List clone URLs for all repos in a GitHub org or user account |
| `mvrepo.py` | Move git repositories to organized directory structure with symlinking |
| `path_check.py` | Display Python sys.path and environment information |
| `requests_ex.py` | Example of downloading binary files via requests |
| `ve-pip-call.py` | Find and use wheels from virtualenv to bootstrap installations |
| `wheel-dist.py` | Distutils configuration for non-pure wheel distributions |

## Subdirectories

| Directory | Description |
|-----------|-------------|
| `color_util/` | Color utility modules |
| `ws/` | Working scratch space (gitignored) |

## Prerequisites

- Python 3.13+ (see `Pipfile` at repo root)
- Core deps: `pipenv install` at repo root
- Jira scripts: `pip install jira atlassian-python-api keyring`
- YouTube scripts: `yt-dlp` and `ffmpeg`
- Facebook scripts: `FACEBOOK_ACCESS_TOKEN` env var or OAuth via `facebook_auth.py`
