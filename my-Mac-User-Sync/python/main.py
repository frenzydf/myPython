import read_intune
import read_device
import read_dhcp
import write_db
import write_db_device
import write_db_dhcp
import put_dhcp

def main():
    print('Execute Module1')
    myobj = read_intune.read_file()
    print('File Complete')
    write_db.write_database(myobj)
    print('Module1 Done!')

    print('Execute Module2')
    myobj = read_device.read_api()
    print('API GET Complete')
    write_db_device.write_database(myobj)
    print('Module2 Done!')

    print('Execute Module3')
    read_dhcp.read_api()
    print('API GET Complete')
    write_db_dhcp.write_database()
    print('Module3 Done!')
    
    print('DHCP Reservation')
    myobj = put_dhcp.read_data_from_db()
    response = put_dhcp.send_data_to_api(myobj)
    print(response)

if __name__ == "__main__":
  main()