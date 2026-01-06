import json
import datetime
import logging
import boto3
import os
from datetime import datetime

def get_control_findings(securityhub, control_id: str, standard: str, title: str) -> dict[str, str]:
    try:
        finding_filters = {
            'ComplianceSecurityControlId': [{'Value': control_id, 'Comparison': 'EQUALS'}], 
            'WorkflowStatus': [{'Value': 'SUPPRESSED', 'Comparison': 'NOT_EQUALS'}],
            'ProductFields': [{'Key': 'StandardsSubscriptionArn', 'Value': standard, 'Comparison': 'EQUALS'}]}
        paginator = securityhub.get_paginator('get_findings')
        count_passed=0;count_failed=0;count_warning=0;no_data=0
        for page in paginator.paginate(Filters=finding_filters, MaxResults=100):
            findings = page.get('Findings', [])
            for finding in findings:
                finding_status = finding['Compliance']['Status']
                if finding_status == 'PASSED': count_passed+=1
                elif finding_status == 'FAILED': count_failed+=1
                elif finding_status == 'WARNING': count_warning+=1
                elif finding_status == 'None': no_data+=1
                #finding_product_files = finding['ProductFields']
                #finding_previous_status = finding_product_files.get('PreviousComplianceStatus', 'None')
                #if finding_previous_status == 'None': no_data+=1
        #if no_data>=1: control_result='NoData' #There is no way to know if the result is nodata
        if count_warning >=1:control_result='Unknown'
        elif count_failed >=1: control_result='Failed'
        elif count_failed ==0:control_result='Passed'
        else:control_result='No Data'
        result = {"ComplianceStatus": control_result,"passed": count_passed, "failed": count_failed, "warning": count_warning, "no_data": no_data}
        logging.info(f"{control_id};{title};{control_result};{count_failed};{count_warning};{no_data};{count_passed}")
    except Exception as e:
        logging.error(f"Ocurrió un error al obtener los hallazgos para el control {control_id}: {e}")
        result = {"ComplianceStatus": "Error","passed": 0, "failed": 0, "warning": 0, "no_data": 0}
    except ClientError as e:
        logging.error(f"Error de AWS (ClientError) al obtener los hallazgos para el control {control_id}: {e}")
        result = {"ComplianceStatus": "Error","passed": 0, "failed": 0, "warning": 0, "no_data": 0}
    return result

def upload_to_s3(file_name: str, bucket: str, data: dict) -> None: 
    session = boto3.Session(profile_name='security')
    s3_client = session.client('s3')
    try:
        s3_client.put_object(Body=json.dumps(data), Bucket=bucket, Key=file_name, ContentType='application/json')
        logging.info(f"Archivo {file_name} subido exitosamente al bucket {bucket}.")
    except ClientError as e:
        logging.error(f"Error al subir el archivo {file_name} al bucket {bucket}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado al subir el archivo {file_name} al bucket {bucket}: {e}", exc_info=True)

def process_all_control(securityhub, security_controls_dict: dict, account: str) -> dict:
    controls_passed=0;controls_failed=0;controls_warning=0;controls_nodata=0
    controls_dict = security_controls_dict['Controls']
    for control_id, data in controls_dict.items():
        if data.get('status') == 'ENABLED':
            result = get_control_findings(securityhub, control_id, data.get('standard'),data.get('title'))
            if result['ComplianceStatus'] == "Failed": controls_failed+=1 
            elif result['ComplianceStatus'] == "Unknown": controls_warning+=1 
            elif result['ComplianceStatus'] == "Passed": controls_passed+=1 
            else: controls_nodata+=1
            security_controls_dict['Controls'][control_id]['results'] = result
        else:logging.info(f"{control_id};{data.get('title')};Disabled;0;0;0;0")
    logging.info(f"PASSED: {controls_passed} FAILED: {controls_failed} WARNINGS: {controls_warning} NO DATA: {controls_nodata}")
    total_controls=controls_passed+controls_failed+controls_warning
    general_data = {"TotalPassed":controls_passed,"TotalFailed":controls_failed,"TotalUnknown":controls_warning,"TotalControls":total_controls}
    security_controls_dict['General'].update(general_data)
    if total_controls>0:score=(controls_passed/total_controls)*100
    score_prc=f"{score:.0f}%"
    security_score = {"SecurityScore": score_prc}
    security_controls_dict['General'].update(security_score)
    now = datetime.now()
    year = now.strftime('%Y');month = now.strftime('%m');day = now.strftime('%d')
    filename = f"data/{year}/{month}/{day}/control_status_{account}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    try:
        s3_bucket = os.environ.get('S3_BUCKET_NAME')
        if s3_bucket:upload_to_s3(filename, s3_bucket, security_controls_dict)
        else: logging.warning("No se ha especificado el nombre del bucket S3 en las variables de entorno. No se subirá el archivo.")
    except Exception as e:
        logging.error(f"Ocurrió un error al intentar subir el archivo a S3: {e}", exc_info=True) 
    return security_controls_dict
