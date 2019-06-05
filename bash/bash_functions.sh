#!/usr/bin/env bash
ddp() {
    TMP=$(mktemp)
    OLDIFS=$IFS
    IFS=':'
    for p in $PATH; do
        grep -q "^$p$" $TMP || echo $p >> $TMP
    done
    IFS=$OLDIFS
    _OLDPATH=$PATH
    _NEWPATH=$(cat $TMP)
    PATH="$(echo $_NEWPATH | sed 's/\ /:/g')"
    rm $TMP
}

npy() {
    npyd() {
        PATH=$_FULLPATH
        unset _FULLPATH
        unset _NPYPATH
        unset npyd
    }
    TMP=$(mktemp)
    IFS=':'
    for p in $PATH; do
        if ! echo $p | grep -q "pyenv"; then
            grep -q "^$p$" $TMP || echo $p >> $TMP
        fi
    done
    IFS=$OLDIFS
    _FULLPATH=$PATH
    _NPYPATH=$(cat $TMP)
    PATH="$(echo $_NPYPATH | sed 's/\ /:/g')"
    rm $TMP
}


#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  aws-switch
#   DESCRIPTION:  Change between aws profiles that are locally setup
#----------------------------------------------------------------------------------------------------------------------
aws-switch() {
    case ${1} in
        "" | clear)
            export AWS_PROFILE=""
            ;;
        *)
            export AWS_PROFILE="${1}"
            ;;
    esac
}

#--- COMPDEF ------------------------------------------------------------------#
#      FUNCTION: aws-switch
#   DESCRIPTION: Switch the AWS profile
#------------------------------------------------------------------------------#

_aws_switch() {
    local -a aws_profiles
    local curr_arg;
    curr_arg=${COMP_WORDS[COMP_CWORD]}

     aws_profiles=$( \
         grep '\[profile' ~/.aws/config \
         | awk '{sub(/]/, "", $2); print $2}' \
         | while read -r profile; do echo -n "$profile "; done \
     )
     COMPREPLY=( $(compgen -W "$aws_profiles" -- $curr_arg ) );
}
 
complete -F _aws_switch aws-switch


aws-profile () {
    if [ -n "$AWS_PROFILE" ]; then
        echo "$AWS_PROFILE"
    elif [ -n "$AWS_DEFAULT_PROFILE" ]; then
        echo "$AWS_DEFAULT_PROFILE"
    else
        echo "default"
    fi
}

aws-profiles () {
    cat ~/.aws/config | grep profile | cut -d ' ' -f2- | tr ']' ' '
}

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
#          NAME:  echo_error
#   DESCRIPTION:  Echo errors to stderr.
#------------------------------------------------------------------------------#
echo_error() {
    printf "${RC} * ERROR${EC}: %s\n" "$@" 1>&2;
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echo_info
#   DESCRIPTION:  Echo information to stdout.
#------------------------------------------------------------------------------#
echo_info() {
    printf "${GC} *  INFO${EC}: %s\n" "$@";
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echo_warn
#   DESCRIPTION:  Echo warning informations to stdout.
#------------------------------------------------------------------------------#
echo_warn() {
    printf "${YC} *  WARN${EC}: %s\n" "$@";
}

#------------------------------------------------------------------------------#
#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echo_debug
#   DESCRIPTION:  Echo debug information to stdout.
#------------------------------------------------------------------------------#
echo_debug() {
    _ECHO_DEBUG=${DEBUG:-1}
    if [ "$_ECHO_DEBUG" -eq $BS_TRUE ]; then
        printf "${BC} * DEBUG${EC}: %s\n" "$@";
    fi
}

_demo_log_colors() {
    echo_error "This is an error message"
    echo_info  "This is an info message"
    echo_warn  "This is a warning message"
    echo_debug "This is a debug message"
}

# Make python history work in virualenvs
python () {
    if [ "$#" -eq 0 ]; then
        PYTHONSTARTUP=~/.pythonrc $(type -P python)
    else
        $(type -P python) "$@"
    fi
}
