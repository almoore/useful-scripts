#!/bin/bash
# Convert Markdown to a Confluence page
# Usage: md2confluence INPUT.md --space ERD [--parent-id ID] [--title "Title"]
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  TARGET="$(readlink "$SOURCE")"
  [[ "$TARGET" != /* ]] && TARGET="$(cd -P "$(dirname "$SOURCE")" && pwd)/$TARGET"
  SOURCE="$TARGET"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
export PIPENV_PIPFILE="${SCRIPT_DIR}/../Pipfile"
exec pipenv run python "${SCRIPT_DIR}/../python/md_to_confluence.py" "$@"
