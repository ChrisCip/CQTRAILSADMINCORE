from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class EmpresaBase(BaseModel):
    Nombre: str
    ContactoEmail: EmailStr
    ContactoTelefono: str
    Activo: Optional[bool] = True

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    Nombre: Optional[str] = None
    ContactoEmail: Optional[EmailStr] = None
    ContactoTelefono: Optional[str] = None
    Activo: Optional[bool] = None

class EmpresaResponse(EmpresaBase):
    IdEmpresa: int
    FechaRegistro: Optional[datetime] = None
    
    class Config:
        from_attributes = True
