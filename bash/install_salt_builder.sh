
if [ -e /etc/redhat-release ]
then
    yum makecache
    yum -y install curl
else
    apt-get update
    apt-get install -y curl
fi
curl -s -L https://bootstrap.saltstack.com/develop -o install_salt.sh
sh install_salt.sh -D -n git v2015.5.1
mkdir -p /etc/salt/minion.d

cat > /etc/salt/minion <<MINION
id: $HOSTNAME
master: cm-salt-master
grains:
  role:
    - standard_builder
MINION
service salt-minion restart
