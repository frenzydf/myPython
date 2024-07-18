import update_s3_whitelist2
import update_fw_whitelist2
import get_secrets
import logging


def main():
    secrets = get_secrets.main()
    update_s3_whitelist2.main(secrets)
    update_fw_whitelist2.main(secrets)

if __name__ == "__main__":
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    main()
