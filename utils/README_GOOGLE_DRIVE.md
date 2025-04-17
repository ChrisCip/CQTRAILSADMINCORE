# Configuración de Google Drive API

Este proyecto utiliza Google Drive API para almacenar imágenes de vehículos. A continuación, se detallan los pasos para configurar y utilizar esta funcionalidad.

## Requisitos previos

1. Tener una cuenta de Google
2. Acceso a [Google Cloud Console](https://console.cloud.google.com/)

## Pasos para configurar Google Drive API

### 1. Crear un proyecto en Google Cloud Console

1. Accede a [Google Cloud Console](https://console.cloud.google.com/)
2. Haz clic en "Seleccionar un proyecto" y luego en "Nuevo proyecto"
3. Asigna un nombre al proyecto (por ejemplo, "CQTrails") y haz clic en "Crear"
4. Selecciona el proyecto recién creado

### 2. Habilitar Google Drive API

1. En el menú lateral, ve a "APIs y servicios" > "Biblioteca"
2. Busca "Google Drive API" y selecciónala
3. Haz clic en "Habilitar"

### 3. Crear credenciales de cuenta de servicio

1. En el menú lateral, ve a "APIs y servicios" > "Credenciales"
2. Haz clic en "Crear credenciales" y selecciona "Cuenta de servicio"
3. Asigna un nombre a la cuenta de servicio (por ejemplo, "cqtrails-service")
4. Haz clic en "Crear y continuar"
5. En "Otorgar a esta cuenta de servicio acceso al proyecto", selecciona el rol "Editor" para tener permisos de escritura
6. Haz clic en "Continuar" y luego en "Listo"

### 4. Crear y descargar la clave JSON

1. En la página de "Credenciales", busca la cuenta de servicio que acabas de crear y haz clic en ella
2. Ve a la pestaña "Claves"
3. Haz clic en "Agregar clave" > "Crear nueva clave"
4. Selecciona "JSON" y haz clic en "Crear"
5. Se descargará un archivo JSON con las credenciales. Guárdalo como `credentials.json`

### 5. Colocar las credenciales en el proyecto

1. Coloca el archivo `credentials.json` descargado en una de estas ubicaciones:
   - En la raíz del proyecto
   - En la carpeta `/utils/`
   - En la carpeta `/app/`

### 6. Funcionamiento de carpetas en Google Drive (Importante)

El sistema ahora tiene la capacidad de gestionar carpetas automáticamente:

1. **Creación automática**: Si no existe una carpeta para guardar los archivos, el sistema la creará automáticamente con el nombre `CQTrailsVehiculos` en la raíz de tu Google Drive.

2. **Permisos de carpeta**: La carpeta será creada con permisos públicos de lectura para que las imágenes sean accesibles.

3. **Configuración manual** (opcional): Si deseas usar una carpeta específica existente:
   - Obtén el ID de la carpeta desde la URL de Google Drive (la parte después de "folders/" en la URL)
   - Modifica el parámetro `folder_id` al instanciar `GoogleDriveService` en `controllers/vehiculo_controller.py`

   ```python
   google_drive_service = GoogleDriveService(folder_id="tu_id_de_carpeta_aqui")
   ```

## Solución de problemas

### Error de autenticación

Si obtienes errores de autenticación, verifica:
- Que el archivo `credentials.json` esté correctamente ubicado
- Que la API de Google Drive esté habilitada
- Que la cuenta de servicio tenga permisos suficientes

### Errores de permisos

Si las imágenes se suben pero no son accesibles públicamente:
- Verifica que la configuración de permisos en el código esté correcta
- Asegúrate de que la carpeta de destino no tenga restricciones especiales

### Error "File not found" para folder_id

Este error ocurre cuando el ID de carpeta especificado no existe o no es accesible. El sistema manejará este error automáticamente:
1. Intentará buscar una carpeta con el nombre predeterminado
2. Si no la encuentra, creará una nueva carpeta automáticamente

### Dependencias faltantes

Asegúrate de tener instaladas todas las dependencias necesarias ejecutando:

```bash
pip install -r requirements.txt
``` 