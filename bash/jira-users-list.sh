#!/bin/bash
# List all users in a Jira group.
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  TARGET="$(readlink "$SOURCE")"
  [[ "$TARGET" != /* ]] && TARGET="$(cd -P "$(dirname "$SOURCE")" && pwd)/$TARGET"
  SOURCE="$TARGET"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
export PIPENV_PIPFILE="${SCRIPT_DIR}/../Pipfile"
exec pipenv run python "${SCRIPT_DIR}/../python/jira_uses_list.py" "$@"
