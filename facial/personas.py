import cv2
import face_recognition
import pickle
import numpy as np
from facial.db_connection import connect_to_db


def registrar_persona(nombre, apellido):

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        return False

    print("Iniciando registro")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        height, width, _ = frame.shape
        center_x = width // 2
        center_y = height // 2

        oval_width = 300
        oval_height = 400

        
        # CREAR MÁSCARA DEL ÓVALO
        
        mask = np.zeros((height, width), dtype=np.uint8)

        cv2.ellipse(mask,
                    (center_x, center_y),
                    (oval_width // 2, oval_height // 2),
                    0, 0, 360,
                    255,
                    -1)

        
        # EFECTO OSCURO TRANSPARENTE
        
        overlay = frame.copy()
        overlay[mask == 0] = (0, 0, 0)  # todo lo de afuera negro

        alpha = 0.6  # transparencia
        frame_oval = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        mensaje = "Coloque su rostro dentro del ovalo"
        color = (0, 0, 255)
        rostro_valido = False

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if len(face_locations) > 0:

            top, right, bottom, left = face_locations[0]

            face_width = right - left
            face_center_x = (left + right) // 2
            face_center_y = (top + bottom) // 2

            top_left = (center_x - oval_width // 2, center_y - oval_height // 2)
            bottom_right = (center_x + oval_width // 2, center_y + oval_height // 2)

            # VALIDAR DISTANCIA
            if face_width < 150:
                mensaje = "Acerquese a la camara"
            elif face_width > 300:
                mensaje = "Aléjese un poco"
            else:
                # VALIDAR CENTRADO
                if (top_left[0] < face_center_x < bottom_right[0] and
                        top_left[1] < face_center_y < bottom_right[1]):

                    mensaje = "Rostro correcto - Presione S"
                    color = (0, 255, 0)
                    rostro_valido = True
                else:
                    mensaje = "Centre su rostro en el ovalo"

        
        # DIBUJAR ÓVALO
        
        cv2.ellipse(frame_oval,
                    (center_x, center_y),
                    (oval_width // 2, oval_height // 2),
                    0, 0, 360,
                    color, 2)

        
        # BARRA INFERIOR
        
        cv2.rectangle(frame_oval, (0, height - 60),
                      (width, height), (0, 0, 0), -1)

        cv2.putText(frame_oval, mensaje,
                    (30, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 2)

        cv2.imshow("Registro Facial", frame_oval)

        key = cv2.waitKey(1) & 0xFF

       
        # GUARDAR PERSONA
       
        if key == ord('s') and rostro_valido:

            encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if len(encodings) == 0:
                continue

            embedding = encodings[0]
            embedding_binario = pickle.dumps(embedding)

            connection = connect_to_db()
            if connection is None:
                return False

            try:
                cursor = connection.cursor()
                query = """
                INSERT INTO personas (nombre, apellido, vector_facial)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query, (nombre, apellido, embedding_binario))
                connection.commit()
                print("Persona registrada correctamente")

            except Exception as e:
                print(f"Error al registrar persona: {e}")

            finally:
                cursor.close()
                connection.close()

            break

        elif key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    return True