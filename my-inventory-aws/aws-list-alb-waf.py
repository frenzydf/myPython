import boto3
import json

def get_lb_waf_report():
    # Inicializamos los cliente de AWS con profile vpc1
    session = boto3.Session(profile_name='vpc1')
    waf = session.client('wafv2')
    web_acls = waf.list_web_acls(Scope='REGIONAL')
    
    waf_dict = {}
    for acl in web_acls['WebACLs']:
        waf_dict[acl['Name']] = acl['ARN']
        #print(f"Web ACL Name: {acl['Name']}, ARN: {acl['ARN']}")
    
    # Listamos recursos agrupados por web ACL
    resources_by_acl = {}
    for acl_name, acl_arn in waf_dict.items():
        resources = waf.list_resources_for_web_acl(WebACLArn=acl_arn, ResourceType='APPLICATION_LOAD_BALANCER')
        resources_by_acl[acl_name] = resources.get('ResourceArns', [])
        #print(f"Resources for Web ACL {acl_name}: {resources.get('ResourceArns', [])}")
    # Imprimimos el reporte
    print("--------------------------------------------------------------------------------------------")
    print("AWS LOAD BALANCER WAF REPORT")
    print("--------------------------------------------------------------------------------------------")
    for acl_name, resource_arns in resources_by_acl.items():
        print(f"WAF Web ACL: {acl_name}")
        if resource_arns:
            for arn in resource_arns:
                print(f"\tAssociated ALB ARN: {arn}")
        else:
            print("\tNo associated ALBs found.")
        print("--------------------------------------------------------------------------------------------")

if __name__ == "__main__":
    get_lb_waf_report()