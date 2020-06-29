#!/usr/bin/env bash
set -Eeo pipefail
_KEYNAME="$@"

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  detect_color_support
#   DESCRIPTION:  Try to detect color support.
#----------------------------------------------------------------------------------------------------------------------
# If the BS_COLORS value is not set get it from tput
_COLORS=${BS_COLORS:-$(tput colors 2>/dev/null || echo 0)}
detect_color_support() {
    # shellcheck disable=SC2181
    if [ $? -eq 0 ] && [ "$_COLORS" -gt 2 ]; then
        BKC="\033[1;30m"
        RC="\033[1;31m"
        GC="\033[1;32m"
        YC="\033[1;33m"
        BC="\033[1;34m"
        MC="\033[1;35m"
        CYC="\033[1;36m"
        WC="\033[1;37m"
        EC="\033[0m"
    else
        BKC=""
        RC=""
        GC=""
        YC=""
        BC=""
        MC=""
        CYC=""
        WC=""
        EC=""
    fi
}
detect_color_support

error() {
    printf "${RC} * ERROR${EC}: %s\n" "$@" 1>&2;
}

warn() {
    printf "${YC} *  WARN${EC}: %s\n" "$@";
}

info() {
    printf "${GC} *  INFO${EC}: %s\n" "$@";
}

if [ "$#" -eq 0 ]; then
    error "Please provide key name to create"
    exit 1
fi

GITBASE=$(git rev-parse --show-toplevel)

RESULT=$(aws ec2 describe-key-pairs --filters "Name=key-name,Values=${_KEYNAME}" --output text)
if [ -z "${RESULT}" ]; then
    TMP=(mktemp)
    info "Generating key with awscli ${_KEYNAME}"
    aws ec2 create-key-pair --key-name ${_KEYNAME} | tee $TMP
    mkdir -p $GITBASE/user-keys
    cat $TMP | jq '.KeyMaterial' -r > $GITBASE/user-keys/${_KEYNAME}.pem
    info "Key saved to $GITBASE/user-keys/${_KEYNAME}.pem"
    rm $TMP
else
    warn "The key name ${_KEYNAME} already exists. Nothing done"
fi
