# Bash Utilities

General-purpose bash scripts covering git, Docker, AWS, system diagnostics, and miscellaneous automation.

## Shell Dotfile Symlinks

Two library scripts are symlinked into `~/` as dotfiles and sourced by `~/.bashrc`:

```
~/.bash_functions -> bash/lib/bash_functions.sh   (PATH deduplication, pyenv management)
~/.bash_tricks    -> bash/lib/bash-tricks.sh      (aliases and shell shortcuts)
```

## ~/bin Symlinks

```
aws-docker-login      -> bash/aws-docker-login.sh
aws-ssm-find          -> bash/aws-ssm-find.sh
clone_match_path      -> bash/clone_match_path.sh
dockerfile-from-image -> bash/dockerfile-from-image.sh
for_each_dir          -> bash/for_each_dir.sh
git-base              -> bash/git-base.sh
git-bump              -> bash/git-bump.sh
x509-check            -> bash/x509-check.sh
```

## Scripts

### AWS

| Script | Description |
|--------|-------------|
| `aws-create-key-pair.sh` | Create AWS EC2 key pairs with color-coded output |
| `aws-docker-login.sh` | Authenticate Docker to AWS ECR registry |
| `aws-secretmanager-find.sh` | Search Secrets Manager for secrets by name/path with region/profile filtering |
| `aws-ssm-find.sh` | Search SSM Parameter Store for parameters by name/path |

### Git

| Script | Description |
|--------|-------------|
| `git-base.sh` | Print the root directory of a git repository |
| `git-bump.sh` | Increment semantic version tags and create new git tags |
| `git-change-author.sh` | Rewrite git history to change author email/username |
| `clone_match_path.sh` | Clone a git repo into a directory structure matching its URL path |

### Docker

| Script | Description |
|--------|-------------|
| `docker-clean-node.sh` | Clean up exited containers and dangling images with configurable expiration |
| `docker-remove-all-images.sh` | Remove all exited containers and unused Docker images |
| `dockerfile-from-image.sh` | Reconstruct a Dockerfile from an existing Docker image |
| `save-images.sh` | Save Docker images to tar files from a list |
| `save-load-docker-images.sh` | Selectively save/load Docker images with compression support |

### System / Diagnostics

| Script | Description |
|--------|-------------|
| `audit-logging.sh` | Configure bash audit logging via rsyslog and logrotate |
| `get-os-type.sh` | Detect and display OS type (darwin, linux, windows) |
| `sys_diag.sh` | Comprehensive system diagnostics (hardware, OS, environment) |
| `ssh-key-permissions.sh` | Set standard file permissions for SSH keys |
| `remote_stty_width.sh` | Set terminal width on serial connections |

### File / URL / Text

| Script | Description |
|--------|-------------|
| `branch-name.sh` | Convert text to lowercase hyphenated branch-name format |
| `find-links.sh` | Find symbolic links pointing to a specific file |
| `find-symlinks.sh` | Find all broken symbolic links in a directory |
| `for_each_dir.sh` | Execute a command in each subdirectory |
| `jq-grep.sh` | Wrapper around jq for searching JSON with debug output |
| `link-script-dir.sh` | Create symlinks to all executable scripts in a directory into ~/bin |
| `png2svg.sh` | Convert PNG images to SVG using ImageMagick and autotrace |
| `urlparse.sh` | URL character reference for parsing URL components |

### Certificates

| Script | Description |
|--------|-------------|
| `x509-check.sh` | Check certificate details and expiration for a host |
| `x509-check-all.sh` | Check certificates for multiple hosts |

### Build / Package

| Script | Description |
|--------|-------------|
| `build_lxml_wheel.sh` | Build Python lxml wheel with development dependencies |
| `check_depends.sh` | List apt package dependencies recursively |
| `combine-old-apt-list.sh` | Combine multiple apt sources.list files for distro upgrades |
| `header_script.sh` | Check Visual Studio project headers in vcxproj files |
| `replace-submodule-urls.sh` | Replace SSH git submodule URLs with HTTPS |

### Other

| Script | Description |
|--------|-------------|
| `bamboo-agent-sys5.sh` | SystemV init wrapper for Bamboo CI agent |
| `download-site.sh` | Download a website for offline viewing |
| `get-matching-nodes.sh` | Get matching nodes from a cluster |
| `import_all_terraform.sh` | Import all Terraform resources |
| `install_salt_builder.sh` | Install SaltStack minion configured for builder role |
| `locktables.sh` | MySQL table locking wrapper for backup snapshots |
| `mfa-example.sh` | AWS MFA authentication example |
| `qt_conf.sh` | Qt5 environment configuration for cross-compilation |
| `qt_conf_meta.sh` | Qt5.3.2 static build configuration |
| `rsync-incremental-backup-local.sh` | Incremental local backups using rsync |
| `run_cmake.sh` | CMake build runner |
| `trap_test.sh` | Example signal trapping (SIGINT/SIGTERM handling) |
| `ubuntu_package_check.sh` | Check Ubuntu package availability |

## Library Scripts — `lib/` (source, don't execute)

These live in `bash/lib/` and are meant to be sourced by other scripts, not run directly:

| Script | Description |
|--------|-------------|
| `lib/bash_functions.sh` | Utility functions: PATH deduplication, pyenv management |
| `lib/bash-tricks.sh` | Useful bash aliases and shell shortcuts |
| `lib/check-command-exists.sh` | Check if a command exists in PATH |
| `lib/colors-print-functions.sh` | ANSI color variables and terminal color detection |
| `lib/colors-print.sh` | Terminal color utilities with associative arrays |
| `lib/detect-being-sourced.sh` | Detect whether a script is being sourced or executed |
| `lib/docker-mock-functions.sh` | Mock Docker run function for testing |
| `lib/get_script_dir.sh` | Get absolute path of the script's directory |
| `lib/logging.sh` | Color-coded logging with formatting functions |
| `lib/metadata.sh` | Image metadata display using exiftool |

## Subdirectories

| Directory | Contents |
|-----------|----------|
| `lib/` | Shell libraries meant to be sourced (see table above) |
| `automation/` | Build automation (`cmake_clone_build.sh`), MySQL load testing (`mysql_slap/`) |
| `display/` | Display configuration (`vga_add`) |
| `packaging/` | iOS app re-signing (`ios_resign.sh`), Redis packaging (`redis_make_package.sh`) |
