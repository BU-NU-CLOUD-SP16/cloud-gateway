#Possible technical solution for CloudGateway

	After spending an afterternoon doing research, I think I have possible technical solution for CloudGateway. And here's my ideas and some materials(those hyper links) that may help.

----------------

###Solution: site-to-site VPN(tunnel mode)
Essentially what we are making is a VPN server, used to connect subnets in different clouds. According to [WikiPedia](https://en.wikipedia.org/wiki/Virtual_private_network), this is a [site-to-site VPN](VPN https://www.youtube.com/watch?v=CuxyZiSCSfc). More specifically, a site-to-site VPN running on [tunnel mode](http://www.firewall.cx/networking-topics/protocols/870-ipsec-modes.html). 

-----------------

###Implementation: iptables and XxxxSwan
Since the goal is clear, a simple research led to solution: [how to implement site-to-site vpn](http://xmodulo.com/create-site-to-site-ipsec-vpn-tunnel-openswan-linux.html). This article introduce people how to set up a VPN server using iptables and OpenSwan. Basically, OpenSwan provides a mature IPsec VPN technique, we only need to set up some configuration. And in iptables we will need to add some firewall rules to enable NAT and disable some other network traffic.

------------------

###Tools:

####iptables
Some document from redhat may help you understand how iptable works:

* [Red Hat Enterprise Linux 3, Chapter17: iptabls](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/3/html/Reference_Guide/ch-iptables.html)
*  [Red Har Customer protal, Chapter7: firewalls](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/4/html/Security_Guide/ch-fw.html#s2-firewall-ipt-background)
* [another document talking about IP masqurate and NAT](http://www.oreilly.com/openbook/linag2/book/ch11.html)

#### IPsec:

I think the article about [tunnel mode](http://www.firewall.cx/networking-topics/protocols/870-ipsec-modes.html) will give you a bref understanding about IPsec. Currently, there's two libraies provide IPsec funtionality: [OpenSwan](https://www.openswan.org/) and [StrongSwan](https://www.strongswan.org/). While StrongSwan seems to provide better documentation, OpenSwan  does have an example about [how to setup OpenSwan on EC2 instances](https://github.com/xelerance/Openswan/wiki/Amazon-ec2-example), which might be useful.

---------------

###My ideas:

1. While this seems to be feasible, I am not sure we can do use this as out first demo. Maybe we can just create a point-to-point VPN as our first demo
2. Some of the implementation will require root privileges. I am not sure whether all cloud would support such operation.(MOC does not)
3. If we can make this work early, we ca focus on configuration or automation part, which will be more useful for production use. 




