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
    msg="$msg$*"
    format $F $C
    printf "%b" "$msg"
    # reset format and color
    F=$F1; C=$C1
    format
    echo
}

#formats_l="normal bold italic underline blink reverse nondisplayed"
#colors_l="black red green yellow blue magenta cyan white"
formats_l="${!FORMAT[@]}"
colors_l="${!COLORS[@]}"

echo "Using the array method the formats are:"
for f in $formats_l ; do
    echo "${f^^}: (${FORMAT[$f]})"
    for c in $colors_l ; do
        echo -ne "${c^^}\t:\t"
        message=$c
        if [ $c == "black" ]; then
            WHITE_BG="\E[107m"
            message="${WHITE_BG}$message"
            print_form $c $f "$message"
        else
            print_form $c $f "$message"
        fi
    done
    echo; echo
done
