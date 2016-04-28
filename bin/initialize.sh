#!/bin/bash

# installing cloud gateway project dependencies
echo "Installing cloud gateway project dependencies"
sudo apt-get update
sudo apt-get install -y strongswan python-pip 
sudo pip install pyyaml boto3 requests flask

# Configure netowrk setting to enable redirects
echo "Enabling packets redirection"
for path in /proc/sys/net/ipv4/conf/*;
do echo 0 > $path/accept_redirects;
echo 0 > $path/send_redirects;
done

sudo cp ./others/ipsec.conf /etc/ipsec.conf

echo net.ipv4.ip_forward = 1 >> /etc/sysctl.conf
echo net.ipv4.conf.all.accept_redirects = 0 >> /etc/sysctl.conf
echo net.ipv4.conf.all.send_redirects = 0 >> /etc/sysctl.conf
echo 1 > /proc/sys/net/ipv4/ip_forward 
sudo sysctl -p

# Install aws cli
echo "Installing AWS CLI and configur default region"
echo "This step may require you to provide Access Key and \
      Secret Access Key of your account"
sudo pip install awscli
aws configure

echo "Configuration done, please do your netowrk configuration \
       in \'config.yaml\'"


