#!/usr/bin/env bash

PID_DIR=${PID_DIR:=/var/run}
PIDFILE=$PID_DIR/docker-clean-node
# Executable to use
DOCKER_BIN=${DOCKER_BIN:=docker}
# Only show what would be done
DRY_RUN=${DRY_RUN:=0}
# remove containers that finished more than 24 hours ago
EXPIRE=${DOCKER_EXPIRE:=24}
EXCLUDE_CONTAINERS=${EXCLUDE_CONTAINERS:=''}
EXCLUDE_CONTAINER_FILE=${EXCLUDE_CONTAINER_FILE:=/tmp/docker-clean-node-exclude.txt}

WAIT_TIME=${WAIT_TIME:=3}
# logging variables
LOG_TO_SYSLOG=${LOG_TO_SYSLOG:=0}
LOG_TO_STD_OUT=${LOG_TO_STD_OUT:=0}
LOG_DATE=${LOG_DATE:=0}
SYSLOG_FACILITY=${SYSLOG_FACILITY:=user}
SYSLOG_LEVEL=${SYSLOG_LEVEL:=info}
SYSLOG_TAG=${SYSLOG_TAG:=docker-clean-node}


# Cleanup on exit
function on_exit() {
    rm -f -- $PIDFILE
}
trap on_exit EXIT

read -r -d '' USAGE << EOF
Usage: docker-clean-node [options]

  -h, --help print this message and exit

  --wait-time              The amount of time to wait between removing containers images and volumes

  --docker-bin DOCKER-BIN  Optionaly pass in the path to the docker binary to use

  -d, --dry-run            Just show what would be done

  -e, --expire TIME        The time in hours to look keep exited containers defaults to 24

  -x, --exclude-containers "<ID_1> [ID_2] [ID_3]"

                           A list of container ids to exclude from removal. If doing more than one use
                           quotes to indecate the start and end of the list

  -f, --exclude-file FILE  The path to file that has a list of container ids to exclude from removal

  --pid-dir DIR            The directory that the pid file is stored

  -l, --log-to-syslog      Log to syslog rather defaulting to stdout

  -L, --log-to-stdout      Use this in combination with --log-to-syslog in order to log to stdout as well as syslog

  -D, --log-date-output    Add date to the output. This is already added to the syslog.

EOF

usage() {
    echo "$USAGE"
}

function log() {
    msg=$1
    # Select a single method to output
    if [[ $LOG_TO_SYSLOG -gt 0 ]]; then
        logger -i -t "$SYSLOG_TAG" -p "$SYSLOG_FACILITY.$SYSLOG_LEVEL" "$msg"
        # Log to std out as well
        if [[ $LOG_TO_STD_OUT -gt 0 ]]; then        
            if [[ $LOG_DATE -gt 0 ]]; then
                echo "[$(date +'%Y-%m-%dT%H:%M:%S')] [INFO] : $msg"
            else
                echo "$msg"
            fi
        fi
    elif [[ $LOG_DATE -gt 0 ]]; then
         echo "[$(date +'%Y-%m-%dT%H:%M:%S')] [INFO] : $msg"
    else
         echo "$msg"
    fi

}

exec 3>>$PIDFILE
if ! flock -x -n 3; then
  echo "[$(date)] : docker-clean-node : Process is already running"
  exit 1
fi

while [ "$1" != "" ] ; do
    case $1 in
        -h | --help )
            usage
            exit
        ;;
        --pid-dir )
            shift
            PID_DIR=$1
        ;;
        --docker-bin )
            shift
            DOCKER_BIN=1$
        ;;
        -d | --dry-run )
            DRY_RUN=1
        ;;
        -e | --expire )
            shift
            EXPIRE=$1
        ;;
        -x | --exclude-containers )
            shift
            EXCLUDE_CONTAINERS=1$
        ;;
        -f | --exclude-file )
            shift
            EXCLUDE_CONTAINER_FILE=$1
        ;;
        --wait-time )
            shift
            WAIT_TIME=${1}
        ;;
        -l | --log-to-syslog )
            LOG_TO_SYSLOG=1
        ;;
        -L | --log-to-stdout )
            LOG_TO_STD_OUT=1
        ;;
        -D | --log-date-output )
            LOG_DATE=1
        ;;
    esac
shift
done

EXPIRE_SEC=$(expr ${EXPIRE} \* 60 \* 60)

echo $$ > $PIDFILE

containers=$($DOCKER_BIN ps -a -q -f status=exited)
if [ "$EXCLUDE_CONTAINERS"x != ""x ]; then
    echo $EXCLUDE_CONTAINERS > $EXCLUDE_CONTAINER_FILE
fi
if [ "${containers}"x != ""x ]; then
    if [ "${DRY_RUN}" != "0" ] ; then
        log "DRY RUN:"
    fi
    log "Found stoped containers "${containers}" checking if they are older than ${EXPIRE} hour(s)"
    echo "${containers}" | while read cid ; do
        excluded=$(grep -o "$cid" $EXCLUDE_CONTAINER_FILE 2>/dev/null)
        if [ "$excluded"x != ""x ] ; then
            log "EXCLUDING: ${cid}"
        else
            finish=$($DOCKER_BIN inspect -f '{{.State.FinishedAt}}' $cid)
            name=$($DOCKER_BIN inspect -f '{{.Name}}' $cid)
            diff=$(expr $(date +"%s") - $(date --date="$finish" +"%s"))
            # remove containers that finished more than 24 hours ago
            if [ "${diff}" -gt "${EXPIRE_SEC}" ] ; then
                if [ "${DRY_RUN}" != "0" ] ; then
                    log "DRY RUN: Would have removed exited docker container ID: ${cid} NAME: ${name} finished more than ${EXPIRE} hour(s) ago"
                else
                    log "REMOVING: Exited docker container ID: ${cid} NAME: ${name} finished more than ${EXPIRE} hours ago"
                    $DOCKER_BIN rm -v $cid
                fi
            else
                log "KEEPING: Container ID: ${cid}  NAME: ${name} exited less than ${EXPIRE} hours ago"
            fi
        fi
    done
else
    log "No exited containers found"
fi

sleep ${WAIT_TIME}
i_dangling=$($DOCKER_BIN images -q -f "dangling=true")
if [ "${i_dangling}"x != ""x ]; then
    if [ "${DRY_RUN}" != "0" ] ; then
        log "DRY RUN: Would have removed dangling docker images ${i_dangling}"
    else
        log "Removing dangling docker images ${i_dangling}"
        $DOCKER_BIN rmi ${i_dangling}
    fi
else
    log "No dangling docker images found"
fi

sleep ${WAIT_TIME}
v_dangling=$($DOCKER_BIN volume ls -q -f "dangling=true")
if [ "${v_dangling}"x != ""x ]; then
    if [ "${DRY_RUN}" != "0" ] ; then
        log "DRY RUN: Would have removed dangling docker volumes ${v_dangling}"
    else
        log "Removing dangling docker volumes ${v_dangling}"
        $DOCKER_BIN volume rm ${v_dangling}
    fi
else
    log "No dangling docker volumes found"
fi
