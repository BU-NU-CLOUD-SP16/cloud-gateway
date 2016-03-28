import yaml
import boto3
import subprocess
import uuid
import time
import os

conn_template  = 
"""
conn %s-%s
    auto=start
    leftid=%s
    left=%s
    leftsubnet=%s
    rightid=%s
    right=%s
    rightsubnet=%s
"""
secret_template = "%s %s: PSK %s\n"

def add_connection(left_id,left,left_subnet,
                    right_id,right,right_subnet,psk):

    new_conn = conn_template % (left_id, right_id,
                                left_id,left,left_subnet,
                                right_id,right,right_subnet)
    new_secret = secret_template % (left_id, right_id, psk)

    if os.path.isdir("/home/ubuntu/.ipsec"):
        os.makedirs("/home/ubuntu/.ipsec")

    with open("/home/ubuntu/.ipsec/ipsec.conf", "a") as conf_file:
        conf.write(new_conn)
    with open("/home/ubuntu/.ipsec/ipsec.secrets", "a") as secrets_file:
        secrets_file.write(new_secret) 

    subprocess.call(['./bin/ipsec_restart'])


def deploy_vcg(vpc_cidr, public_subnet, private_subnet, vcg_id, vcg_ip):
    config = yaml.load('config.yaml')
    psk = uuid.uuid4().hex

    template = open("./StackTemplate/aws.template").read()
    template = (template) % ( config['KeyPair'], 
                            vpc_cidr, public_subnet, private_subnet,
                            vcg_id,  vcg_ip, config['HqPublicIp'], psk,
                            config['InstanceType'], config['ImageId']) 

    # initialize client
    client = boto3.client('cloudformation')
    response = client.create_stack( StackName = 'cloudgateway', TemplateBody = template)
    print "Creating stack, stack id:", response

    # wait until create progress ends or interrupted
    while True:
        response = client.describe_stacks(StackName = "cloudgateway")
        status = response['Stacks'][0]['StackStatus']  
        print status
        if status != "CREATE_IN_PROGRESS":
           break
        time.sleep(5)

    # check stack create status, if success, add ipsec connecion
    response = client.describe_stacks(StackName = "cloudgateway")
    if response['Stacks'][0]['StackStatus'] == "CREATE_COMPLETE":
        vcg_public_ip = response['Stacks'][0]["Outputs"][0]['VcgPublicIp']
        add_connection(config['HqPublicIp'], config['HqPrivateIp'], "0.0.0.0/0",
                       vcg_id, vcg_public_ip, private_subnet, psk)
        return vcg_public_ip
    else:
        reason = response['Stacks'][0]['StackStatusReason']  
        print "Stack Create Fail, reason:", reason
        return false
