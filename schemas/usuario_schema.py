from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UsuarioBase(BaseModel):
    Email: EmailStr
    Nombre: str
    Apellido: str
    IdRol: int
    Activo: Optional[bool] = True

class UsuarioCreate(UsuarioBase):
    Password: str  # Plain password to be hashed

class UsuarioUpdate(BaseModel):
    Email: Optional[EmailStr] = None
    Nombre: Optional[str] = None
    Apellido: Optional[str] = None
    IdRol: Optional[int] = None
    Activo: Optional[bool] = None

class RolSimple(BaseModel):
    IdRol: int
    NombreRol: str
    
    class Config:
        from_attributes = True

class UsuarioResponse(UsuarioBase):
    IdUsuario: int
    FechaRegistro: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UsuarioDetailResponse(UsuarioResponse):
    Role: Optional[RolSimple] = None
    
    class Config:
        from_attributes = True
