import mysql.connector

def write_database():
    connection = mysql.connector.connect(
        user = 'root', 
        password = 'root', 
        host='localhost', 
        port ="3306", 
        database='db')
    cursor = connection.cursor()
    print("DB connected")

    cursor.execute('DELETE FROM dhcp_list')

    cursor.execute("""
    INSERT INTO dhcp_list (mac, ip, hostname)
    SELECT d.macaddr, d.ipaddr, iu.hostname FROM intune_users iu
    JOIN devices d ON d.hostname = iu.hostname 
    """)
    
    connection.commit()
    cursor.close()
    connection.close()