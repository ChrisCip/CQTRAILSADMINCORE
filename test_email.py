#!/usr/bin/env python3
"""
Script para probar el envío de correos electrónicos
Uso: python test_email.py [correo_destino]
"""

import sys
import os
from dotenv import load_dotenv
from services.email_service import email_service

# Cargar variables de entorno
load_dotenv()

def main():
    # Verificar argumentos
    if len(sys.argv) > 1:
        to_email = sys.argv[1]
    else:
        to_email = os.getenv("SMTP_USER", "")
    
    if not to_email:
        print("Error: No se especificó un correo electrónico de destino")
        print("Uso: python test_email.py [correo_destino]")
        return 1
    
    print(f"Enviando correo de prueba a {to_email}...")
    
    # Datos de prueba para la reservación
    reservation_details = {
        "id": "123456",
        "fecha": "01/01/2023",
        "hora": "15:00",
        "duracion": "2",
        "cabanas": "Cabaña 1, Cabaña 2"
    }
    
    try:
        result = email_service.send_reservation_confirmation(
            user_email=to_email,
            user_name="Usuario de Prueba",
            reservation_details=reservation_details
        )
        
        if result:
            print("✅ Correo enviado exitosamente!")
            return 0
        else:
            print("❌ No se pudo enviar el correo. Verificar configuración.")
            return 1
    except Exception as e:
        print(f"❌ Error al enviar correo: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 