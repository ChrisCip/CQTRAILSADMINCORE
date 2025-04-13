from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from typing import Optional, List

class LoginRequest(BaseModel):
    """Esquema para solicitud de login"""
    email: EmailStr = Field(..., description="Email del usuario", example="usuario@example.com")
    password: str = Field(
        ..., 
        description="Contraseña del usuario", 
        min_length=6,
        example="contraseña123"
    )
    
    # Este formato es importante para Pydantic v2
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "usuario@example.com",
                "password": "contraseña123"
            }
        }
    }

class RegisterRequest(BaseModel):
    """Esquema para registro de usuario"""
    email: EmailStr = Field(..., description="Email del usuario", example="nuevo@example.com")
    password: str = Field(
        ..., 
        description="Contraseña del usuario", 
        min_length=6,
        example="contraseña123"
    )
    confirm_password: str = Field(
        ..., 
        description="Confirmar contraseña",
        example="contraseña123"
    )
    nombre: str = Field(
        ..., 
        description="Nombre del usuario", 
        min_length=2, 
        max_length=20,
        example="Juan"
    )
    apellido: str = Field(
        ..., 
        description="Apellido del usuario", 
        min_length=2, 
        max_length=30,
        example="Pérez"
    )
    idRol: Optional[int] = Field(
        None, 
        description="ID del rol a asignar (2=Admin, 3=Empleado). Si no se proporciona, se asigna rol de Usuario.",
        example=3,
        ge=1
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Las contraseñas no coinciden')
        return v
    
    # Este formato es importante para Pydantic v2
    model_config = {
        "json_schema_extra": {
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

class TokenResponse(BaseModel):
    """Esquema para respuesta de token"""
    access_token: str = Field(..., description="Token JWT")
    token_type: str = Field("bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")
    user_id: int = Field(..., description="ID del usuario")
    role: str = Field(..., description="Rol del usuario")
    email: str = Field(..., description="Email del usuario")
    nombre: str = Field(..., description="Nombre del usuario")
    apellido: str = Field(..., description="Apellido del usuario")
    permissions: List[str] = Field([], description="Permisos del usuario")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 28800,
                "user_id": 1,
                "role": "Administrador",
                "email": "admin@example.com",
                "nombre": "Admin",
                "apellido": "Usuario",
                "permissions": ["crear_usuario", "editar_usuario", "eliminar_usuario"]
            }
        }
    )

class UserAuthInfo(BaseModel):
    """Esquema para información de usuario autenticado"""
    user_id: int
    email: str
    role: str
    permissions: List[str] = []
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "email": "admin@example.com",
                "role": "Administrador",
                "permissions": ["crear_usuario", "editar_usuario", "eliminar_usuario"]
            }
        }
    )
