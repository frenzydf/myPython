import boto3
import csv

def get_lb_waf_report():
    # Inicializamos los clientes de AWS
    elbv2 = boto3.client('elbv2')
    wafv2 = boto3.client('wafv2')
    
    results = []
    
    print("Iniciando auditoría de balanceadores...")

    # 1. Obtener todos los balanceadores de carga v2 (ALB/NLB)
    paginator = elbv2.get_paginator('describe_load_balancers')
    for page in paginator.paginate():
        for lb in page['LoadBalancers']:
            # Filtrar solo los que están expuestos a internet
            if lb['Scheme'] == 'internet-facing':
                lb_arn = lb['LoadBalancerArn']
                lb_name = lb['LoadBalancerName']
                lb_dns = lb['DNSName']
                waf_name = "N/A"

                try:
                    # 2. Intentar obtener el WAF asociado a ese ARN
                    response = wafv2.get_web_acl_for_resource(ResourceArn=lb_arn)
                    if 'WebACL' in response:
                        waf_name = response['WebACL']['Name']
                except wafv2.exceptions.WAFNonexistentItemException:
                    waf_name = "Sin WAF"
                except Exception as e:
                    waf_name = f"Error: {str(e)}"

                results.append({
                    'Nombre': lb_name,
                    'DNS': lb_dns,
                    'Esquema': lb['Scheme'],
                    'WAF_Asociado': waf_name
                })

    # 3. Exportar a CSV
    keys = results[0].keys() if results else []
    with open('reporte_seguridad_lb.csv', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)

    print(f"Reporte generado con éxito: {len(results)} balanceadores encontrados.")

if __name__ == "__main__":
    get_lb_waf_report()