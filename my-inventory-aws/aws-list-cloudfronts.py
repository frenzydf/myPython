import boto3

session = boto3.Session(profile_name='vpc1')
client = session.client('cloudfront')
def list_cloudfronts():
    print("Id,DomainName,Status,PriceClass,ViewerCertificate,WebACLId")
    try:
        paginator = client.get_paginator('list_distributions')
        for page in paginator.paginate():
            for dist in page['DistributionList']['Items']:
                dist_id = dist['Id']
                domain_name = dist['DomainName']
                status = dist['Status']
                price_class = dist['PriceClass']
                viewer_certificate = dist['ViewerCertificate']['CloudFrontDefaultCertificate'] if 'CloudFrontDefaultCertificate' in dist['ViewerCertificate'] else 'Custom'
                web_acl_id = dist.get('WebACLId', 'None')
                # alternate domain names
                if 'Aliases' in dist and 'Items' in dist['Aliases']:
                    domain_name += " (Aliases: " + ", ".join(dist['Aliases']['Items']) + ")"
                print(f"{dist_id},{domain_name},{status},{price_class},{viewer_certificate},{web_acl_id}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_cloudfronts()
