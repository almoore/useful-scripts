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
    OLDIFS=$IFS
    IFS=':'
    for p in $PATH; do
        if ! echo $p | grep -q "pyenv"; then
            grep -q "^$p$" $TMP || echo $p >> $TMP
        fi
    done
    if [ -z "$OLDIFS" ]; then
        unset IFS
    else
        IFS=$OLDIFS
    fi
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

aws-profiles () {
    cat ~/.aws/config | grep '\[' | sed 's/profile//g'| tr '[' ' ' | tr ']' ' '
}

#--- COMPDEF ------------------------------------------------------------------#
#      FUNCTION: aws-switch
#   DESCRIPTION: Switch the AWS profile
#------------------------------------------------------------------------------#

_aws_switch() {
    local -a aws_profiles
    local curr_arg;
    curr_arg=${COMP_WORDS[COMP_CWORD]}

     _aws_profiles=$(aws-profiles)
     COMPREPLY=( $(compgen -W "$_aws_profiles" -- $curr_arg ) );
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

#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  gcp-switch
#   DESCRIPTION:  Change between gcp profiles that are locally setup
#----------------------------------------------------------------------------------------------------------------------
gcp-switch() {
    case ${1} in
        "" | clear)
            gcloud config configurations activate default
            ;;
        *)
            gcloud config configurations activate ${1}
            ;;
    esac
}

gcp-profiles () {
    gcloud config configurations list --format text|grep -E "^name"|awk '{print $2}'
}

#--- COMPDEF ------------------------------------------------------------------#
#      FUNCTION: gcp-switch
#   DESCRIPTION: Switch the GCP profile
#------------------------------------------------------------------------------#

_gcp_switch() {
    local -a gcp_profiles
    local curr_arg;
    curr_arg=${COMP_WORDS[COMP_CWORD]}

     _gcp_profiles=$(gcp-profiles)
     COMPREPLY=( $(compgen -W "$_gcp_profiles" -- $curr_arg ) );
}
 
complete -F _gcp_switch gcp-switch

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
_COLORS=${BS_COLORS:-$(tput colors 2>/dev/null || echo 0)}
detect_color_support() {
    # shellcheck disable=SC2181
    if [ "$?" == "0" ] && [ "$_COLORS" -gt 2 ]; then
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

function tsh {
    host=$1
    session_name=$2
    if [ -z "$session_name" ]; then
        echo "Need to provide session-name. Example: tsh <hostname> main"
        return 1;
    fi
    ssh -X $host -t "tmux -CC attach -t $session_name || tmux -CC new -s $session_name"
}


# activate-vpn-cert() {
#     export SSL_CERT_DIR=${HOME}/.aws/certs
#     export SSL_CERT_FILE=${HOME}/.aws/certs/root.pem
#     export AWS_CA_BUNDLE=${HOME}/.aws/certs/root.pem
#     export PIP_CERT=${HOME}/.aws/certs/root.pem
# }

activate-vpn-cert () {
    export SSL_CERT_DIR=${HOME}/anthem;
    export SSL_CERT_FILE=${HOME}/anthem/wellpoint-certifi-ca-bundle.pem;
    export AWS_CA_BUNDLE=${HOME}/anthem/wellpoint-certifi-ca-bundle.pem;
    export PIP_CERT=${HOME}/anthem/wellpoint-certifi-ca-bundle.pem
    export REQUESTS_CA_BUNDLE=${HOME}/anthem/wellpoint-certifi-ca-bundle.pem
}

deactivate-vpn-cert() {
    unset SSL_CERT_DIR
    unset SSL_CERT_FILE
    unset AWS_CA_BUNDLE
    unset PIP_CERT
    unset REQUESTS_CA_BUNDLE
}

toggle-vpn-cert() { test -n "$AWS_CA_BUNDLE" && deactivate-vpn-cert || activate-vpn-cert; }

# https://gitlab.com/gnachman/iterm2/-/wikis/Status-Bar-Tips
test -e "${HOME}/.iterm2_shell_integration.bash" && source "${HOME}/.iterm2_shell_integration.bash"
function iterm2_print_user_vars() {
  iterm2_set_user_var AWS_PROFILE "${AWS_PROFILE:-default}"
  iterm2_set_user_var K8S_CONTEXT "$(kubectl config current-context || "None")"
}



function jq_repl() {
    echo ‘’ | fzf --print-query --preview "jq {q} ${1}"
}

switch-terraform-gcp-env() {
  GIT_BASE=$(git rev-parse --show-toplevel)
  if [ "$GOOGLE_APPLICATION_CREDENTIALS" == "$GOOGLE_APPLICATION_CREDENTIALS_CDC" ]; then
      export GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS_DCDC
      cd ${GIT_BASE}/envs/dev.carelon-digital.com
  else
      export GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS_CDC
      cd ${GIT_BASE}/envs/carelon-digital.com
  fi
}

csvl () {
    OLDIFS=$IFS
    IFS=','
    for v in $@; do
        echo $v
    done
    IFS=$OLDIFS
}
