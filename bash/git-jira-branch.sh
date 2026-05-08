#!/bin/bash
# Create a git branch name from a Jira issue key and summary.
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  TARGET="$(readlink "$SOURCE")"
  [[ "$TARGET" != /* ]] && TARGET="$(cd -P "$(dirname "$SOURCE")" && pwd)/$TARGET"
  SOURCE="$TARGET"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
export PIPENV_PIPFILE="${SCRIPT_DIR}/../Pipfile"
exec pipenv run python "${SCRIPT_DIR}/../python/git_jira_branch.py" "$@"
