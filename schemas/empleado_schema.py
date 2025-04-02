from pydantic import BaseModel
from typing import Optional, List

class EmpleadoBase(BaseModel):
    IdEmpresa: int
    IdUsuario: int

class EmpleadoCreate(EmpleadoBase):
    pass

class EmpleadoUpdate(BaseModel):
    IdEmpresa: Optional[int] = None
    IdUsuario: Optional[int] = None

class UsuarioSimple(BaseModel):
    IdUsuario: int
    Nombre: str
    Apellido: str
    Email: str
    
    class Config:
        from_attributes = True

class EmpresaSimple(BaseModel):
    IdEmpresa: int
    Nombre: str
    
    class Config:
        from_attributes = True

class EmpleadoResponse(EmpleadoBase):
    IdEmpleado: int
    
    class Config:
        from_attributes = True

class EmpleadoDetailResponse(EmpleadoResponse):
    Empresas1: Optional[EmpresaSimple] = None
    Usuarios1: Optional[UsuarioSimple] = None
    
    class Config:
        from_attributes = True
