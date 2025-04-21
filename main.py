from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from dbcontext.mydb import SessionLocal, engine
import re
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import auth_controller first (important for order)
from controllers import auth_controller

# Import other controllers
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
    vehiculoreservacion_controller,
    rolespermiso_controller
)

# Import the roles permissions middleware
from rolespermisosmiddleware import RolesPermisosMiddleware
from dependencies.auth import decode_token, UserAuthInfo
from dbcontext.models import Usuarios

# Function to generate unique operation IDs
def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "api"
    operation_id = route.operation_id or f"{route.name}_{route.path.replace('/', '_')}"
    return f"{tag.lower()}_{operation_id}"

# Create the FastAPI app with enhanced OpenAPI documentation
app = FastAPI(
    title="CQ Trails Admin API",
    description="""
    API para administración de CQ Trails con autenticación JWT y control de acceso basado en roles.
    
    ## Autenticación
    
    Para acceder a los endpoints protegidos:
    1. Use el endpoint `/auth/login` para obtener un token JWT
    2. Incluya el token en el header `Authorization: Bearer <token>`
    
    ## Roles y Permisos
    
    * **Administrador**: Acceso completo al sistema
    * **Gerente**: Acceso a gestión de reservaciones y vehículos
    * **Empleado**: Acceso limitado a funciones básicas
    * **Usuario**: Solo acceso a sus propios datos
    
    ## Funcionalidades
    
    * 📝 **CRUD completo** para todos los modelos con permisos adecuados
    * 🔒 **Seguridad** mediante autenticación JWT y RBAC
    * 📊 **Reportes** para análisis de datos
    * 📱 **API REST** para integración con aplicaciones
    """,
    version="1.0.0",
    generate_unique_id_function=custom_generate_unique_id,
    openapi_tags=[
        {
            "name": "AUTH",
            "description": "Autenticación y gestión de sesiones mediante JWT"
        },
        {
            "name": "Usuarios",
            "description": "Gestión de usuarios del sistema"
        },
        {
            "name": "Roles",
            "description": "Administración de roles y permisos"
        },
        {
            "name": "Ciudades",
            "description": "Operaciones con ciudades donde opera CQ Trails"
        },
        {
            "name": "Permisos",
            "description": "Gestión de permisos para control de acceso"
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
        "persistAuthorization": True,
        "defaultModelsExpandDepth": 1,
        "docExpansion": "list",
        "filter": True,
        "tryItOutEnabled": True,  # Enable "Try it out" by default
        "displayRequestDuration": True,  # Show request duration
        "syntaxHighlight.theme": "monokai",  # Syntax highlighting theme
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "deepLinking": True,
    }
)


app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las origenes en desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Roles Permissions middleware for permission checking
app.add_middleware(RolesPermisosMiddleware)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include auth router first (unprotected endpoints)
app.include_router(auth_controller.router)

# Status endpoint (public)
@app.get("/", tags=["Status"])
def read_root():
    """API status check - no authentication required"""
    return {
        "message": "Bienvenido a CQ Trails Admin API",
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0"
    }

# Include all protected routers
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
app.include_router(rolespermiso_controller.router)

# Update the custom_openapi function

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ensure components section exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # Ensure schemas section exists in components
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    # Add JWT security scheme with improved description for clarity
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authentication. Ingrese SOLO el token JWT (sin la palabra 'bearer' y sin comillas) obtenido desde /auth/login"
        }
    }
    
    # Expanded list of public endpoints that don't need authentication
    public_paths = [
        "/auth/login", 
        "/auth/token", 
        "/auth/register", 
        "/auth/debug/roles",
        "/"  # Root endpoint
    ]
    
    # Fix schema references in paths and apply security to all endpoints
    for path_key, path_item in openapi_schema["paths"].items():
        # Fix references
        for method_key, method_item in path_item.items():
            # Skip OPTIONS method (for CORS)
            if method_key.lower() == "options":
                continue
                
            # Check if this is a public path that doesn't need auth
            is_public = False
            for public_path in public_paths:
                if path_key == public_path or path_key.startswith(f"{public_path}/"):
                    is_public = True
                    break
            
            # Apply or remove security requirement based on path
            if not is_public:
                # Set security requirement for protected endpoints
                method_item["security"] = [{"bearerAuth": []}]
            elif "security" in method_item:
                # Explicitly remove any security requirements from public routes
                del method_item["security"]
            
            # Fix references in responses
            if "responses" in method_item:
                for response_key, response_item in method_item["responses"].items():
                    if "content" in response_item:
                        for content_type, content_item in response_item["content"].items():
                            if "schema" in content_item and "$ref" in content_item["schema"]:
                                ref = content_item["schema"]["$ref"]
                                if not ref.startswith("#/components/"):
                                    if ref.startswith("#/schemas/"):
                                        content_item["schema"]["$ref"] = ref.replace("#/schemas/", "#/components/schemas/")
            
            # Fix references in request bodies
            if "requestBody" in method_item and "content" in method_item["requestBody"]:
                for content_type, content_item in method_item["requestBody"]["content"].items():
                    if "schema" in content_item and "$ref" in content_item["schema"]:
                        ref = content_item["schema"]["$ref"]
                        if not ref.startswith("#/components/"):
                            if ref.startswith("#/schemas/"):
                                content_item["schema"]["$ref"] = ref.replace("#/schemas/", "#/components/schemas/")
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi