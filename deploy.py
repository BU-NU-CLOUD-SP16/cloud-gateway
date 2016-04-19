"""
TODO:
    1. Add Change deploy_vcp.vcg -> create_vpc/vcg and dump 
       all necessary infomation to yaml file
    2. Add delete_vpc/vcg method to delete resource created by 1 for scale down
"""
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
        response = client.create_stack(StackName=stack_name, TemplateBody=template)
    except Exception as exception:
        print str(exception)
        return

    if not wait:
        return response["StackID"]

    while True:
        response = client.describe_stacks(StackName=stack_name)
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
    response = client.describe_stacks(StackName=stack_name)['Stacks'][0]
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
    response = client.delete_stack(StackName=stack_name)
    return response


def create_image(vpc_stack="vpc"):
    """
    Params:
    vpc_stack -- {string} The VPC stack where this a temprorary instance will
    be created
    ----------------------
    Outputs:
    The image id with Aws tools, StrongSwan installed and repo cloned.
    """
    vpc_desc = describe_stack(vpc_stack)["outputs"]

    # create temporary vcg 
    template = open("./StackTemplates/image.template").read()
    template = (template) % (config['KeyPair'], vpc_desc["VpcId"], 
                             vpc_desc["PublicSubnetId"],config['VcgIp'],
                             config['InstanceType'], config['ImageId'], 
                             vpc_desc["SecurityGroup"]) 
    
    # createan instance with all libs installed
    create_stack("TempStack", template)
    instance_id = describe_stack("TempStack")["outputs"]["InstanceId"]

    ###################
    # CHECK INSTANCE STATUS HERE,
    # ONLY CREATE IMAGE AFTER ALL IS OK
    ###################

    client = boto3.client('ec2')
    rsp = client.create_image(InstanceId=instance_id,
                               Name='string',
                               Description='string')

    # create an image of that instance and wait until it's available
    image_id = rsp['ImageId']
    while 1:
        rsp = client.describe_images(ImageIds=[image_id])
        if rsp['Images'][0]['State']  == 'available':
            print "Image created, delete temp instance"
            break
        print ("Image %s state:") % (image_id), rsp['Images'][0]['State'] 
        time.sleep(5)

    # delete temporary instance
    delete_stack("TempStack")

    return image_id


def delete_image(image_id):
    """
    Params:
    image_id -- {string} The AMI image-to delete
    ----------------------
    Outputs:
    True if operation success, otherwise return error message
    """
    try:
        client = boto3.client('ec2')
        rsp = client.describe_images(ImageIds=[image_id])
        snapshot_id = rsp['BlockDeviceMappings']['Ebs']['SnapshotId']

        # deregister image
        client.deregister_image(ImageId=image_id)

        # delete snapshot
        client.delete_snapshot(SnapshotId=snapshot_id)
        return True
    except Exception as e:
        return str(e)


def deploy_vpc(stack_name="vpc"):
    """
    Params:
        None
    ----------------------
    Outputs:
        vpc -- {string} ID of ceated VPC
        public_subnet -- {string} ID of ceated public subnet
        private_subnet -- {string} ID of ceated private subnet
        private_route_table -- {string} ID of ceated route table for private subnet
        image_id -- {string} The id of a configured image
    """
    # create VPC 
    print "Deploying VPC and network..."
    template = open("./StackTemplates/vpc.template").read()
    template = (template) % (config["VpcCidr"], 
                            config["PublicCidr"], 
                            config["PrivateCidr"]) 
    stack =  create_stack(stack_name, template)
    desc = describe_stack(stack_name)["outputs"]

    # Create AMI of a configured instance in that VPC 
    print "Creating pre configured image..."
    image_id = create_image(stack_name)
    print ("Image \'%s\' created") % (image_id)

    return desc["VpcId"], desc["PublicSubnetId"], \
            desc["PrivateSubnetId"], desc["PrivateRouteTableId"], image_id


def deploy_vcg(image_id, vpc_stack="vpc", stack_name="vcg"):
    """
    Params:
    vpc_stack -- {string} The stack name of VPC to where this VCG is added
    vpc_ip -- {string} The private ip address of VCG
    ----------------------
    Outputs:
    vcg_id -- {string} The id of created vcg
    eip_ip -- {string} The allocated public ip
    eip_id -- {string} The id of allocated public ip
    """
    psk = uuid.uuid4().hex

    # get id informatin from pre-create VPC stack
    vpc_desc = describe_stack(vpc_stack)["outputs"]

    # create eip
    print ("Allocating Elastic IP to %s") % (vpc_desc["VpcId"])
    ec2_client = boto3.client('ec2')
    eip_rsp = ec2_client.allocate_address(Domain='vpc')
    eip_ip = eip_rsp['PublicIp']
    eip_id = eip_rsp['AllocationId']
    print ("ElasticIP: %s, ElasticIpId: %s") % (eip_ip, eip_id)

    # Add connection in this machine and start tunnel
    # So that when IPsec is start in the remote site will have responde
    add_connection(config["HqPublicIp"], config["HqPrivateIp"], "0.0.0.0/0",
                    eip_ip, eip_ip, config["VpcCidr"], psk)
    
    # Construct template and create VCG
    template = open("./StackTemplates/vcg.template").read()
    template = (template) % (config['KeyPair'], vpc_desc["VpcId"], 
                             vpc_desc["PublicSubnetId"], config['VpcCidr'], 
                             config['VcgIp'], eip_ip, eip_id, 
                             config['HqPublicIp'], psk, 
                             config['InstanceType'], image_id, 
                             vpc_desc["SecurityGroup"])
    create_stack(stack_name, template)
    
    vcg_id = describe_stack(stack_name)["outputs"]["VcgId"]

    # Associate VCG with EIP
    rsp = ec2_client.associate_address(InstanceId=vcg_id, AllocationId=eip_id)

    # Route all traffic in private subnet to new vcg
    rsp = ec2_client.create_route( RouteTableId=vpc_desc["PrivateRouteTableId"],
                                    DestinationCidrBlock='0.0.0.0/0',
                                    InstanceId=vcg_id)

    return vcg_id, eip_ip, eip_id


def test():
    _1, _2, _3, _4, image_id = deploy_vpc()
    deploy_vcg(image)

if __name__ == "__main__":
    test()

       

