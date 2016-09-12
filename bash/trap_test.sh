#!/bin/bash
# trap_test.sh

trap_caught()
{
    echo "caught signal"
    exit 1
}

trap trap_caught SIGINT SIGTERM
echo "pid is $$"

while :			# This is the same as "while true".
do
        sleep 60	# This script is not really doing anything.
done
