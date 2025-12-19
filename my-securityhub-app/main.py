import get_standards_enabled
import get_controls_status
import get_controls_result
import put_sns_notification

def main():
    print("==================================================")
    print("  INICIANDO Security Hub CSPM")
    print("==================================================")
    account_list = ['vpc2']
    mensaje = ""
    for account in account_list:
        print(f"1. Buscando estándares habilitados en {account}")
        securityhub, standard_enable_list = get_standards_enabled.main(account)
        print(f"2. Consultando controles de {len(standard_enable_list)} estándares habilitados")
        security_controls_dict = get_controls_status.main(securityhub, standard_enable_list)
        print(f"3. Consultando resultado de controles habilitados")
        securityhub_dict = get_controls_result.process_all_control(securityhub, security_controls_dict, account)
        print(f"4. Enviando notificación SNS")
        mensaje += put_sns_notification.build_message(securityhub_dict['General'], account)
    put_sns_notification.send_sns_notification_with_profile(mensaje)

if __name__ == "__main__":
    main()