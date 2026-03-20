#!/usr/bin/env bash
#------------------------------------------------------------------------------#
# Using printf and terminal env valuse "tput"
#------------------------------------------------------------------------------#

BS_TRUE=1
BS_FALSE=0
_ECHO_DEBUG=${DEBUG:-1}

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  detect_color_support
#   DESCRIPTION:  Try to detect color support.
#----------------------------------------------------------------------------------------------------------------------
# If the BS_COLORS value is not set get it from tput
_COLORS=${BS_COLORS:-$(tput colors 2>/dev/null ||  0)}
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

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  error
#   DESCRIPTION:  Echo errors to stderr.
#------------------------------------------------------------------------------#
error() {
    printf "${RC} * ERROR${EC}: %s\n" "$@" 1>&2;
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  info
#   DESCRIPTION:  Echo information to stdout.
#------------------------------------------------------------------------------#
info() {
    printf "${GC} *  INFO${EC}: %s\n" "$@";
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  warn
#   DESCRIPTION:  Echo warning informations to stdout.
#------------------------------------------------------------------------------#
warn() {
    printf "${YC} *  WARN${EC}: %s\n" "$@";
}

#------------------------------------------------------------------------------#
#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  debug
#   DESCRIPTION:  Echo debug information to stdout.
#------------------------------------------------------------------------------#
debug() {
    _ECHO_DEBUG=${DEBUG:-1}
    if [ "$_ECHO_DEBUG" -eq $BS_TRUE ]; then
        printf "${BC} * DEBUG${EC}: %s\n" "$@";
    fi
}

_demo_log_colors() {
    error "This is an error message"
    info  "This is an info message"
    warn  "This is a warning message"
    debug "This is a debug message"
}
