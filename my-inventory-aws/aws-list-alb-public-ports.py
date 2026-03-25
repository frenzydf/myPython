import boto3
import os

accounts = ['vpc1', 'vpc2']
print("AccountId,LoadBalancerName,DNSName,Status,Scheme,ListenerProtocol/Port/ActionType,Entorno,Grupo")
for account in accounts:
    session = boto3.Session(profile_name=account)
    elb = session.client('elbv2')
    if account == 'vpc1': account_id = os.getenv('AccountId_1')
    else: account_id = os.getenv('AccountId_2')
    lbs = elb.describe_load_balancers()
    for i in lbs['LoadBalancers']:
        alb_arn=i['LoadBalancerArn']
        listeners = elb.describe_listeners(LoadBalancerArn=alb_arn)
        #obtener Tags 'Entorno' y 'Grupo'
        tags = elb.describe_tags(ResourceArns=[alb_arn])
        entorno = None
        grupo = None
        for tag in tags['TagDescriptions'][0]['Tags']:
            if tag['Key'] == 'Entorno':
                entorno = tag['Value']
            elif tag['Key'] == 'Grupo':
                grupo = tag['Value']
        for port in listeners['Listeners']:
            if i['Scheme'] == 'internet-facing' and (port['Port'] == 80 or port['Port'] == 443):
                print(account_id,",",i['LoadBalancerName'],",",i['DNSName'],",",i['State']['Code'],",",i['Scheme'],",",port['Protocol'],"/", port['Port'],"/", port['DefaultActions'][0]['Type'],",", entorno,",", grupo)

