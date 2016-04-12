#Cloud Gateway

###Group Members
___
##### Mania Abdi
##### Rahul Bahal
##### Qianli Ma
##### Ayush Singh

###Description
***
Provisioning on-premise compute resources for peak workloads can be cost prohibitive. Therefore, enterprises provision sufficient compute resources in their private cloud for the anticipated average workload. In contrast, the public cloud does not require significant initial capital expenditures, as resources are served on-demand and customers only pay for the resources they consume. Thus, the hybrid cloud model may be employed as a cost-effective method of scaling resources to peak demand. The average-sized workload stays in the private cloud, and peak workload is provisioned in the public cloud.

You are the administrator of an OpenStack private cloud, and your goal is to allow your application team to seamlessly scale their applications for peak demand via a burst to the public cloud. A Cloud Gateway (CG) virtual machine runs on an OpenStack (or any) network to expand the local resource via an AWS Virtual Private Cloud (VPC). Machines will utilize the CG to send traffic between the private and public cloud subnets.

***
###Key Features

1. One Virtual Private Cloud(VPC) is assumed to be already set up on the Private Side.
2. Public VPC is set up using CloudFormation Template.
3. With the help of the user interface, the admin can take care of DNAT, enable/disable internet for the public side worker machines and modify port forwarding tables to make sure IP tables on both sides are consistent.
4. The user interface console is written in Flask(Python) as backend and Sqlite3 database engine.

