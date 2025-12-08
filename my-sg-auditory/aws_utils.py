# aws_utils.py
import os
import boto3
from botocore.exceptions import ClientError

# Mapeo de Account ID a ProfileName 
ACCOUNT_A = os.environ.get('AccountId_1')
ACCOUNT_B = os.environ.get('AccountId_2')
ACCOUNT_C = os.environ.get('AccountId_3')
ACCOUNT_D = os.environ.get('AccountId_4')
ACCOUNT_TO_PROFILE_MAP = {
    ACCOUNT_A: 'vpc1',
    ACCOUNT_B: 'vpc2',
    ACCOUNT_C: 'pocbd',
    ACCOUNT_D: 'security'
}

MEMBER_PROFILES = list(ACCOUNT_TO_PROFILE_MAP.values())

def get_profile_name_from_account_id(account_id):
    return ACCOUNT_TO_PROFILE_MAP.get(account_id)

def get_tags_from_resource(tags_list, key_entorno='Entorno', key_grupo='Grupo'):
    entorno = 'None'
    grupo = 'None'
    if not isinstance(tags_list, list):
        tags_list = []
    for tag in tags_list:
        key = tag.get('Key') or tag.get('key')
        value = tag.get('Value') or tag.get('value')        
        if key == key_entorno: entorno = value
        elif key == key_grupo: grupo = value
    return entorno, grupo

