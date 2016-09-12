#!/bin/bash

set -e

trap_caught()
{
    echo "Some signal caught. Stopping"
    export run=0
}

trap trap_caught SIGTSTP
trap trap_caught SIGQUIT
trap trap_caught SIGTERM
trap trap_caught INT

tools_dir=$(dirname $0)
if [ -e $tools_dir/colors.sh ]; then
    ./$tools_dir/colors.sh
fi

force=0
while [ "$1" != "" ]; do
    case $1 in
        -u | --user)
            shift; user="$1";
            ;;
        -p | --pass)
            shift; password="$1";
            ;;
        -f | --force)
            force=1;
            ;;
        *)
            echo "Unknown argument $1" >&2
            exit 1
            ;;
    esac
    shift
done

pi()
{
    echo "scale=$1; 4 * a (1)" | BC_LINE_LENGTH=0 bc -l
}

mysql="mysql -u $user -p$password"

mysql_query() {
    date
    echo $mysql -e "\"$1\"" $db
    $mysql -ss -e "SELECT NOW();"
    $mysql -e "${1}" $db
    echo
}

mysql_insert_text()
{
    text="$1"
    mysql_query "INSERT INTO test VALUES (null, '$text', CRC32('$text'));"
    mysql_query "SELECT * FROM test;"
    mysql_query "CHECKSUM TABLE test;"
}

mysql_insert_random_text()
{
    mysql_insert_text $(openssl rand -hex $((RANDOM % 30)))
}

mysql_insert_random_pi()
{
    mysql_insert_text $(pi $1)
}

mysql_query "SHOW DATABASES;"
if [ $force -ne 0 ]; then
    mysql_query "DROP DATABASE test;"
fi
mysql_query "CREATE DATABASE test;"
db="test"
mysql_query "CREATE TABLE test (id INT NOT NULL AUTO_INCREMENT, data VARCHAR(2000), crc INT, PRIMARY KEY (id));"
mysql_insert_text "First post!"

export run=1
while [ $run -eq 1 ]; do
    mysql_insert_random_text 
    mysql_insert_random_pi 2000
done
