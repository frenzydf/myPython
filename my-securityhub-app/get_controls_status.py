import logging
import boto3
import json
import re
from botocore.exceptions import ClientError


def main(securityhub, standard_enable_list: list) -> dict:
    controls_status = {} #Diccionario para procesar Controles
    controls_status_dict = {"General":{},"StandardsEnabled":{},"Controls":{}} #Diccionario General
    control_mapper = {
            "1.12": "IAM.22",
            "1.19": "IAM.26",
            "1.20": "IAM.28",
            "1.22": "IAM.27",
            "1.8": "IAM.15",
            "3.8": "S3.22",
            "3.9": "S3.23",
            "2.1.1": "S3.5",
            "2.1.2": "S3.20",
            "2.1.4.1": "S3.1",
            "2.1.4.2": "S3.8",
            "ELBv2.1": "ELB.1",
            "3.3": "Config.1",
            "3.6": "KMS.4",
            "3.2": "CloudTrail.4",
            "3.1": "CloudTrail.1",
            "3.5": "CloudTrail.2",
            "2.2.1": "EC2.7",
            "5.6": "EC2.8",
            "5.3": "EC2.54",
            "5.2": "EC2.53",
            "2.4.1": "EFS.1",
            "1.17": "IAM.18",
            "1.9": "IAM.16",
            "3.4": "CloudTrail.7",
            "1.6": "IAM.6",
            "1.4": "IAM.4",
            "1.15": "IAM.2",
            "1.14": "IAM.3",
            "1.10": "IAM.5",
            "1.5": "IAM.9",
            "5.1": "EC2.21",
            "2.3.2": "RDS.13",
            "2.3.1": "RDS.3",
            "2.3.3": "RDS.2",
            "1.2": "Account.1",
            "5.4": "EC2.2",
            "3.7": "EC2.6",
            "1.14": "IAM.3"
        }
    try:
        paginator_controls = securityhub.get_paginator('describe_standards_controls')
        for standard_arn in standard_enable_list:
            count_enabled = 0; count_disabled = 0
            for controls_page in paginator_controls.paginate(StandardsSubscriptionArn=standard_arn):
                for control in controls_page['Controls']:
                    title = control.get('Title', 'N/A')
                    status = control.get('ControlStatus', 'N/A')
                    severity = control.get('SeverityRating')
                    remediation = control.get('RemediationUrl', 'N/A')
                    identificador = control.get('ControlId', remediation.split('/')[-2])
                    if identificador in control_mapper:
                        identificador = control_mapper[identificador]
                    controls_status[identificador] = {"title": title,"status": status, "severity":severity, "standard": standard_arn}
                    if status == "ENABLED": count_enabled += 1
                    elif status == "DISABLED": count_disabled += 1
                search_standard_name = re.search(r'subscription/(.*)', standard_arn)
                if search_standard_name: standard_name = search_standard_name.group(1)
                else: standard_name = 'None'
            logging.info(f"Estándar: {standard_name}")
            logging.info(f"Enabled: {count_enabled} Disabled: {count_disabled} Total: {count_enabled+count_disabled}")
            standard_data = {"Enabled": count_enabled, "Disabled": count_disabled, "Total": count_enabled+count_disabled}
            controls_status_dict['StandardsEnabled'][standard_name]=standard_data 
        logging.info(f"Se encontraron {len(controls_status)} Controles Totales")
        controls_status_dict['Controls'] = controls_status
        total_enabled=0; total_disabled=0; total_nodata=0
        for control, control_data in controls_status_dict['Controls'].items():
            if control_data.get("status") == "ENABLED": total_enabled+=1
            elif control_data.get("status") == "DISABLED": total_disabled+=1
            else: total_nodata+=1
        total_controls = total_enabled+total_disabled+total_nodata
        controls_status_dict['General'] = {"TotalEnabled":total_enabled,"TotalDisabled":total_disabled,
            "TotalNoData":total_nodata,"TotalSumControls":total_controls}
        logging.info(f"TOTAL ENABLED: {total_enabled} DISABLED: {total_disabled} NODATA: {total_nodata} TOTALES: {total_controls}")
    except ClientError as e:
        logging.error(f"Error de AWS (ClientError) al obtener el estado de los controles: {e}")
        raise e
    except Exception as e:
        logging.error(f"Ocurrió un error al obtener el estado de los controles: {e}")
        raise e
    logging.info("Finalizó la obtención del estado de los controles.")
    return controls_status_dict

