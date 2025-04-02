from pydantic import BaseModel
from typing import Optional, List, Set

class RolBase(BaseModel):
    NombreRol: str
    Descripcion: Optional[str] = None

class RolCreate(RolBase):
    pass

class RolUpdate(RolBase):
    NombreRol: Optional[str] = None

class PermisoSimple(BaseModel):
    IdPermiso: int
    NombrePermiso: str
    
    class Config:
        from_attributes = True

class RolResponse(RolBase):
    IdRol: int
    
    class Config:
        from_attributes = True

class RolDetailResponse(RolResponse):
    Permisos: List[PermisoSimple] = []
    
    class Config:
        from_attributes = True
