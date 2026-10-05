import sys
import os

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, request, redirect, render_template, flash, jsonify, session, url_for
from flask_mail import Mail, Message
from datetime import datetime, timedelta, time
import secrets
from werkzeug.security import check_password_hash, generate_password_hash

from facial.config import (
    PRODUCT_NAME, PRODUCT_TAGLINE, SECRET_KEY,
    MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER,
    HORA_INICIO, HORA_FINAL, HORA_SALIDA_ALMUERZO, HORA_REGRESO_ALMUERZO,
    cargar_configuracion
)
from facial.db_connection import conectar_a_bd, connect_to_db
from facial.auth import (
    requiere_autenticacion, requiere_rol, iniciar_bd_autenticacion,
    obtener_usuario_por_nombre, obtener_usuario_por_email,
    crear_token_recuperacion, verificar_token_recuperacion,
    marcar_token_usado, actualizar_contrasena,
    login_required, role_required
)
from facial.detector import (
    decodificar_imagen_base64,
    procesar_reconocimiento_facial,
    registrar_persona_desde_imagen
)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = SECRET_KEY

# Configuración de Seguridad en Cookies de Sesión
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Configuración de Correo Electrónico
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

mail = Mail(app)
iniciar_bd_autenticacion()

# -------------------- FILTRO JINJA: HORA 12H NO MILITAR --------------------
def filtro_hora12(val, con_segundos=True):
    """
    Convierte horas militares (24h) a formato estándar 12 horas (AM/PM).
    Soporta datetime.time, datetime.timedelta, datetime.datetime y cadenas.
    """
    if not val:
        return '--:--'
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        val = time(hours, minutes, seconds)
    elif isinstance(val, str):
        val = val.strip()
        if not val or val in ('--:--', '--:--:--'):
            return '--:--'
        for fmt in ('%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'):
            try:
                val = datetime.strptime(val, fmt).time()
                break
            except ValueError:
                pass
    if isinstance(val, (time, datetime)):
        if con_segundos and getattr(val, 'second', 0) > 0:
            return val.strftime('%I:%M:%S %p')
        return val.strftime('%I:%M %p')
    return str(val)

filter_hora12 = filtro_hora12
app.jinja_env.filters['hora12'] = filtro_hora12

# -------------------- PROCESADOR DE CONTEXTO GLOBAL --------------------
@app.context_processor
def inyectar_datos_globales():
    """Inyecta el nombre del producto, slogan y token CSRF a todas las plantillas."""
    return {
        'product_name': PRODUCT_NAME,
        'product_tagline': PRODUCT_TAGLINE,
        'csrf_token': session.get('csrf_token', ''),
        'current_year': datetime.now().year
    }

inject_global_data = inyectar_datos_globales

# -------------------- SEGURIDAD: TOKEN CSRF --------------------
@app.before_request
def asegurar_token_csrf():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(24)

ensure_csrf_token = asegurar_token_csrf

def validar_csrf():
    """Valida el token CSRF tanto en formularios POST como en encabezados HTTP."""
    token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
    session_token = session.get('csrf_token')
    if not token or not session_token or token != session_token:
        flash('Error de validación de seguridad (CSRF). Intenta nuevamente.', 'danger')
        return False
    return True

validate_csrf = validar_csrf

# -------------------- CONTROL DE RATE LIMITING DE ACCESO --------------------
intentos_login = {}
login_attempts = intentos_login

# ==============================================================
# RUTAS DE NAVEGACIÓN Y VISTAS PRINCIPALES
# ==============================================================
@app.route('/')
@requiere_autenticacion
def inicio():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@requiere_autenticacion
def dashboard():
    return render_template('dashboard.html')

@app.route('/index')
@requiere_autenticacion
@requiere_rol(['admin'])
def index():
    """Vista de registro facial de nuevo colaborador."""
    return render_template('index.html')

@app.route('/capturar', methods=['POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def capturar():
    if not validate_csrf():
        return redirect(url_for('index'))
    
    nombre = request.form.get('nombre', '').strip()
    apellido = request.form.get('apellido', '').strip()
    foto_b64 = request.form.get('foto_b64')
    
    if not nombre or not apellido:
        flash("Nombre y apellido son obligatorios.", "danger")
        return redirect(url_for('index'))

    # Si se envió la foto desde la cámara web/celular
    if foto_b64:
        img_bgr = decodificar_imagen_base64(foto_b64)
        exito, msg = registrar_persona_desde_imagen(nombre, apellido, img_bgr)
        if exito:
            return render_template('result.html', nombre=nombre, apellido=apellido)
        else:
            flash(f"Error al registrar: {msg}", "danger")
            return redirect(url_for('index'))

    flash("No se recibió la captura de la cámara.", "warning")
    return redirect(url_for('index'))

@app.route('/tomar_asistencia', methods=['GET'])
@requiere_autenticacion
@requiere_rol(['admin', 'secretario'])
def tomar_asistencia():
    """Vista principal de marcación con cámara WebRTC (móvil y PC)."""
    return render_template('tomar_asistencia.html')

@app.route('/asistencia_listado')
@requiere_autenticacion
@requiere_rol(['admin', 'secretario'])
def asistencia_listado():
    cargar_configuracion()
    from facial.config import HORA_SALIDA_ALMUERZO, HORA_REGRESO_ALMUERZO
    salida_almuerzo = HORA_SALIDA_ALMUERZO.strftime('%I:%M %p') if HORA_SALIDA_ALMUERZO else '--:--'
    regreso_almuerzo = HORA_REGRESO_ALMUERZO.strftime('%I:%M %p') if HORA_REGRESO_ALMUERZO else '--:--'

    conn = conectar_a_bd()
    asistencia = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.nombre, p.apellido, a.fecha, a.hora_entrada,
                   a.hora_salida, a.estado, a.id
            FROM asistencia a
            JOIN personas p ON a.id_persona = p.id
            ORDER BY a.fecha DESC, a.hora_entrada DESC
        """)
        asistencia = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template('asistencia_listado.html', 
                           asistencia=asistencia,
                           salida_almuerzo=salida_almuerzo,
                           regreso_almuerzo=regreso_almuerzo)

@app.route('/personas')
@requiere_autenticacion
@requiere_rol(['admin'])
def personas():
    conn = conectar_a_bd()
    lista_personas = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, apellido FROM personas ORDER BY id DESC")
        lista_personas = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('personas.html', personas=lista_personas)

@app.route('/admin/personas/eliminar/<int:id>', methods=['POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def admin_eliminar_persona(id):
    if not validate_csrf():
        return redirect(url_for('personas'))
    
    from facial.personas import eliminar_persona
    exito, msg = eliminar_persona(id)
    if exito:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('personas'))

# ==============================================================
# ADMINISTRACIÓN DE USUARIOS
# ==============================================================
@app.route('/admin/usuarios')
@requiere_autenticacion
@requiere_rol(['admin'])
def admin_usuarios():
    conn = conectar_a_bd()
    if not conn:
        flash('Error de conexión con la base de datos', 'danger')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, rol, email FROM usuarios ORDER BY id")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/crear', methods=['POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def admin_crear_usuario():
    if not validate_csrf():
        return redirect(url_for('admin_usuarios'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    rol = request.form.get('rol', 'secretario').strip()
    email = request.form.get('email', '').strip()

    if not username or not password or not email:
        flash('Todos los campos son obligatorios', 'danger')
        return redirect(url_for('admin_usuarios'))
    if len(password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres', 'danger')
        return redirect(url_for('admin_usuarios'))

    conn = conectar_a_bd()
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('admin_usuarios'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
    if cursor.fetchone():
        flash('El nombre de usuario o correo electrónico ya existe', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_usuarios'))

    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    cursor.execute("INSERT INTO usuarios (username, password_hash, rol, email) VALUES (%s, %s, %s, %s)",
                   (username, password_hash, rol, email))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f'Usuario {username} creado exitosamente con rol {rol}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def admin_eliminar_usuario(id):
    """Eliminación protegida contra CSRF vía POST."""
    if not validate_csrf():
        return redirect(url_for('admin_usuarios'))

    if id == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta en sesión activa', 'danger')
        return redirect(url_for('admin_usuarios'))

    conn = conectar_a_bd()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuario eliminado del sistema correctamente', 'success')
    else:
        flash('Error al conectar a la base de datos', 'danger')

    return redirect(url_for('admin_usuarios'))

# ==============================================================
# CONFIGURACIÓN DE HORARIOS
# ==============================================================
@app.route('/admin/configuracion', methods=['GET', 'POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def admin_configuracion():
    conn = conectar_a_bd()
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        if not validate_csrf():
            cursor.close()
            conn.close()
            return redirect(url_for('admin_configuracion'))
        
        hora_inicio = request.form.get('hora_inicio')
        hora_final = request.form.get('hora_final')
        hora_limite = request.form.get('hora_limite')
        hora_salida_almuerzo = request.form.get('hora_salida_almuerzo')
        hora_regreso_almuerzo = request.form.get('hora_regreso_almuerzo')
        
        try:
            datetime.strptime(hora_inicio, '%H:%M')
            datetime.strptime(hora_final, '%H:%M')
            datetime.strptime(hora_limite, '%H:%M')
            datetime.strptime(hora_salida_almuerzo, '%H:%M')
            datetime.strptime(hora_regreso_almuerzo, '%H:%M')
        except (ValueError, TypeError):
            flash('Formato de hora inválido. Utiliza el selector HH:MM', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('admin_configuracion'))
        
        cursor.execute("""
            UPDATE configuracion 
            SET hora_inicio = %s, hora_final = %s, hora_limite = %s,
                hora_salida_almuerzo = %s, hora_regreso_almuerzo = %s
            WHERE id = 1
        """, (hora_inicio + ':00', hora_final + ':00', hora_limite + ':00',
              hora_salida_almuerzo + ':00', hora_regreso_almuerzo + ':00'))
        conn.commit()
        cursor.close()
        conn.close()
        
        cargar_configuracion()
        flash('Configuración de horarios actualizada exitosamente', 'success')
        return redirect(url_for('admin_configuracion'))
    
    # GET
    cursor.execute("""
        SELECT hora_inicio, hora_final, hora_limite,
               hora_salida_almuerzo, hora_regreso_almuerzo
        FROM configuracion WHERE id = 1
    """)
    config_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    def normalizar_hora(valor):
        if hasattr(valor, 'strftime'):
            return valor.strftime('%H:%M')
        if isinstance(valor, str) and len(valor) >= 5 and valor[2] == ':':
            return valor[:5]
        return str(valor)[:5] if valor else '08:00'
    
    hora_inicio_act = normalizar_hora(config_data.get('hora_inicio') if config_data else '08:25:00')
    hora_final_act = normalizar_hora(config_data.get('hora_final') if config_data else '20:00:00')
    hora_limite_act = normalizar_hora(config_data.get('hora_limite') if config_data else '08:30:00')
    hora_salida_act = normalizar_hora(config_data.get('hora_salida_almuerzo') if config_data else '12:00:00')
    hora_regreso_act = normalizar_hora(config_data.get('hora_regreso_almuerzo') if config_data else '13:00:00')
    
    return render_template('admin_configuracion.html', 
                           hora_inicio=hora_inicio_act,
                           hora_final=hora_final_act,
                           hora_limite=hora_limite_act,
                           hora_salida_almuerzo=hora_salida_act,
                           hora_regreso_almuerzo=hora_regreso_act)

# ==============================================================
# RECUPERACIÓN DE CONTRASEÑA
# ==============================================================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('forgot_password'))
        
        email = request.form.get('email', '').strip()
        if not email:
            flash('Por favor ingresa tu correo electrónico', 'danger')
            return redirect(url_for('forgot_password'))
        
        user = obtener_usuario_por_email(email)
        if not user:
            # Mensaje genérico para prevenir enumeración de usuarios
            flash('Si el correo está registrado en el sistema, recibirás un enlace de recuperación.', 'info')
            return redirect(url_for('login'))
        
        token = crear_token_recuperacion(email)
        if not token:
            flash('Error temporal al generar la recuperación. Intenta más tarde.', 'danger')
            return redirect(url_for('forgot_password'))
        
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message(f'Recuperación de Acceso - {PRODUCT_NAME}', recipients=[email])
        msg.body = f'''Hola {user['username']},

Has solicitado restablecer tu contraseña en {PRODUCT_NAME}.
Haz clic en el siguiente enlace seguro (válido durante 1 hora):

{reset_url}

Si no realizaste esta solicitud, puedes ignorar este mensaje de forma segura.

Atentamente,
Equipo de Seguridad - {PRODUCT_NAME}
'''
        try:
            mail.send(msg)
            flash('Se ha enviado un enlace de recuperación a tu correo electrónico.', 'success')
        except Exception as e:
            flash('No se pudo enviar el correo en este momento. Contacta al administrador.', 'danger')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verificar_token_recuperacion(token)
    if not email:
        flash('El enlace de recuperación es inválido o ha expirado.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        if not validate_csrf():
            return redirect(url_for('reset_password', token=token))
        
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
        elif password != confirm:
            flash('Las contraseñas no coinciden', 'danger')
        else:
            if actualizar_contrasena(email, password):
                marcar_token_usado(token)
                flash('Tu contraseña ha sido actualizada con éxito. Inicia sesión.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Ocurrió un error al actualizar la contraseña', 'danger')
    
    return render_template('reset_password.html', token=token)

# ==============================================================
# AUTENTICACIÓN
# ==============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    
    if ip in intentos_login and intentos_login[ip].get('blocked_until') and intentos_login[ip]['blocked_until'] > datetime.now():
        flash('Demasiados intentos fallidos. Acceso temporalmente bloqueado por 5 minutos.', 'danger')
        return render_template('login.html')
    
    if request.method == 'POST':
        if not validate_csrf():
            return render_template('login.html')
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = obtener_usuario_por_nombre(username)
        
        if user and check_password_hash(user['password_hash'], password):
            if ip in intentos_login:
                del intentos_login[ip]
            session.permanent = True
            session['user_id'] = user['id']
            session['user_role'] = user['rol']
            session['username'] = user['username']
            flash(f'Bienvenido(a), {username}', 'success')
            return redirect(url_for('dashboard'))
        else:
            if ip not in intentos_login:
                intentos_login[ip] = {'count': 0, 'blocked_until': None}
            intentos_login[ip]['count'] += 1
            
            if intentos_login[ip]['count'] >= 5:
                intentos_login[ip]['blocked_until'] = datetime.now() + timedelta(minutes=5)
                flash('Demasiados intentos fallidos. Bloqueado temporalmente por 5 minutos.', 'danger')
            else:
                intentos_restantes = 5 - intentos_login[ip]['count']
                flash(f'Credenciales incorrectas. Te quedan {intentos_restantes} intento(s).', 'danger')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión finalizada correctamente', 'info')
    return redirect(url_for('login'))

# ==============================================================
# ENDPOINTS API REST PARA CELULAR Y WEBRTC
# ==============================================================
@app.route('/api/v1/reconocer', methods=['POST'])
@requiere_autenticacion
def api_reconocer_facial():
    """
    Recibe un fotograma en Base64 desde el celular o navegador,
    ejecuta el reconocimiento biométrico y registra la asistencia sin abrir GUI.
    """
    data = request.get_json(silent=True) or {}
    foto_b64 = data.get('imagen')
    latitud = data.get('latitud')
    longitud = data.get('longitud')
    dispositivo = data.get('dispositivo', 'Móvil WebRTC')
    verificado_parpadeo = data.get('verificado_parpadeo', False) or data.get('verificado', False)

    if not foto_b64:
        return jsonify({'success': False, 'message': 'No se recibió la imagen de la cámara'}), 400

    img_bgr = decodificar_imagen_base64(foto_b64)
    if img_bgr is None:
        return jsonify({'success': False, 'message': 'Formato de imagen inválido'}), 400

    resultado = procesar_reconocimiento_facial(
        img_bgr, 
        latitud=latitud, 
        longitud=longitud, 
        dispositivo=dispositivo, 
        verificado_parpadeo=verificado_parpadeo
    )
    return jsonify(resultado)

@app.route('/api/v1/registrar', methods=['POST'])
@requiere_autenticacion
@requiere_rol(['admin'])
def api_registrar_persona():
    """Registra una persona recibiendo foto en Base64 desde la web/móvil."""
    data = request.get_json(silent=True) or {}
    nombre = data.get('nombre', '').strip()
    apellido = data.get('apellido', '').strip()
    foto_b64 = data.get('imagen')

    if not nombre or not apellido or not foto_b64:
        return jsonify({'success': False, 'message': 'Nombre, apellido e imagen son obligatorios'}), 400

    img_bgr = decodificar_imagen_base64(foto_b64)
    if img_bgr is None:
        return jsonify({'success': False, 'message': 'No se pudo decodificar la imagen'}), 400

    exito, msg = registrar_persona_desde_imagen(nombre, apellido, img_bgr)
    return jsonify({'success': exito, 'message': msg})

# ==============================================================
# ENDPOINTS API PARA DASHBOARD Y ESTADÍSTICAS
# ==============================================================
@app.route('/api/stats')
@requiere_autenticacion
def api_stats():
    conn = conectar_a_bd()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) as total FROM personas")
        total_estudiantes = cursor.fetchone()['total']
        
        hoy = datetime.now().date()
        cursor.execute("SELECT COUNT(DISTINCT id_persona) as asistentes FROM asistencia WHERE fecha = %s", (hoy,))
        asistencias_hoy = cursor.fetchone()['asistentes'] or 0
        
        cursor.execute("SELECT COUNT(*) as retrasos FROM asistencia WHERE fecha = %s AND (estado = 'Tarde' OR estado = 'tarde')", (hoy,))
        retrasos_hoy = cursor.fetchone()['retrasos'] or 0
        
        fechas_ultima_semana = [(hoy - timedelta(days=i)) for i in range(7)]
        suma_asistentes_semana = 0
        for fecha in fechas_ultima_semana:
            cursor.execute("SELECT COUNT(DISTINCT id_persona) as asistentes FROM asistencia WHERE fecha = %s", (fecha,))
            count = cursor.fetchone()['asistentes'] or 0
            suma_asistentes_semana += count
            
        if total_estudiantes > 0:
            tasa_semanal = round((suma_asistentes_semana / (total_estudiantes * 7)) * 100, 1)
        else:
            tasa_semanal = 0.0

        return jsonify({
            'total_colaboradores': total_estudiantes,
            'total_estudiantes': total_estudiantes,
            'asistencias_hoy': asistencias_hoy,
            'retrasos_hoy': retrasos_hoy,
            'tasa_asistencia': tasa_semanal
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/weekly')
@requiere_autenticacion
def api_weekly():
    conn = conectar_a_bd()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        hoy = datetime.now().date()
        fechas = [(hoy - timedelta(days=i)) for i in range(6, -1, -1)]
        labels = [fecha.strftime('%a %d/%m') for fecha in fechas]
        data = []
        for fecha in fechas:
            cursor.execute("SELECT COUNT(DISTINCT id_persona) as asistentes FROM asistencia WHERE fecha = %s", (fecha,))
            count = cursor.fetchone()['asistentes'] or 0
            data.append(count)
        return jsonify({'labels': labels, 'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recent-activity')
@requiere_autenticacion
def api_recent_activity():
    conn = conectar_a_bd()
    if not conn:
        return jsonify([])
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.nombre, p.apellido, a.fecha, a.hora_entrada, a.estado
            FROM asistencia a
            JOIN personas p ON a.id_persona = p.id
            WHERE a.hora_entrada IS NOT NULL
            ORDER BY a.fecha DESC, a.hora_entrada DESC
            LIMIT 6
        """)
        rows = cursor.fetchall()
        actividades = []
        ahora = datetime.now()
        for row in rows:
            nombre_completo = f"{row['nombre']} {row['apellido']}".strip()
            hora = row['hora_entrada']
            if isinstance(hora, timedelta):
                total_seconds = hora.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                hora_time = time(hours, minutes, seconds)
            else:
                hora_time = hora
            
            # Formato 12 horas con AM/PM (no militar)
            hora_12h = hora_time.strftime('%I:%M %p')
            
            fecha_hora = datetime.combine(row['fecha'], hora_time)
            diff = ahora - fecha_hora
            if diff.total_seconds() < 60:
                tiempo_rel = "Hace unos segundos"
            elif diff.total_seconds() < 3600:
                minutos = int(diff.total_seconds() // 60)
                tiempo_rel = f"Hace {minutos} m"
            elif diff.total_seconds() < 86400:
                horas = int(diff.total_seconds() // 3600)
                tiempo_rel = f"Hace {horas} h"
            else:
                tiempo_rel = row['fecha'].strftime('%d/%m/%Y')
                
            tiempo = f"{hora_12h} • {tiempo_rel}"
                
            estado_lower = (row['estado'] or '').lower()
            if estado_lower in ('temprano', 'presente'):
                estado_texto = "A tiempo"
                estado_clase = "temprano"
            elif estado_lower == 'tarde':
                estado_texto = "Retraso"
                estado_clase = "retraso"
            else:
                estado_texto = row['estado']
                estado_clase = "salida"

            actividades.append({
                'nombre': nombre_completo,
                'tiempo': tiempo,
                'estado_texto': estado_texto,
                'estado_clase': estado_clase,
                'estado': row['estado']
            })
        return jsonify(actividades)
    except Exception as e:
        print("Error en api_recent_activity:", e)
        return jsonify([])
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    cert_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cert.pem')
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'key.pem')

    ssl_ctx = None
    protocolo = "http"
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_ctx = (cert_file, key_file)
        protocolo = "https"

    import socket
    def _get_lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            pass

        # Si no hay conexión a internet hacia afuera, detectar la IP de la interfaz local
        try:
            import fcntl
            import struct
            for iface in ['wlo1', 'wlan0', 'eth0', 'enp3s0', 'enp2s0', 'ens33']:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    ip = socket.inet_ntoa(fcntl.ioctl(
                        s.fileno(),
                        0x8915,  # SIOCGIFADDR
                        struct.pack('256s', iface[:15].encode('utf-8'))
                    )[20:24])
                    s.close()
                    if ip and not ip.startswith('127.'):
                        return ip
                except Exception:
                    pass
        except Exception:
            pass

        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            if host_ip and not host_ip.startswith('127.'):
                return host_ip
        except Exception:
            pass

        return "192.168.40.32"

    lan_ip = _get_lan_ip()

    if protocolo == "https":
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class RedirectHTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                host_header = self.headers.get('Host', '').split(':')[0]
                target_ip = host_header if host_header and host_header not in ('localhost', '127.0.0.1') else lan_ip
                target_url = f"https://{target_ip}:{port}" + self.path
                self.send_response(302)
                self.send_header('Location', target_url)
                self.end_headers()
            def log_message(self, format, *args):
                pass

        def iniciar_servidor_redireccion():
            try:
                httpd = HTTPServer(('0.0.0.0', 5080), RedirectHTTPHandler)
                httpd.serve_forever()
            except Exception:
                pass

        threading.Thread(target=iniciar_servidor_redireccion, daemon=True).start()

    print("\n" + "="*72)
    print(f"  [Nexum ID] Control Biométrico Facial Activo ({protocolo.upper()} Seguro):")
    print(f"  💻 Computador Local:  {protocolo}://localhost:{port}/tomar_asistencia")
    print(f"  📱 Celular en Red:    {protocolo}://{lan_ip}:{port}/tomar_asistencia")
    if protocolo == "https":
        print(f"  🔄 Redirección HTTP:  http://{lan_ip}:5080 (redirige a HTTPS automáticamente)")
        print("-" * 72)
        print("  Pasos para tomar asistencia desde tu celular:")
        print("  1. Conecta tu celular a la misma red WiFi.")
        print(f"  2. Abre en Chrome o Safari: https://{lan_ip}:{port}/tomar_asistencia")
        print("  3. Si el navegador advierte del certificado local, presiona:")
        print("     'Configuración avanzada' -> 'Acceder al sitio (no seguro)'.")
        print("  4. La cámara en vivo se abrirá y te pedirá parpadear para registrarte.")
    print("="*72 + "\n")

    app.run(host='0.0.0.0', port=port, debug=False, ssl_context=ssl_ctx)