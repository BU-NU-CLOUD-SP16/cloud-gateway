import yaml
import boto3
import subprocess
import uuid
import time
import os

conn_template  = """
conn %s-%s
 auto=start
 leftid=%s
 left=%s
 leftsubnet=%s
 rightid=%s
 right=%s
 rightsubnet=%s
"""
secret_template = "%s %s : PSK \\\"%s\\\"\n"

config = yaml.load(open('config.yaml').read())


def add_connection(left_id,left,left_subnet,
                    right_id,right,right_subnet,psk):
    home_path = config['IpsecConfigPath']
    new_conn = conn_template % (left_id, right_id,
                                left_id,left,left_subnet,
                                right_id,right,right_subnet)
    new_secret = secret_template % (left_id, right_id, psk)

    if not os.path.isdir(home_path):
        os.makedirs(home_path, 0777)
        open(os.path.join(home_path, "ipsec.conf"), "w").close()
        open(os.path.join(home_path, "ipsec.secrets"), "w").close()

    with open(os.path.join(home_path, "ipsec.conf"), "a") as conf_file:
        conf_file.write(new_conn)

    subprocess.call("echo "+ new_secret + " | sudo tee --append /etc/ipsec.secrets",shell=True)
    subprocess.call("./bin/ipsec_restart",shell=True)


def deploy_vcg(vpc_cidr, public_subnet, private_subnet, vcg_id, vcg_ip):
    psk = uuid.uuid4().hex

    template = open("./StackTemplates/aws.template").read()
    template = (template) % (config['KeyPair'], 
                                vpc_cidr, public_subnet, private_subnet,
                                vcg_id,  vcg_ip, config['HqPublicIp'], psk,
                                config['InstanceType'], config['ImageId']) 

    # initialize client
    client = boto3.client('cloudformation')
    response = client.create_stack( StackName = 'cloudgateway', TemplateBody = template)
    print "Creating stack, stack id:", response['StackId']

    # wait until create progress ends or interrupted
    while True:
        response = client.describe_stacks(StackName = "cloudgateway")
        status = response['Stacks'][0]['StackStatus']  
        print status
        if status != "CREATE_IN_PROGRESS":
           break
        time.sleep(5)

    # check stack create status, if success, add ipsec connecion
    response = client.describe_stacks(StackName = "cloudgateway")['Stacks'][0]
    if response['StackStatus'] == "CREATE_COMPLETE":
        vcg_public_ip = response["Outputs"][0]['OutputValue']
        add_connection(config['HqPublicIp'], config['HqPrivateIp'], "0.0.0.0/0",
                      vcg_id, vcg_public_ip, private_subnet, psk)
        return vcg_public_ip
    else:
        reason = response['StackStatusReason']  
        print "Stack Create Fail, reason:", reason
        return false

if __name__ == "__main__":
    deploy_vcg("10.1.0.0/16", "10.1.0.0/24", "10.1.1.0/24", "viginia_vcg", "10.1.0.100")
