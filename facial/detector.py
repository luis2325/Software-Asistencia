import cv2
import face_recognition
import numpy as np
import base64
import pickle
from facial.db_connection import conectar_a_bd
from facial.asistencia import registrar_asistencia
from facial.config import TOLERANCIA_FACIAL

UMBRAL_EAR_CERRADO = 0.18    # Ojos completamente cerrados (umbral estricto para evitar falsos positivos)
UMBRAL_EAR_ABIERTO = 0.23    # Ojos plenamente abiertos
UMBRAL_EAR_PARPADEO = 0.18   # Alias para retrocompatibilidad

def vector_a_bytes(embedding):
    """Serializa un vector NumPy de 128 flotantes de forma segura sin pickle."""
    return np.asarray(embedding, dtype=np.float64).tobytes()

def bytes_a_vector(blob):
    """Deserializa de forma segura un vector binario con compatibilidad para datos antiguos."""
    if not blob:
        return None
    try:
        arr = np.frombuffer(blob, dtype=np.float64)
        if arr.size == 128:
            return arr
    except Exception:
        pass
    
    try:
        return pickle.loads(blob)
    except Exception as e:
        print(f"Error deserializando vector facial: {e}")
        return None

def decodificar_imagen_base64(data_uri):
    """Convierte una cadena data:image/...;base64 en una imagen NumPy BGR."""
    try:
        if ',' in data_uri:
            header, encoded = data_uri.split(',', 1)
        else:
            encoded = data_uri
        img_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decodificando imagen Base64: {e}")
        return None

def calcular_ear(puntos_ojo):
    """Calcula el Eye Aspect Ratio (EAR) para un ojo (6 puntos clave de landmarks)."""
    A = np.linalg.norm(np.array(puntos_ojo[1]) - np.array(puntos_ojo[5]))
    B = np.linalg.norm(np.array(puntos_ojo[2]) - np.array(puntos_ojo[4]))
    C = np.linalg.norm(np.array(puntos_ojo[0]) - np.array(puntos_ojo[3]))
    return (A + B) / (2.0 * C)

def analizar_ojos_parpadeo(rgb_frame, ubicacion_rostro):
    """
    Analiza los puntos de los ojos y retorna el valor EAR exacto y su estado con histeresis estricta:
    - 'ABIERTO': EAR >= 0.23 (ojos claramente abiertos frente a la camara)
    - 'CERRADO': EAR < 0.18 (ojos completamente cerrados / oclusion real)
    - 'ENTRECERRADO': 0.18 <= EAR < 0.23 (mirando hacia abajo al celular o parpadeo parcial)
    """
    try:
        landmarks_list = face_recognition.face_landmarks(rgb_frame, [ubicacion_rostro])
        if not landmarks_list:
            return None, "DESCONOCIDO"
        landmarks = landmarks_list[0]
        if 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            return None, "DESCONOCIDO"
        
        left_ear = calcular_ear(landmarks['left_eye'])
        right_ear = calcular_ear(landmarks['right_eye'])
        ear_promedio = (left_ear + right_ear) / 2.0
        ear_val = round(float(ear_promedio), 3)

        # Clasificación estricta con histeresis para anular falsos positivos
        if ear_promedio < UMBRAL_EAR_CERRADO:
            estado = "CERRADO"
        elif ear_promedio >= UMBRAL_EAR_ABIERTO:
            estado = "ABIERTO"
        else:
            estado = "ENTRECERRADO"

        return ear_val, estado
    except Exception as e:
        print(f"Aviso analizando parpadeo EAR: {e}")
        return None, "DESCONOCIDO"

_embeddings_cache = {
    'ids': [],
    'nombres': [],
    'embeddings': [],
    'last_loaded': 0
}

def invalidar_cache_embeddings():
    """Fuerza la recarga de los vectores faciales en memoria tras un registro o eliminación."""
    global _embeddings_cache
    _embeddings_cache['last_loaded'] = 0

def cargar_embeddings_bd(force_reload=False):
    """
    Carga todos los colaboradores y sus vectores faciales.
    Utiliza caché en memoria de alto rendimiento para evitar sobrecargar la BD en cada fotograma.
    """
    global _embeddings_cache
    import time
    ahora = time.time()
    
    if not force_reload and (ahora - _embeddings_cache['last_loaded'] < 60) and len(_embeddings_cache['ids']) > 0:
        return _embeddings_cache['ids'], _embeddings_cache['nombres'], _embeddings_cache['embeddings']
        
    conn = conectar_a_bd()
    if not conn:
        return _embeddings_cache['ids'], _embeddings_cache['nombres'], _embeddings_cache['embeddings']
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, apellido, vector_facial FROM personas")
        filas = cursor.fetchall()
        ids = []
        nombres = []
        embeddings = []
        for f in filas:
            vec = bytes_a_vector(f['vector_facial'])
            if vec is not None:
                ids.append(f['id'])
                nombres.append(f"{f['nombre']} {f['apellido']}".strip())
                embeddings.append(vec)
        
        _embeddings_cache['ids'] = ids
        _embeddings_cache['nombres'] = nombres
        _embeddings_cache['embeddings'] = embeddings
        _embeddings_cache['last_loaded'] = ahora
        return ids, nombres, embeddings
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def procesar_reconocimiento_facial(frame_bgr, latitud=None, longitud=None, dispositivo="Móvil WebRTC", verificado_parpadeo=False):
    """
    Procesa un fotograma capturado desde el celular o navegador.
    Verifica prueba de vida por parpadeo antes de registrar la asistencia.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return {'success': False, 'message': 'Imagen vacía o ilegible'}

    altura, ancho = frame_bgr.shape[:2]
    escala = 1.0
    if ancho > 800:
        escala = 800.0 / ancho
        small_frame = cv2.resize(frame_bgr, (0, 0), fx=escala, fy=escala)
    else:
        small_frame = frame_bgr

    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # 1. Detección de ubicaciones de rostros
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    if len(face_locations) == 0:
        return {'success': False, 'codigo': 'sin_rostro', 'message': 'No se detecta ningún rostro. Por favor, encuadre su rostro en el óvalo.'}
    if len(face_locations) > 1:
        return {'success': False, 'codigo': 'multiples_rostros', 'message': 'Se detectan múltiples personas. Debe presentarse una sola persona.'}

    face_loc = face_locations[0]

    # 2. Análisis de Prueba de Vida (Parpadeo)
    ear_val, estado_ojos = analizar_ojos_parpadeo(rgb_frame, face_loc)

    # Si aún no ha completado el ciclo de parpadeo, informamos el estado para guiarlo
    if not verificado_parpadeo:
        return {
            'success': False,
            'codigo': 'esperando_parpadeo',
            'estado_ojos': estado_ojos,
            'ear': ear_val,
            'message': 'Por favor, parpadee frente a la cámara para verificar que está presente (prueba de vida)'
        }

    # Si se envía verificado_parpadeo pero en este fotograma los ojos están cerrados, se rechaza
    if estado_ojos == 'CERRADO':
        return {
            'success': False,
            'codigo': 'esperando_parpadeo',
            'estado_ojos': estado_ojos,
            'ear': ear_val,
            'message': 'Abre los ojos frente a la cámara para completar el reconocimiento'
        }

    # 3. Extracción de embedding facial una vez verificado el parpadeo
    encodings = face_recognition.face_encodings(rgb_frame, [face_loc])
    if len(encodings) == 0:
        return {'success': False, 'codigo': 'sin_encoding', 'message': 'No fue posible extraer los rasgos faciales. Mejore la iluminación.'}

    encoding_detectado = encodings[0]

    # 4. Comparación contra la base de datos
    ids, nombres, embeddings_bd = cargar_embeddings_bd()
    if len(embeddings_bd) == 0:
        return {'success': False, 'codigo': 'sin_personal', 'message': 'No hay personal registrado en el sistema.'}

    distancias = face_recognition.face_distance(embeddings_bd, encoding_detectado)
    mejor_indice = int(np.argmin(distancias))
    mejor_distancia = float(distancias[mejor_indice])

    # Umbral de coincidencia
    if mejor_distancia <= TOLERANCIA_FACIAL:
        persona_id = ids[mejor_indice]
        resultado = registrar_asistencia(persona_id, latitud=latitud, longitud=longitud, dispositivo=dispositivo)
        resultado['distancia'] = round(mejor_distancia, 3)
        resultado['confianza'] = round((1.0 - mejor_distancia) * 100, 1)
        resultado['parpadeo_ok'] = True
        return resultado
    else:
        return {
            'success': False,
            'codigo': 'no_coincide',
            'message': 'Rostro no reconocido en el sistema. Asegúrate de estar registrado.',
            'distancia': round(mejor_distancia, 3),
            'parpadeo_ok': True
        }

def registrar_persona_desde_imagen(nombre, apellido, frame_bgr):
    """
    Extrae el vector facial desde un fotograma recibido por la web/celular
    y almacena al colaborador en MySQL de forma segura.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return False, 'Imagen vacía o ilegible'

    rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    if len(face_locations) == 0:
        return False, 'No se detectó ningún rostro en la foto. Intente nuevamente mirando de frente a la cámara.'
    if len(face_locations) > 1:
        return False, 'Se detectaron varios rostros. Capture únicamente a la persona que se registra.'

    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    if len(encodings) == 0:
        return False, 'No se pudo codificar el rostro. Ajuste la luz e intente de nuevo.'

    vector_binario = vector_a_bytes(encodings[0])

    conn = conectar_a_bd()
    if not conn:
        return False, 'Error de conexión con la base de datos'

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO personas (nombre, apellido, vector_facial)
            VALUES (%s, %s, %s)
        """, (nombre.strip(), apellido.strip(), vector_binario))
        conn.commit()
        invalidar_cache_embeddings()
        return True, 'Empleado registrado exitosamente'
    except Exception as e:
        print(f"Error al registrar persona: {e}")
        return False, f'Error en base de datos: {str(e)}'
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
