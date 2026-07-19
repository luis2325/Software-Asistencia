from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from facial.db_connection import connect_to_db
import secrets
from datetime import datetime, timedelta

def init_auth_db():
    conn = connect_to_db()
    if conn is None:
        print("Error de conexión para inicializar auth")
        return
    cursor = conn.cursor()
    
    cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'email'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) UNIQUE")
        print("Columna 'email' agregada a la tabla usuarios")
    
    cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
        cursor.execute("INSERT INTO usuarios (username, password_hash, rol, email) VALUES (%s, %s, %s, %s)",
                       ('admin', hashed, 'admin', 'admin@example.com'))
        print("Usuario admin creado con contraseña: admin123, email: admin@example.com")
    
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
    
    conn.commit()
    cursor.close()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Inicia sesión para continuar', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Inicia sesión', 'warning')
                return redirect(url_for('login'))
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                flash('No tienes permiso para ver esta página', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_by_username(username):
    conn = connect_to_db()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, password_hash, rol, email FROM usuarios WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_by_email(email):
    conn = connect_to_db()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, rol, email FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def create_reset_token(email):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    conn = connect_to_db()
    if not conn:
        return None
    cursor = conn.cursor()
    cursor.execute("INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)",
                   (email, token, expires_at))
    conn.commit()
    cursor.close()
    conn.close()
    return token

def verify_reset_token(token):
    conn = connect_to_db()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT email, expires_at, used 
        FROM password_resets 
        WHERE token = %s AND used = FALSE AND expires_at > NOW()
        ORDER BY id DESC LIMIT 1
    """, (token,))
    record = cursor.fetchone()
    cursor.close()
    conn.close()
    if record:
        return record['email']
    return None

def mark_token_used(token):
    conn = connect_to_db()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (token,))
    conn.commit()
    cursor.close()
    conn.close()

def update_password(email, new_password):
    hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
    conn = connect_to_db()
    if not conn:
        return False
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE email = %s", (hashed, email))
    conn.commit()
    success = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return success