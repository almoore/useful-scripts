#!/bin/bash
# Written by: Alex Moore March 2015
# Description: Gathers system information for Ubuntu and CentOS machines
# Name: sys_diag.sh
# 1.1.0 formatting edits made by JS + BR

OUTPUT_FILE_NAME=Sysinfo.txt
touch ${OUTPUT_FILE_NAME}
# Information for
# Making sure they are on the correct supported Kernel, platform, etc.
# This could be all displayed by a -a for all but it would be nice to
# have it in separate lines to be a little more human readable.
echo "SYS Diagnostic Script (Build 1.1.0)" > ${OUTPUT_FILE_NAME} 2>&1;
echo "═════════════════════════════════════════════════════════════════════════════════════════════" >> ${OUTPUT_FILE_NAME}
NOW=`date +"%c %z"`
echo "Date Created: $NOW" >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;

echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
echo "System Information"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Kernel Name:        "  >> ${OUTPUT_FILE_NAME} 2>&1 
uname -s >> ${OUTPUT_FILE_NAME}  2>&1;
echo -n "Hostname:           "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -n >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Kernel Release:     "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -r >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Kernel Version:     "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -v >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Machine HW Type:    "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -m >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Processor Type:     "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -p >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Hw Platform:        "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -i >> ${OUTPUT_FILE_NAME} 2>&1;
echo -n "Operating System:   "  >> ${OUTPUT_FILE_NAME} 2>&1
uname -o >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# Mounts at the time of startup	Troubleshooting destination if the customer had
# a mounted destination but forgot to add to fstab and the server rebooted
# accidently, also checking against the db3 to make sure it’s the correct 
# destination we’re expecting 
echo "File Systems Table - fstab"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
cat /etc/fstab >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# Current mounts
# Same reason as above to see what’s currently mounted and any misconfiguration
# in regards to destination 
echo "Currently Mounted Filesystems - mount"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
mount >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# Volume Stats
# Show current volume sizes, if its running out of space, how many volumes, see
# if all volumes are included in their backup jobs, etc
echo "Volume Statistics - df"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
df >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# Storage info
# Shows what kind of storage does this machine have, we can see if we’re having
# problems with certain storage also we can try to have the customer move the
# chain to another storage device to troubleshoot if backups are failing
#####sudo lshw -class disk -class storage  >> ${OUTPUT_FILE_NAME} 2>&1
echo "Storage Devices - lsblk"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
lsblk -io KNAME,TYPE,MOUNTPOINT,SIZE,MODEL,LOG-SEC,PHY-SEC,RM,RO,OWNER,MODE,GROUP,STATE >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}


# System uptime	See how long has the system been up
echo "System Uptime"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
uptime >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# IP info
# Shows IP configuration of the machine for troubleshooting possible
# connectivity issues different lans, etc
echo "IP Information - ifconfig"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
ifconfig >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# IP info
# One of the data sources that would contribute to the IP troubleshooting
if [ -e /etc/network/interfaces ]; then
echo "Network Interface Settings - /etc/network/interfaces"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
    cat /etc/network/interfaces >> ${OUTPUT_FILE_NAME} 2>&1
else
echo "Network Interface Settings - /etc/sysconfig/network-scripts/ifcfg-*"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
    for I in `ls /etc/sysconfig/network-scripts/ifcfg-*`; do
        basename $I >> ${OUTPUT_FILE_NAME} 2>&1
        cat $I >> ${OUTPUT_FILE_NAME} 2>&1
        echo "" >> ${OUTPUT_FILE_NAME} 2>&1
    done
fi
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# DNS info
# Data source that would show us DNS info even if they are not pulling into
# their interface file above. This would be beneficial in troubleshooting
# Activations making sure we’re able to resolve our activation server. 
echo "DNS Settings - /etc/resolv.conf"  >> ${OUTPUT_FILE_NAME} 2>&1;
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
cat /etc/resolv.conf >> ${OUTPUT_FILE_NAME} 2>&1
echo "" >> ${OUTPUT_FILE_NAME} 2>&1

echo "_____________________________________________________________________________________________" >> ${OUTPUT_FILE_NAME}

# searching conflicting packages - yum - dpkg
# If someone goes to install another program with conflicting packages they can
# override warnings about conflictions and install the conflicting package
# anyways. We need to know that no conflicting packages are installed.
# By getting the list of installed packages we can check if there are known
# issues with them. 
echo "Installed Packages" >> ${OUTPUT_FILE_NAME} 2>&1
echo ""  >> ${OUTPUT_FILE_NAME} 2>&1;
which apt-get > /dev/null 2>&1
if [ $? == 0 ] ; then
    # Ubuntu: 
	dpkg -l >> ${OUTPUT_FILE_NAME} 2>&1
else
    # CentOs:
	yum list >> ${OUTPUT_FILE_NAME} 2>&1
fi
tar -czf ${OUTPUT_FILE_NAME}.tar.gz ${OUTPUT_FILE_NAME}
