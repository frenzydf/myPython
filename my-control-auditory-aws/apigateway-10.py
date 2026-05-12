import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
profile = "vpc2"
session = boto3.Session(profile_name=profile)
client = session.client("apigatewayv2", region_name=REGION) 

def list_apis():
    paginator = client.get_paginator("get_apis")
    apis = []

    for page in paginator.paginate():
        apis.extend(page.get("Items", []))

    return apis


def list_integrations(api_id):
    return client.get_integrations(ApiId=api_id).get("Items", [])


def main():
    apis = list_apis()

    total_apis = len(apis)
    compliant_apis = 0
    non_compliant_apis = 0
    non_compliant_integrations = 0

    print("\nAPIs NO CONFORMES – Control APIGateway.10")
    print("=" * 80)

    for api in apis:
        api_id = api["ApiId"]
        api_non_compliant = False

        try:
            integrations = list_integrations(api_id)

            for integ in integrations:
                if integ.get("ConnectionType") == "VPC_LINK" and not integ.get("TlsConfig"):
                    if not api_non_compliant:
                        non_compliant_apis += 1
                        api_non_compliant = True

                    non_compliant_integrations += 1

                    print(f"❌ API ID        : {api_id}")
                    print(f"   Name          : {api.get('Name')}")
                    print(f"   Protocol      : {api.get('ProtocolType')}")
                    print(f"   IntegrationId : {integ.get('IntegrationId')}")
                    print(f"   Type          : {integ.get('IntegrationType')}")
                    print(f"   URI           : {integ.get('IntegrationUri')}")
                    print(f"   Connection    : {integ.get('ConnectionType')}")
                    print(f"   TLS Config    : {integ.get('TlsConfig')}")
                    print("   Finding       : APIGateway.10 (FAILED)")
                    print("-" * 80)

            if not api_non_compliant:
                compliant_apis += 1

        except ClientError as e:
            print(f"Error consultando API {api_id}: {e}")

    print("\nRESUMEN FINAL")
    print("=" * 80)
    print(f"Total de APIs evaluadas      : {total_apis}")
    print(f"APIs conformes               : {compliant_apis}")
    print(f"APIs NO conformes            : {non_compliant_apis}")
    print(f"Integraciones NO conformes   : {non_compliant_integrations}")
    print("=" * 80)


if __name__ == "__main__":
    main()