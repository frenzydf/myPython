import mysql.connector

connection = mysql.connector.connect(user = 'root', password = 'root', host='192.168.0.4', port ="3306", database='db')
cursor = connection.cursor()
print("DB connected")

query = "INSERT INTO intune_users (hostname, macaddress, actualstatus) VALUES (%s, %s ,%s)"
values = [
    ('OMNI-001', '00:11:22:33:44:55', True),
    ('OMNI-002', '22:33:44:55:66:77', False),
]
cursor.executemany(query, values)
print('DB Updated')

cursor.execute('Select * FROM intune_users')
intune_users = cursor.fetchall()
print("Los datos de la base de datos son: ")
print(intune_users)

connection.commit()
cursor.close()
connection.close()