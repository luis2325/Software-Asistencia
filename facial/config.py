from datetime import time, datetime, timedelta
from facial.db_connection import connect_to_db

# Valores por defecto
HORA_INICIO_DEFECTO = time(8, 25)
HORA_FINAL_DEFECTO = time(20, 0)
HORA_LIMITE_DEFECTO = time(8, 30)
HORA_SALIDA_ALMUERZO_DEFECTO = time(12, 0)
HORA_REGRESO_ALMUERZO_DEFECTO = time(13, 0)

TIEMPO_CONFIRMACION = 2
TIEMPO_MENSAJE = 4

# Variables globales
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
        conn = connect_to_db()
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
        print(f"Error cargando configuración: {e}")

cargar_configuracion()