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
    return response

def get_s3_data(prefix: str) -> dict:
    try:
        response = get_object_list(prefix)
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
    base_prefix = f"securityhub-cspm/{yesterday.strftime('%Y/%m/%d/')}"
    base_name = f"control_status_{account}_{yesterday.strftime('%Y%m%d')}_"
    return base_prefix + base_name

def main(dict_today: dict, account: str) -> dict:
    prefix = get_prefix(account)
    dict_yesterday = get_s3_data(prefix)   
    logging.info(f"Data for yesterday retrieved with {len(dict_yesterday['Controls'])} controls.")
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main({}, 'VPC1')
    