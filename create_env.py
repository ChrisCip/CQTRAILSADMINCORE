#!/usr/bin/env python3
"""
Script para crear el archivo .env con las variables necesarias
Uso: python create_env.py
"""

import os

ENV_CONTENT = """# Configuración SMTP para envío de correos
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=jessielopez0987@gmail.com
SMTP_PASSWORD=nhwi wkol ekhv nupt
FROM_EMAIL=jessielopez0987@gmail.com
EMAIL_NOTIFICATIONS_ENABLED=True

# Configuración del sistema
SITE_NAME=GUELOS'CARD

# Configuración de la base de datos
DATABASE_URL=mysql+pymysql://root:password@localhost/cqtrails
# Si estás usando SQLite, puedes usar:
# DATABASE_URL=sqlite:///./cqtrails.db

# Configuración JWT
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
"""

def main():
    # Verificar si el archivo ya existe
    if os.path.exists('.env'):
        backup_path = '.env.backup'
        print(f"El archivo .env ya existe, creando backup en {backup_path}")
        try:
            with open('.env', 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"Error al crear backup: {str(e)}")
            return 1
    
    # Crear el archivo .env
    try:
        with open('.env', 'w') as f:
            f.write(ENV_CONTENT)
        print("✅ Archivo .env creado exitosamente")
        print("Contenido:")
        for line in ENV_CONTENT.splitlines():
            # No mostrar la contraseña completa por seguridad
            if "PASSWORD" in line or "SECRET_KEY" in line:
                parts = line.split('=')
                if len(parts) > 1:
                    safe_line = f"{parts[0]}=****"
                    print(f"  {safe_line}")
                continue
            print(f"  {line}")
        return 0
    except Exception as e:
        print(f"❌ Error al crear el archivo .env: {str(e)}")
        return 1

if __name__ == "__main__":
    main() 