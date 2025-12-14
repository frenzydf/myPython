import json
import re


def main(securityhub, standard_enable_list):
    controls_status = {} #Diccionario para procesar Controles
    controls_status_dict = {"General":{},"StandardsEnabled":{},"Controls":{}} #Diccionario General
    paginator_controls = securityhub.get_paginator('describe_standards_controls')
    print("-" * 50)
    for standard_arn in standard_enable_list:
        count_enabled = 0; count_disabled = 0
        for controls_page in paginator_controls.paginate(StandardsSubscriptionArn=standard_arn):
            for control in controls_page['Controls']:
                title = control.get('Title', 'N/A')
                status = control.get('ControlStatus', 'N/A')
                severity = control.get('SeverityRating')
                remediation = control.get('RemediationUrl', 'N/A')
                identificador = remediation.split('/')[-2]
                controls_status[identificador] = {"title": title,"status": status, "severity":severity, "standard": standard_arn}
                if status == "ENABLED": count_enabled += 1
                elif status == "DISABLED": count_disabled += 1
            search_standard_name = re.search(r'subscription/(.*)', standard_arn)
            if search_standard_name: standard_name = search_standard_name.group(1)
            else: standard_name = 'None'
        print(f"Estándar: {standard_name}")
        print(f"Enabled: {count_enabled} Disabled: {count_disabled} Total: {count_enabled+count_disabled}")
        standard_data = {"Enabled": count_enabled, "Disabled": count_disabled, "Total": count_enabled+count_disabled}
        controls_status_dict['StandardsEnabled'][standard_name]=standard_data 
    print(f"Se encontraron {len(controls_status)} Controles Totales")
    print("-" * 50)
    controls_status_dict['Controls'] = controls_status
    total_enabled=0; total_disabled=0; total_nodata=0
    for control, control_data in controls_status_dict['Controls'].items():
        if control_data.get("status") == "ENABLED": total_enabled+=1
        elif control_data.get("status") == "DISABLED": total_disabled+=1
        else: total_nodata+=1
    total_controls = total_enabled+total_disabled+total_nodata
    controls_status_dict['General'] = {"TotalEnabled":total_enabled,"TotalDisabled":total_disabled,
        "TotalNoData":total_nodata,"TotalSumControls":total_controls}
    print(f"TOTAL ENABLED: {total_enabled} DISABLED: {total_disabled} NODATA: {total_nodata} TOTALES: {total_controls}")
    return controls_status_dict

