# ==============================================================
# CONEXIÓN A BASE DE DATOS CON GRUPO DE CONEXIONES (POOLING)
# ==============================================================
import os
import mysql.connector
from mysql.connector import Error, pooling

_pool_conexiones = None

def obtener_credenciales_bd():
    """Retorna los parámetros de conexión a MySQL desde las variables de entorno."""
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', 'Valeria2325'),
        'database': os.environ.get('DB_NAME', 'facial')
    }

def obtener_pool_conexiones():
    """Inicializa y retorna el grupo de conexiones (Connection Pool) para alta concurrencia."""
    global _pool_conexiones
    if _pool_conexiones is None:
        credenciales = obtener_credenciales_bd()
        try:
            _pool_conexiones = pooling.MySQLConnectionPool(
                pool_name="nexum_pool",
                pool_size=10,
                pool_reset_session=True,
                host=credenciales['host'],
                port=credenciales['port'],
                user=credenciales['user'],
                password=credenciales['password'],
                database=credenciales['database']
            )
        except Error:
            # En caso de que el entorno no soporte pooling, recurre a conexión directa
            _pool_conexiones = False
    return _pool_conexiones

def conectar_a_bd():
    """Retorna una conexión activa a MySQL usando el pool si está disponible, o conexión directa segura."""
    pool = obtener_pool_conexiones()
    if pool:
        try:
            return pool.get_connection()
        except Error as e:
            print(f"Aviso al obtener conexión del pool: {e}")
    
    # Conexión directa de respaldo
    credenciales = obtener_credenciales_bd()
    try:
        conexion = mysql.connector.connect(
            host=credenciales['host'],
            port=credenciales['port'],
            user=credenciales['user'],
            password=credenciales['password'],
            database=credenciales['database']
        )
        if conexion.is_connected():
            return conexion
    except Error as e:
        print(f"Error al conectar a la base de datos MySQL: {e}")
        return None

# Alias compatibles
connect_to_db = conectar_a_bd
get_db_credentials = obtener_credenciales_bd
get_connection_pool = obtener_pool_conexiones
