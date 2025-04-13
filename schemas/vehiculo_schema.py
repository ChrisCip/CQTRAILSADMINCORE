from pydantic import BaseModel
from typing import Optional, List

class VehiculoBase(BaseModel):
    Placa: str
    Modelo: str
    TipoVehiculo: str
    Capacidad: int
    Ano: int
    Price: int
    Disponible: Optional[bool] = True
    Image_url: Optional[str] = None

class VehiculoCreate(VehiculoBase):
    pass

class VehiculoUpdate(BaseModel):
    Placa: Optional[str] = None
    Modelo: Optional[str] = None
    TipoVehiculo: Optional[str] = None
    Capacidad: Optional[int] = None
    Ano: Optional[int] = None
    Price: Optional[int] = None
    Disponible: Optional[bool] = None
    Image_url: Optional[str] = None

class VehiculoResponse(VehiculoBase):
    IdVehiculo: int
    
    class Config:
        from_attributes = True

class VehiculoDisponibilidad(BaseModel):
    """Modelo para actualizar exclusivamente la disponibilidad de un vehículo"""
    disponible: bool
