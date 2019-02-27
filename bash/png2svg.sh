#! /bin/bash
################################################################################
#                                  _____
#                                 / __  \
#               _ __  _ __   __ _ `' / /'_____   ____ _
#              | '_ \| '_ \ / _` |  / / / __\ \ / / _` |
#              | |_) | | | | (_| |./ /__\__ \\ V / (_| |
#              | .__/|_| |_|\__, |\_____/___/ \_/ \__, |
#              | |           __/ |                 __/ |
#              |_|          |___/                 |___/
#
################################################################################
#------------------------------------------------------------------------------#
#
# SCRIPT NAME:      png2svg.sh
#
# DESCRIPTION:      Perform basic conversion of PNG images into SVG format
#
# MODIFIED DATE:    20181020
#
# SCRIPT AUTHOR:    h8rt3rmin8r (for ResoNova.com)
#
# SOURCE CODE:      bit.ly/png2svg-sh
#
# USAGE:
#
#      Save this script locally as "png2svg.sh" and make it executable:
#        sudo chmod +x png2svg.sh
#
#      Run the script in the following manner:
#        ./png2svg.sh <file.png>
#
#      This script can be run without verbosity with the following:
#        sudo ./png2svg.sh --silent <file.png>
#
#      Enable this script to have global execution availability by placing it
#      into /usr/local/bin (or somewhere else in your user's PATH). By doing
#      this, you can call "png2svg.sh" from anywhere on the system.
#
# LICENSE:
#
#      Copyright 2018 ResoNova International Consulting, LLC
#
#      Licensed under the Apache License, Version 2.0 (the "License");
#      you may not use this file except in compliance with the License.
#      You may obtain a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.
#
#------------------------------------------------------------------------------#
# VARIABLE DECLARATIONS & SET PIPEFAIL
set -Eeo pipefail
DEPENDS=( "convert" "curl" "dos2unix" "potrace" )
DEPENDS_REQ=""; V_X=""; V_S=""; INPUT_X=""; INPUT_Y=""
INFO_SRC="https://pastebin.com/raw/VAnFpDLH"
VB_00="Beginning PNG conversion process. Please wait..."
VB_01="ERROR: A valid PNG image was not detected in your input parameters!"
VB_02="Please try again"
VB_03=" USAGE EXAMPLES: "
VB_04="    [ Verbose (Slow) ]  -->  ./png2svg.sh <file.png>"
VB_04B="    [ Piped Input v1 ]  -->  echo <file.png> | ./png2svg.sh"
VB_05="    [ Silent (Fast)  ]  -->  ./png2svg.sh --silent <file.png>"
VB_05B="    [ Piped Input v2 ]  -->  echo <file.png> | ./png2svg.sh --silent"
VB_06="    [ Usage Examples ]  -->  ./png2svg.sh --help"
VB_07="    [ General Info   ]  -->  ./png2svg.sh --info"
VB_08="ERR: Missing required package: "
VB_09="The following required packages are not installed on your system: "
VB_10="Terminating file conversion process."
VB_11="Done!"

#------------------------------------------------------------------------------#
# FUNCTION DECLARATIONS

function inputstream() {
    # Write all incoming data into an array, "INST", to allow for both
    # interactive and piped inputs in parent functions
    INST=""
    if [ -t 0 ]
        then local IN=( $(echo -n "$@") )
        else local IN=( $(</dev/stdin) $(echo -n "$@") )
    fi
    export INST=( $(echo ${IN[@]}) ); return
}

function n_tc() {
    # Colorize text outputs
    inputstream "$@"; local COLOR_FILTER=$(echo ${INST[@]})
    echo -e "\e[34m${COLOR_FILTER}\e[39m"; return
}

function vb_out() {
    # Output verbosity function
    echo $(n_tc "[$0]")" $@"; return
}

function depends_check() {
    # Make sure necessary software packages are present
    TEST_A=$("$1" --version > /dev/null 2>&1; echo -n $?)
    TEST_B=$("$1" -version > /dev/null 2>&1; echo -n $?)
    if [[ ! "${TEST_A}" == "0" && ! "${TEST_B}" == "0" ]];
        then echo "FALSE"
        else echo "TRUE"
    fi; return
}

function depends() {
    # Core dependancy checking loop
    for i in ${DEPENDS[@]};
    do
        case $(depends_check "$i") in
            FALSE) vb_out "${VB_08}$i"; DEPENDS_REQ+=( "$i" ) ;;
        esac
    done
    if [[ $(echo "${DEPENDS_REQ[@]}") =~ [A-Za-z0-9] ]];
    then
        vb_out "${VB_09}"
        for i in "${DEPENDS_REQ[@]}"; do n_tc "$i"; done
        echo; read -p "Would you like to install them? [y/n]: " -n 1 -r
        echo "" # insert new line
        if [[ $REPLY =~ ^[Yy]$ ]];
        then
            clear; echo $(vb_out "Installing ${DEPENDS_REQ[@]}")" Please wait..."
            sudo apt-get update
            for i in ${DEPENDS_REQ[@]}; do sudo apt-get install -y $i; done; clear
        else
            vb_out "${VB_10}"; exit 1
        fi
    fi
    return
}

function help_p2s() {
    # Print the png2svg help text
    echo; echo "${VB_03}"; echo
    echo "${VB_04}"; echo "${VB_04B}"
    echo "${VB_05}"; echo "${VB_05B}"
    echo "${VB_06}"; echo "${VB_07}"
    echo; return
}

#------------------------------------------------------------------------------#
# EXECUTE CORE OPERATIONS

inputstream "$@"; INPUT_VARS=( $(echo ${INST[@]}) )
case "$1" in
    -h|-help|--help) help_p2s; exit 0 ;;
    -i|-info|--info)
        depends; curl -s ${INFO_SRC} | dos2unix; echo; exit 0
        ;;
    -q|--quiet|-quiet|-s|--silent|-silent)
        V_X="/dev/null"; V_S="sleep 0"
        ;;
    *|'')
        if [[ "x${INPUT_VARS}" == "x" ]]; then help_p2s; exit 0
            else V_X="/dev/stdout"; V_S="sleep 0.5"; fi
        ;;
esac

depends; vb_out ${VB_00} &>${V_X}; ${V_S}

if [[ $(echo "${#INPUT_VARS[@]}") -gt 1 ]];
then
    touch .tempfile; INPUT_T=".tempfile"
    for i in "${INPUT_VARS[@]}";
    do
        if [[ -f "$i" && "$i" =~ \.png$ ]]; then echo -n "$i" > ${INPUT_T}; fi
    done
    INPUT_Y=$(cat ${INPUT_T})
    if [[ "x${INPUT_Y}" == "x" ]];
    then
        vb_out "${VB_01}" &>${V_X}; vb_out "${VB_02}" &>${V_X}
        help_p2s &>${V_X}; ${V_S}; exit 1
    else
        convert -flatten "${INPUT_Y}" "temp.ppm" &>${V_X}; ${V_S}
        potrace -s "temp.ppm" -o "${INPUT_Y%.*}.svg" &>${V_X}; ${V_S}
        rm temp.ppm &>/dev/null; rm ${INPUT_T} &>/dev/null
        vb_out "${VB_11}" &>${V_X}; ${V_S}
    fi
    exit 0
else
    INPUT_1=$(if [[ -f ${INPUT_VARS} && ${INPUT_VARS} =~ \.png$ ]]; then echo -n TRUE; else echo -n; fi)
    if [[ "x${INPUT_1}" == "x" ]];
    then
        vb_out "${VB_01}" &>${V_X}; vb_out "${VB_02}" &>${V_X}
        help_p2s &>${V_X}; ${V_S}; exit 1
    else
        convert -flatten "${INPUT_VARS}" "temp.ppm" &>${V_X}; ${V_S}
        potrace -s "temp.ppm" -o "${INPUT_VARS%.*}.svg" &>${V_X}; ${V_S}
        rm temp.ppm &>/dev/null; vb_out "${VB_11}" &>${V_X}; ${V_S}
    fi
    exit 0
fi

################################################################################
                                                   #                           #
                                                   #  "think outside the box"  #
                                                   #                           #
                                                   #     ($) ¯\_(ツ)_/¯ (฿)    #
                                                   #                           #
                                                   #############################
