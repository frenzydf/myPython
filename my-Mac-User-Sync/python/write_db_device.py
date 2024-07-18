import mysql.connector

def write_database(reserved_hostnames):
    connection = mysql.connector.connect(
        user = 'root', 
        password = 'root', 
        host='localhost', 
        port ="3306", 
        database='db')
    cursor = connection.cursor()
    print("DB connected")

    cursor.execute('SELECT hostname FROM devices')
    existing_hosts = set(row[0] for row in cursor.fetchall())
    
    for hostnames in reserved_hostnames:
        macaddr = hostnames['macaddr']
        ipaddress = hostnames['ipaddr']
        hostname = hostnames['hostname']
        lastseen = hostnames['lastseen']
        if hostname not in existing_hosts:
            query = "INSERT INTO devices (macaddr, ipaddr, hostname, lastseen) VALUES (%s,%s, %s, %s)"
            values = (macaddr, ipaddress, hostname, lastseen)
            cursor.execute(query, values)
            print(f"Se inserto un nuevo registro para el hostname {hostname}.")

    connection.commit()
    cursor.close()
    connection.close()