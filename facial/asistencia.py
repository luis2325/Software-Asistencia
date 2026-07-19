from facial.db_connection import connect_to_db
from datetime import datetime
from .config import HORA_INICIO, HORA_FINAL

HORA_LIMITE_TARDE = HORA_INICIO


def registrar_asistencia(persona_id):

    connection = connect_to_db()
    if connection is None:
        return

    try:

        cursor = connection.cursor()

        fecha_actual = datetime.now().date()
        hora_actual = datetime.now().time()

        cursor.execute("SELECT * FROM asistencia WHERE id_persona = %s AND fecha = %s",
                       (persona_id, fecha_actual))

        asistencia_existente = cursor.fetchone()

        if asistencia_existente:

            cursor.execute("""
                UPDATE asistencia
                SET hora_salida = %s
                WHERE id_persona = %s AND fecha = %s
            """, (hora_actual, persona_id, fecha_actual))

        else:

            if hora_actual < HORA_INICIO:
                estado = 'presente'

            elif HORA_INICIO <= hora_actual < HORA_LIMITE_TARDE:
                estado = 'presente'

            elif HORA_LIMITE_TARDE <= hora_actual <= HORA_FINAL:
                estado = 'tarde'

            else:
                estado = 'ausente'

            cursor.execute("""
                INSERT INTO asistencia (id_persona, fecha, hora_entrada, estado)
                VALUES (%s, %s, %s, %s)
            """, (persona_id, fecha_actual, hora_actual, estado))

        connection.commit()

    except Exception as e:
        print(f"Error al registrar asistencia: {e}")

    finally:

        if cursor:
            cursor.close()

        if connection.is_connected():
            connection.close()