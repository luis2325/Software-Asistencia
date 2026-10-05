import os
from datetime import time, datetime, timedelta

# ==============================================================
# CARGADOR DE VARIABLES DE ENTORNO (.env)
# ==============================================================
def cargar_archivo_env():
    """Carga variables desde el archivo .env sin dependencias externas."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"Aviso al cargar .env: {e}")

load_env_file = cargar_archivo_env
cargar_archivo_env()

# ==============================================================
# IDENTIDAD DEL PRODUCTO (Nexum ID)
# ==============================================================
PRODUCT_NAME = os.environ.get('PRODUCT_NAME', 'Nexum ID')
PRODUCT_TAGLINE = os.environ.get('PRODUCT_TAGLINE', 'Inteligencia Biométrica & Control de Asistencia')
SECRET_KEY = os.environ.get('SECRET_KEY', 'nexum_id_secure_token_secret_key_2026_98df87a6d8')

# ==============================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==============================================================
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Valeria2325')
DB_NAME = os.environ.get('DB_NAME', 'facial')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# ==============================================================
# CONFIGURACIÓN DE CORREO (SMTP)
# ==============================================================
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'ljcpconductor23@gmail.com')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'yipkgcznfchbglra')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

# ==============================================================
# PARÁMETROS BIOMÉTRICOS Y TIMINGS
# ==============================================================
TIEMPO_CONFIRMACION = 1.5
TIEMPO_MENSAJE = 3
TOLERANCIA_FACIAL = 0.50  # Distancia euclidiana máxima para coincidencia

# Valores por defecto de horarios
HORA_INICIO_DEFECTO = time(8, 25)
HORA_FINAL_DEFECTO = time(20, 0)
HORA_LIMITE_DEFECTO = time(8, 30)
HORA_SALIDA_ALMUERZO_DEFECTO = time(12, 0)
HORA_REGRESO_ALMUERZO_DEFECTO = time(13, 0)

# Variables globales dinámicas de horarios
HORA_INICIO = HORA_INICIO_DEFECTO
HORA_FINAL = HORA_FINAL_DEFECTO
HORA_LIMITE = HORA_LIMITE_DEFECTO
HORA_SALIDA_ALMUERZO = HORA_SALIDA_ALMUERZO_DEFECTO
HORA_REGRESO_ALMUERZO = HORA_REGRESO_ALMUERZO_DEFECTO

def convertir_a_time(valor):
    if valor is None:
        return None
    if isinstance(valor, timedelta):
        total_seconds = valor.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return time(hours, minutes, seconds)
    elif isinstance(valor, str):
        if len(valor) == 5:
            valor += ':00'
        return datetime.strptime(valor, '%H:%M:%S').time()
    elif isinstance(valor, time):
        return valor
    return None

def cargar_configuracion():
    global HORA_INICIO, HORA_FINAL, HORA_LIMITE, HORA_SALIDA_ALMUERZO, HORA_REGRESO_ALMUERZO
    try:
        from facial.db_connection import conectar_a_bd
        conn = conectar_a_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT hora_inicio, hora_final, hora_limite,
                       hora_salida_almuerzo, hora_regreso_almuerzo
                FROM configuracion WHERE id = 1
            """)
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                hi = convertir_a_time(row['hora_inicio'])
                hf = convertir_a_time(row['hora_final'])
                hl = convertir_a_time(row['hora_limite'])
                hsa = convertir_a_time(row['hora_salida_almuerzo'])
                hra = convertir_a_time(row['hora_regreso_almuerzo'])
                if hi: HORA_INICIO = hi
                if hf: HORA_FINAL = hf
                if hl: HORA_LIMITE = hl
                if hsa: HORA_SALIDA_ALMUERZO = hsa
                if hra: HORA_REGRESO_ALMUERZO = hra
    except Exception as e:
        print(f"Aviso cargando configuración de horarios: {e}")

cargar_configuracion()