(
echo "FLUSH TABLES WITH READ LOCK;" &&
sleep 5 &&
touch ${WAITFORSNAPSHOT} &&
rm -f ${WAITFORLOCK} &&
while [ -e ${WAITFORSNAPSHOT} ]; do sleep 1; done &&
echo "SHOW MASTER STATUS;" &&
echo "UNLOCK TABLES;" &&
echo "quit"
) | mysql --defaults-file=/root/.my.cnf
