#!/usr/bin/env bash -e

# For BASH shells, edit the system-wide BASH runtime config file:
# sudo -e /etc/bash.bashrc
# /etc/bash.bashrc or /etc/bashrc
# Append to the end of that file:

_ensure_installed() {
    pkg=$1
    if command -v brew > /dev/null; then
        brew list | grep -q $pkg || brew install $pkg
    fi
}

_ensure_installed rsyslog
_ensure_installed logrotate

BASERC=${BASHRC:-/etc/bashrc}

TMP=$(mktemp)
cat <<'EOF' > $TMP
export PROMPT_COMMAND='RETRN_VAL=$?;logger -p local6.debug "$(whoami) [$$]: $(history 1 | sed "s/^[ ]*[0-9]\+[ ]*//" ) [$RETRN_VAL]"'
EOF

if [ -r ${BASHRC} ]; then
  if ! grep PROMPT_COMMAND $BASHRC; then
    mv $TMP $BASHRC
  fi
else
  cat $TMP >> $BASHRC
fi
rm $TMP

# Set up logging for "local6" with a new file:
# Linux /etc/rsyslog.d
# OSX   /usr/local/etc/rsyslog.d
# And the contents...
RSYSLOGD=${RSYSLOGD:-/usr/local/etc/rsyslog.d}
mkdir -p $RSYSLOGD
if ! grep history.log $SYSLOGD/bash.conf; then
    echo 'local6.*    /var/log/history.log' >> $SYSLOGD/bash.conf
fi

# Restart rsyslog:
# sudo service rsyslog restart
brew 

#Log rotation:
sudo -e /etc/logrotate.d/rsyslog

#There is a list of log files to rotate the same way...

/var/log/mail.warn
/var/log/mail.err
[...]
/var/log/message
# So add the new bash-commands log file in that list:
/var/log/commands.log
