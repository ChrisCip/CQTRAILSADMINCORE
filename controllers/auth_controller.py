from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import bcrypt
import time
import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import logging

from dbcontext.mydb import SessionLocal
from dbcontext.models import Usuarios, Roles, Permisos
from schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse, UserAuthInfo
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, get_current_user_optional
from utils.jwt_utils import create_access_token, decode_token, JWT_EXPIRATION_SECONDS

# Configure logger
logger = logging.getLogger("auth_controller")

# Load environment variables
load_dotenv()

# JWT Configuration
JWT_KEY = os.getenv("JWT_KEY")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
JWT_SUBJECT = os.getenv("JWT_SUBJECT")
JWT_EXPIRATION_SECONDS = 3600 * 8  # 8 hours by default

# Set up OAuth2 scheme for Swagger UI integration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
security = HTTPBearer()

# Configure router
router = APIRouter(
    prefix="/auth",
    tags=["AUTH"],
    responses={
        400: {"description": "Datos de entrada incorrectos"},
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Acceso prohibido"},
        404: {"description": "Recurso no encontrado"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash"""
    try:
        # Ensure both inputs are correctly encoded
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
            
        # Use constant time comparison to prevent timing attacks
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {str(e)}")
        # In case of error, return False for security
        return False

def hash_password(password: str) -> str:
    """Genera un hash para la contraseña"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Add this function at the top of your file to help with role name mapping
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
        
    normalized = role_map.get(role_name.lower(), role_name)
    print(f"Normalized role: {role_name} -> {normalized}")
    return normalized

# Public login endpoint - no authentication required
@router.post(
    "/login", 
    response_model=ResponseBase[TokenResponse],
    summary="Iniciar sesión en el sistema",
    operation_id="login_user",
    include_in_schema=True,
    responses={
        200: {
            "description": "Login exitoso con token JWT",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Login exitoso",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 28800,
                            "user_id": 1,
                            "role": "Administrador",
                            "email": "admin@example.com",
                            "nombre": "Administrador",
                            "apellido": "Sistema",
                            "permissions": ["crear_usuario", "eliminar_usuario"]
                        }
                    }
                }
            }
        },
        401: {"description": "Credenciales inválidas"}
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "example": "usuario@example.com"
                            },
                            "password": {
                                "type": "string",
                                "format": "password",
                                "minLength": 6,
                                "example": "contraseña123"
                            }
                        }
                    },
                    "example": {
                        "email": "usuario@example.com", 
                        "password": "contraseña123"
                    }
                }
            }
        }
    }
)
def login_user(
    login_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    """Iniciar sesión en el sistema"""
    # Find user by email
    user = db.query(Usuarios).filter(Usuarios.Email == login_data.email).first()
    
    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Check if user is active
    if not user.Activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo. Contacte al administrador."
        )
    
    # Verify password
    if not verify_password(login_data.password, user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Get role and permissions
    role = db.query(Roles).filter(Roles.IdRol == user.IdRol).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error del sistema: rol de usuario no encontrado"
        )
    
    # Get permissions
    permissions_list = [p.NombrePermiso for p in role.Permisos_]
    
    # Create JWT token using the imported function from jwt_utils
    token = create_access_token(
        user_id=user.IdUsuario,
        email=user.Email,
        role=role.NombreRol,
        permissions=permissions_list
    )
    
    # Create response
    token_response = TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user_id=user.IdUsuario,
        role=role.NombreRol,
        email=user.Email,
        nombre=user.Nombre,
        apellido=user.Apellido,
        permissions=permissions_list
    )
    
    return ResponseBase[TokenResponse](
        message="Login exitoso",
        data=token_response
    )

# Token endpoint for Swagger UI
@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=True,
    summary="Obtener token OAuth2",
    description="Endpoint compatible con el estándar OAuth2 para obtener un token JWT (usado por Swagger UI)",
    responses={
        200: {
            "description": "Token obtenido correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 28800,
                        "user_id": 1,
                        "role": "Administrador",
                        "email": "admin@example.com",
                        "nombre": "Administrador",
                        "apellido": "Sistema",
                        "permissions": ["crear_usuario", "eliminar_usuario"]
                    }
                }
            }
        },
        401: {"description": "Credenciales inválidas"}
    }
)
async def get_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint for Swagger UI authorization.
    
    - **username**: Email del usuario
    - **password**: Contraseña del usuario
    """
    # Find user by email (username in OAuth2)
    user = db.query(Usuarios).filter(Usuarios.Email == form_data.username).first()
    
    # Verify user exists and is active
    if not user or not user.Activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas o usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user role
    role = db.query(Roles).filter(Roles.IdRol == user.IdRol).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener rol del usuario"
        )
    
    # Normalize role name to ensure consistency
    normalized_role_name = normalize_role_name(role.NombreRol)
    
    # Get user permissions
    permissions_list = []
    if role.Permisos_:
        permissions_list = [permiso.NombrePermiso for permiso in role.Permisos_]
    
    # Generate JWT token with normalized role name
    token = create_access_token(
        user_id=user.IdUsuario,
        email=user.Email,  # Cambiar de user_email a email
        role=normalized_role_name,
        permissions=permissions_list
    )
    
    # Return OAuth2 compatible response with normalized role
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user_id=user.IdUsuario,
        role=normalized_role_name,
        email=user.Email,
        nombre=user.Nombre,
        apellido=user.Apellido,
        permissions=permissions_list
    )

# User registration endpoint - NO AUTHENTICATION REQUIRED
@router.post(
    "/register", 
    response_model=ResponseBase[TokenResponse], 
    status_code=status.HTTP_201_CREATED,
    include_in_schema=True,
    summary="Registrar usuario",
    description="Registra un nuevo usuario en el sistema, permitiendo especificar el rol por ID",
    responses={
        201: {
            "description": "Usuario registrado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Usuario registrado exitosamente",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 28800,
                            "user_id": 5,
                            "role": "Usuario",
                            "email": "nuevo@example.com",
                            "nombre": "Juan",
                            "apellido": "Pérez",
                            "permissions": ["ver_reservaciones"]
                        }
                    }
                }
            }
        },
        400: {"description": "Datos de entrada inválidos o email ya registrado"},
        404: {"description": "Rol no encontrado"}
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "password", "confirm_password", "nombre", "apellido"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "example": "nuevo@example.com"
                            },
                            "password": {
                                "type": "string",
                                "format": "password",
                                "minLength": 6,
                                "example": "contraseña123"
                            },
                            "confirm_password": {
                                "type": "string",
                                "example": "contraseña123"
                            },
                            "nombre": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 20,
                                "example": "Juan"
                            },
                            "apellido": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 30,
                                "example": "Pérez"
                            },
                            "idRol": {
                                "type": "integer",
                                "description": "ID del rol a asignar (2=Admin, 3=Empleado, default=4 Usuario)",
                                "example": 3
                            }
                        }
                    },
                    "example": {
                        "email": "nuevo@example.com",
                        "password": "contraseña123",
                        "confirm_password": "contraseña123",
                        "nombre": "Juan",
                        "apellido": "Pérez",
                        "idRol": 3
                    }
                }
            }
        }
    }
)
async def register(
    register_data: RegisterRequest, 
    db: Session = Depends(get_db),
):
    """
    Registra un nuevo usuario en el sistema
    
    - **email**: Email único para el nuevo usuario
    - **password**: Contraseña (mínimo 6 caracteres)
    - **confirm_password**: Debe coincidir con la contraseña
    - **nombre**: Nombre del usuario
    - **apellido**: Apellido del usuario
    - **idRol**: (Opcional) ID del rol a asignar (2=Admin, 3=Empleado, default=4 Usuario)
    """
    # Check if email already exists
    existing_user = db.query(Usuarios).filter(Usuarios.Email == register_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email ya está registrado"
        )
    
    # Determine role to assign
    if register_data.idRol is not None:
        # Verify role exists
        role = db.query(Roles).filter(Roles.IdRol == register_data.idRol).first()
        if not role:
            # List available roles for better error message
            available_roles = db.query(Roles).all()
            role_info = [f"{r.IdRol}:{r.NombreRol}" for r in available_roles]
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El rol con ID {register_data.idRol} no existe. Roles disponibles: {', '.join(role_info)}"
            )
            
        role_id = register_data.idRol
        role_name = role.NombreRol
        
        logger.info(f"Asignando rol ID {role_id} ({role_name}) especificado en la solicitud")
    else:
        # Get "Usuario" role by default using ID
        role = db.query(Roles).filter(Roles.NombreRol.ilike("usuario")).first()
        
        if not role:
            # Fallback to a default role
            role = db.query(Roles).filter(Roles.IdRol == 4).first()
            
        if not role:
            # If still no role found, list available roles for better error message
            available_roles = db.query(Roles).all()
            role_info = [f"{r.IdRol}:{r.NombreRol}" for r in available_roles]
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error: No se encontró el rol 'Usuario'. Roles disponibles: {', '.join(role_info)}"
            )
            
        role_id = role.IdRol
        role_name = role.NombreRol
        
        logger.info(f"Asignando rol ID {role_id} ({role_name}) por defecto")
    
    # Hash password
    hashed_password = hash_password(register_data.password)
    
    # Create new user
    new_user = Usuarios(
        Email=register_data.email,
        PasswordHash=hashed_password,
        Nombre=register_data.nombre,
        Apellido=register_data.apellido,
        IdRol=role_id,
        Activo=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Get user permissions
    permissions_list = []
    if role.Permisos_:
        permissions_list = [permiso.NombrePermiso for permiso in role.Permisos_]
    
    # Generate JWT token for immediate login
    token = create_access_token(
        user_id=new_user.IdUsuario,
        email=new_user.Email,
        role=role_name,
        permissions=permissions_list
    )
    
    # Create response
    token_response = TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user_id=new_user.IdUsuario,
        role=role_name,
        email=new_user.Email,
        nombre=new_user.Nombre,
        apellido=new_user.Apellido,
        permissions=permissions_list
    )
    
    return ResponseBase[TokenResponse](
        message="Usuario registrado exitosamente",
        data=token_response
    )

# Current user info endpoint - requires authentication
@router.get(
    "/me",
    response_model=ResponseBase,
    include_in_schema=True,
    summary="Información de usuario actual",
    description="Obtiene información del usuario autenticado con el token JWT",
    responses={
        200: {
            "description": "Información del usuario obtenida correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Información del usuario actual",
                        "data": {
                            "user_id": 1,
                            "email": "admin@example.com",
                            "role": "Administrador",
                            "permissions": ["crear_usuario", "eliminar_usuario"]
                        }
                    }
                }
            }
        },
        401: {"description": "Token inválido o expirado"}
    }
)
async def get_me(current_user: UserAuthInfo = Depends(get_current_user)):
    """
    Este endpoint requiere autenticación mediante token JWT.
    
    Obtiene información del usuario autenticado actualmente
    """
    return ResponseBase(
        message="Información del usuario actual",
        data={
            "user_id": current_user.user_id,
            "email": current_user.email,
            "role": current_user.role,
            "permissions": current_user.permissions
        }
    )

# Add a test endpoint to check authentication
@router.get(
    "/test-auth",
    response_model=ResponseBase,
    include_in_schema=True,
    summary="Probar autenticación",
    description="Endpoint para probar si la autenticación funciona correctamente"
)
async def test_auth(current_user: UserAuthInfo = Depends(get_current_user)):
    """
    Endpoint para probar autenticación - verificar si el token funciona
    """
    return ResponseBase(
        message="Autenticación exitosa",
        data={
            "user_id": current_user.user_id,
            "email": current_user.email,
            "role": current_user.role,
            "role_normalized": normalize_role_name(current_user.role),
            "permissions": current_user.permissions
        }
    )

# Add this diagnostic endpoint to debug roles
@router.get(
    "/debug/roles",
    response_model=ResponseBase,
    include_in_schema=True,
    summary="Debug - Ver roles",
    description="Endpoint de diagnóstico para ver roles en la base de datos"
)
async def debug_roles(db: Session = Depends(get_db)):
    """
    Endpoint de diagnóstico para ver roles en la base de datos
    """
    roles = db.query(Roles).all()
    role_info = [{"id": r.IdRol, "nombre": r.NombreRol} for r in roles]
    
    return ResponseBase(
        message="Roles en la base de datos",
        data=role_info
    )