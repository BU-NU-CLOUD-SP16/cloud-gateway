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
cp conn_default_temp.conf conn_default.conf
sed 's/connection_name/$CONNECTION_NAME/' conn_default.conf
sed 's/leftid=LEFT_IP/leftid=$LEFT_IP/' conn_default.conf
sed 's/leftsubnet=LEFT_SUBNET_IP/leftsubnet=$LEFT_SUBNET_IP/' conn_default.conf
sed 's/right=RIGHT_IP/right=$RIGHT_IP/' conn_default.conf

$DIRECTORY=/etc/other_connections	
# Append include at the end of ipsec.conf
sed -i "$ a\Include \'$DIRECTORY/conn_default.conf\'" /etc/ipsec.conf
if [ ! -d "$DIRECTORY" ]; then
  # Control will enter here if $DIRECTORY doesn't exist.
  mkdir $DIRECTORY
fi
# We can even go ahead and check for duplicates here but i'm ignoring that
mv conn_default.conf $DIRECTORY

echo "Creating PSK"
cat $LEFT_IP $RIGHT_IP: PSK "$PSK" >> /etc/ipsec.secrets

echo "Enabling Previous Setting"
sysctl -p

echo "Tunnel Started"
service ipsec restart

echo "Verifying tunnel status"
ipsec verify

echo "Tunnel status"
service ipsec status