from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PreFacturaBase(BaseModel):
    IdReservacion: int
    CostoVehiculo: Decimal
    CostoTotal: Decimal
    CostoAdicional: Optional[Decimal] = Decimal('0.00')
    ArchivoPDF: Optional[str] = None

class PreFacturaCreate(PreFacturaBase):
    pass

class PreFacturaUpdate(BaseModel):
    CostoVehiculo: Optional[Decimal] = None
    CostoTotal: Optional[Decimal] = None
    CostoAdicional: Optional[Decimal] = None
    ArchivoPDF: Optional[str] = None

class ReservacionSimple(BaseModel):
    IdReservacion: int
    FechaInicio: datetime
    FechaFin: datetime
    Estado: str
    
    class Config:
        from_attributes = True

class PreFacturaResponse(PreFacturaBase):
    IdPreFactura: int
    FechaGeneracion: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class PreFacturaDetailResponse(PreFacturaResponse):
    Reservaciones1: Optional[ReservacionSimple] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }
