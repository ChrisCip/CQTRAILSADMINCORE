from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict

class RolPermisoBase(BaseModel):
    """Esquema base para permisos de rol"""
    IdRol: int = Field(..., description="ID del rol")
    IdPermiso: int = Field(..., description="ID del permiso")
    Crear: bool = Field(False, description="Permiso para crear")
    Editar: bool = Field(False, description="Permiso para editar")
    Leer: bool = Field(False, description="Permiso para leer")
    Eliminar: bool = Field(False, description="Permiso para eliminar")

class RolPermisoCreate(RolPermisoBase):
    """Esquema para crear permiso de rol"""
    pass

class RolPermisoUpdate(BaseModel):
    """Esquema para actualizar permiso de rol"""
    Crear: Optional[bool] = Field(None, description="Permiso para crear")
    Editar: Optional[bool] = Field(None, description="Permiso para editar")
    Leer: Optional[bool] = Field(None, description="Permiso para leer")
    Eliminar: Optional[bool] = Field(None, description="Permiso para eliminar")

class RolPermisoResponse(RolPermisoBase):
    """Esquema para respuesta de permiso de rol"""
    NombreRol: str = Field(..., description="Nombre del rol")
    NombrePermiso: str = Field(..., description="Nombre del permiso")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "IdRol": 1,
                "IdPermiso": 2,
                "Crear": True,
                "Editar": True,
                "Leer": True,
                "Eliminar": False,
                "NombreRol": "Gerente",
                "NombrePermiso": "Reservaciones"
            }
        }
    )

class RolPermisoByController(BaseModel):
    """Esquema para comprobar permisos por controlador"""
    tabla: str = Field(..., description="Nombre del controlador/tabla")
    Crear: bool = Field(False, description="Permiso para crear")
    Editar: bool = Field(False, description="Permiso para editar")
    Leer: bool = Field(False, description="Permiso para leer")
    Eliminar: bool = Field(False, description="Permiso para eliminar")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tabla": "usuarios",
                "Crear": True,
                "Editar": True,
                "Leer": True,
                "Eliminar": False
            }
        }
    )

class PermisosResumen(BaseModel):
    """Resumen de permisos por controlador para un rol"""
    controladores: Dict[str, RolPermisoByController] = Field(
        {}, 
        description="Mapa de controladores a permisos"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "controladores": {
                    "usuarios": {
                        "tabla": "usuarios",
                        "Crear": True,
                        "Editar": True,
                        "Leer": True,
                        "Eliminar": False
                    }
                }
            }
        }
    ) 