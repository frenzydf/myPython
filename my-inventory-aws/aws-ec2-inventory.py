import boto3
#import csv
from termcolor import colored

#ec2_client = boto3.client('ec2')
collect_all_regions=[]
#for each_region in ec2_client.describe_regions()['Regions']:
#    collect_all_regions.append(each_region['RegionName'])
collect_all_regions.append('us-east-1')
#collect_all_regions.append('us-west-2')

#fo=open('Nameless_ec2_inventory_new.csv','w',newline='')
#data_obj=csv.writer(fo)
#data_obj.writerow(['EC2no','PrivateIP','PublicIP','InstanceId','State','SecurityGroup','VPC','InstanceType','OS'])

for each_region in collect_all_regions:
    count=0
    ec2 = boto3.resource('ec2',region_name=each_region)
    print('Region: ',each_region)
    print("--------------------------------------------------------------------------------------------")
    print("EC2no\tPrivateIP\tPublicIP\tInstanceId\t     State\t    SecurityGroup\t\tVPC\t\t\t  InstanceType\t  OS")
    print("--------------------------------------------------------------------------------------------")
    for i in ec2.instances.all():
        count+=1
        if i.public_ip_address == None:
            public_ip = 'No Ip Assigned'
        else:
            public_ip = i.public_ip_address
        if i.platform == None:
            ec2_os = 'Linux/UNIX'
        else:
            ec2_os = i.platform
        if i.state['Name'] == 'terminated':
            sg_id = 'No SecurityG Assigned'
        else:
            sg_id = i.security_groups[0]['GroupId']
        if i.private_ip_address == None:
            private_ip = 'No Ip Assigned'
        else:
            private_ip = i.private_ip_address
        print("{}\t{}\t{}\t{}  {}  {}\t{}{}{}  {}".format(
            colored(count, 'cyan'),
            colored(private_ip, 'green'),
            colored(public_ip, 'green'),
            colored(i.id, 'cyan'),
            colored(i.state['Name'], 'red').ljust(22),
            colored(sg_id, 'cyan').ljust(20),
            colored(i.vpc_id, 'cyan').ljust(35),
            colored(i.instance_type, 'red').ljust(25),
            colored(ec2_os, 'cyan'),
            colored(i.subnet_id,'cyan')
        ))
        #data_obj.writerow([
            #count,
            #i.private_ip_address,
            #public_ip,
            #i.id,
            #i.state['Name'],
            #i.security_groups[0]['GroupId'],
            #i.vpc_id,
            #i.instance_type,
            #ec2_os,
        #])
    count=0
    ec2 = boto3.resource('ec2',region_name=each_region)
    print("--------------------------------------------------------------------------------------------")
    print("EIPno\tPrivateIP\tPublicIP\tAllocationId\t\t\tNetworkInterfaceId")
    print("--------------------------------------------------------------------------------------------")
    for i in ec2.vpc_addresses.all():
        count+=1
        if i.private_ip_address == None:
            private_ip = 'No Ip Assigned'
        else:
            private_ip = i.private_ip_address
        print("{0}\t{1}\t{2}\t{3}\t{4}".format(
            colored(count, 'cyan'),
            colored(private_ip, 'green'),
            colored(i.public_ip, 'green'),
            colored(i.allocation_id, 'cyan'),
            colored(i.network_interface_id, 'red')
        ))
    count=0
    s3 = boto3.client('s3',region_name=each_region)
    response = s3.list_buckets()
    print("--------------------------------------------------------------------------------------------")
    print("S3-no\tName\t\t\t\t\t\t\tCreated")
    print("--------------------------------------------------------------------------------------------")
    for bucket in response['Buckets']:
        count+=1
        print("{}\t{}\t{}".format(
            colored(count, 'cyan'),
            colored(bucket["Name"],'green').ljust(50),
            colored(bucket["CreationDate"],'red')
        ))
    count=0
    ec2 = boto3.client('ec2',region_name=each_region)
    print("--------------------------------------------------------------------------------------------")
    print("Subnet\tCIDR\t\tSubnetId\t\t State\t\tVPC")
    print("--------------------------------------------------------------------------------------------")
    subnets = ec2.describe_subnets()
    for i in subnets['Subnets']:
        count+=1
        print("{}\t{}\t{} {}\t{}".format(
            colored(count, 'cyan'),
            colored(i['CidrBlock'], 'green'),
            colored(i['SubnetId'], 'cyan'),
            colored(i['State'], 'red'),
            colored(i['VpcId'], 'cyan')
        ))
    count=0
    ec2 = boto3.client('ec2')
    print("--------------------------------------------------------------------------------------------")
    print("Route Table\tID\t\t\tVPC")
    print("--------------------------------------------------------------------------------------------")
    routes = ec2.describe_route_tables()
    for i in routes['RouteTables']:
        count+=1
        print("{}\t{}\t{}".format(
            colored(count, 'cyan'),
            colored(i['RouteTableId'], 'green'),
            colored(i['VpcId'], 'red'),
        ))
        for route_subnets in i['Routes']:
            if 'GatewayId' in route_subnets:
                target=route_subnets['GatewayId']
            elif 'TransitGatewayId' in route_subnets:
                target=route_subnets['TransitGatewayId']
            elif 'NatGatewayId' in route_subnets:
                target=route_subnets['NatGatewayId']
            elif 'NetworkInterfaceId' in route_subnets:
                target=route_subnets['NetworkInterfaceId']
            elif 'VpcPeeringConnectionId' in route_subnets:
                target=route_subnets['VpcPeeringConnectionId']
            elif 'DestinationPrefixListId' in route_subnets:
                target=route_subnets['DestinationPrefixListId']
            else:
                target="Other Element"
            if 'DestinationCidrBlock' in route_subnets:
                cidrblock=route_subnets['DestinationCidrBlock']
            elif 'DestinationPrefixListId' in route_subnets:
                target=route_subnets['DestinationPrefixListId']
            else:
                cidrblock="Other element"
            print("\t {}   {}\t{}".format(
                colored(cidrblock, 'cyan').ljust(30),
                colored(target, 'cyan').ljust(30),
                colored(route_subnets['State'], 'cyan')
            ))
        print("-----------------------------------------------------------------")
    count=0
    ec2 = boto3.client('ec2')
    print("--------------------------------------------------------------------------------------------")
    print("Transit Gateway\tID\t\t\tStatus")
    print("--------------------------------------------------------------------------------------------")
    twg = ec2.describe_transit_gateways()
    for i in twg['TransitGateways']:
        count+=1
        print("{}\t{}\t{}".format(
                colored(count, 'cyan'),
                colored(i['TransitGatewayId'], 'green'),
                colored(i['State'], 'red')
            ))