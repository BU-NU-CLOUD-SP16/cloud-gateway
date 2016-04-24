#!/bin/bash
clear
# echo "Hello $USER"
# echo
# echo "Today's date is `date`, this is week `date +"%V"`."
# echo
# echo "These users are currently connected:"
# w | cut -d " " -f 1 - | grep -v USER | sort -u
# echo
# echo "This is `uname -s` running on a `uname -m` processor."
# echo
# echo "This is the uptime information:"
# uptime
# echo
echo "This script is provided by cloud-gateway team to configure your network for scaling to public clouds on peak workloads.  Automation starts now."

# Q. Will I be needing any information from the user or from the user's environment?
# A. 5 : left IP,subnet and right IP,subnet and PSK

# Q. How will I store that information?
# A. Variables

# Q. Are there any files that need to be created? Where and with which permissions and ownerships?
# A. Everything here needs sudo priveledges 

# Q. What commands will I use? When using the script on different systems, do all these systems have these commands in the required versions?
# A. https://github.com/BU-NU-CLOUD-SP16/cloud-gateway/issues/2#issuecomment-186081235

# Q. Does the user need any notifications? When and why?
# A. - Success on openswan install
#    - Enabled Redirects
#    - Sysctl configured
#    - ipsec configured
#    - Pre Shared Key created as "cloud-gateway"
#    - Tunnel Started
#    - Verifying tunnel status

# Q. Dividing into multiple suites?
# A. • add-connection <connection_name > <right_public_IP> <PSK>
#    • delete-connection <connection_name>
#    • connection-on <connection_name>
#    • connection-off <connection_name>
#    • add-left-subnet <CIDR1> <CIDR2> …
#    • add-right-subnet <CIDR1> <CIDR2> …
#    • enable-internet
#    • disable-internet

# We can even prompt user but i don't think thats the way admins would like
# echo -n "Enter your LEFT IP and press [ENTER]: "
# read LEFT_IP
 
if [ $# -lt 5 ]; then
        echo "Usage: ./automate.sh COMND_NAME CONNECTION_NAME RIGHT_IP PSK"
        exit 1
fi
# Below command is used to extract Left IP from a user's VM
LEFT_IP=`ifconfig | grep -A 1 enp0s3 | grep "inet addr:" | cut -d ":" -f2 | cut -d " " -f1`
LEFT_SUBNET_IP=`ifconfig | grep -A 1 enp0s3 | grep "Bcast:" | cut -d ":" -f2 | cut -d " " -f1`
COMND_NAME=$1
CONN_NAME=$2
RIGHT_IP=$3	
PSK=$4

# Need to color these variables later on
echo "Your IP Address: $LEFT_IP"
echo "Your Subnet Address: $LEFT_SUBNET_IP"
echo "New Connection Name: $CONN_NAME"
echo "Public Gateway IP Address: $RIGHT_IP"
# echo "Pre Shared Key: $PSK" This cannot be printed, its a secret

if [ $(dpkg-query -W -f='${Status}' openswan 2>/dev/null | grep -c "ok installed") -eq 0 ];
then
	echo "openswan not installed!"
	echo "Installing openswan.."
	apt-get install openswan
fi

switch '$COMND_NAME' in 
	'add-connection')
		./add-con.sh $CONNECTION_NAME $LEFT_IP $LEFT_SUBNET_IP $RIGHT_IP $PSK
		;;
	'delete-connection')
		;;
	'connection-on')
		ipsec --auto up $CONN_NAME
		;;
	'connection-off')
		ipsec --auto down $CONN_NAME
		;;
esac		
