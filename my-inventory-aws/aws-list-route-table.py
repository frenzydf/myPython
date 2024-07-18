import boto3
from termcolor import colored

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