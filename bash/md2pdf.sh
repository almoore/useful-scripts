#!/bin/bash
# Convert Markdown to styled PDF using ReportLab
# Usage: md2pdf INPUT.md [-o OUTPUT.pdf]
SCRIPT_DIR=$(cd $(dirname $(realpath ${BASH_SOURCE[0]})); echo $PWD)
export PIPENV_PIPFILE="${SCRIPT_DIR}/../Pipfile"
exec pipenv run python "$HOME/repos/github.com/almoore/useful-scripts/python/md_to_pdf.py" "$@"
