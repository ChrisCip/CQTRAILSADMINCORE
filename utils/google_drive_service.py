import os
import json
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import tempfile

class GoogleDriveService:
    """Servicio para manejar operaciones con Google Drive"""
    
    def __init__(self, folder_id: Optional[str] = None, folder_name: str = "CQTrailsVehiculos", credentials_path: Optional[str] = None):
        """
        Inicializa el servicio de Google Drive.
        
        Args:
            folder_id: ID de la carpeta de Google Drive donde se subirán los archivos (opcional)
            folder_name: Nombre de la carpeta a crear si folder_id no existe
            credentials_path: Ruta al archivo de credenciales de Google. Si es None, se busca en ubicaciones predeterminadas.
        """
        self.folder_id = folder_id
        self.folder_name = folder_name
        self.logger = logging.getLogger("GoogleDriveService")
        
        # Intentar cargar credenciales desde variables de entorno primero
        if self._load_credentials_from_env():
            self.logger.info("Credenciales cargadas exitosamente desde variables de entorno")
            return
        
        # Si no hay variables de entorno, buscar archivo de credenciales
        self.logger.info("Buscando archivo de credenciales...")
        if credentials_path is None:
            possible_paths = [
                os.path.join(os.getcwd(), "credentials.json"),
                os.path.join(os.getcwd(), "utils", "credentials.json"),
                os.path.join(os.getcwd(), "app", "credentials.json"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    credentials_path = path
                    self.logger.info(f"Archivo de credenciales encontrado en: {path}")
                    break
        
        if not credentials_path or not os.path.exists(credentials_path):
            self.logger.warning("No se encontró el archivo de credenciales. Se usará la autenticación por defecto.")
            self.credentials = None
        else:
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    credentials_path, 
                    scopes=['https://www.googleapis.com/auth/drive']
                )
            except Exception as e:
                self.logger.error(f"Error al cargar credenciales desde archivo: {str(e)}")
                self.credentials = None

    def _load_credentials_from_env(self) -> bool:
        """
        Carga las credenciales desde variables de entorno
        
        Las credenciales deben estar definidas como:
        - GOOGLE_CREDENTIALS_JSON: El contenido completo del archivo credentials.json como string
        o como variables individuales:
        - GOOGLE_TYPE 
        - GOOGLE_PROJECT_ID
        - GOOGLE_PRIVATE_KEY_ID
        - GOOGLE_PRIVATE_KEY
        - GOOGLE_CLIENT_EMAIL
        - GOOGLE_CLIENT_ID
        - GOOGLE_AUTH_URI
        - GOOGLE_TOKEN_URI
        - GOOGLE_AUTH_PROVIDER_X509_CERT_URL
        - GOOGLE_CLIENT_X509_CERT_URL
        - GOOGLE_UNIVERSE_DOMAIN
        
        Returns:
            bool: True si las credenciales se cargaron correctamente, False en caso contrario
        """
        try:
            # Verificar si existe la variable con el JSON completo
            creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                # Crear un archivo temporal con las credenciales
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                    temp_file.write(creds_json)
                    temp_path = temp_file.name
                
                try:
                    self.credentials = service_account.Credentials.from_service_account_file(
                        temp_path, 
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    return True
                finally:
                    # Eliminar el archivo temporal
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            # Verificar si existen las variables individuales
            required_vars = [
                'GOOGLE_TYPE', 'GOOGLE_PROJECT_ID', 'GOOGLE_PRIVATE_KEY_ID', 
                'GOOGLE_PRIVATE_KEY', 'GOOGLE_CLIENT_EMAIL', 'GOOGLE_CLIENT_ID',
                'GOOGLE_AUTH_URI', 'GOOGLE_TOKEN_URI', 'GOOGLE_AUTH_PROVIDER_X509_CERT_URL',
                'GOOGLE_CLIENT_X509_CERT_URL'
            ]
            
            # Verificar que todas las variables requeridas existan
            if not all(var in os.environ for var in required_vars):
                self.logger.debug("No se encontraron todas las variables de entorno necesarias para las credenciales")
                return False
            
            # Construir el diccionario de credenciales
            creds_dict = {
                "type": os.environ.get('GOOGLE_TYPE'),
                "project_id": os.environ.get('GOOGLE_PROJECT_ID'),
                "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.environ.get('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                "auth_uri": os.environ.get('GOOGLE_AUTH_URI'),
                "token_uri": os.environ.get('GOOGLE_TOKEN_URI'),
                "auth_provider_x509_cert_url": os.environ.get('GOOGLE_AUTH_PROVIDER_X509_CERT_URL'),
                "client_x509_cert_url": os.environ.get('GOOGLE_CLIENT_X509_CERT_URL')
            }
            
            # Añadir universe_domain si está disponible
            if 'GOOGLE_UNIVERSE_DOMAIN' in os.environ:
                creds_dict["universe_domain"] = os.environ.get('GOOGLE_UNIVERSE_DOMAIN')
            
            # Crear un archivo temporal con las credenciales
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                json.dump(creds_dict, temp_file)
                temp_path = temp_file.name
            
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    temp_path, 
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                return True
            finally:
                # Eliminar el archivo temporal
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
        except Exception as e:
            self.logger.error(f"Error al cargar credenciales desde variables de entorno: {str(e)}")
            return False
    
    def _get_drive_service(self):
        """Crea y devuelve el servicio de Google Drive"""
        if self.credentials:
            return build('drive', 'v3', credentials=self.credentials)
        else:
            # Fallback a la autenticación por defecto
            self.logger.warning("Usando autenticación por defecto")
            return build('drive', 'v3')
    
    def _find_or_create_folder(self, service):
        """
        Busca la carpeta por su ID o nombre, o crea una nueva si no existe.
        
        Args:
            service: Servicio de Google Drive
        
        Returns:
            ID de la carpeta
        """
        try:
            # Si tenemos un ID de carpeta, verificar si existe
            if self.folder_id:
                try:
                    folder = service.files().get(fileId=self.folder_id, fields="id,name").execute()
                    self.logger.info(f"Carpeta encontrada: {folder.get('name')} (ID: {folder.get('id')})")
                    return self.folder_id
                except HttpError as error:
                    if error.resp.status == 404:
                        self.logger.warning(f"Carpeta con ID {self.folder_id} no encontrada. Buscando por nombre...")
                    else:
                        raise
            
            # Buscar carpeta por nombre
            query = f"name='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            folders = response.get('files', [])
            
            if folders:
                folder_id = folders[0].get('id')
                self.logger.info(f"Carpeta existente encontrada: {self.folder_name} (ID: {folder_id})")
                return folder_id
            
            # Crear nueva carpeta
            folder_metadata = {
                'name': self.folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            # Establecer permisos públicos para la carpeta
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            service.permissions().create(
                fileId=folder_id,
                body=permission
            ).execute()
            
            self.logger.info(f"Carpeta creada exitosamente: {self.folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            self.logger.error(f"Error al buscar/crear carpeta: {str(e)}")
            return None
    
    def upload_file(self, file_path: str, file_name: Optional[str] = None, mime_type: Optional[str] = None) -> Optional[str]:
        """
        Sube un archivo a Google Drive.
        
        Args:
            file_path: Ruta local del archivo a subir
            file_name: Nombre que tendrá el archivo en Google Drive (opcional, usa el nombre original si no se especifica)
            mime_type: Tipo MIME del archivo (opcional, se detecta automáticamente si no se especifica)
        
        Returns:
            URL del archivo en Google Drive o None si hubo un error
        """
        if not os.path.exists(file_path):
            self.logger.error(f"El archivo no existe: {file_path}")
            return None
        
        # Usar el nombre del archivo si no se proporciona uno
        if file_name is None:
            file_name = os.path.basename(file_path)
        
        # Detectar tipo MIME basado en la extensión si no se proporciona
        if mime_type is None:
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif extension == '.png':
                mime_type = 'image/png'
            elif extension == '.gif':
                mime_type = 'image/gif'
            elif extension == '.pdf':
                mime_type = 'application/pdf'
            else:
                mime_type = 'application/octet-stream'
        
        try:
            # Crear cliente de Google Drive
            service = self._get_drive_service()
            
            # Encontrar o crear carpeta
            folder_id = self._find_or_create_folder(service)
            
            # Metadatos del archivo, incluyendo la carpeta destino
            file_metadata = {
                'name': file_name
            }
            
            # Agregar la carpeta como parent solo si se encontró o creó correctamente
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Crear el objeto MediaFileUpload
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            # Crear el archivo en Google Drive
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()
            
            # Configurar permisos para acceso público
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            service.permissions().create(
                fileId=file.get('id'),
                body=permission
            ).execute()
            
            # Obtener el enlace actualizado después de cambiar permisos
            updated_file = service.files().get(
                fileId=file.get('id'),
                fields='webViewLink,webContentLink'
            ).execute()
            
            # Devolver la URL al archivo
            file_url = updated_file.get('webViewLink') or updated_file.get('webContentLink')
            if not file_url:
                file_url = f"https://drive.google.com/file/d/{file.get('id')}/view?usp=sharing"
            
            self.logger.info(f"Archivo subido correctamente: {file_url}")
            return file_url
            
        except HttpError as error:
            self.logger.error(f"Error del API de Google Drive: {str(error)}")
            return None
        except Exception as e:
            self.logger.error(f"Error al subir archivo a Google Drive: {str(e)}")
            return None 