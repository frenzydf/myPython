import boto3
from termcolor import colored

elb = boto3.client('elbv2')
print("--------------------------------------------------------------------------------------------")
print("AWS LOAD BALANCERS")
print("--------------------------------------------------------------------------------------------")
lbs = elb.describe_load_balancers()
for i in lbs['LoadBalancers']:
    alb_arn=i['LoadBalancerArn']
    print("Name: ", i['LoadBalancerName'])
    print("DNS name: ", i['DNSName'])
    print("Status: ", i['State']['Code'])
    print("Scheme: ", i['Scheme'])
    listeners = elb.describe_listeners(LoadBalancerArn=alb_arn)
    print("Listeners:")
    for port in listeners['Listeners']:
        print(port['Protocol'],":\t ", port['Port'],"\t", port['DefaultActions'][0]['Type'])
    print("--------------------------------------------------------------------------------------------")

