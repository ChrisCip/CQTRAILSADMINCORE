from functools import wraps
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, text, join
from typing import Optional, List, Dict, Any, Callable, Set, Tuple
import os
import logging
import traceback
import time
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

from dbcontext.models import Usuarios, Roles, Permisos, t_RolesPermisos
from dbcontext.mydb import SessionLocal
import re
from schemas.auth_schema import UserAuthInfo
from utils.jwt_utils import decode_token

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

# Configuración de uso de caché a través de variable de entorno (por defecto desactivado)
USE_PERMISSIONS_CACHE = os.getenv("USE_PERMISSIONS_CACHE", "false").lower() == "true"

# Tiempo de expiración de caché en segundos (5 minutos)
CACHE_EXPIRY_TIME = int(os.getenv("CACHE_EXPIRY_TIME", "300"))

# Cache de permisos para evitar consultas repetidas (solo si está habilitado)
# Formato: {"rol_nombre:controlador:permiso": {"value": bool, "timestamp": float}}
permission_cache: Dict[str, Dict[str, Any]] = {}

if USE_PERMISSIONS_CACHE:
    logger.info(f"Permissions cache ENABLED with {CACHE_EXPIRY_TIME}s expiry time")
else:
    logger.info("Permissions cache DISABLED - DB will always be queried")

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

def clear_permissions_cache():
    """Limpiar el caché de permisos"""
    permission_cache.clear()
    logger.info("Permission cache cleared")

class RolesPermisosMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        logger.info("RolesPermisosMiddleware initialized - Role-based Permission System")
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Log request processing
        logger.info(f"Processing request: {request.method} {request.url.path}")
        
        # Allow public paths without authentication
        for pattern in PUBLIC_PATHS:
            if re.match(pattern, request.url.path):
                logger.info(f"Public path detected: {request.url.path} - allowing without authentication")
                response = await call_next(request)
                return response
            
        # Allow OPTIONS requests (for CORS preflight)
        if request.method == "OPTIONS":
            logger.info("OPTIONS request detected - allowing without authentication")
            response = await call_next(request)
            return response
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            return JSONResponse(
                status_code=401,
                content={"detail": "No se proporcionó token de autenticación"}
            )
        
        # Extract and verify token
        token = auth_header.replace("Bearer ", "")
        try:
            # Decode token
            payload = decode_token(token)
            
            # Create user auth info object
            user = UserAuthInfo(
                user_id=payload["user_id"],
                email=payload["email"],
                role=payload["role"],
                permissions=payload.get("permissions", [])
            )
            
            # Store user in request state
            request.state.user = user
            logger.info(f"Authenticated user: {user.email}, role: {user.role}")
            
        except Exception as e:
            logger.error(f"Token authentication failed: {str(e)}")
            return JSONResponse(
                status_code=401,
                content={"detail": f"Token inválido: {str(e)}"}
            )
        
        # Get controller name from path
        path_parts = request.url.path.strip("/").split("/")
        if path_parts:
            controller = path_parts[0]
        else:
            controller = ""
            
        # Skip permission check for auth controller
        if controller == "auth":
            logger.info(f"Skipping permission check for 'auth' controller")
            response = await call_next(request)
            return response
            
        # If controller is empty, deny access to non-Admin users
        if not controller:
            if user.role == "Admin":  # Solo Admin, no 'admin' ni 'Administrador'
                logger.info(f"Admin role detected: granting access to root path")
                response = await call_next(request)
                return response
            else:
                logger.warning(f"Access denied for non-Admin role to root path")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Acceso denegado a la ruta raíz"}
                )
        
        # Get HTTP method and map to permission type
        permission_name = HTTP_METHOD_TO_PERMISSION.get(request.method)
        if not permission_name:
            logger.warning(f"Unsupported HTTP method: {request.method}")
            return JSONResponse(
                status_code=405,
                content={"detail": f"Método HTTP no soportado: {request.method}"}
            )
        
        # Check if user is Admin - only exact "Admin" role has special privileges
        if user.role == "Admin":
            logger.info(f"Admin role detected: granting access")
            response = await call_next(request)
            return response
        
        # Check if user has permission
        has_permission = await self.check_permission(user.role, controller, permission_name)
        
        if has_permission:
            logger.info(f"Permission granted for {user.role} to {permission_name} on {controller}")
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        else:
            logger.warning(f"Permission denied for {user.role} to {permission_name} on {controller}")
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Acceso denegado. No tiene permiso para {permission_name} en {controller}"
                }
            )
    
    def _get_controller_variants(self, controller: str) -> List[str]:
        """
        Generate possible controller name variants (singular/plural)
        """
        variants = [controller.lower()]
        
        # Handle Spanish pluralization rules (simplified)
        if controller.lower().endswith('es'):
            # posible singular: remove 'es'
            variants.append(controller.lower()[:-2])
        elif controller.lower().endswith('s'):
            # posible singular: remove 's'
            variants.append(controller.lower()[:-1])
        else:
            # posible plural: add 's'
            variants.append(f"{controller.lower()}s")
            # posible plural: add 'es'
            variants.append(f"{controller.lower()}es")
            
        logger.info(f"Generated controller variants for '{controller}': {variants}")
        return variants
    
    async def check_permission(self, role: str, controller: str, permission_name: str) -> bool:
        """
        Check if a role has permission for a specific controller and action
        
        Args:
            role: Role name (e.g. "Admin", "Empleado")
            controller: Controller name (e.g. "ciudades")
            permission_name: Permission name from database (Crear, Leer, Editar, Eliminar)
            
        Returns:
            bool: True if permission granted, False otherwise
        """
        # Normalize role name to lowercase for case-insensitive comparison
        role_lower = role.lower()
        
        # Generate controller variants to handle singular/plural forms
        controller_variants = self._get_controller_variants(controller)
        
        logger.info(f"Checking permission for role={role}, controller={controller} (variants={controller_variants}), permission={permission_name}")
        
        # Check cache only if enabled
        cache_key = f"{role_lower}:{controller.lower()}:{permission_name}"
        current_time = time.time()
        
        if USE_PERMISSIONS_CACHE and cache_key in permission_cache:
            cache_entry = permission_cache[cache_key]
            # Verificar si el cache ha expirado
            if current_time - cache_entry.get("timestamp", 0) < CACHE_EXPIRY_TIME:
                has_permission = cache_entry["value"]
                logger.info(f"Permission cache hit for '{cache_key}': {has_permission}")
                return has_permission
            else:
                logger.info(f"Permission cache expired for '{cache_key}', refreshing from database")
        
        # Query database for permission - always fetch fresh data
        try:
            with SessionLocal() as db:
                # Build SQL to check if role has permission for any variant of the controller
                sql = """
                SELECT p."NombrePermiso", rp."{permission}"
                FROM miguel."RolesPermisos" rp
                JOIN miguel."Roles" r ON rp."IdRol" = r."IdRol"
                JOIN miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
                WHERE LOWER(r."NombreRol") = :role_name
                AND LOWER(p."NombrePermiso") IN :controller_variants
                """.format(permission=permission_name)
                
                # Log the actual SQL and parameters for debugging
                logger.debug(f"SQL: {sql}")
                logger.debug(f"Params: role_name={role_lower}, controller_variants={tuple(controller_variants)}")
                
                # Execute query with parameters
                result = db.execute(
                    text(sql),
                    {
                        "role_name": role_lower,
                        "controller_variants": tuple(controller_variants)
                    }
                ).fetchone()
                
                if result:
                    # Second column contains the boolean permission value
                    has_permission = bool(result[1])
                    controller_name = result[0]
                    
                    # Save result in cache only if enabled
                    if USE_PERMISSIONS_CACHE:
                        permission_cache[cache_key] = {
                            "value": has_permission,
                            "timestamp": current_time
                        }
                    
                    if has_permission:
                        logger.info(f"Permission granted for {role} to {permission_name} on {controller_name}")
                    else:
                        logger.warning(f"Permission denied for {role} to {permission_name} on {controller_name}")
                    
                    return has_permission
                else:
                    # No permission record found - check deeper
                    logger.warning(f"No permission found for role={role}, controller={controller_variants}")
                    
                    # Double-check role and permission existence for better diagnosis
                    role_result = db.execute(
                        text("SELECT \"IdRol\", \"NombreRol\" FROM miguel.\"Roles\" WHERE LOWER(\"NombreRol\") = :role_name"),
                        {"role_name": role_lower}
                    ).fetchone()
                    
                    if role_result:
                        logger.info(f"Role exists in database: ID={role_result[0]}, Name={role_result[1]}")
                        
                        # Find permissions matching any controller variant
                        perm_check = db.execute(
                            text("""
                            SELECT "IdPermiso", "NombrePermiso" 
                            FROM miguel."Permisos" 
                            WHERE LOWER("NombrePermiso") IN :controller_variants
                            """),
                            {"controller_variants": tuple(controller_variants)}
                        ).fetchall()
                        
                        if perm_check:
                            logger.info(f"Found permissions in database: {[p[1] for p in perm_check]}")
                            
                            # Check if role-permission association exists but is set to false
                            for perm_id, perm_name in [(p[0], p[1]) for p in perm_check]:
                                explicit_check = db.execute(
                                    text(f"""
                                    SELECT "{permission_name}" 
                                    FROM miguel."RolesPermisos" 
                                    WHERE "IdRol" = :role_id AND "IdPermiso" = :perm_id
                                    """),
                                    {"role_id": role_result[0], "perm_id": perm_id}
                                ).fetchone()
                                
                                if explicit_check is not None:
                                    logger.info(f"Found explicit permission setting for {role}:{perm_name}:{permission_name} = {explicit_check[0]}")
                                    
                                    # Save result in cache only if enabled
                                    has_permission = bool(explicit_check[0])
                                    if USE_PERMISSIONS_CACHE:
                                        permission_cache[cache_key] = {
                                            "value": has_permission,
                                            "timestamp": current_time
                                        }
                                    return has_permission
                    else:
                        logger.warning(f"Role '{role}' not found in database")
                    
                    # Save negative result in cache only if enabled
                    if USE_PERMISSIONS_CACHE:
                        permission_cache[cache_key] = {
                            "value": False,
                            "timestamp": current_time
                        }
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            traceback.print_exc()
            return False
