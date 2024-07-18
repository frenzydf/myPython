import mysql.connector

def write_database(reserved_addresses):
    connection = mysql.connector.connect(
        user = 'root', 
        password = 'root', 
        host='localhost', 
        port ="3306", 
        database='db')
    cursor = connection.cursor()
    print("DB connected")

    cursor.execute('UPDATE intune_users SET status = False')

    cursor.execute('SELECT hostname FROM intune_users')
    existing_hostnames = set(row[0] for row in cursor.fetchall())
    
    for address in reserved_addresses:
        hostname = address['hostname']
        macaddress = address['mac']
        username = address['username']
        email = address['email']

        if hostname in existing_hostnames:
            # Actualizar el estado a True
            query = "UPDATE intune_users SET status = TRUE WHERE hostname = %s"
            values = (hostname,)
            cursor.execute(query, values)
            print(f"Se actualizó el estado a 'True' para el hostname {hostname} del usuario {username}.")
        else:
            # Insertar un nuevo registro con el estado como True
            query = "INSERT INTO intune_users (hostname, macaddress, username, email, status) VALUES (%s, %s, %s, %s, True)"
            values = (hostname, macaddress, username, email)
            cursor.execute(query, values)
            print(f"Se insertó un nuevo registro para el hostname {hostname} con estado 'True'.")

    connection.commit()
    cursor.close()
    connection.close()