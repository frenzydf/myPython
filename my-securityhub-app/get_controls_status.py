import json
import re


def main(securityhub, standard_enable_list, account_name):
    controls_status = {} #Diccionario para procesar Controles
    paginator_controls = securityhub.get_paginator('describe_standards_controls')
    print("-" * 50)
    for standard_arn in standard_enable_list:
        count_enabled = 0
        count_disabled = 0
        for controls_page in paginator_controls.paginate(StandardsSubscriptionArn=standard_arn):
            for control in controls_page['Controls']:
                title = control.get('Title', 'N/A')
                status = control.get('ControlStatus', 'N/A')
                severity = control.get('SeverityRating')
                remediation = control.get('RemediationUrl', 'N/A')
                identificador = remediation.split('/')[-2]
                controls_status[identificador] = {"title": title,"status": status, "Severity":severity, "standard": standard_arn}
                if status == "ENABLED": count_enabled += 1
                elif status == "DISABLED": count_disabled += 1
            standard_name = re.search(r'subscription/(.*)', standard_arn).group(1)
        print(f"Estándar: {standard_name}")
        print(f"Enabled: {count_enabled} Disabled: {count_disabled} Total: {count_enabled+count_disabled}")
    print(f"Se encontraron {len(controls_status)} Controles Totales")
    print("-" * 50)
    controls_status_dict = {"Controls":controls_status}
    filename = f"control_status_{account_name}.json"
    with open(filename, 'w', encoding='utf-8') as archivo:
        json.dump(controls_status_dict, archivo, indent=4)
    return controls_status_dict

