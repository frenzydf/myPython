import boto3

ec2 = boto3.resource('ec2')
for i in ec2.vpc_addresses.all():
    print(i.allocation_id)
    print(i.network_interface_id)
    print(i.private_ip_address)
    print(i.public_ip)