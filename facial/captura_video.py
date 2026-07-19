import cv2
import os

def capturar_video(nombre, apellido):
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return None

    # Crear carpeta para el alumno si no existe
    directorio = f'videos/{nombre}_{apellido}'
    os.makedirs(directorio, exist_ok=True)

    # Configurar el códec y crear el objeto VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_path = f'{directorio}/video.avi'
    out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))

    start_time = cv2.getTickCount()  # Obtener el tiempo inicial

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        
        # Escribir el cuadro en el archivo de video
        out.write(frame)
        
        # Mostrar el marco en una ventana
        cv2.imshow('Grabando Video', frame)

        # Salir si han pasado más de 30 segundos
        elapsed_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
        if elapsed_time > 15:  # 30 segundos
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Presiona 'q' para salir
            break

    # Liberar la captura y cerrar las ventanas
    video_capture.release()
    out.release()
    cv2.destroyAllWindows()

    print(f"Video guardado en: {video_path}")
    return video_path  # Retornar la ruta del video grabado
