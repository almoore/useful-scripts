#!/usr/bin/env bash
RUN() { printf "+ %b\n" "$*" >&2; "${@}"; }
