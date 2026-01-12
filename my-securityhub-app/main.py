import boto3
import logging

import get_standards_enabled
import get_controls_status
import get_controls_result
import put_sns_notification
import get_findings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_account_client(account_name: str) -> boto3.client:
    try:
        session = boto3.Session(profile_name=account_name)
        securityhub = session.client('securityhub', 'us-east-1')
        return securityhub
    except Exception as e:
        logger.error(f"Error al crear el cliente de SecurityHub para la cuenta {account_name}: {e}")
        raise e

def main():
    account_list = ['vpc1']  
    mensaje_final_sns = ""
    for account in account_list:
        try:
            logger.info(f"Conectando al client de la cuenta: {account}")
            securityhub_client = get_account_client(account)

            logger.info(f"1. Buscando estándares habilitados en {account}")
            standard_enable_list = get_standards_enabled.main(securityhub_client, account)

            logger.info(f"2. Consultando controles de {len(standard_enable_list)} estándares habilitados")
            security_controls_dict = get_controls_status.main(securityhub_client, standard_enable_list)

            logger.info(f"3. Consultando resultado de controles habilitados")
            securityhub_dict = get_controls_result.process_all_control(securityhub_client, security_controls_dict, account)

            logger.info(f"4. Comparando resultados con el día anterior")
            cambios_dict = get_findings.main(securityhub_dict, account.upper())

            logger.info(f"5. Enviando notificación SNS")
            mensaje_final_sns += put_sns_notification.build_message(securityhub_dict['General'], account)

        except Exception as e:
            logger.error(f"Error procesando la cuenta {account}: {e}")
            continue
    put_sns_notification.send_sns_notification_with_profile(mensaje_final_sns)

if __name__ == "__main__":
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    main()