# TODO Ask if change source list
# Edit /etc/apt/sources.list. Comment out or remove the installation CD from the file and make sure that the universe and multiverse repositories are enabled. It should look like this afterwards:
TMP=/tmp/perf-install
mkdir ${TMP}
cat > ${TMP}/etc/apt/sources.list <<EOF
#

# deb cdrom:[Ubuntu-Server 16.04 LTS _Xenial Xerus_ - Release amd64 (20160420)]/ xenial main restricted

#deb cdrom:[Ubuntu-Server 16.04 LTS _Xenial Xerus_ - Release amd64 (20160420)]/ xenial main restricted

# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to
# newer versions of the distribution.
deb http://de.archive.ubuntu.com/ubuntu/ xenial main restricted
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial main restricted

## Major bug fix updates produced after the final release of the
## distribution.
deb http://de.archive.ubuntu.com/ubuntu/ xenial-updates main restricted
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial-updates main restricted

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team, and may not be under a free licence. Please satisfy yourself as to
## your rights to use the software. Also, please note that software in
## universe WILL NOT receive any review or updates from the Ubuntu security
## team.
deb http://de.archive.ubuntu.com/ubuntu/ xenial universe
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial universe
deb http://de.archive.ubuntu.com/ubuntu/ xenial-updates universe
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial-updates universe

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team, and may not be under a free licence. Please satisfy yourself as to
## your rights to use the software. Also, please note that software in
## multiverse WILL NOT receive any review or updates from the Ubuntu
## security team.
deb http://de.archive.ubuntu.com/ubuntu/ xenial multiverse
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial multiverse
deb http://de.archive.ubuntu.com/ubuntu/ xenial-updates multiverse
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial-updates multiverse

## N.B. software from this repository may not have been tested as
## extensively as that contained in the main release, although it includes
## newer versions of some applications which may provide useful features.
## Also, please note that software in backports WILL NOT receive any review
## or updates from the Ubuntu security team.
deb http://de.archive.ubuntu.com/ubuntu/ xenial-backports main restricted universe multiverse
# deb-src http://de.archive.ubuntu.com/ubuntu/ xenial-backports main restricted universe multiverse
## Uncomment the following two lines to add software from Canonical's
## 'partner' repository.
## This software is not part of Ubuntu, but is offered by Canonical and the
## respective vendors as a service to Ubuntu users.
# deb http://archive.canonical.com/ubuntu xenial partner
# deb-src http://archive.canonical.com/ubuntu xenial partner

deb http://security.ubuntu.com/ubuntu xenial-security main restricted
# deb-src http://security.ubuntu.com/ubuntu xenial-security main restricted
deb http://security.ubuntu.com/ubuntu xenial-security universe
# deb-src http://security.ubuntu.com/ubuntu xenial-security universe
deb http://security.ubuntu.com/ubuntu xenial-security multiverse
# deb-src http://security.ubuntu.com/ubuntu xenial-security multiverse
EOF
# Then update the apt cache
apt-get update
# Fix the sh config default shell for ISPConfig to work properly
# the dpkg-reconfig can do this but only with user interaction 
## dpkg-reconfigure dash
unlink /bin/sh
ln -s /bin/bash /bin/sh
# Disable AppArmor
service apparmor stop
update-rc.d -f apparmor remove 
apt-get remove apparmor apparmor-utils

###
# ADD EXTRA
###

challengeme
