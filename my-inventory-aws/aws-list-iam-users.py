import csv
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

PROFILES = ['vpc1', 'vpc2']

HEADER = [
    'User name', 'Last activity', 'MFA', 'Password age', 'Console last sign-in',
    'Active key age', 'Access key last used', 'Creation time', 'Console access',
]


def ago(dt):
    if not dt:
        return '-'
    seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
    if seconds < 60:
        return 'Just now'
    for unit, size in (('year', 365 * 86400), ('month', 30 * 86400), ('day', 86400),
                       ('hour', 3600), ('minute', 60)):
        if seconds >= size:
            n = seconds // size
            return f'{n} {unit}{"s" if n != 1 else ""} ago'
    return '-'


def age_days(dt):
    if not dt:
        return '-'
    return f'{(datetime.now(timezone.utc) - dt).days} days'


def user_row(iam, user):
    name = user['UserName']

    # Console access / password age
    console = 'Disabled'
    password_age = '-'
    try:
        profile = iam.get_login_profile(UserName=name)['LoginProfile']
        console = 'Enabled'
        password_age = age_days(profile['CreateDate'])
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise

    # MFA
    mfa_devices = iam.list_mfa_devices(UserName=name)['MFADevices']
    mfa = 'Virtual' if mfa_devices else '-'
    if mfa_devices and not mfa_devices[0]['SerialNumber'].startswith('arn:'):
        mfa = 'Hardware'

    # Access keys (oldest active key)
    key_age = '-'
    key_last_used = None
    active = [k for k in iam.list_access_keys(UserName=name)['AccessKeyMetadata']
              if k['Status'] == 'Active']
    if active:
        key = min(active, key=lambda k: k['CreateDate'])
        key_age = age_days(key['CreateDate'])
        key_last_used = iam.get_access_key_last_used(
            AccessKeyId=key['AccessKeyId'])['AccessKeyLastUsed'].get('LastUsedDate')

    sign_in = user.get('PasswordLastUsed')
    activity = [d for d in (sign_in, key_last_used) if d]
    last_activity = ago(max(activity)) if activity else '-'

    return [name, last_activity, mfa, password_age, ago(sign_in), key_age,
            ago(key_last_used), ago(user['CreateDate']), console]


def list_users(profile, writer):
    iam = boto3.Session(profile_name=profile).client('iam')
    print(f'# Profile: {profile}')
    writer.writerow(HEADER)
    for page in iam.get_paginator('list_users').paginate():
        for user in page['Users']:
            writer.writerow(user_row(iam, user))


def main():
    writer = csv.writer(sys.stdout, lineterminator='\n')
    for profile in PROFILES:
        try:
            list_users(profile, writer)
        except Exception as e:
            print(f'# Error in profile {profile}: {e}', file=sys.stderr)
        print()


if __name__ == '__main__':
    main()
