import json


def get_control_findings(securityhub, control_id: str, standard: str, title: str) -> dict[str, str]:
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
    if count_failed >=1: control_result='Failed'
    elif count_warning >=1:control_result='Unknown'
    elif count_failed ==0:control_result='Passed'
    else:control_result='No Data'
    result = {"ComplianceStatus": control_result,"passed": count_passed, "failed": count_failed, "warning": count_warning, "no_data": no_data}
    print(f"{control_id};{title};{control_result};{count_failed};{count_warning};{no_data};{count_passed}")
    return result

def process_all_control(securityhub, security_controls_dict, account):
    controls_passed=0;controls_failed=0;controls_warning=0;controls_nodata=0
    controls_dict = security_controls_dict['Controls']
    for control_id, data in controls_dict.items():
        #if control_id in ["IAM.22"]:
            if data.get('status') == 'ENABLED':
                result = get_control_findings(securityhub, control_id, data.get('standard'),data.get('title'))
                if result['ComplianceStatus'] == "Failed": controls_failed+=1 
                elif result['ComplianceStatus'] == "Unknown": controls_warning+=1 
                elif result['ComplianceStatus'] == "Passed": controls_passed+=1 
                else: controls_nodata+=1
                security_controls_dict['Controls'][control_id]['results'] = result
            else:print(f"{control_id};{data.get('title')};Disabled;0;0;0;0")
    print(f"PASSED: {controls_passed} FAILED: {controls_failed} WARNINGS: {controls_warning} NO DATA: {controls_nodata}")
    filename = f"control_status_{account}.json"
    with open(filename, 'w', encoding='utf-8') as archivo:
        json.dump(security_controls_dict, archivo, indent=4)


