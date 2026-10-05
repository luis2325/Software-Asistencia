# ==============================================================
# MÓDULO DE AUTENTICACIÓN, ROLES Y RECUPERACIÓN DE CUENTAS
# ==============================================================
from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from facial.db_connection import conectar_a_bd
import secrets
import hashlib
from datetime import datetime, timedelta

def iniciar_bd_autenticacion():
    """Verifica e inicializa las tablas de autenticación y el usuario administrador inicial."""
    conexion = conectar_a_bd()
    if conexion is None:
        print("Aviso: no fue posible conectar a MySQL para verificar tablas de autenticación.")
        return
    cursor = None
    try:
        cursor = conexion.cursor()
        
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'email'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) UNIQUE")
            print("Columna 'email' agregada a la tabla usuarios.")
        
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
        if not cursor.fetchone():
            clave_cifrada = generate_password_hash('admin123', method='pbkdf2:sha256')
            cursor.execute("INSERT INTO usuarios (username, password_hash, rol, email) VALUES (%s, %s, %s, %s)",
                           ('admin', clave_cifrada, 'admin', 'admin@nexum.local'))
            print("Usuario admin inicial verificado (admin / admin123)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(100) NOT NULL,
                token VARCHAR(100) NOT NULL,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                INDEX (token)
            )
        """)
        conexion.commit()
    except Exception as e:
        print(f"Aviso en iniciar_bd_autenticacion: {e}")
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def requiere_autenticacion(f):
    """Decorador para proteger rutas que requieren inicio de sesión activo."""
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if 'user_id' not in session:
            flash('Inicia sesión para continuar', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return funcion_decorada

def requiere_rol(roles_permitidos):
    """Decorador para restringir rutas a roles de usuario específicos (ej. admin)."""
    def decorador(f):
        @wraps(f)
        def funcion_decorada(*args, **kwargs):
            if 'user_id' not in session:
                flash('Inicia sesión para continuar', 'warning')
                return redirect(url_for('login'))
            rol_usuario = session.get('user_role')
            if rol_usuario not in roles_permitidos:
                flash('No tienes permiso para acceder a este módulo', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return funcion_decorada
    return decorador

def obtener_usuario_por_nombre(nombre_usuario):
    """Busca un usuario en la base de datos por su nombre de usuario."""
    conexion = conectar_a_bd()
    if not conexion:
        return None
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, username, password_hash, rol, email FROM usuarios WHERE username = %s", (nombre_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()
    return usuario

def obtener_usuario_por_email(correo):
    """Busca un usuario en la base de datos por su correo electrónico."""
    conexion = conectar_a_bd()
    if not conexion:
        return None
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, username, rol, email FROM usuarios WHERE email = %s", (correo,))
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()
    return usuario

def crear_token_recuperacion(correo):
    """Genera y almacena un token seguro con expiración de 1 hora para restablecer contraseña."""
    token = secrets.token_urlsafe(32)
    hash_token = hashlib.sha256(token.encode()).hexdigest()
    fecha_expiracion = datetime.now() + timedelta(hours=1)
    conexion = conectar_a_bd()
    if not conexion:
        return None
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)",
                   (correo, hash_token, fecha_expiracion))
    conexion.commit()
    cursor.close()
    conexion.close()
    return token

def verificar_token_recuperacion(token):
    """Valida si un token de recuperación existe, no ha sido usado y sigue vigente."""
    if not token:
        return None
    hash_token = hashlib.sha256(token.encode()).hexdigest()
    conexion = conectar_a_bd()
    if not conexion:
        return None
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT email, expires_at, used 
        FROM password_resets 
        WHERE (token = %s OR token = %s) AND used = FALSE AND expires_at > NOW()
        ORDER BY id DESC LIMIT 1
    """, (hash_token, token))
    registro = cursor.fetchone()
    cursor.close()
    conexion.close()
    if registro:
        return registro['email']
    return None

def marcar_token_usado(token):
    """Marca un token de recuperación como utilizado para evitar reutilización."""
    if not token:
        return
    hash_token = hashlib.sha256(token.encode()).hexdigest()
    conexion = conectar_a_bd()
    if not conexion:
        return
    cursor = conexion.cursor()
    cursor.execute("UPDATE password_resets SET used = TRUE WHERE token = %s OR token = %s", (hash_token, token))
    conexion.commit()
    cursor.close()
    conexion.close()

def actualizar_contrasena(correo, nueva_contrasena):
    """Actualiza la contraseña de un usuario mediante hash criptográfico PBKDF2:SHA256."""
    clave_cifrada = generate_password_hash(nueva_contrasena, method='pbkdf2:sha256')
    conexion = conectar_a_bd()
    if not conexion:
        return False
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE email = %s", (clave_cifrada, correo))
    conexion.commit()
    exito = cursor.rowcount > 0
    cursor.close()
    conexion.close()
    return exito

# ==============================================================
# ALIAS DE COMPATIBILIDAD
# ==============================================================
init_auth_db = iniciar_bd_autenticacion
login_required = requiere_autenticacion
role_required = requiere_rol
get_user_by_username = obtener_usuario_por_nombre
get_user_by_email = obtener_usuario_por_email
create_reset_token = crear_token_recuperacion
verify_reset_token = verificar_token_recuperacion
mark_token_used = marcar_token_usado
update_password = actualizar_contrasena