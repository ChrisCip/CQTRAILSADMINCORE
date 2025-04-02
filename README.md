# CQ Trails Admin API

API para administración de CQ Trails, desarrollada con FastAPI y SQLAlchemy para gestión de reservaciones, vehículos, usuarios y más.

## Tabla de Contenidos

1. [Requisitos](#requisitos)
2. [Instalación](#instalación)
3. [Configuración](#configuración)
4. [Ejecución](#ejecución)
5. [Estructura del Proyecto](#estructura-del-proyecto)
6. [Documentación API](#documentación-api)
7. [Uso de Ejemplos](#uso-de-ejemplos)
8. [Solución de Problemas](#solución-de-problemas)
9. [Desarrollo y Contribución](#desarrollo-y-contribución)

## Requisitos

Para ejecutar este proyecto necesitarás:

- Python 3.8 o superior
- PostgreSQL 12 o superior
- pip (gestor de paquetes de Python)
- Un editor de código (VS Code, PyCharm, etc.)

## Instalación

1. **Clonar el repositorio:**

```bash
git clone https://github.com/tuusuario/CQTRAILSADMINCORE.git
cd CQTRAILSADMINCORE
```

2. **Crear un entorno virtual:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. **Instalar dependencias:**

```bash
pip install -r requirements.txt
```

## Configuración

1. **Configurar la base de datos PostgreSQL:**
   - Crear una base de datos en PostgreSQL
   - Asegurarse de tener un usuario con permisos de creación y modificación

2. **Configurar variables de entorno:**
   - Copiar el archivo `.env.example` a `.env` (si no existe, crearlo)
   - Editar el archivo `.env` con los datos de conexión a la base de datos

```
DATABASE_URL=postgresql://usuario:contraseña@host:puerto/nombre_db?sslmode=require
JWT_KEY=tu_clave_secreta_para_jwt
JWT_ISSUER=cqtrails
JWT_AUDIENCE=cq_api_clients
JWT_SUBJECT=cq_api_access
```

3. **Configurar esquema inicial (solo primera vez):**
   - Descomentar la línea `Base.metadata.create_all(bind=engine)` en `main.py` solo para la primera ejecución
   - Volver a comentarla después de la primera ejecución

## Ejecución

### Método 1: Usando script de ejecución (recomendado)

```bash
python run_server.py
```

### Método 2: Usando uvicorn directamente

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Al iniciar, verás mensajes como:
```
⚡ Iniciando CQ Trails Admin API
📄 Documentación Swagger UI: http://127.0.0.1:8000/docs
📖 Documentación ReDoc: http://127.0.0.1:8000/redoc
🔎 API Status: http://127.0.0.1:8000/
```

## Estructura del Proyecto

```
CQTRAILSADMINCORE/
├── controllers/           # Controladores para cada modelo
│   ├── __init__.py        
│   ├── ciudad_controller.py
│   ├── usuario_controller.py
│   └── ...
├── dbcontext/             # Configuración de base de datos
│   ├── mydb.py            # Conexión a la base de datos
│   └── models.py          # Modelos SQLAlchemy
├── schemas/               # Esquemas Pydantic
│   ├── __init__.py
│   ├── ciudad_schema.py
│   └── ...
├── main.py                # Punto de entrada de la aplicación
├── run_server.py          # Script para ejecutar el servidor
├── .env                   # Variables de entorno (no incluir en git)
├── requirements.txt       # Dependencias del proyecto
└── README.md              # Este archivo
```

## Documentación API

Una vez que el servidor esté corriendo, podrás acceder a:

- **Swagger UI**: http://127.0.0.1:8000/docs
   - Interfaz interactiva para probar todos los endpoints
   - Documentación completa de parámetros y respuestas

- **ReDoc**: http://127.0.0.1:8000/redoc
   - Documentación detallada en formato más legible
   - Modelos de datos y ejemplos de uso

- **API Status**: http://127.0.0.1:8000/
   - Verificación básica del estado del API

## Uso de Ejemplos

El archivo `test_main.http` contiene ejemplos de uso para cada endpoint. Puedes utilizarlo con la extensión "REST Client" de VS Code o adaptarlo a herramientas como Postman.

### Ejemplos básicos:

1. **Verificar que el API está funcionando:**
```
GET http://127.0.0.1:8000/
```

2. **Listar ciudades:**
```
GET http://127.0.0.1:8000/ciudades/
```

3. **Crear una reservación:**
```
POST http://127.0.0.1:8000/reservaciones/
Content-Type: application/json

{
  "FechaInicio": "2023-10-01T10:00:00",
  "FechaFin": "2023-10-03T18:00:00",
  "IdUsuario": 1,
  "RutaPersonalizada": "Ruta por la selva",
  "RequerimientosAdicionales": "Necesito 4x4"
}
```

## Solución de Problemas

### Error de conexión a la base de datos

Verifica:
- Que la URL de conexión en `.env` es correcta
- Que PostgreSQL está corriendo
- Que el usuario tiene permisos adecuados

### Error de módulos no encontrados

Si ves errores de importación, asegúrate de:
- Tener activado el entorno virtual
- Haber instalado todas las dependencias: `pip install -r requirements.txt`

### Error de relaciones ambiguas

Si ves `AmbiguousForeignKeysError`, significa que hay relaciones mal definidas. Verifica:
- Las relaciones en `models.py`
- Usar `foreign_keys` explícitamente en relaciones complejas

## Desarrollo y Contribución

1. **Crear una nueva rama para desarrollo:**
```bash
git checkout -b feature/nueva-funcionalidad
```

2. **Ejecutar pruebas antes de enviar cambios:**
```bash
# (Configurar tests en el futuro)
```

3. **Seguir convenciones de código:**
- Usar PEP 8 para Python
- Documentar nuevos endpoints
- Mantener compatibilidad con versiones anteriores

---

Para más información, contactar al equipo de desarrollo de CQ Trails.
