import mysql.connector

connection = mysql.connector.connect(
    user = 'root', 
    password = 'root', 
    host='192.168.1.104', 
    port ="3306", 
    database='db')
cursor = connection.cursor()
print("DB connected")

cursor.execute('Select * FROM intune_users')
intune_users = cursor.fetchall()
print("Los datos de la base de datos son: ")
print(intune_users)

connection.commit()
cursor.close()
connection.close()