import boto3
from datetime import datetime, timedelta, timezone

session = boto3.Session(profile_name='pocbd')
lambda_client = session.client('lambda')
limite_dias = datetime.now(timezone.utc) - timedelta(days=90)

functions = lambda_client.list_functions()['Functions']

print(f"{'Función':<30} | {'Última Modificación':<30} | {'Estado Inspector'}")
print("-" * 80)

for f in functions:
    # Convertir string de fecha a objeto datetime
    last_mod = datetime.strptime(f['LastModified'], '%Y-%m-%dT%H:%M:%S.%f%z')
    
    estado = "ELEGIBLE" if last_mod > limite_dias else "INACTIVA (Excluida)"
    print(f"{f['FunctionName']:<30} | {f['LastModified']:<30} | {estado}")