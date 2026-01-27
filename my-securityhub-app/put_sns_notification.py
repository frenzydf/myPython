import logging
import boto3
import os

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC')
ALERT_SUBJECT = "TEST Postura de Seguridad AWS"

def build_message(securityhub_dict_general, cambios_dict, account):
    cadena_mensaje = f"Reporte de SecurityHub en {account}:\n"
    for clave, valor in securityhub_dict_general.items():
        cadena_mensaje += f"- {clave}: {valor}\n"
    if cambios_dict:
        cadena_mensaje += "Cambios detectados en los controles respecto al día anterior:\n"
        for clave, valor in cambios_dict.items():
            cadena_mensaje += f"{clave} - {valor['title']}: {valor['status_yesterday']} -> {valor['status_today']}\n"
    else:
        cadena_mensaje += "No se detectaron cambios en los controles respecto al día anterior.\n\n" 
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