from datetime import datetime
from facial.db_connection import conectar_a_bd
from facial.config import HORA_INICIO, HORA_LIMITE, HORA_FINAL, cargar_configuracion

def registrar_asistencia(persona_id, latitud=None, longitud=None, dispositivo="Web"):
    """
    Registra entrada o salida de un colaborador y retorna un diccionario con el resultado.
    """
    cargar_configuracion()
    from facial.config import HORA_INICIO, HORA_LIMITE, HORA_FINAL
    
    connection = conectar_a_bd()
    if connection is None:
        return {'success': False, 'message': 'Error de conexión a la base de datos'}

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        hoy = datetime.now().date()
        ahora = datetime.now().time()

        # Obtener información del colaborador
        cursor.execute("SELECT id, nombre, apellido FROM personas WHERE id = %s", (persona_id,))
        persona = cursor.fetchone()
        if not persona:
            return {'success': False, 'message': 'Empleado no encontrado'}

        nombre_completo = f"{persona['nombre']} {persona['apellido']}".strip()

        # Verificar si ya existe marcación el día de hoy
        cursor.execute("""
            SELECT id, hora_entrada, hora_salida, estado 
            FROM asistencia 
            WHERE id_persona = %s AND fecha = %s
            ORDER BY id DESC LIMIT 1
        """, (persona_id, hoy))
        registro = cursor.fetchone()

        # Formato estándar 12 horas con AM/PM (no militar)
        hora_str = ahora.strftime('%I:%M:%S %p')

        if registro is None:
            # Marcación de ENTRADA
            if ahora <= HORA_LIMITE:
                estado = 'Temprano'
                mensaje = f'¡Bienvenido(a), {persona["nombre"]}! Entrada a tiempo.'
            elif ahora <= HORA_FINAL:
                estado = 'Tarde'
                mensaje = f'Ingreso registrado con retraso: {hora_str}.'
            else:
                estado = 'Fuera de horario'
                mensaje = f'Ingreso fuera del horario habitual: {hora_str}.'

            cursor.execute("""
                INSERT INTO asistencia (id_persona, fecha, hora_entrada, estado)
                VALUES (%s, %s, %s, %s)
            """, (persona_id, hoy, ahora, estado))
            connection.commit()

            return {
                'success': True,
                'tipo': 'entrada',
                'persona': nombre_completo,
                'hora': hora_str,
                'estado': estado,
                'mensaje': mensaje
            }

        elif registro['hora_salida'] is None:
            # Marcación de SALIDA
            cursor.execute("""
                UPDATE asistencia
                SET hora_salida = %s
                WHERE id = %s
            """, (ahora, registro['id']))
            connection.commit()

            return {
                'success': True,
                'tipo': 'salida',
                'persona': nombre_completo,
                'hora': hora_str,
                'estado': 'Salida',
                'mensaje': f'¡Hasta luego, {persona["nombre"]}! Salida registrada.'
            }

        else:
            # Ya registró entrada y salida hoy
            return {
                'success': True,
                'tipo': 'registrado',
                'persona': nombre_completo,
                'hora': hora_str,
                'estado': registro['estado'],
                'mensaje': f'{persona["nombre"]}, tu asistencia ya está completa el día de hoy.'
            }

    except Exception as e:
        print(f"Error al registrar asistencia: {e}")
        return {'success': False, 'message': f'Error interno: {str(e)}'}

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()