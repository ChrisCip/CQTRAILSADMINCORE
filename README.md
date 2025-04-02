# CQ Trails Admin API

API para administración de CQ Trails, desarrollada con FastAPI.

## Requisitos

- Python 3.8+
- PostgreSQL

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/tuusuario/CQTRAILSADMINCORE.git
cd CQTRAILSADMINCORE
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno en el archivo `.env`:

```
DATABASE_URL=postgresql://usuario:password@host/dbname
JWT_KEY=your_secret_key
JWT_ISSUER=your_issuer
JWT_AUDIENCE=your_audience
JWT_SUBJECT=your_subject
```

## Ejecución

### Método 1: Usando script de ejecución

```bash
python run_server.py
```

### Método 2: Usando uvicorn directamente

```bash
uvicorn main:app --reload
```

## Documentación API

Una vez que el servidor esté en ejecución, puedes acceder a:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Estado del API**: http://127.0.0.1:8000/

## Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación
- `controllers/`: Controladores para cada modelo
- `schemas/`: Esquemas Pydantic para validación de datos
- `dbcontext/`: Contexto de base de datos y modelos
