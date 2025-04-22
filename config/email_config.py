import os
from dotenv import load_dotenv

# Carga las variables de entorno
load_dotenv()

# Configuración de SMTP para el envío de correos
SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "user": os.getenv("SMTP_USER", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
    "from_email": os.getenv("FROM_EMAIL", "")
}

# Para Gmail, es recomendable usar contraseñas de aplicación
# Instrucciones:
# 1. Activa la verificación en dos pasos en tu cuenta de Google
# 2. Ve a: https://myaccount.google.com/apppasswords
# 3. Genera una contraseña de aplicación para "Otra aplicación personalizada"
# 4. Usa esa contraseña en SMTP_PASSWORD

# Configuración de notificaciones por correo
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "True").lower() in ("true", "1", "t") 