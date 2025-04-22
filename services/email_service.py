import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException, status
from typing import List, Optional
from email.utils import formataddr, make_msgid, formatdate
from datetime import datetime
import uuid

try:
    from config.email_config import SMTP_CONFIG, EMAIL_NOTIFICATIONS_ENABLED
except ImportError:
    # Configuración predeterminada si no se puede importar
    SMTP_CONFIG = {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("FROM_EMAIL", "")
    }
    EMAIL_NOTIFICATIONS_ENABLED = True

# Obtener el nombre del sitio para usar en correos
SITE_NAME = os.getenv("SITE_NAME", "CQ TRAILS")
# Dominio para Message-ID (usará el dominio del correo del remitente)
EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN", "cqtrails.com")

class EmailService:
    def __init__(self, smtp_host: str = None, smtp_port: int = None, 
                 smtp_user: str = None, smtp_password: str = None, 
                 from_email: str = None, site_name: str = None):
        # Use parameters or config values
        self.smtp_host = smtp_host or SMTP_CONFIG["host"]
        self.smtp_port = smtp_port or SMTP_CONFIG["port"]
        self.smtp_user = smtp_user or SMTP_CONFIG["user"]
        self.smtp_password = smtp_password or SMTP_CONFIG["password"]
        self.from_email = from_email or SMTP_CONFIG["from_email"] or self.smtp_user
        self.site_name = site_name or SITE_NAME
        self.enabled = EMAIL_NOTIFICATIONS_ENABLED
        
        # Extract domain from email for Message-ID
        if '@' in self.from_email:
            self.email_domain = self.from_email.split('@')[1]
        else:
            self.email_domain = EMAIL_DOMAIN
        
        # Verify configuration
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            print("WARNING: Email configuration incomplete. Email sending will be disabled.")
            self.enabled = False
    
    def send_email(self, 
                  to_email: str, 
                  subject: str, 
                  message_html: str, 
                  message_text: Optional[str] = None,
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None) -> bool:
        """
        Send an email to the specified recipient
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message_html: HTML message content
            message_text: Plain text message (optional)
            cc: Carbon copy recipients (optional)
            bcc: Blind carbon copy recipients (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if email notifications are enabled
        if not self.enabled:
            print(f"Email would be sent to {to_email}, but email notifications are disabled.")
            return False
            
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email service is not properly configured"
            )
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        
        # Format the sender with a friendly name
        msg['From'] = formataddr((self.site_name, self.from_email))
        msg['To'] = to_email
        
        # Add anti-spam headers
        msg['Message-ID'] = make_msgid(domain=self.email_domain)
        msg['Date'] = formatdate(localtime=True)
        msg['X-Mailer'] = f"CQ TRAILS Email Service {datetime.now().year}"
        # Add a unique identifier to help with threading
        msg['X-Entity-Ref-ID'] = str(uuid.uuid4())
        
        if cc:
            msg['Cc'] = ", ".join(cc)
        if bcc:
            msg['Bcc'] = ", ".join(bcc)
        
        # Add text and HTML versions
        if message_text:
            msg.attach(MIMEText(message_text, 'plain', 'utf-8'))
        
        msg.attach(MIMEText(message_html, 'html', 'utf-8'))
        
        try:
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                
                # Prepare recipients list
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                # Send email
                server.sendmail(self.from_email, recipients, msg.as_string())
                return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )
    
    def send_reservation_confirmation(self, user_email: str, user_name: str, reservation_details: dict) -> bool:
        """
        Send a reservation confirmation email
        
        Args:
            user_email: User's email address
            user_name: User's name
            reservation_details: Dictionary with reservation details
            
        Returns:
            bool: True if successful, False otherwise
        """
        subject = f"Confirmación de Reservación #{reservation_details.get('id', 'N/A')} - CQ TRAILS"
        
        # Format dates nicely
        fecha_inicio = self._format_datetime(reservation_details.get('fecha_inicio', ''))
        fecha_fin = self._format_datetime(reservation_details.get('fecha_fin', ''))
        fecha_reservacion = self._format_datetime(reservation_details.get('fecha_reservacion', ''))
        
        # Format price with commas
        total = self._format_price(reservation_details.get('total', 0))
        subtotal = self._format_price(reservation_details.get('subtotal', 0))
        
        # Get current year for copyright
        current_year = datetime.now().year
        
        # Create a unique reservation reference
        reservation_ref = f"RES-{reservation_details.get('id', 'XXX')}-{current_year}"
        
        # Create HTML message with reservation details
        html_message = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirmación de Reservación - CQ TRAILS</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 0; }}
                .header {{ background-color: #0056b3; color: white; padding: 20px; text-align: center; }}
                .logo {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
                .content {{ padding: 20px; border: 1px solid #ddd; background-color: #f9f9f9; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; padding: 20px; background-color: #efefef; }}
                .details {{ margin: 15px 0; background-color: #fff; padding: 15px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .details h3 {{ margin-top: 0; color: #0056b3; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                .details div {{ margin-bottom: 8px; }}
                .details .label {{ font-weight: bold; display: inline-block; width: 150px; }}
                .confirmation-box {{ background-color: #e7f3ff; border-left: 4px solid #0056b3; padding: 10px 15px; margin: 20px 0; }}
                .price {{ font-size: 18px; color: #0056b3; font-weight: bold; }}
                .info-section {{ margin-top: 25px; }}
                .trip-summary {{ display: flex; justify-content: space-between; background-color: #e9ecef; padding: 10px; border-radius: 5px; margin-bottom: 15px; }}
                .trip-from, .trip-to {{ flex: 1; }}
                .trip-arrow {{ display: flex; align-items: center; justify-content: center; font-size: 24px; color: #0056b3; }}
                .contact-info {{ margin-top: 20px; background-color: #e9ecef; padding: 10px; border-radius: 5px; }}
                .button {{ display: inline-block; background-color: #0056b3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
                .reservation-ref {{ text-align: center; font-size: 16px; margin-top: 15px; background-color: #f8f9fa; padding: 5px; border-radius: 3px; }}
                
                /* Estilos para responsividad */
                @media only screen and (max-width: 480px) {{
                    .trip-summary {{ flex-direction: column; }}
                    .trip-arrow {{ transform: rotate(90deg); margin: 10px 0; }}
                    .details .label {{ width: 100%; display: block; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">CQ TRAILS</div>
                    <h2>Confirmación de Reservación</h2>
                </div>
                <div class="content">
                    <p>Estimado(a) <strong>{user_name}</strong>,</p>
                    
                    <div class="confirmation-box">
                        <p>¡Nos complace informarle que su reservación <strong>#{reservation_details.get('id', 'N/A')}</strong> ha sido <strong>CONFIRMADA</strong>!</p>
                    </div>

                    <div class="reservation-ref">
                        <strong>Referencia:</strong> {reservation_ref}
                    </div>

                    <div class="trip-summary">
                        <div class="trip-from">
                            <div><strong>Origen:</strong></div>
                            <div>{reservation_details.get('ciudad_inicio', {}).get('Nombre', 'N/A')}, {reservation_details.get('ciudad_inicio', {}).get('Estado', '')}</div>
                        </div>
                        <div class="trip-arrow">→</div>
                        <div class="trip-to">
                            <div><strong>Destino:</strong></div>
                            <div>{reservation_details.get('ciudad_fin', {}).get('Nombre', 'N/A')}, {reservation_details.get('ciudad_fin', {}).get('Estado', '')}</div>
                        </div>
                    </div>
                    
                    <div class="details">
                        <h3>Detalles de la Reservación</h3>
                        <div><span class="label">ID de Reservación:</span> {reservation_details.get('id', 'N/A')}</div>
                        <div><span class="label">Estado:</span> {reservation_details.get('estado', 'Confirmada')}</div>
                        <div><span class="label">Fecha de Inicio:</span> {fecha_inicio}</div>
                        <div><span class="label">Fecha de Fin:</span> {fecha_fin}</div>
                        <div><span class="label">Fecha de Reservación:</span> {fecha_reservacion}</div>
                        <div><span class="label">Ruta Personalizada:</span> {reservation_details.get('ruta', 'Estándar')}</div>
                        <div><span class="label">Requerimientos:</span> {reservation_details.get('requerimientos', 'Ninguno')}</div>
                    </div>
                    
                    <div class="details">
                        <h3>Información de Pago</h3>
                        <div><span class="label">Subtotal:</span> ${subtotal} DOP</div>
                        <div><span class="label">Total:</span> <span class="price">${total} DOP</span></div>
                    </div>
                    
                    <div class="info-section">
                        <p>Por favor, asegúrese de llegar puntualmente a la fecha y hora acordadas. Si necesita hacer algún cambio en su reservación, comuníquese con nosotros lo antes posible.</p>
                        <p>¡Esperamos recibirle pronto en CQ TRAILS!</p>
                    </div>
                    
                    <div class="contact-info">
                        <p><strong>¿Preguntas o inquietudes?</strong></p>
                        <p>Contacte a nuestro equipo de atención al cliente:</p>
                        <p>Email: info@cqtrails.com | Teléfono: (998) 123-4567</p>
                    </div>
                </div>
                <div class="footer">
                    <p>Este es un correo electrónico automático. Por favor, no responda a este mensaje.</p>
                    <p>&copy; {current_year} CQ TRAILS. Todos los derechos reservados.</p>
                    <p>Quintana Roo, México</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version as fallback
        text_message = f"""
        CQ TRAILS - Confirmación de Reservación #{reservation_details.get('id', 'N/A')}
        
        Estimado(a) {user_name},
        
        ¡Nos complace informarle que su reservación #{reservation_details.get('id', 'N/A')} ha sido CONFIRMADA!
        
        Referencia: {reservation_ref}
        
        DETALLES DEL VIAJE:
        - Origen: {reservation_details.get('ciudad_inicio', {}).get('Nombre', 'N/A')}, {reservation_details.get('ciudad_inicio', {}).get('Estado', '')}
        - Destino: {reservation_details.get('ciudad_fin', {}).get('Nombre', 'N/A')}, {reservation_details.get('ciudad_fin', {}).get('Estado', '')}
        
        DETALLES DE LA RESERVACIÓN:
        - ID de Reservación: {reservation_details.get('id', 'N/A')}
        - Estado: {reservation_details.get('estado', 'Confirmada')}
        - Fecha de Inicio: {fecha_inicio}
        - Fecha de Fin: {fecha_fin}
        - Fecha de Reservación: {fecha_reservacion}
        - Ruta Personalizada: {reservation_details.get('ruta', 'Estándar')}
        - Requerimientos: {reservation_details.get('requerimientos', 'Ninguno')}
        
        INFORMACIÓN DE PAGO:
        - Subtotal: ${subtotal} DOP
        - Total: ${total} DOP
        
        Por favor, asegúrese de llegar puntualmente a la fecha y hora acordadas. Si necesita hacer algún cambio en su reservación, comuníquese con nosotros lo antes posible.
        
        ¡Esperamos recibirle pronto en CQ TRAILS!
        
        ¿PREGUNTAS O INQUIETUDES?
        Contacte a nuestro equipo de atención al cliente:
        Email: info@cqtrails.com | Teléfono: (998) 123-4567
        
        Este es un correo electrónico automático. Por favor, no responda a este mensaje.
        © {current_year} CQ TRAILS. Todos los derechos reservados.
        Quintana Roo, México
        """
        
        return self.send_email(
            to_email=user_email,
            subject=subject,
            message_html=html_message,
            message_text=text_message
        )
    
    def _format_datetime(self, date_str: str) -> str:
        """Format datetime string to a nice readable format"""
        if not date_str:
            return "N/A"
        
        try:
            # Try to parse ISO format datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d de %B de %Y, %H:%M")
        except (ValueError, TypeError):
            # If not a valid datetime, return as is
            return date_str
    
    def _format_price(self, price) -> str:
        """Format price with commas as thousands separator"""
        if not price:
            return "0.00"
        
        try:
            return f"{float(price):,.2f}"
        except (ValueError, TypeError):
            return str(price)

# Instantiate email service
email_service = EmailService() 