from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dbcontext.mydb import SessionLocal, engine
from dbcontext.models import Base, Usuarios

# Import controllers
from controllers import (
    ciudad_controller, 
    permiso_controller,
    rol_controller,
    usuario_controller,
    empresa_controller,
    empleado_controller,
    vehiculo_controller,
    reservacion_controller,
    notificacion_controller,
    prefactura_controller,
    vehiculoreservacion_controller
)

# Crear las tablas en la base de datos si no existen
#Base.metadata.create_all(bind=engine)

# Create the FastAPI app with enhanced OpenAPI documentation
app = FastAPI(
    title="CQ Trails Admin API",
    description="""
    API para administración de CQ Trails.
    
    ## Funcionalidades
    
    * 📝 **CRUD completo** para todos los modelos de la base de datos
    * 🔒 **Seguridad** mediante autenticación JWT
    * 📊 **Reportes** para análisis de datos
    * 📱 **API REST** para integración con aplicaciones móviles y web
    
    ## Modelo de datos
    
    La API expone las siguientes entidades principales:
    
    * Ciudades - Información de ciudades donde operan los tours
    * Usuarios - Gestión de usuarios del sistema
    * Roles - Definición de roles y permisos
    * Permisos - Capacidades específicas en el sistema
    * Empresas - Clientes corporativos
    * Empleados - Personal de empresas cliente
    * Vehículos - Flota disponible
    * Reservaciones - Solicitudes de servicio
    * Prefacturas - Proceso de facturación
    """,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Ciudades",
            "description": "Operaciones con ciudades donde opera CQ Trails"
        },
        {
            "name": "Permisos",
            "description": "Gestión de permisos para control de acceso"
        },
        {
            "name": "Roles",
            "description": "Administración de roles de usuario"
        },
        {
            "name": "Usuarios",
            "description": "Gestión de usuarios del sistema"
        },
        {
            "name": "Empresas",
            "description": "Clientes corporativos de CQ Trails"
        },
        {
            "name": "Empleados",
            "description": "Personal de empresas cliente"
        },
        {
            "name": "Vehiculos",
            "description": "Flota de vehículos disponibles para tours"
        },
        {
            "name": "Reservaciones",
            "description": "Reservas de tours y experiencias"
        },
        {
            "name": "Notificaciones",
            "description": "Sistema de notificaciones para reservaciones"
        },
        {
            "name": "PreFacturas",
            "description": "Gestión de prefacturas para servicios"
        },
        {
            "name": "VehiculosReservaciones",
            "description": "Asignación de vehículos a reservaciones"
        },
        {
            "name": "Status",
            "description": "Estado del servicio API"
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,
        "deepLinking": True,
        "displayRequestDuration": True,
        "syntaxHighlight.theme": "obsidian"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include routers from controllers
app.include_router(ciudad_controller.router)
app.include_router(permiso_controller.router)
app.include_router(rol_controller.router)
app.include_router(usuario_controller.router)
app.include_router(empresa_controller.router)
app.include_router(empleado_controller.router)
app.include_router(vehiculo_controller.router)
app.include_router(reservacion_controller.router)
app.include_router(notificacion_controller.router)
app.include_router(prefactura_controller.router)
app.include_router(vehiculoreservacion_controller.router)

@app.get("/", tags=["Status"])
def read_root():
    """
    Endpoint para verificar que la API está funcionando correctamente.
    
    Returns:
        dict: Mensaje de bienvenida y estado del servicio
    """
    return {
        "message": "Bienvenido a CQ Trails Admin API",
        "status": "online",
        "swagger_ui": "/docs",
        "redoc_ui": "/redoc",
        "version": "1.0.0"
    }