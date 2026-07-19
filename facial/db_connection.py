import mysql.connector
from mysql.connector import Error

def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host='localhost',       # Cambia esto si tu base de datos está en otro host
            user='root',           # Reemplaza con tu usuario de MySQL
            password='Valeria2325',   # Reemplaza con tu contraseña de MySQL
            database='facial' # Nombre de la base de datos
        )
        if connection.is_connected():
            print("Conexión exitosa a la base de datos.")
            return connection
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None
