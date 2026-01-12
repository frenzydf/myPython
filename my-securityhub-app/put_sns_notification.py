import logging
import boto3
import os

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC')
ALERT_SUBJECT = "Postura de Seguridad AWS"

def build_message(securityhub_dict_general, account):
    cadena_mensaje = f"Reporte de SecurityHub en {account}:\n"
    for clave, valor in securityhub_dict_general.items():
        cadena_mensaje += f"- {clave}: {valor}\n"
    return cadena_mensaje

def send_sns_notification_with_profile(mensaje: str) -> None:
    try:
        session = boto3.Session(profile_name='security')
        sns_client = session.client('sns', 'us-east-1' )
        sns_client.publish(TopicArn=SNS_TOPIC_ARN,Message=mensaje,Subject=ALERT_SUBJECT)
        logging.info(f"Notificación SNS enviada con éxito.")
        return 
    except Exception as e:
        logging.error(f"Error al enviar la notificación SNS: {e}")
        return None