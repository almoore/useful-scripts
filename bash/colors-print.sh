#!/bin/sh

#------------------------------------------------------------------------------#
# One way using bash declared array
# Note only bash verions 4 fully supports this.
# Examples: 
# http://www.artificialworlds.net/blog/2012/10/17/bash-associative-array-examples/
#------------------------------------------------------------------------------#

# Set variables
name=${0##*/}
RPATH=$(readlink $0)
if [ "$RPATH" == "" ] ; then
    WD=$PWD
else
    WD=${RPATH%/*}
fi

declare -A COLORS=( ["black"]="30" ["red"]="31" ["green"]="32" ["yellow"]="33" ["blue"]="34" ["magenta"]="35" ["cyan"]="36" ["white"]="37" )
declare -A FORMAT=( ["normal"]="0" ["bold"]="1" ["italic"]="3" ["underline"]="4" ["blink"]="5" ["reverse"]="7" ["nondisplayed"]="8" )

RESET='\E[0m'
F=0
C=0
# Set control variables
bg=0

var_grep() {
    if [ "$2" != in ] || [ ! ${#} -eq 3 ] ; then
        print_form yellow bold "Incorrect usage."
        print_form yellow bold "Correct usage: vag_grep {key} in {variable}"
        return
    fi
    var=${!3}
    if [ -z "$var" ]; then
        print_form red bold "The variable \"$3\" is not defined or is of zero length"
        return
    fi
    echo $var | grep -e "\b${1}\b" > /dev/null
}

format() {
    if [ ${#} -eq 2 ] ; then
        echo -en "\E[${1};${2}m"
    else
        echo -en "\E[${F};${C}m"
    fi
}

print_form() {
    RESET='\E[0m'
    # Backup format and color
    msg=""
    FORMS=""
    F1=$F; C1=$C
    if  [ ! ${#} -eq 3 ] ; then
        format "${FORMAT[normal]}" ${COLORS[yellow]}
        echo -e "Incorrect usage.\nCorrect usage: print_form <color> \"[format[;format]]\" \"{message}\""
        echo -en "$RESET"
        return
    fi

    # Check that the value is a single key and is in the dictionary
    if [ "$1" != "" ] && [[ "$1" != *" "* ]] && [ ${COLORS["$1"]} ]; then
        C=${COLORS["$1"]}
        shift
    fi

    if [ "$1" != "" ] && [[ "$1" != *" "* ]] ; then
        forms=$1
        for f in ${forms/;/ }; do
        if [ ${FORMAT[$f]} ]; then
            FORMS="$FORMS;${FORMAT[$f]}"
        fi
        done
        if [ "$FORMS" != "" ]; then
            F="$FORMS"
            shift
        fi
    fi
    msg="$msg $*"
    format $F $C
    echo -en $msg
    # reset format and color
    F=$F1; C=$C1
    format
    echo
}

formats_l="normal bold italic underline blink reverse nondisplayed"
colors_l="black red green yellow blue magenta cyan white"

echo "Using the array method the formats are:"
for f in $formats_l ; do
    echo -n "${f^^}: "
    for c in $colors_l ; do
        print_form $c $f "$c"
    done
    echo; echo
done



#------------------------------------------------------------------------------#
# Using case statement to get the values
#------------------------------------------------------------------------------#

# Set variables
name=${0##*/}
RPATH=$(readlink $0)
if [ "$RPATH" == "" ] ; then
    WD=$PWD
else
    WD=$(cd ${RPATH%/*}; pwd)
fi

get_color_code() {
    case $1 in
        black)   echo "30";;
        red)     echo "31";;
        green)   echo "32";;
        yellow)  echo "33";;
        blue)    echo "34";;
        magenta) echo "35";;
        cyan)    echo "36";;
        white)   echo "37";;
        *)       echo "37";
    esac
}

get_format_code() {
    case $1 in 
        normal)       echo "0";;
        bold)         echo "1" ;;
        italic)       echo "3" ;;
        underline)    echo "4" ;;
        blink)        echo "5" ;;
        reverse)      echo "7" ;;
        nondisplayed) echo "8" ;;
        *)       echo "0";
    esac
}

RESET='\E[0m'
format_case() {
    local FORMAT=1
    local COLOR=$(get_color_code $1);shift
    if [ ${#} -eq 2 ]; then
        local FORMAT=$(get_format_code $1);shift
    fi
    msg="$*"
    echo -en "\E[${FORMAT};${COLOR}m${msg}${RESET}"
}

formats_l="normal bold italic underline blink reverse nondisplayed"
colors_l="black red green yellow blue magenta cyan white"

echo "Using the case method the formats are"
for f in $formats_l ; do
    echo -n "$f: "
    for c in $colors_l ; do
        format_case $c $f "$c "
    done
    echo; echo
done

#------------------------------------------------------------------------------#
# Using printf and terminal env valuse "tput"
#------------------------------------------------------------------------------#

BS_TRUE=1
BS_FALSE=0
_ECHO_DEBUG=1

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
        CC="\033[1;36m"
        WC="\033[1;37m"
        EC="\033[0m"
    else
        BKC=""
        RC=""
        GC=""
        YC=""
        BC=""
        MC=""
        CC=""
        WC=""
        EC=""
    fi
}

detect_color_support

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echoerr
#   DESCRIPTION:  Echo errors to stderr.
#------------------------------------------------------------------------------#
echoerror() {
    printf "${RC} * ERROR${EC}: %s\n" "$@" 1>&2;
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echoinfo
#   DESCRIPTION:  Echo information to stdout.
#------------------------------------------------------------------------------#
echoinfo() {
    printf "${GC} *  INFO${EC}: %s\n" "$@";
}

#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echowarn
#   DESCRIPTION:  Echo warning informations to stdout.
#------------------------------------------------------------------------------#
echowarn() {
    printf "${YC} *  WARN${EC}: %s\n" "$@";
}

#------------------------------------------------------------------------------#
#---  FUNCTION  ---------------------------------------------------------------#
#          NAME:  echodebug
#   DESCRIPTION:  Echo debug information to stdout.
#------------------------------------------------------------------------------#
echodebug() {
    if [ "$_ECHO_DEBUG" -eq $BS_TRUE ]; then
        printf "${BC} * DEBUG${EC}: %s\n" "$@";
    fi
}

echoerror "This is an error message"
echoinfo  "This is an info message"
echowarn  "This is a warning message"
echodebug "This is a debug message"
