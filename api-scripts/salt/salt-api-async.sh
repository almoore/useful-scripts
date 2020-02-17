#!/usr/bin/env bash

WAIT_TIME=10
CLIENT=local_async
#set -x

usage() {
    echo "Usage: ${0##*/} [options]"
    echo "  --client CLIENT       specify the salt-api client to use (local,"
    echo "                        local_async, runner, etc)"
    echo "  --wait-time           the amount of time to wait between checks"
    echo "                        to the salt api job status"
    echo "  -u SALTAPIURL, --saltapi-url SALTAPIURL"
    echo "                        Specify the host url.  Defaults to"
    echo "                        https://localhost:8080"
    echo "  -a EAUTH, --auth=EAUTH, --eauth=EAUTH, --extended-auth=EAUTH"
    echo "                        Specify the external_auth backend to authenticate"
    echo "                        against and interactively prompt for credentials"
    echo "  --username=USERNAME"
    echo "                        Optional, defaults to user name. will be prompt if"
    echo "                        empty unless --non-interactive"
    echo "  --password=PASSWORD"
    echo "                        Optional, but will be prompted unless --non-"
    echo "                        interactive"
    echo "  -e, --ignore-errors"
    echo "                        Ignore errors produced by other jobs running at the same time."
    echo "                        Example:"
    echo "                        The function \"state.apply\" is running as PID 11605 and was started at..."
    echo "  -S, --ignore-stderr"
    echo "                        Ignore return that contains messages with the stderr key in the changes field"
}

CMD=( "${@}" )

RC=0
IGNORE_ERRORS=0
IGNORE_STDERR=0
ERROR_MSGS=()

while [ "$1" != "" ] ; do
    case $1 in 
        --client )
            shift
            CLIENT=$1
            ;;
        --wait-time )
            shift
            WAIT_TIME=$1
            ;;
        -u | --saltapi-url* )
            if echo "$1" | grep '=' > /dev/null ; then
                export SALTAPI_URL=$(echo "$1" | awk -F '=' '{print $2}')
            else
                shift
                export SALTAPI_URL=$1
            fi
            ;;
        -e | --ignore-errors )
            IGNORE_ERRORS=1
            ;;
        -S | --ignore-stderr )
            IGNORE_STDERR=1
            ;;
        * )
            ARGS+=("$1")
            ;;
    esac
shift
done

RET=$(pepper --client $CLIENT "${ARGS[@]}" )
JID=$(echo $RET | jq '.return[].jid' | sed s/\"//g)
MINIONS=$(echo $RET | jq '.return[].minions[]')
MINION_COUNT=$(echo $RET | jq '.return[].minions|length')

if [ -z "$JID" ]; then
    echo "$RET"
    exit 1
fi

yellow="33m"
red="31m"
bold="1"

var_grep()
{
    if [ "$2" != in ] || [ ! ${#} -eq 3 ] ; then
        echo -e "\033[${bold};${yellow}Incorrect usage: ${@}\nCorrect usage: var_grep {key} in {variable}\033[0m"
        return
    fi
    var=${3}
    if [ -z "$var" ]; then
        echo -e "\033[${bold};${red} The variable \"\$3\" is not defined or is of zero length\033[0m"
        return
    fi
    local data=$(grep -e "\b${1}\b" <<< $3)
    return $?
}

lookup_job(){
    # lookup the job id / status
    RET=$(pepper --client runner jobs.lookup_jid $JID)
    RC=$?
    RET_FLAT=$(echo $RET)
}

check_return_keys() {
    RET_DATA=$(pepper --client runner jobs.print_job $JID | jq '.return[0][].Result')
    KEYS=$(echo $RET_DATA | jq 'keys|.[]')
    for k in $KEYS; do
        # TODO Add check to parse data and validate that the return does not contian
        # Errors or messages about jobs blocking

        # Example:
        #       "The function \"state.apply\" is running as PID 11605 and was started at 2017, Mar 15 16:28:43.601237 with jid 20170315162843601237"
        IS_RUNNING=$(echo $RET_DATA | jq '.['$k']' | grep " is running as PID ")

        if [ ! -z "$IS_RUNNING" ] && [ "$IGNORE_ERRORS" == "0" ];then
            RC=1
            ERROR_MSGS+=("$k has error $IS_RUNNING")
        fi
        # Example:
        #  "changes": {
        #    "stdout": "",
        #    "stderr": "Traceback (most recent call last):\n  File \"bin/rovi\", line 11, in <module>\n    load_entry_point('ivory==1.3.101', 'console_scripts', 'rovi')()\n  File \"/opt/move/ivory/lib/python3.5/site-packages/pkg_resources/__init__.py\", line 560, in load_entry_point\n    return get_distribution(dist).load_entry_point(group, name)\n  File \"/opt/move/ivory/lib/python3.5/site-packages/pkg_resources/__init__.py\", line 2648, in load_entry_point\n    return ep.load()\n  File \"/opt/move/ivory/lib/python3.5/site-packages/pkg_resources/__init__.py\", line 2302, in load\n    return self.resolve()\n  File \"/opt/move/ivory/lib/python3.5/site-packages/pkg_resources/__init__.py\", line 2308, in resolve\n    module = __import__(self.module_name, fromlist=['__name__'], level=0)\n  File \"/opt/move/ivory/lib/python3.5/site-packages/ivory/rovi.py\", line 15, in <module>\n    from pycommon3.standardlogging import setup_logging, get_log_level\nImportError: No module named 'pycommon3'",
        #    "retcode": 1,
        #    "pid": 29247
        #  }
        if [ "$IGNORE_STDERR" == "0" ]; then
            STD_ERROR=$(echo $RET_DATA | jq '.['$k']' | grep "stderr")
            if [ -z "$STD_ERROR" ]; then
                RC=1
                ERROR_MSGS+=("$k has error $STD_ERROR")
            fi
        fi
        
    done
}

check_return_keys() {
    RET_KEYS=$(pepper --client runner jobs.print_job $JID | jq '.return[0][].Result|keys')
    return test [ "$MINIONS" == "$RET_KEYS" ]
}

check_return_count() {
    RET_COUNT=$(pepper --client runner jobs.print_job $JID | jq '.return[0][].Result|keys|length')
}

manage_up(){
    MINION_UP_ARRAY=$(pepper --client runner manage.up | jq '.return[0][]')
}

minion_is_up() {
    if [ -z "$MINION_UP_ARRAY" ]; then
        manage_up
    fi
    IS_UP="1"

    if var_grep $1 in "$MINION_UP_ARRAY" ; then
        IS_UP="0"
        return
    fi
}

get_minion_up_count(){
    MINION_UP_COUNT=0
    for i in $MINIONS; do
        minion_is_up "$i"
        if [ "$IS_UP" == "0" ]; then
            let MINION_UP_COUNT+=1
        fi
    done

    if [ "$MINION_UP_COUNT" != "$MINION_COUNT" ]; then
        echo "WARNING: Not all the targeted minions are up." 
        echo "Only checking for return from number of minions that are up."
        MINION_COUNT=$MINION_UP_COUNT
    fi
}

manage_up
get_minion_up_count
check_return_count

# loop to check the state
while [ "$RET_COUNT" -lt "$MINION_COUNT" ] ; do
    # each call using pepper re-authorizes the client
    check_return_count
    sleep ${WAIT_TIME}
done

check_return_keys

# grab the actual return data
pepper --client runner jobs.print_job $JID

exit $RC
