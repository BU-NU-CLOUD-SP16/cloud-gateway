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

# We can even prompt user but i don't think thats the way admins would like
# echo -n "Enter your LEFT IP and press [ENTER]: "
# read LEFT_IP
 
if [ $# -lt 5 ]; then
        echo "Usage: ./automate.sh LEFT_IP LEFT_SUBNET RIGHT_IP RIGHT_SUBNET PSK"
        exit 1
fi
# Below command is used to extract Left IP from a user's VM
# ifconfig | grep -A 1 enp0s3 | grep "inet addr:" | cut -d ":" -f2 | cut -d " " -f1
# ifconfig | grep -A 1 enp0s3 | grep "Bcast:" | cut -d ":" -f2 | cut -d " " -f1
LEFT_IP=$1
LEFT_SUBNET=$2
RIGHT_IP=$3
RIGHT_SUBNET=$4
PSK=$5
# Need to color these variables later on
echo "Your IP Address: $LEFT_IP"
echo "Your Subnet Address: $LEFT_SUBNET"
echo "Public Gateway IP Address: $RIGHT_IP"
echo "Public Gateway Subnet Address: $RIGHT_SUBNET"
echo "Pre Shared Key: $PSK"

echo "Installing openswan"
apt-get install openswan

echo "Enable Redirects"
for path in /proc/sys/net/ipv4/conf/*;
do echo 0 > $path/accept_redirects;
echo 0 > $path/send_redirects;
done

echo "Configuring Sysctl"
echo net.ipv4.ip_forward = 1 >> /etc/sysctl.conf
echo net.ipv4.conf.all.accept_redirects = 0 >> /etc/sysctl.conf
echo net.ipv4.conf.all.send_redirects = 0 >> /etc/sysctl.conf
echo 1 > /proc/sys/net/ipv4/ip_forward 

echo "Configuring ipsec"
# sed 's/^#.*id$/leftid=$LEFT_IP/' /etc/ipsec.conf


echo "Creating PSK"
cat $LEFT_IP $RIGHT_IP: PSK "cloud-gateway" >> /etc/ipsec.secrets

echo "Tunnel Started"
service ipsec restart

echo "Verifying tunnel status"
ipsec verify

echo "Tunnel status"
service ipsec status
