#!/bin/sh
# chkconfig: 2345 80 20
# description: Bamboo Wrapper Script Wrapper
# This script sets bamboo's native wrapper script up so as to run it as bamboo-agent.
# processname: bamboo-agent

export RUN_AS_USER=bamboo-agent
cd /opt/bamboo/bin
if ls /opt/bamboo/bin/bamboo-agent.pid 2> /dev/null ; then
    PID=$(cat /opt/bamboo/bin/bamboo-agent.pid)
    RM=0
    
    if echo $1 | grep "start" > /dev/null ; then
        if ps -p $PID > /dev/null ; then
            PID_USER=$(ps -oruser= -p $PID)
            if ps -oruser= -p $PID | grep "$RUN_AS_USER" > /dev/null ; then
                NAME=$(ps -ocomm= -p $PID)
                if ! ps -ocomm= -p $PID | grep "wrapper" > /dev/null ; then
                    RM=1
                fi
            else
                echo "bad user $PID_USER"
            RM=1
            fi
        else
            echo "bad pid $PID"
            RM=1
        fi
    fi

    if echo $RM | grep "1" > /dev/null ; then
        echo bad pid file ... removing
#        rm /opt/bamboo/bin/bamboo-agent.pid
        exit 1
    fi
fi


/opt/bamboo/bin/bamboo-agent.sh "$@"
