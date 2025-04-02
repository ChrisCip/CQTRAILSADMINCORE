from pydantic import BaseModel
from typing import Optional, List

class PermisoBase(BaseModel):
    NombrePermiso: str
    Descripcion: Optional[str] = None

class PermisoCreate(PermisoBase):
    pass

class PermisoUpdate(PermisoBase):
    NombrePermiso: Optional[str] = None

class PermisoResponse(PermisoBase):
    IdPermiso: int
    
    class Config:
        from_attributes = True
