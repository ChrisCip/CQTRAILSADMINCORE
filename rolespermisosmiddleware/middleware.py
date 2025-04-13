from functools import wraps
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, text, join
from typing import Optional, List, Dict, Any, Callable, Set
import os
import logging
import traceback
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

from dbcontext.models import Usuarios, Roles, Permisos, t_RolesPermisos
from dbcontext.mydb import SessionLocal
import re

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("roles_middleware")

# Load environment variables
load_dotenv()

# JWT Configuration with fallback values for safety
JWT_KEY = os.getenv("JWT_KEY")
if not JWT_KEY:
    logger.warning("JWT_KEY not found in environment variables! Using fallback key for development")
    JWT_KEY = "fallback_dev_key_not_for_production"

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

logger.info(f"Middleware initialized with JWT_ALGORITHM: {JWT_ALGORITHM}")
logger.debug(f"JWT_KEY first 5 chars: {JWT_KEY[:5] if JWT_KEY else ''}...")

security = HTTPBearer()

# Mapeo de métodos HTTP a nombres de permisos en la base de datos
HTTP_METHOD_TO_PERMISSION = {
    'GET': 'Leer',         # Leer -> booleano en la BD
    'POST': 'Crear',       # Crear -> booleano en la BD
    'PUT': 'Editar',       # Editar -> booleano en la BD
    'PATCH': 'Editar',     # También usa Editar -> booleano en la BD
    'DELETE': 'Eliminar'   # Eliminar -> booleano en la BD
}

# Cache de permisos para evitar consultas repetidas
# Formato: {"rol_nombre": {"controlador": {"Leer": bool, "Crear": bool, ...}}}
PERMISOS_CACHE: Dict[str, Dict[str, Dict[str, bool]]] = {}

# Lista de rutas públicas que no requieren autenticación
PUBLIC_PATHS = [
    r"^/docs$",
    r"^/docs/.*$",
    r"^/redoc$",
    r"^/openapi.json$",
    r"^/$",
    r"^/auth/login$",
    r"^/auth/register$",
    r"^/favicon.ico$",
]

class RolesPermisosMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        logger.info("RolesPermisosMiddleware initialized - Role-based Permission System")
        
    async def dispatch(self, request: Request, call_next):
        # Verificar si la ruta es pública
        path = request.url.path
        method = request.method
        
        logger.info(f"Procesando petición: {method} {path}")
        
        # Ruta pública - dar acceso
        if any(re.match(pattern, path) for pattern in PUBLIC_PATHS):
            logger.info(f"Ruta pública, omitiendo verificación: {path}")
            return await call_next(request)
            
        # Verificar token en headers directamente
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning(f"No se proporcionó token de autenticación para: {method} {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "No autenticado"}
            )
        
        # Extraer y verificar token directamente en el middleware
        token = auth_header.replace('Bearer ', '')
        
        try:
            # Decodificar token usando la utilidad existente
            from utils.jwt_utils import decode_token
            from schemas.auth_schema import UserAuthInfo
            
            payload = decode_token(token)
            
            # Extraer la información de usuario del token
            user_id = payload.get("user_id")
            email = payload.get("email")
            user_role = payload.get("role", "")
            
            if not user_id or not user_role:
                logger.error(f"Token sin información de usuario o rol: {user_id}, {user_role}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token inválido: falta información de usuario o rol"}
                )
            
            # Crear objeto de usuario y almacenarlo en request.state
            request.state.user = UserAuthInfo(
                user_id=user_id,
                email=email,
                role=user_role,
                permissions=payload.get("permissions", [])
            )
            
            logger.info(f"Usuario autenticado: {email}, rol: {user_role}, id: {user_id}")
            
        except Exception as e:
            logger.error(f"Error al decodificar token: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Token inválido: {str(e)}"}
            )
            
        # Extraer el controlador del path
        # Ejemplo: /usuarios/1 -> usuarios
        path_parts = path.strip("/").split("/")
        if not path_parts:
            logger.error(f"Ruta inválida: {path}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Ruta inválida"}
            )
            
        controller_name = path_parts[0].lower()
        logger.info(f"Controlador solicitado: {controller_name}")
        
        # Obtener el ID del rol directamente de la base de datos
        try:
            db = SessionLocal()
            try:
                # 1. Obtener el ID del rol desde la tabla Roles
                role_query = text("""
                SELECT "IdRol" FROM miguel."Roles" 
                WHERE LOWER("NombreRol") = LOWER(:role_name)
                """)
                
                role_result = db.execute(role_query, {"role_name": user_role})
                role_id = role_result.scalar()
                
                if not role_id:
                    logger.error(f"Rol '{user_role}' no encontrado en la base de datos")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": f"Acceso denegado: Rol '{user_role}' no encontrado"}
                    )
                    
                logger.info(f"ID del rol '{user_role}': {role_id}")
                
                # Normalizar nombre de controlador para variantes singular/plural
                controller_variants = [controller_name]
                if controller_name.endswith('es'):
                    controller_variants.append(controller_name[:-2])  # ciudades -> ciudad
                elif controller_name.endswith('s'):
                    controller_variants.append(controller_name[:-1])  # usuarios -> usuario
                else:
                    controller_variants.append(controller_name + 's')  # usuario -> usuarios
                    controller_variants.append(controller_name + 'es')  # ciudad -> ciudades
                
                # 2. Obtener el permiso correspondiente para el controlador solicitado
                permission_found = False
                permission_id = None
                used_controller = None
                
                for variant in controller_variants:
                    permission_query = text("""
                    SELECT "IdPermiso", "NombrePermiso" FROM miguel."Permisos" 
                    WHERE LOWER("NombrePermiso") = LOWER(:controller_name)
                    """)
                    
                    permission_result = db.execute(permission_query, {"controller_name": variant})
                    permission_row = permission_result.first()
                    
                    if permission_row:
                        permission_id = permission_row[0]
                        used_controller = permission_row[1]
                        permission_found = True
                        logger.info(f"Permiso encontrado para controlador '{variant}': ID={permission_id}")
                        break
                
                if not permission_found:
                    logger.error(f"No se encontró permiso para controlador: {controller_name}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": f"Acceso denegado: No existe permiso para '{controller_name}'"}
                    )
                
                # 3. Verificar la relación rol-permiso y los valores booleanos específicos
                permission_column = HTTP_METHOD_TO_PERMISSION.get(method)
                if not permission_column:
                    logger.error(f"Método HTTP no soportado: {method}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": f"Método HTTP no soportado: {method}"}
                    )
                
                logger.info(f"Verificando permiso '{permission_column}' para método {method}")
                
                # Consulta SQL para verificar el permiso booleano específico
                access_query = text(f"""
                SELECT rp."{permission_column}" 
                FROM miguel."RolesPermisos" rp
                WHERE rp."IdRol" = :role_id AND rp."IdPermiso" = :permission_id
                """)
                
                access_result = db.execute(access_query, {
                    "role_id": role_id,
                    "permission_id": permission_id
                })
                
                has_permission_row = access_result.first()
                
                # Si no se encontró relación rol-permiso o el valor booleano es False
                if not has_permission_row:
                    logger.error(f"No existe relación rol-permiso para rol {role_id} y permiso {permission_id}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": f"Acceso denegado: No existe relación rol-permiso para {user_role} y {used_controller}"}
                    )
                
                # Obtener el valor booleano específico para este método HTTP
                boolean_value = bool(has_permission_row[0])
                logger.info(f"Valor booleano para permiso '{permission_column}': {boolean_value}")
                
                if not boolean_value:
                    logger.error(f"El rol {user_role} no tiene permiso '{permission_column}' para {used_controller}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": f"Acceso denegado: El rol '{user_role}' no tiene permiso para {method} en '{used_controller}'"}
                    )
                
                # Si llegamos aquí, el usuario tiene permiso
                logger.info(f"Permiso concedido para {user_role} en {used_controller}, método {method}")
                return await call_next(request)
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error al verificar permisos: {str(e)}")
            traceback.print_exc()
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Error del servidor al verificar permisos: {str(e)}"}
            )

    def check_permission(self, role_name: str, controller_name: str, http_method: str) -> bool:
        """
        Verifica si un rol tiene permiso para acceder a un controlador con un método HTTP
        
        Args:
            role_name: Nombre del rol
            controller_name: Nombre del controlador (extraído de la URL)
            http_method: Método HTTP (GET, POST, PUT, DELETE)
            
        Returns:
            bool: True si tiene permiso, False si no
        """
        # Admin siempre tiene todos los permisos (no debería llegar aquí, pero por si acaso)
        if role_name == "Admin" or role_name.lower() == "admin":
            logger.info(f"Rol Admin tiene permiso directo")
            return True
            
        # Convertir método HTTP a nombre de permiso
        permission_name = HTTP_METHOD_TO_PERMISSION.get(http_method)
        if not permission_name:
            logger.error(f"Método HTTP no soportado: {http_method}")
            return False
            
        logger.info(f"Verificando permiso {permission_name} para rol '{role_name}' en controlador '{controller_name}'")
        
        # Normalizar nombres - Ajustar para manejar nombres en singular/plural
        controller_variants = [controller_name]
        
        # Agregar variantes singular/plural
        if controller_name.endswith('es'):
            controller_variants.append(controller_name[:-2])  # ciudades -> ciudad
        elif controller_name.endswith('s'):
            controller_variants.append(controller_name[:-1])  # usuarios -> usuario
        else:
            controller_variants.append(controller_name + 's')  # usuario -> usuarios
            controller_variants.append(controller_name + 'es')  # ciudad -> ciudades
            
        logger.info(f"Variantes de controlador a verificar: {controller_variants}")
        
        # Verificar en caché primero
        if role_name in PERMISOS_CACHE:
            # Buscar en las diferentes variantes del controlador en caché
            for variant in controller_variants:
                if variant in PERMISOS_CACHE[role_name]:
                    # Obtener el valor booleano específico según el permiso requerido
                    result = PERMISOS_CACHE[role_name][variant].get(permission_name, False)
                    logger.info(f"Resultado de caché para {variant}: {result}")
                    return result
            
        # Si no está en caché, consultar a la base de datos
        try:
            db = SessionLocal()
            try:
                # Consultar directamente con SQL
                db_query = text("""
                SELECT 
                    r."IdRol", r."NombreRol",
                    p."IdPermiso", p."NombrePermiso",
                    CAST(rp."Crear" AS BOOLEAN) as crear, 
                    CAST(rp."Editar" AS BOOLEAN) as editar, 
                    CAST(rp."Leer" AS BOOLEAN) as leer, 
                    CAST(rp."Eliminar" AS BOOLEAN) as eliminar
                FROM 
                    miguel."RolesPermisos" rp
                JOIN 
                    miguel."Roles" r ON rp."IdRol" = r."IdRol"
                JOIN 
                    miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
                WHERE 
                    LOWER(r."NombreRol") = :role_name AND
                    (LOWER(p."NombrePermiso") = :controller OR 
                     LOWER(p."NombrePermiso") = :controller_alt)
                """)
                
                # Buscar con cada variante del controlador
                rol_permiso = None
                for variant in controller_variants:
                    params = {
                        "role_name": role_name.lower(),
                        "controller": variant.lower(),
                        "controller_alt": variant.lower()
                    }
                    
                    result = db.execute(db_query, params)
                    rol_permiso = result.first()
                    if rol_permiso:
                        logger.info(f"Encontrado permiso para controlador: {variant}")
                        break
                
                if not rol_permiso:
                    logger.info(f"No se encontró permiso en BD para {role_name} y {controller_name}")
                    
                    # Si es Admin y no hay permiso explícito, conceder acceso por defecto
                    if role_name.lower() == "admin":
                        logger.info(f"Concediendo permiso a Admin por defecto")
                        return True
                    
                    # Si no es Admin y no hay permiso explícito, se deniega el acceso
                    return False
                
                # Guardar en caché
                if role_name not in PERMISOS_CACHE:
                    PERMISOS_CACHE[role_name] = {}
                
                # Imprimir valor crudo para depuración
                logger.info(f"Valores crudos del permiso: {rol_permiso}")
                
                # Extraer valores booleanos correctamente según la columna correspondiente en "RolesPermisos"
                PERMISOS_CACHE[role_name][controller_name] = {
                    # Mapeo de métodos HTTP a campos booleanos en la BD:
                    # POST -> Crear, PUT/PATCH -> Editar, GET -> Leer, DELETE -> Eliminar
                    "Crear": bool(rol_permiso[4]),     # para método POST
                    "Editar": bool(rol_permiso[5]),    # para métodos PUT/PATCH
                    "Leer": bool(rol_permiso[6]),      # para método GET
                    "Eliminar": bool(rol_permiso[7])   # para método DELETE
                }
                
                # Mostrar explícitamente el tipo de dato y valor para depuración
                for perm, value in PERMISOS_CACHE[role_name][controller_name].items():
                    logger.info(f"Permiso '{perm}': valor={value}, tipo={type(value)}")
                
                # Verificar si tiene el permiso específico según el método HTTP solicitado
                # Por ejemplo, si es GET, se verifica el valor de "Leer"
                permission_value = PERMISOS_CACHE[role_name][controller_name].get(permission_name, False)
                logger.info(f"Verificando permiso '{permission_name}' para método HTTP '{http_method}': {permission_value}")
                
                return permission_value
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error al verificar permisos: {e}")
            traceback.print_exc()
            return False
            
def clear_permissions_cache():
    """Limpia la caché de permisos para forzar recarga desde DB"""
    global PERMISOS_CACHE
    old_size = len(PERMISOS_CACHE)
    PERMISOS_CACHE = {}
    logger.info(f"Caché de permisos limpiada. Tamaño anterior: {old_size} roles")
    return {"status": "success", "message": f"Cache limpiada. {old_size} roles eliminados de la caché"}
