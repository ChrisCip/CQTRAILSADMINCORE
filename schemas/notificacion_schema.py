from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NotificacionBase(BaseModel):
    IdReservacion: int
    TipoNotificacion: str

class NotificacionCreate(NotificacionBase):
    pass

class NotificacionUpdate(BaseModel):
    TipoNotificacion: Optional[str] = None

class ReservacionSimple(BaseModel):
    IdReservacion: int
    FechaInicio: datetime
    FechaFin: datetime
    Estado: str
    
    class Config:
        from_attributes = True

class NotificacionResponse(NotificacionBase):
    IdNotificacion: int
    FechaEnvio: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificacionDetailResponse(NotificacionResponse):
    Reservaciones1: Optional[ReservacionSimple] = None
    
    class Config:
        from_attributes = True
