import yaml
import boto3
import subprocess
import uuid
import time
import os
import json

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
secret_template = "%s %s : PSK \\\"%s\\\" \\\n"

config = yaml.load(open('config.yaml').read())

def get_ubuntu_amiid():
    """
    Return the Ubuntu AMI ID in the default Region in HVM virtualization
    """
    cmd = "aws ec2 describe-images " \
          +"--filters \"Name=name,Values=ubuntu\"" \
          +" \"Name=virtualization-type,Values=hvm\"" \
          +" --query \'Images[*].{ID:ImageId}\'"

    json_str = subprocess.check_output(cmd,shell=True)
    return json.loads(json_str)[0]["ID"]


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
    
    subprocess.call("echo " + new_secret 
                    + " | sudo tee --append /etc/ipsec.secrets",shell=True)
    subprocess.call("./bin/ipsec_restart",shell=True)

def create_stack(stack_name, template, wait = True):
    """
    Params:
    stack_name -- {string} The name of stack to create
    template -- {string} The content of template
    wait -- {boolean} If true, the program will not return until the stack is
        successfully created.
    ----------------------
    Outpurs:
    StackID if create successfully 
    Otherwise raise an exception with failure reason
    """
    client = boto3.client('cloudformation')
    try:
        response = client.create_stack(StackName = stack_name, TemplateBody = template)
    except Exception as exception:
        print str(exception)
        return

    if not wait:
        return response["StackID"]

    while True:
        response = client.describe_stacks(StackName = stack_name)
        status = response['Stacks'][0]['StackStatus']  
        print status
        if status != "CREATE_IN_PROGRESS":
           break
        time.sleep(5)
    return response["Stacks"][0]["StackId"]

def describe_stack(stack_name):
    """
    Params:
    stack_name -- {string} the name of stack to describe
    ----------------------
    Outpurs:
    A dictionary with a "status" key indicate stack status and "outputs" key
    mapped to hash that store stack description output value
    """
    client = boto3.client('cloudformation')
    response = client.describe_stacks(StackName = stack_name)['Stacks'][0]
    outputs = {}
    for output in response["Outputs"]:
        outputs[output["OutputKey"]] = output["OutputValue"]
    return {"status":response['StackStatus'], "outputs" : outputs }

def delete_stack(stack_name):
    """
    Params:
    stack_name -- {string} the name of stack to delete
    ----------------------
    Outpurs:
    The original response from boto3 API
    """
    client = boto3.client('cloudformation')
    response = client.delete_stack(StackName = stack_name)
    return response

def deploy_vpc(stack_name = "vpc"):
    """
    Params:
        None
    ----------------------
    Outputs:
    vpc -- {string} ID of ceated VPC
    public_subnet -- {string} ID of ceated public subnet
    private_subnet -- {string} ID of ceated private subnet
    private_route_table -- {string} ID of ceated route table for private subnet
    """
    # create VPC 
    template = open("./StackTemplates/vpc.template").read()
    template = (template) % (config["VpcCidr"], 
                            config["PublicCidr"], 
                            config["PrivateCidr"]) 
    
    stack =  create_stack(stack_name, template)
    desc = describe_stack(stack_name)["outputs"]

    return desc["VpcId"], desc["PublicSubnetId"], \
            desc["PrivateSubnetId"], desc["PrivateRouteTableId"]

def deploy_vcg(vcg_ip, vpc_stack = "vpc", stack_name = "vcg"):
    """
    Params:
    vpc_stack -- {string} The stack name of VPC to where this VCG is added
    vpc_ip -- {string} The private ip address of VCG
    ----------------------
    Outputs:
    vcg_id -- {string} The id of created vcg
    """
    psk = uuid.uuid4().hex

    # get id informatin from pre-create VPC stack
    print "Allocating Elastic IP"
    vpc_desc = describe_stack(vpc_stack)["outputs"]
    print vpc_desc["VpcId"]

    # create eip
    template = open("./StackTemplates/eip.template").read()
    template = (template) % (vpc_desc["VpcId"]) 

    create_stack("eip", template)

    desc = describe_stack("eip")["outputs"]
    eip_ip, eip_id = desc["EipIp"], desc["EipId"]

    # Add connection in this machine and start tunnel
    # So that when IPsec is start in the remote site will have responde
    add_connection(config["HqPublicIp"], config["HqPrivateIp"], "0.0.0.0/0",
                    eip_ip, eip_ip, config["VpcCidr"], psk)
    
    # create vcg 
    vpc_desc = describe_stack(vpc_stack)["outputs"]
    template = open("./StackTemplates/vcg.template").read()
    template = (template) % (config['KeyPair'], vpc_desc["VpcId"], vpc_desc["PublicSubnetId"],
                            config['VpcCidr'], vpc_desc["PrivateRouteTableId"], 
                             vcg_ip, eip_ip, eip_id, config['HqPublicIp'], 
                             psk, config['InstanceType'], config['ImageId'], vpc_desc["SecurityGroup"])

    create_stack(stack_name, template)

    return describe_stack("vcg")["outputs"]["VcgId"]

def test():
    #deploy_vpc()
    deploy_vcg(config['VcgIp'])
#    delete_stack('eip')

 #   delete_stack('vpc')
#    delete_stack('vcg')

if __name__ == "__main__":
    test()

