"""
Configuración SPF (Sender Policy Framework) para mejorar la entrega de correos.

SPF es un protocolo de autenticación de correo electrónico que ayuda a prevenir 
la suplantación de remitentes y mejora la entrega de correos, evitando que sean 
marcados como spam.

Nota: Este archivo solo contiene instrucciones. La configuración real de SPF
se realiza a nivel del registro DNS de tu dominio.
"""

# Configuración recomendada de SPF para el dominio cqtrails.com
SPF_RECORD = "v=spf1 a mx ip4:SERVER_IP include:_spf.google.com ~all"

# Instrucciones para implementar SPF
SPF_INSTRUCTIONS = """
Para implementar SPF y mejorar la entrega de correos, debes agregar un registro TXT
a la configuración DNS de tu dominio con la siguiente información:

1. Nombre/Host: @ o dominio (cqtrails.com)
2. Tipo: TXT
3. Valor/Contenido: v=spf1 a mx ip4:TU_IP_DEL_SERVIDOR include:_spf.google.com ~all

Dónde:
- "a" permite el envío desde los servidores web asociados con tu dominio
- "mx" permite el envío desde los servidores de correo de tu dominio
- "ip4:TU_IP_DEL_SERVIDOR" permite el envío desde la IP específica de tu servidor
- "include:_spf.google.com" permite el envío a través de los servidores de Gmail
- "~all" indica que los correos que no coincidan con esta política deben ser tratados con sospecha pero no rechazados

Reemplaza "TU_IP_DEL_SERVIDOR" con la dirección IP pública de tu servidor.

Para un servicio de correo de Gmail, puedes utilizar:
v=spf1 include:_spf.google.com ~all
"""

# Configuración recomendada de DKIM para Gmail
DKIM_INSTRUCTIONS = """
Para implementar DKIM con Gmail:

1. Inicia sesión en la consola de administración de Google Workspace
2. Ve a Aplicaciones > Google Workspace > Gmail > Autenticación de correo electrónico
3. Haz clic en "Generar nuevo registro"
4. Sigue las instrucciones para agregar el registro DKIM a tu DNS

Este paso es crucial para que los correos no sean marcados como spam.
"""

# Configuración recomendada de DMARC
DMARC_RECORD = "v=DMARC1; p=quarantine; sp=quarantine; adkim=r; aspf=r; pct=100; fo=1; ri=86400; rua=mailto:dmarc-reports@cqtrails.com;"

# Instrucciones para implementar DMARC
DMARC_INSTRUCTIONS = """
Para implementar DMARC, agrega el siguiente registro TXT a tu DNS:

1. Nombre/Host: _dmarc.cqtrails.com
2. Tipo: TXT
3. Valor/Contenido: v=DMARC1; p=quarantine; sp=quarantine; adkim=r; aspf=r; pct=100; fo=1; ri=86400; rua=mailto:dmarc-reports@cqtrails.com;

Esta configuración:
- Solicita que los mensajes que fallen en SPF/DKIM sean puestos en cuarentena
- Requiere reportes de fallas para ser enviados a dmarc-reports@cqtrails.com
- Aplica la política al 100% de los mensajes
"""

def print_email_delivery_advice():
    """Imprime consejos para mejorar la entrega de correos"""
    advice = """
    Para evitar que los correos lleguen a la carpeta de spam:
    
    1. Configura registros SPF, DKIM y DMARC para tu dominio
    2. Utiliza un servidor SMTP confiable (como Gmail, SendGrid o Amazon SES)
    3. Mantén una buena reputación de IP (no envíes spam)
    4. Incluye siempre un asunto claro y contenido relevante
    5. Evita palabras o frases típicas de spam
    6. Incluye enlaces legítimos y evita demasiados enlaces
    7. Mantén un ratio balanceado de texto e imágenes
    8. Proporciona una forma clara de darse de baja
    9. Usa un dominio de correo electrónico corporativo, no un correo gratuito
    10. Pide a los destinatarios que agreguen tu dirección a sus contactos
    
    Si usas Gmail como proveedor SMTP:
    - Asegúrate de utilizar una contraseña de aplicación
    - Verifica que la verificación en dos pasos esté activada
    - Configura correctamente SPF, DKIM y DMARC
    """
    print(advice)
    return advice 