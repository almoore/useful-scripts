#!/bin/bash

set -e

usage()
{
    echo "$0 -u <mysql_user> -p <mysql_password> [options]" 
    echo "Options:"
    echo " -h , --help       print this message"
    echo " -u , --user       mysql username with access to employee database"
    echo " -p , --password   mysql password for user"
    echo " -d , --debug      show all output from commands"
    echo " -f , --force      force deletion of test table to run"
}

force=0
debug=0
user=""
pass=""
log_file=$(basename -s .sh $0).log
while [ "$1" != "" ]; do
    case $1 in
        -u | --user)
            shift; user="$1";
            ;;
        -p | --password)
            shift; pass="$1";
            ;;
        -d | --debug)
            debug=1;
            ;;
        -f | --force)
            force=1;
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument $1" >&2
            exit 1
            ;;
    esac
    shift
done

if [ "$user" == "" -o "$pass" == "" ]; then
    echo ""
    echo "ERROR: Need user and password"
    usage
    exit 1
fi

echo "pid is $$"
db="employees"
mysql="mysql -u $user -p$pass"

clean_up()
{
    if mysql -u${user} -p${pass} ${db} -e "show tables" | grep test ; then
        echo "drop test table"
        mysql -u${user} -p${pass} ${db} -e "DROP table test"
    fi
}

trap_caught()
{
    echo "caught signal"
    run=0
    clean_up
    exit 1
}
trap trap_caught SIGINT SIGTERM
trap 'kill $(jobs -p)' EXIT

mysql_query() {
    if [ $debug == 1 ] ; then
        date
        echo "mysql -e \"$1\" $db"
        $mysql -ss -e "SELECT NOW();"
        $mysql ${db} -e "${1}"
        echo
    else
        $mysql -ss -e "SELECT NOW();" > /dev/null
        $mysql ${db} -e "${1}" > /dev/null
        echo -n .
    fi
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
    mysql_insert_text $(openssl rand -base64 $((RANDOM % 30)))
}

#pi()
#{
#    echo "scale=$1; 4 * a (1)" | BC_LINE_LENGTH=0 bc -l
#}

mysql_insert_random_pi()
{
    mysql_insert_text $(pi $((RANDOM % $1)))
}

# Generate a list of employee numbers and randomly select one
query="select emp_no from employees"
emp_no_list=$(mysql -u${user} -p${pass} ${db} -e "$query")
emp_no_array=($emp_no_list)
# delete the table title from the array
del=(emp_no)
emp_no_array=( ${emp_no_array[@]:1} )

selected_emp_no=${emp_no_array[$RANDOM % ${#emp_no_array[@]} ]}

# Get the employee info for the employee
if [ $debug == 1 ] ; then
    echo "Employee No. = $selected_emp_no"
fi
mysql_query "select * from employees where emp_no = $selected_emp_no"

# Get salary history for the employee
if [ $debug == 1 ] ; then
    echo "Employee salary history"
fi
mysql_query "select * from salaries where emp_no = $selected_emp_no"

# Generate a table
$mysql -e "SHOW DATABASES;"
if [ $force -ne 0 ] ; then
    clean_up
fi
$mysql $db -e "CREATE TABLE test (id INT NOT NULL AUTO_INCREMENT, data VARCHAR(2000), crc INT, PRIMARY KEY (id));"
mysql_insert_text "First post!"

pi_test()
{
    export run=1
    count=0
    echo
    while [ $run -eq 1 -a $count -lt 50 ]; do
        countx=0
        while [ $run -eq 1 -a $countx -lt 10 ]; do
            mysql_insert_random_text 
            mysql_insert_random_pi 20
            sleep 0.5
            let countx+=1
        done
        let count+=1
        echo
    done
    echo
}

pi_test &

query="SELECT e.first_name, e.last_name, d.dept_name, t.title, t.from_date, t.to_date FROM employees e INNER JOIN  dept_emp de ON e.emp_no=de.emp_no INNER JOIN departments d ON de.dept_no=d.dept_no INNER JOIN titles t ON e.emp_no=t.emp_no ORDER BY  e.first_name, e.last_name, d.dept_name, t.from_date"

mysqlslap --user=$user --password=$pass  --concurrency=20 --iterations=20 --create-schema=employees --query="$query" --verbose
export run=0
#clean_up
exit 0
