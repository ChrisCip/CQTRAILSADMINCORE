from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from typing import List, Callable, Optional
from dotenv import load_dotenv

from schemas.auth_schema import UserAuthInfo
from dbcontext.mydb import SessionLocal
from dbcontext.models import Usuarios, Roles
from utils.jwt_utils import decode_token  # Importamos solo lo que necesitamos

# Load environment variables
load_dotenv()

# JWT Configuration
JWT_KEY = os.getenv("JWT_KEY")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
JWT_SUBJECT = os.getenv("JWT_SUBJECT")

# Security scheme for bearer token
security = HTTPBearer(
    scheme_name="JWT Authentication",
    description="Enter JWT token (without 'bearer' prefix)",
    auto_error=False  # Set this here instead of in Security function
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
    request: Request = None
) -> UserAuthInfo:
    """
    Authenticate and get current user from JWT token
    
    This dependency validates the JWT token and returns user information.
    All protected endpoints should depend on this.
    """
    if not credentials:
        print("No se proporcionó token de autenticación")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    try:
        # Extract and verify token
        print(f"Decodificando token: {credentials.credentials[:20]}...")
        payload = decode_token(credentials.credentials)
        print(f"Token decodificado correctamente para usuario: {payload.get('email')}")
        
        # Check if user still exists and is active
        user_id = payload.get("user_id")
        user = db.query(Usuarios).filter(
            Usuarios.IdUsuario == user_id, 
            Usuarios.Activo == True
        ).first()
        
        if not user:
            print(f"Usuario inactivo o no encontrado: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo o no encontrado",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Create user info object
        user_info = UserAuthInfo(
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            permissions=payload.get("permissions", [])
        )
        
        # Store user info in request state for middleware
        if request:
            print(f"Guardando información del usuario en request.state: {user_info.email}, rol: {user_info.role}")
            request.state.user = user_info
        else:
            print("ADVERTENCIA: request es None, no se puede guardar la información del usuario")
        
        return user_info
    except Exception as e:
        # Usar Exception genérica en lugar de PyJWT específico para evitar errores de importación
        print(f"Error al decodificar token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> Optional[UserAuthInfo]:
    """
    Optional authentication - doesn't raise an exception if token is missing
    
    This is useful for endpoints that can work both with and without authentication,
    or that have different behavior depending on whether the user is authenticated.
    """
    if not credentials:
        return None
        
    try:
        # Extract and verify token
        payload = decode_token(credentials.credentials)
        
        # Check if user still exists and is active
        user_id = payload.get("user_id")
        user = db.query(Usuarios).filter(
            Usuarios.IdUsuario == user_id, 
            Usuarios.Activo == True
        ).first()
        
        if not user:
            return None
        
        # Create user info object
        user_info = UserAuthInfo(
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            permissions=payload.get("permissions", [])
        )
        
        return user_info
    except:
        # Any error with the token means we return None
        return None

def require_role(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory for role-based access control
    
    Args:
        allowed_roles: List of role names that are allowed to access the endpoint
        
    Returns:
        Dependency function that checks if the current user has an allowed role
    """
    async def role_dependency(current_user: UserAuthInfo = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de estos roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_dependency

def require_permission(required_permissions: List[str]) -> Callable:
    """
    Dependency factory for permission-based access control
    
    Args:
        required_permissions: List of permission names required to access the endpoint
        
    Returns:
        Dependency function that checks if the current user has the required permissions
    """
    async def permission_dependency(current_user: UserAuthInfo = Depends(get_current_user)):
        # Admins always have access to everything
        if current_user.role == "Administrador":
            return current_user
            
        # Check if user has any of the required permissions
        user_permissions = set(current_user.permissions)
        if not any(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de estos permisos: {', '.join(required_permissions)}"
            )
        return current_user
    return permission_dependency

# Add role name normalization similar to auth_controller
def normalize_role_name(role_name):
    """
    Normalize role names to handle case differences and variations
    between code expectations and database values
    """
    role_map = {
        # Database values (lowercase for case-insensitive comparison)
        "admin": "Administrador",
        "usuario": "Usuario",
        # Add other mappings as needed
    }
    
    if not role_name:
        return None
        
    return role_map.get(role_name.lower(), role_name)

def require_admin(current_user: UserAuthInfo = Depends(get_current_user)) -> UserAuthInfo:
    """
    Dependency for admin-only endpoints
    
    This is a shortcut for require_role(["Administrador"])
    """
    # Compare normalized roles
    admin_roles = ["Administrador", "ADMIN", "admin"]
    if current_user.role not in admin_roles and normalize_role_name(current_user.role) != "Administrador":
        print(f"Access denied: User role '{current_user.role}' is not admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol de Administrador."
        )
    return current_user
