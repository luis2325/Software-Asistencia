import cv2
import face_recognition
import pickle
import numpy as np
import time
from datetime import datetime, timedelta
from facial.db_connection import connect_to_db
from facial.config import TIEMPO_CONFIRMACION, TIEMPO_MENSAJE, cargar_configuracion

# Parámetros para detección de un parpadeo
EAR_THRESHOLD = 0.22
FRAMES_CERRADO = 2
FRASES_ABIERTO = 2

def ojos_cerrados(landmarks):
    left_eye = landmarks['left_eye']
    right_eye = landmarks['right_eye']

    def ear(eye):
        A = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
        B = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
        C = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
        return (A + B) / (2.0 * C)

    ear_left = ear(left_eye)
    ear_right = ear(right_eye)
    return (ear_left + ear_right) / 2.0

def detectar_parpadeo(ear_actual, estado, cont_cerrado, cont_abierto):
    parpadeo = False
    if estado == "OPEN":
        if ear_actual < EAR_THRESHOLD:
            cont_cerrado += 1
            if cont_cerrado >= FRAMES_CERRADO:
                estado = "CLOSED"
                cont_cerrado = 0
        else:
            cont_cerrado = 0
    elif estado == "CLOSED":
        if ear_actual >= EAR_THRESHOLD:
            cont_abierto += 1
            if cont_abierto >= FRASES_ABIERTO:
                parpadeo = True
                estado = "OPEN"
                cont_abierto = 0
        else:
            cont_abierto = 0
    return estado, cont_cerrado, cont_abierto, parpadeo

def reconocer_persona_en_tiempo_real():
    cargar_configuracion()
    from facial.config import HORA_INICIO, HORA_FINAL, HORA_LIMITE

    if isinstance(HORA_INICIO, timedelta):
        HORA_INICIO = (datetime.min + HORA_INICIO).time()
    if isinstance(HORA_FINAL, timedelta):
        HORA_FINAL = (datetime.min + HORA_FINAL).time()
    if isinstance(HORA_LIMITE, timedelta):
        HORA_LIMITE = (datetime.min + HORA_LIMITE).time()

    connection = connect_to_db()
    if connection is None:
        return None, "error_conexion"

    cursor = connection.cursor()
    cursor.execute("SELECT id, nombre, apellido, vector_facial FROM personas")
    personas = cursor.fetchall()

    if not personas:
        cursor.close()
        connection.close()
        return None, "sin_personas"

    ids = []
    nombres = []
    embeddings = []
    for persona in personas:
        ids.append(persona[0])
        nombres.append(f"{persona[1]} {persona[2]}")
        embeddings.append(pickle.loads(persona[3]))

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None, "error_camara"

    time.sleep(1)
    tiempo_confirmacion = None
    persona_id_detectada = None
    estado_general = "cancelado"
    mensaje = "Parpadee para verificar"
    color_texto = (0, 255, 255)
    verificado = False

    blink_state = "OPEN"
    blink_closed_count = 0
    blink_open_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        ubicaciones = face_recognition.face_locations(rgb_small)
        encodings = face_recognition.face_encodings(rgb_small, ubicaciones)
        landmarks = face_recognition.face_landmarks(rgb_small)

        if len(landmarks) > 0 and not verificado:
            ear = ojos_cerrados(landmarks[0])
            blink_state, blink_closed_count, blink_open_count, blink_completo = detectar_parpadeo(
                ear, blink_state, blink_closed_count, blink_open_count
            )
            if blink_completo:
                verificado = True
                mensaje = "Verificacion completada. Reconociendo..."   # sin tilde
                color_texto = (0, 255, 0)
                print("✓ Verificacion por parpadeo exitosa")

        if verificado and len(encodings) == 1:
            encoding = encodings[0]
            top, right, bottom, left = ubicaciones[0]
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2

            resultados = face_recognition.compare_faces(embeddings, encoding, tolerance=0.5)
            distancias = face_recognition.face_distance(embeddings, encoding)

            if len(distancias) > 0:
                mejor_indice = np.argmin(distancias)
                if resultados[mejor_indice]:
                    persona_id_detectada = ids[mejor_indice]
                    nombre = nombres[mejor_indice]

                    if tiempo_confirmacion is None:
                        tiempo_confirmacion = time.time()
                        mensaje = "Verificando identidad..."
                        color_texto = (0, 255, 0)
                    elif time.time() - tiempo_confirmacion >= TIEMPO_CONFIRMACION:
                        hoy = datetime.now().date()
                        ahora = datetime.now().time()

                        cursor.execute("""
                        SELECT id, hora_entrada, hora_salida
                        FROM asistencia
                        WHERE id_persona = %s AND fecha = %s
                        """, (persona_id_detectada, hoy))
                        registro = cursor.fetchone()

                        if registro is None:
                            ahora_dt = datetime.combine(hoy, ahora)
                            limite_dt = datetime.combine(hoy, HORA_LIMITE)
                            final_dt = datetime.combine(hoy, HORA_FINAL)

                            if ahora_dt <= limite_dt:
                                estado = "Temprano"
                            elif ahora_dt <= final_dt:
                                estado = "Tarde"
                            else:
                                estado = "Fuera de horario"

                            print(f"Asistencia nueva: Hora={ahora}, Limite={HORA_LIMITE}, Estado={estado}")

                            cursor.execute("""
                            INSERT INTO asistencia
                            (id_persona, fecha, hora_entrada, estado)
                            VALUES (%s, %s, %s, %s)
                            """, (persona_id_detectada, hoy, ahora, estado))
                            connection.commit()
                            mensaje = "Bienvenido"
                            color_texto = (0, 255, 0)

                        elif registro[2] is None:
                            estado = "Salida"
                            cursor.execute("""
                            UPDATE asistencia
                            SET hora_salida = %s
                            WHERE id = %s
                            """, (ahora, registro[0]))
                            connection.commit()
                            mensaje = "Hasta luego"
                            color_texto = (255, 0, 0)
                        else:
                            estado = "Registrado"
                            mensaje = "Asistencia ya registrada hoy"
                            color_texto = (0, 0, 255)

                        # Aumentar un poco el alto del rectángulo para que el texto no se corte
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 85), (0, 0, 0), -1)
                        cv2.putText(frame, nombre, (left + 5, bottom + 25),
                                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                        cv2.putText(frame, mensaje, (left + 5, bottom + 45),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_texto, 2)
                        cv2.putText(frame, estado, (left + 5, bottom + 65),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)

                        cv2.imshow("Sistema de Asistencia Facial", frame)
                        cv2.waitKey(TIEMPO_MENSAJE * 1000)
                        break

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.putText(frame, mensaje, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_texto, 2)
        cv2.imshow("Sistema de Asistencia Facial", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            estado_general = "cancelado"
            break

    cap.release()
    cv2.destroyAllWindows()
    cursor.close()
    connection.close()
    return persona_id_detectada, estado_general