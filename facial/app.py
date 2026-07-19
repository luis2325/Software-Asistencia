from flask import Flask, request, redirect, render_template, flash, jsonify, session, url_for
from flask_mail import Mail, Message
from datetime import datetime, timedelta, time
from facial.personas import registrar_persona
from facial.reconocimiento import reconocer_persona_en_tiempo_real
from facial.db_connection import connect_to_db
from facial.config import HORA_INICIO, HORA_FINAL, cargar_configuracion
from werkzeug.security import check_password_hash, generate_password_hash
from facial.auth import (
    login_required, role_required, init_auth_db, get_user_by_username,
    get_user_by_email, create_reset_token, verify_reset_token,
    mark_token_used, update_password
)
import secrets

app = Flask(__name__, template_folder='../templates', static_folder='../static')
# Clave secreta segura generada automáticamente
app.secret_key = secrets.token_hex(32)

#  CONFIGURACIÓN DE CORREO (GMAIL) 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ljcpconductor23@gmail.com'
app.config['MAIL_PASSWORD'] = 'yipkgcznfchbglra'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

init_auth_db()

def get_db_connection():
    return connect_to_db()

# -------------------- SEGURIDAD: CSRF TOKEN --------------------
@app.before_request
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)

def validate_csrf():
    """Valida el token CSRF en todas las peticiones POST."""
    token = request.form.get('csrf_token')
    if not token or token != session.get('csrf_token'):
        flash('Error de seguridad. Recarga la página e intenta de nuevo.', 'danger')
        return False
    return True

# -------------------- SEGURIDAD: LÍMITE DE INTENTOS DE LOGIN --------------------
login_attempts = {}  # Diccionario: IP -> {'count': int, 'blocked_until': datetime}

#  RUTAS PRINCIPALES 
@app.route('/')
@login_required
def inicio():
    return render_template('dashboard.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/index')
@login_required
@role_required(['admin'])
def index():
    return render_template('index.html')

@app.route('/capturar', methods=['POST'])
@login_required
@role_required(['admin'])
def capturar():
    # Validar CSRF
    if not validate_csrf():
        return redirect(url_for('index'))
    
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    exito = registrar_persona(nombre, apellido)
    if exito:
        return render_template('result.html', nombre=nombre, apellido=apellido)
    flash("Error al registrar persona.", "error")
    return redirect(url_for('index'))

@app.route('/tomar_asistencia', methods=['GET'])
@login_required
@role_required(['admin', 'secretario'])
def tomar_asistencia():
    return render_template('tomar_asistencia.html')

@app.route('/tomar_asistencia', methods=['POST'])
@login_required
@role_required(['admin', 'secretario'])
def tomar_asistencia_post():
    # Validar CSRF
    if not validate_csrf():
        return redirect(url_for('tomar_asistencia'))
    
    reconocer_persona_en_tiempo_real()
    flash("Proceso de reconocimiento terminado.", "info")
    return redirect(url_for('asistencia_listado'))

@app.route('/asistencia_listado')
@login_required
@role_required(['admin', 'secretario'])
def asistencia_listado():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        # CORREGIDO: se incluyen las columnas de almuerzo y el id
        cursor.execute("""
            SELECT p.nombre, p.apellido, a.fecha, a.hora_entrada,
                   a.hora_salida, a.estado,
                   a.hora_salida_almuerzo, a.hora_regreso_almuerzo,
                   a.id
            FROM asistencia a
            JOIN personas p ON a.id_persona = p.id
            ORDER BY a.fecha DESC, a.hora_entrada DESC
        """)
        asistencia = cursor.fetchall()
        cursor.close()
        connection.close()
        
        from facial.config import HORA_SALIDA_ALMUERZO, HORA_REGRESO_ALMUERZO
        salida_almuerzo = HORA_SALIDA_ALMUERZO.strftime('%H:%M')
        regreso_almuerzo = HORA_REGRESO_ALMUERZO.strftime('%H:%M')
        
        return render_template('asistencia_listado.html', 
                               asistencia=asistencia,
                               salida_almuerzo=salida_almuerzo,
                               regreso_almuerzo=regreso_almuerzo)
    return redirect(url_for('dashboard'))

@app.route('/personas')
@login_required
@role_required(['admin'])
def personas():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id, nombre, apellido FROM personas")
        personas = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('personas.html', personas=personas)
    return redirect(url_for('dashboard'))

# ADMINISTRACIÓN DE USUARIOS 
@app.route('/admin/usuarios')
@login_required
@role_required(['admin'])
def admin_usuarios():
    conn = get_db_connection()
    if not conn:
        flash('Error de conexión', 'danger')
        return redirect(url_for('dashboard'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, rol, email FROM usuarios ORDER BY id")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/crear', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_crear_usuario():
    # Validar CSRF
    if not validate_csrf():
        return redirect(url_for('admin_usuarios'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    rol = request.form.get('rol')
    email = request.form.get('email')
    if not username or not password or not rol or not email:
        flash('Todos los campos son obligatorios', 'danger')
        return redirect(url_for('admin_usuarios'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
    if cursor.fetchone():
        flash('El nombre de usuario o email ya existe', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_usuarios'))
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    cursor.execute("INSERT INTO usuarios (username, password_hash, rol, email) VALUES (%s, %s, %s, %s)",
                   (username, password_hash, rol, email))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Usuario {username} creado exitosamente', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/eliminar/<int:id>')
@login_required
@role_required(['admin'])
def admin_eliminar_usuario(id):
    if id == session.get('user_id'):
        flash('No puedes eliminarte a ti mismo', 'danger')
        return redirect(url_for('admin_usuarios'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Usuario eliminado', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/generar_enlace/<int:id>')
@login_required
@role_required(['admin'])
def admin_generar_enlace(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT email, username FROM usuarios WHERE id = %s", (id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user or not user['email']:
        flash('El usuario no tiene un correo electrónico asociado', 'danger')
        return redirect(url_for('admin_usuarios'))
    token = create_reset_token(user['email'])
    reset_url = url_for('reset_password', token=token, _external=True)
    flash(f'🔗 Enlace de recuperación para {user["username"]}: {reset_url}', 'info')
    return redirect(url_for('admin_usuarios'))

# CONFIGURACIÓN DE HORARIOS (incluye almuerzo)
@app.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def admin_configuracion():
    conn = get_db_connection()
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('dashboard'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Validar CSRF
        if not validate_csrf():
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
        except ValueError:
            flash('Formato de hora inválido. Use HH:MM', 'danger')
            return redirect(url_for('admin_configuracion'))
        
        cursor.execute("""
            UPDATE configuracion 
            SET hora_inicio = %s, hora_final = %s, hora_limite = %s,
                hora_salida_almuerzo = %s, hora_regreso_almuerzo = %s
            WHERE id = 1
        """, (hora_inicio + ':00', hora_final + ':00', hora_limite + ':00',
              hora_salida_almuerzo + ':00', hora_regreso_almuerzo + ':00'))
        conn.commit()
        
        from facial import config
        config.HORA_INICIO = datetime.strptime(hora_inicio, '%H:%M').time()
        config.HORA_FINAL = datetime.strptime(hora_final, '%H:%M').time()
        config.HORA_LIMITE = datetime.strptime(hora_limite, '%H:%M').time()
        config.HORA_SALIDA_ALMUERZO = datetime.strptime(hora_salida_almuerzo, '%H:%M').time()
        config.HORA_REGRESO_ALMUERZO = datetime.strptime(hora_regreso_almuerzo, '%H:%M').time()
        
        flash('Configuración actualizada correctamente', 'success')
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
    
    if not config_data:
        config_data = {
            'hora_inicio': '08:25:00', 'hora_final': '20:00:00', 'hora_limite': '08:30:00',
            'hora_salida_almuerzo': '12:00:00', 'hora_regreso_almuerzo': '13:00:00'
        }
    
    def normalizar_hora(valor):
        if hasattr(valor, 'strftime'):
            return valor.strftime('%H:%M')
        if isinstance(valor, str) and len(valor) >= 5 and valor[2] == ':':
            return valor[:5]
        return str(valor)[:5]
    
    hora_inicio_actual = normalizar_hora(config_data['hora_inicio'])
    hora_final_actual = normalizar_hora(config_data['hora_final'])
    hora_limite_actual = normalizar_hora(config_data['hora_limite'])
    hora_salida_almuerzo_actual = normalizar_hora(config_data['hora_salida_almuerzo'])
    hora_regreso_almuerzo_actual = normalizar_hora(config_data['hora_regreso_almuerzo'])
    
    return render_template('admin_configuracion.html', 
                           hora_inicio=hora_inicio_actual,
                           hora_final=hora_final_actual,
                           hora_limite=hora_limite_actual,
                           hora_salida_almuerzo=hora_salida_almuerzo_actual,
                           hora_regreso_almuerzo=hora_regreso_almuerzo_actual)

# RECUPERACIÓN DE CONTRASEÑA
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Validar CSRF
        if not validate_csrf():
            return redirect(url_for('forgot_password'))
        
        email = request.form.get('email')
        if not email:
            flash('Ingresa tu correo electrónico', 'danger')
            return redirect(url_for('forgot_password'))
        user = get_user_by_email(email)
        if not user:
            flash('No existe un usuario con ese correo electrónico', 'danger')
            return redirect(url_for('forgot_password'))
        token = create_reset_token(email)
        if not token:
            flash('Error al generar la recuperación, intenta más tarde', 'danger')
            return redirect(url_for('forgot_password'))
        
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message('Recuperación de contraseña - Asistencia Valuju',
                      recipients=[email])
        msg.body = f'''Hola {user['username']},

Haz clic en el siguiente enlace para restablecer tu contraseña (válido por 1 hora):

{reset_url}

Si no solicitaste este cambio, ignora este mensaje.

Saludos,
Sistema de Asistencia Valuju
'''
        try:
            mail.send(msg)
            flash('Se ha enviado un enlace de recuperación a tu correo electrónico', 'success')
        except Exception as e:
            print(f"ERROR al enviar correo: {e}")
            print("\n" + "="*70)
            print(f" ENLACE DE RECUPERACIÓN PARA {email} (FALLBACK)")
            print(reset_url)
            print("="*70 + "\n")
            flash('No se pudo enviar el correo. Revisa la consola del servidor.', 'warning')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        # Validar CSRF
        if not validate_csrf():
            return redirect(url_for('reset_password', token=token))
        
        email = verify_reset_token(token)
        if not email:
            flash('El enlace de recuperación no es válido o ha expirado', 'danger')
            return redirect(url_for('forgot_password'))
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
        elif password != confirm:
            flash('Las contraseñas no coinciden', 'danger')
        else:
            if update_password(email, password):
                mark_token_used(token)
                flash('Contraseña actualizada correctamente. Inicia sesión.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Error al actualizar la contraseña', 'danger')
    
    email = verify_reset_token(token)
    if not email:
        flash('El enlace de recuperación no es válido o ha expirado', 'danger')
        return redirect(url_for('forgot_password'))
    return render_template('reset_password.html', token=token)

#  RUTAS DE AUTENTICACIÓN (CON SEGURIDAD MEJORADA)
@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    
    # Verificar si la IP está bloqueada
    if ip in login_attempts and login_attempts[ip].get('blocked_until') and login_attempts[ip]['blocked_until'] > datetime.now():
        flash('Demasiados intentos fallidos. Espera 5 minutos.', 'danger')
        return render_template('login.html')
    
    if request.method == 'POST':
        # Validar CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            flash('Error de seguridad. Recarga la página e intenta de nuevo.', 'danger')
            return render_template('login.html')
        
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            # Login exitoso: reiniciar intentos
            if ip in login_attempts:
                del login_attempts[ip]
            session.permanent = True
            session['user_id'] = user['id']
            session['user_role'] = user['rol']
            session['username'] = user['username']
            flash(f'Bienvenido {username}', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Login fallido: contar intento
            if ip not in login_attempts:
                login_attempts[ip] = {'count': 0, 'blocked_until': None}
            login_attempts[ip]['count'] += 1
            
            if login_attempts[ip]['count'] >= 5:
                login_attempts[ip]['blocked_until'] = datetime.now() + timedelta(minutes=5)
                flash('Demasiados intentos fallidos. Bloqueado por 5 minutos.', 'danger')
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
            return render_template('login.html')
    
    # GET
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# ENDPOINTS API 
@app.route('/api/stats')
@login_required
def api_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) as total FROM personas")
        total_estudiantes = cursor.fetchone()['total']
        hoy = datetime.now().date()
        cursor.execute("SELECT COUNT(DISTINCT id_persona) as asistentes FROM asistencia WHERE fecha = %s", (hoy,))
        asistencias_hoy = cursor.fetchone()['asistentes'] or 0
        cursor.execute("SELECT COUNT(*) as retrasos FROM asistencia WHERE fecha = %s AND estado = 'Tarde'", (hoy,))
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
            tasa_semanal = 0
        return jsonify({
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
@login_required
def api_weekly():
    conn = get_db_connection()
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
@login_required
def api_recent_activity():
    conn = get_db_connection()
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
            fecha_hora = datetime.combine(row['fecha'], hora_time)
            diff = ahora - fecha_hora
            if diff.total_seconds() < 60:
                tiempo = "Hace unos segundos"
            elif diff.total_seconds() < 3600:
                minutos = int(diff.total_seconds() // 60)
                tiempo = f"Hace {minutos} minuto{'s' if minutos != 1 else ''}"
            elif diff.total_seconds() < 86400:
                horas = int(diff.total_seconds() // 3600)
                tiempo = f"Hace {horas} hora{'s' if horas != 1 else ''}"
            else:
                tiempo = row['fecha'].strftime('%d/%m/%Y')
            estado_texto = "A tiempo" if row['estado'] == 'Temprano' else "Retraso"
            actividades.append({
                'nombre': nombre_completo,
                'tiempo': tiempo,
                'estado_texto': estado_texto,
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
    app.run(debug=False, use_reloader=False, threaded=False)