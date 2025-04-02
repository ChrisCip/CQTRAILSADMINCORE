from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class VehiculoReservacionBase(BaseModel):
    IdVehiculo: int
    IdReservacion: int
    EstadoAsignacion: Optional[str] = "Activa"

class VehiculoReservacionCreate(VehiculoReservacionBase):
    pass

class VehiculoReservacionUpdate(BaseModel):
    EstadoAsignacion: Optional[str] = None

class VehiculoSimple(BaseModel):
    IdVehiculo: int
    Placa: str
    Modelo: str
    TipoVehiculo: str
    
    class Config:
        from_attributes = True

class ReservacionSimple(BaseModel):
    IdReservacion: int
    FechaInicio: datetime
    FechaFin: datetime
    Estado: str
    
    class Config:
        from_attributes = True

class VehiculoReservacionResponse(VehiculoReservacionBase):
    FechaAsignacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class VehiculoReservacionDetailResponse(VehiculoReservacionResponse):
    Vehiculos1: Optional[VehiculoSimple] = None
    Reservaciones1: Optional[ReservacionSimple] = None
    
    class Config:
        from_attributes = True
