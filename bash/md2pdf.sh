#!/bin/bash
# Convert Markdown to styled PDF using ReportLab
# Usage: md2pdf INPUT.md [-o OUTPUT.pdf]
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  SOURCE="$(cd -P "$(dirname "$SOURCE")" && pwd)/$(readlink "$SOURCE")"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
export PIPENV_PIPFILE="${SCRIPT_DIR}/../Pipfile"
exec pipenv run python "${SCRIPT_DIR}/../python/md_to_pdf.py" "$@"
