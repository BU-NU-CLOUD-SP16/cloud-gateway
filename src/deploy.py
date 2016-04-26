import yaml
import boto3
import subprocess
import uuid
import time
import os
import json

# CONSTANTS 
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

config = yaml.load(open('../config/config.yaml').read())

stack_info_path = "../others/stacks_info/"

def dump_stack(stack_name, desc):
    path = os.path.join(stack_info_path, stack_name)
    if not os.path.isdir(stack_info_path):
        os.makedirs(stack_info_path)
    with open(path, "w") as dump_file:
        dump_file.write(yaml.dump(desc))

def load_stack(stack_name):
    path = os.path.join(stack_info_path, stack_name)
    return yaml.load(open(path, 'r').read())

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
    subprocess.call("../bin/ipsec_restart",shell=True)


def del_connecion(left, right):
    """
    Todo:
    Better file sturctur to enable clean remove connection configuration
    """
    return


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
    return {"Status":response['StackStatus'], "Outputs" : outputs }


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
    ec2_client = boto3.client('ec2')
    vpc_desc = describe_stack(vpc_stack)["Outputs"]

    # create temporary vcg 
    template = open("../StackTemplates/image.template").read()
    template = (template) % (config['KeyPair'], vpc_desc["VpcId"], 
                             vpc_desc["PublicSubnetId"],config['VcgIp'],
                             config['InstanceType'], config['ImageId'], 
                             vpc_desc["SecurityGroup"]) 
    
    # createan instance with all libs installed
    create_stack("TempStack", template)
    instance_id = describe_stack("TempStack")["Outputs"]["InstanceId"]

    # wait until this instance is fully initialized
    while 1:
        rsp = ec2_client.describe_instance_status(InstanceIds=[instance_id])
        rsp = rsp["InstanceStatuses"][0]
        print rsp
        if rsp["InstanceStatus"]["Status"] == "ok" and \
            rsp["SystemStatus"]["Status"] == "ok":
            print "Instace Initialized."
            break
        time.sleep(5)

    print "Start creating AMI image..."
    rsp = ec2_client.create_image(InstanceId=instance_id,
                               Name='string',
                               Description='string')

    # create an image of that instance and wait until it's available
    image_id = rsp['ImageId']
    while 1:
        rsp = ec2_client.describe_images(ImageIds=[image_id])
        if rsp['Images'][0]['State']  == 'available':
            break
        print ("Image %s state:") % (image_id), rsp['Images'][0]['State'] 
        time.sleep(10)

    # delete temporary instance
    print "Image created, delete temp instance."
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
    client = boto3.client('ec2')
    rsp = client.describe_images(ImageIds=[image_id])
    snapshot_id = rsp['Images'][0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
    # deregister image
    client.deregister_image(ImageId=image_id)

    # delete snapshot
    client.delete_snapshot(SnapshotId=snapshot_id)
    return True


def deploy_vpc(stack_name="vpc"):
    """
    Params:
        None
    ----------------------
    Outputs:
        desc -- {dict} A dictionary contains the output of vpc description
        and the image of preconfigured image, contains following info
           * vpc: ID of ceated VPC
           * public_subnet: ID of ceated public subnet
           * private_subnet: ID of ceated private subnet
           * private_route_table: ID of ceated route table for private subnet
           * ImageId: The id of a configured image
    """
    # create VPC 
    print "Deploying VPC and network..."
    template = open("../StackTemplates/vpc.template").read()
    template = (template) % (config["VpcCidr"], 
                            config["PublicCidr"], 
                            config["PrivateCidr"]) 
    stack =  create_stack(stack_name, template)
    desc = describe_stack(stack_name)["Outputs"]

    # Create AMI of a configured instance in that VPC 
    print "Creating pre configured image..."
    image_id = create_image(stack_name)
    print ("Image \'%s\' created") % (image_id)

    # store vpc information into temp file
    desc["ImageId"] = image_id
    dump_stack(stack_name, desc)

    return desc


def delete_vpc(stack_name="vpc"):
    delete_stack(stack_name)
    delete_image(load_stack(stack_name)["ImageId"])


def deploy_vcg(vpc_stack="vpc", stack_name="vcg"):
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
    #vpc_desc = describe_stack(vpc_stack)["Outputs"]
    vpc_desc = load_stack(vpc_stack)
    
    # create eip
    print ("Allocating Elastic IP to %s") % (vpc_desc["VpcId"])
    ec2_client = boto3.client('ec2')
    eip_rsp = ec2_client.allocate_address(Domain='vpc')
    eip_ip = eip_rsp['PublicIp']
    eip_id = eip_rsp['AllocationId']
    print ("ElasticIP: %s, ElasticIpId: %s") % (eip_ip, eip_id)

    # Add connection in this machine and start tunnel
    # So that when IPsec is start in the remote site will have responde
    add_connection(config["HqPublicIp"], config["HqPrivateIp"],"0.0.0.0/0",
                    eip_ip, eip_ip, config["VpcCidr"], psk)
    
    # Construct template and create VCG
    template = open("../StackTemplates/vcg.template").read()
    template = (template) % (config['KeyPair'], vpc_desc["VpcId"], 
                             vpc_desc["PublicSubnetId"], config['VpcCidr'], 
                             config['VcgIp'], eip_ip, eip_id, 
                             config['HqPublicIp'], psk, 
                             config['InstanceType'], vpc_desc["ImageId"], 
                             vpc_desc["SecurityGroup"])
    create_stack(stack_name, template)
    
    vcg_id = describe_stack(stack_name)["Outputs"]["VcgId"]

    # Associate VCG with EIP
    ec2_client.associate_address(InstanceId=vcg_id, AllocationId=eip_id)

    # Route all traffic in private subnet to new vcg
    ec2_client.create_route(RouteTableId=vpc_desc["PrivateRouteTableId"],
                            DestinationCidrBlock='0.0.0.0/0',
                            InstanceId=vcg_id)

    desc = {"ElasticIp": eip_ip,
            "ElasticIpId": eip_id,
            "PrivateRouteTableId": vpc_desc["PrivateRouteTableId"],
            "VcgId": vcg_id}

    # Store info of VCG related resources into yaml
    dump_stack(stack_name, desc)

    return desc


def delete_vcg(stack_name="vcg"):
    # delete instance
    ec2_client = boto3.client("ec2")

    # disassociate elastic ip, delete elastic ip and private route
    desc = load_stack(stack_name)
    ec2_client.disassociate_address(PublicIp=desc["ElasticIp"])

    ec2_client.delete_route(RouteTableId=desc["PrivateRouteTableId"],
                            DestinationCidrBlock="0.0.0.0/0")

    ec2_client.release_address(AllocationId=desc["ElasticIpId"])

    # delete VCG stack
    delete_stack(stack_name)


def test():
#    deploy_vpc()
    deploy_vcg()
#    delete_vcg()
 #   delete_vpc()

if __name__ == "__main__":
    test()

       

