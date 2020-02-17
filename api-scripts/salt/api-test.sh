#!/bin/sh

################################################################################
# Note:
#   Good guide:
#   http://bencane.com/2014/07/17/integrating-saltstack-with-other-services-via-salt-api/


################################################################################
# Setup Salt API User
# ------------------------
################################################################################

#USER='saltapi'
#PASS='saltapi'
#URL='https://localhost:8000'
#EAUTH='pam'

COOKIE='/tmp/salt_cookies.txt'

URL=https://p-gp2-salt-1.p.movetv.com:8000
USER=service.saltapi
PASS=service923156
EAUTH=ldap



################################################################################
# Use a cookie instead of a token
# -------------------------------
################################################################################

login_with_cookie(){

    curl -sSk ${URL}/login \
         -H 'Accept: application/x-yaml' \
         -d username=${USER} \
         -d password=${PASS} \
         -d eauth=${EAUTH} \
         -c ${COOKIE}

}

login_with_cookie

################################################################################
# Subsequent calls may use the cookie
# -----------------------------------
################################################################################

test_grains(){
    curl -sSk ${URL} \
         -b ${COOKIE} \
         -H 'Accept: application/x-yaml' \
         -d client=local \
         -d tgt='*' \
         -d fun=grains.items
}

test_grain_id(){
    curl -sSk ${URL} \
         -b ${COOKIE} \
         -H 'Accept: application/json' \
         -d client=local \
         -d tgt='*' \
         -d fun='grains.item' \
         -d arg='id'
}

#test_grains
#test_grain_id

################################################################################
#Accepting a New Minion's Key
#----------------------------
################################################################################

accept_minion(){
    curl -sSk ${URL} \
         -b ${COOKIE} \
         -H 'Accept: application/x-yaml' \
         -d client='wheel' \
         -d fun='key.accept' \
         -d match='my_new_minion'
}

#accept_minion

################################################################################
# Registered URLs
# ---------------
################################################################################
# /               The primary entry point to Salt’s REST API
# /login          Authenticate against Salt’s eauth system
# /logout         Destroy the currently active session and expire the session cookie
# /minions/(min)  Convenience URLs for working with minions
# /jobs           Convenience URL for getting lists of previously run jobs or job
# /run            Class to run commands without normal session handling
# /events         Expose the Salt event bus
# /hook           A generic web hook entry point that fires an event on Salt’s event bus
# /keys/(key)     List all RSA keys or show a specific key
# /ws             Open a WebSocket connection to Salt’s event bus
# /stats          Expose statistics on the running CherryPy server

test_minions_url(){
    curl -sSk ${URL}/minions/ \
         -b ${COOKIE} \
         -H 'Accept: application/x-yaml' 
}

#test_minions_url

test_events_url(){
    curl -sSk ${URL}/events/ \
         -b ${COOKIE} \
         -H 'Accept: application/x-yaml' 
}

test_events_url
