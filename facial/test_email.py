import smtplib
from email.message import EmailMessage

# Configuración
EMAIL = 'ljcpconductor23@gmail.com'
PASSWORD = 'knsagrfflexcxcquslsz'  # ← pega aquí la contraseña de aplicación

to_email = 'valeriamabo02@gmail.com'  # cámbialo por un email al que quieras probar

msg = EmailMessage()
msg.set_content('Este es un correo de prueba desde mi script.')
msg['Subject'] = 'Prueba de envío'
msg['From'] = EMAIL
msg['To'] = to_email

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)
        print("Correo enviado exitosamente")
except Exception as e:
    print(f"Error: {e}")