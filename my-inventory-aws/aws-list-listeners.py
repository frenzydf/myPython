import boto3
from termcolor import colored

elb = boto3.client('elbv2')
print("--------------------------------------------------------------------------------------------")
print("ALB\tID\t\t\tVPC")
print("--------------------------------------------------------------------------------------------")
listeners = elb.describe_listeners(LoadBalancerArn='arn:aws:elasticloadbalancing:us-east-1:123227788096:loadbalancer/net/alb-gitlab/8fcf4b9776db00d7')
for i in listeners['Listeners']:
    print(i['Port'])

print("-----------------------------------------------------------------")