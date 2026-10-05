"""
Nexum ID — Servicio de Gestión y Registro de Personal
"""
from facial.db_connection import conectar_a_bd
from facial.detector import invalidar_cache_embeddings

def listar_personas():
    """Retorna la lista completa de colaboradores registrados."""
    conn = conectar_a_bd()
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, apellido FROM personas ORDER BY id DESC")
        return cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def obtener_persona(persona_id):
    """Obtiene el registro de un colaborador por su ID."""
    conn = conectar_a_bd()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, apellido FROM personas WHERE id = %s", (persona_id,))
        return cursor.fetchone()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def eliminar_persona(persona_id):
    """
    Elimina a un colaborador y sus asistencias asociadas respetando integridad referencial.
    Invalida el caché en memoria para sincronización inmediata.
    """
    conn = conectar_a_bd()
    if not conn:
        return False, "Error de conexión a la base de datos"
    cursor = None
    try:
        cursor = conn.cursor()
        # 1. Eliminar asistencias asociadas
        cursor.execute("DELETE FROM asistencia WHERE id_persona = %s", (persona_id,))
        # 2. Eliminar colaborador
        cursor.execute("DELETE FROM personas WHERE id = %s", (persona_id,))
        conn.commit()
        # 3. Invalidar caché en memoria
        invalidar_cache_embeddings()
        return True, "Empleado eliminado correctamente"
    except Exception as e:
        if conn: conn.rollback()
        return False, f"Error al eliminar empleado: {str(e)}"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()