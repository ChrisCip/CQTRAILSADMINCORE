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

# Cache for permissions to reduce database queries
permission_cache: Dict[Tuple[str, str], bool] = {}

class RolesPermisosMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        logger.info("RolesPermisosMiddleware initialized - Role-based Permission System")
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Log request processing
        logger.info(f"Processing request: {request.method} {request.url.path}")
        
        # Allow public paths without authentication
        public_paths = ["/auth/login", "/auth/register", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in public_paths or request.url.path.startswith("/static/"):
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
            
        # Skip permission check for auth controller and if no controller in path
        if controller == "auth" or not controller:
            logger.info(f"Skipping permission check for '{controller}' controller")
            response = await call_next(request)
            return response
        
        # Check permission based on role and controller
        # Admin role has access to everything
        is_admin = user.role == "Admin" or user.role == "Administrador" or user.role == "administrador"
        
        if is_admin:
            logger.info(f"Admin user detected ({user.role}): granting access")
            response = await call_next(request)
            return response
        
        # Map HTTP method to permission type
        method_to_permission = {
            "GET": "Read",
            "POST": "Create", 
            "PUT": "Edit",
            "PATCH": "Edit",
            "DELETE": "Delete"
        }
        
        permission_type = method_to_permission.get(request.method)
        if not permission_type:
            logger.warning(f"Unsupported HTTP method: {request.method}")
            return JSONResponse(
                status_code=405,
                content={"detail": f"Método HTTP no soportado: {request.method}"}
            )
        
        # Check if user has permission
        has_permission = await self.check_permission(user.role, controller, permission_type)
        
        if has_permission:
            logger.info(f"Permission granted for {user.role} to {permission_type} on {controller}")
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        else:
            logger.warning(f"Permission denied for {user.role} to {permission_type} on {controller}")
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Acceso denegado. No tiene permiso para {permission_type} en {controller}"
                }
            )
    
    async def check_permission(self, role: str, controller: str, permission_type: str) -> bool:
        """
        Check if a role has permission for a specific controller and action
        
        Args:
            role: Role name (e.g. "Admin", "Empleado")
            controller: Controller name (e.g. "ciudades")
            permission_type: Permission type (Create, Read, Edit, Delete)
            
        Returns:
            bool: True if permission granted, False otherwise
        """
        # Normalize controller name to handle singular/plural variants
        controller_variants = self._get_controller_variants(controller)
        
        # Log the controller name and its variants
        logger.info(f"Checking permission for role={role}, controller={controller} (variants={controller_variants}), permission={permission_type}")
        
        # Map permission type to database column names
        db_permission_columns = {
            "Create": "Crear",
            "Read": "Leer",
            "Edit": "Editar",
            "Delete": "Eliminar"
        }
        
        db_permission_column = db_permission_columns.get(permission_type)
        if not db_permission_column:
            logger.error(f"Unknown permission type: {permission_type}")
            return False
        
        # Check cache first
        cache_key = (role, f"{controller}:{permission_type}")
        if cache_key in permission_cache:
            logger.info(f"Permission cache hit for {cache_key}: {permission_cache[cache_key]}")
            return permission_cache[cache_key]
        
        # Query database for permission
        try:
            with SessionLocal() as db:
                # Use a CTE (Common Table Expression) to make the query more efficient
                query = text(f"""
                    WITH role_data AS (
                        SELECT "IdRol" FROM miguel."Roles" WHERE LOWER("NombreRol") = LOWER(:role)
                    ),
                    permission_data AS (
                        SELECT "IdPermiso" FROM miguel."Permisos" 
                        WHERE LOWER("NombrePermiso") IN :controller_variants
                    )
                    SELECT 
                        r."IdRol", 
                        p."IdPermiso", 
                        rp."{db_permission_column}" as permission_value
                    FROM miguel."RolesPermisos" rp
                    JOIN role_data r ON rp."IdRol" = r."IdRol"
                    JOIN permission_data p ON rp."IdPermiso" = p."IdPermiso"
                """)
                
                # Convert controller variants to lowercase for case-insensitive matching
                lowercase_variants = [v.lower() for v in controller_variants]
                
                result = db.execute(
                    query, 
                    {"role": role, "controller_variants": tuple(lowercase_variants)}
                ).fetchone()
                
                if result:
                    # Check if the specific permission type is granted
                    has_permission = bool(result["permission_value"])
                    logger.info(f"Permission check result: role={role}, controller={controller}, {permission_type}={has_permission}")
                    
                    # Update cache
                    permission_cache[cache_key] = has_permission
                    return has_permission
                else:
                    logger.warning(f"No permission record found for role={role}, controller={controller}")
                    
                    # Check if role exists
                    role_check = db.execute(
                        text('SELECT "IdRol" FROM miguel."Roles" WHERE LOWER("NombreRol") = LOWER(:role)'),
                        {"role": role}
                    ).fetchone()
                    
                    if not role_check:
                        logger.error(f"Role '{role}' not found in database")
                        
                    # Check if permission exists
                    perm_check = db.execute(
                        text('SELECT "IdPermiso", "NombrePermiso" FROM miguel."Permisos" WHERE LOWER("NombrePermiso") IN :controller_variants'),
                        {"controller_variants": tuple(lowercase_variants)}
                    ).fetchall()
                    
                    if not perm_check:
                        logger.error(f"No permission found for controller variants: {controller_variants}")
                    else:
                        logger.info(f"Found permissions: {perm_check}")
                    
                    # Update cache with negative result
                    permission_cache[cache_key] = False
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            traceback.print_exc()
            return False
    
    def _get_controller_variants(self, controller: str) -> List[str]:
        """
        Generate possible variations of a controller name
        
        Args:
            controller: Original controller name
            
        Returns:
            List of possible controller name variations
        """
        variants = [controller]
        
        # Handle common singular/plural cases
        if controller.endswith('es'):
            # Spanish plural ending (e.g. "ciudades" -> "ciudad")
            variants.append(controller[:-2])
        elif controller.endswith('s'):
            # English/Spanish plural ending (e.g. "usuarios" -> "usuario")
            variants.append(controller[:-1])
        elif controller.endswith('d'):
            # For singular "ciudad" add "ciudades"
            variants.append(controller + 'es')
        else:
            # Add simple plural form
            variants.append(controller + 's')
        
        logger.info(f"Generated controller variants for '{controller}': {variants}")
        return variants

def clear_permissions_cache():
    """Limpia la caché de permisos para forzar recarga desde DB"""
    global PERMISOS_CACHE
    old_size = len(PERMISOS_CACHE)
    PERMISOS_CACHE = {}
    logger.info(f"Caché de permisos limpiada. Tamaño anterior: {old_size} roles")
    return {"status": "success", "message": f"Cache limpiada. {old_size} roles eliminados de la caché"}
