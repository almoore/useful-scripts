#!/bin/sh

#stack=$1
#
#case $1 in
#    dev)
#        host="vertica.bedap-dev.cmscloud.local";;
#    imp|test|prod)
#        host="vertica.bedap-${stack}.mp.cmscloud.local";;
#    *)
#        echo "Usage: ${0} <stack> <match>"
#        echo "stack must be provided and be one of: dev,test,imp,prod" >&2
#    exit 1
#esac
#shift

match=$1

# aws ec2 describe-instances --filters "Name=tag:Name,Values=*${match}*" 'Name=instance-state-name,Values=running' "Name=tag:stack,Values=$stack" \
    aws ec2 describe-instances --filters "Name=tag:Name,Values=*${match}*" 'Name=instance-state-name,Values=running' \
    --query 'Reservations[*].Instances[*].{ name: Tags[?Key==`Name`].Value|[0], id: InstanceId, state: State.Name, private_ip: NetworkInterfaces[*].PrivateIpAddress|[0], key_name: KeyName}[0]' \
    --output=text

