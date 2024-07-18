import boto3
from termcolor import colored

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
