import json
import boto3
import logging
import os
from datetime import datetime, timedelta

def get_object_list(prefix: str) -> boto3.client:
    session = boto3.Session(profile_name='security')
    s3_client = session.client('s3')
    s3_bucket = os.environ.get('S3_BUCKET_NAME')
    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    return response, s3_bucket, s3_client

def get_s3_data(prefix: str) -> dict:
    try:
        response, s3_bucket, s3_client = get_object_list(prefix)
        logging.info(f"S3 data retrieved successfully for prefix {prefix}.")
        base_name = prefix.split('/')[-1]
        prefix_objects_found = [obj['Key'] for obj in response.get('Contents', []) if base_name in obj['Key']]
        filename_to_download = prefix_objects_found[0] if prefix_objects_found else None
        if filename_to_download:
            response = s3_client.get_object(Bucket=s3_bucket, Key=filename_to_download)
            logging.info(f"File {filename_to_download} downloaded successfully from S3.")
            return json.loads(response['Body'].read().decode('utf-8'))
        else:
            logging.warning(f"No matching files found in S3 for prefix {prefix}.")
            return {}
    except Exception as e:
        logging.error(f"Error retrieving S3 data: {e}")
        return {}

def get_prefix(account: str) -> str:
    yesterday = datetime.now() - timedelta(days=1)
    while yesterday.weekday() >= 5: yesterday -= timedelta(days=1)
    base_prefix = f"securityhub-cspm/{yesterday.strftime('%Y/%m/%d/')}"
    base_name = f"control_status_{account}_{yesterday.strftime('%Y%m%d')}_"
    return base_prefix + base_name

def main(dict_today: dict, account: str) -> dict:
    prefix = get_prefix(account)
    dict_yesterday = get_s3_data(prefix)   
    logging.info(f"Data for yesterday retrieved with {len(dict_yesterday['Controls'])} controls.")
    controls_today = dict_today.get('Controls', {})
    controls_yesterday = dict_yesterday.get('Controls', {})
    cambios = {}
    for control_id, info_today in controls_today.items():
        if control_id in controls_yesterday:
            status_today = info_today.get('status')
            status_yesterday = controls_yesterday[control_id].get('status')
            if status_today != status_yesterday:
                cambios[control_id] = {
                    'title': info_today.get('title'),
                    'status_yesterday': status_yesterday,
                    'status_today': status_today
                }
                logging.info(f"Control {control_id} changed from {status_yesterday} to {status_today}.")
            if status_today == 'ENABLED':
                result_today = info_today.get('results', {}).get('ComplianceStatus')
                result_yesterday = controls_yesterday[control_id].get('results', {}).get('ComplianceStatus')
                if result_today != result_yesterday:
                    cambios[control_id] = {
                        'title': info_today.get('title'),
                        'status_yesterday': result_yesterday,
                        'status_today': result_today
                    }
                    logging.info(f"Control {control_id} changed from {result_yesterday} to {result_today}.")
    return cambios

    