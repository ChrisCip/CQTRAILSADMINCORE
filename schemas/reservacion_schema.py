from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from schemas.ciudad_schema import CiudadResponse

# Basic schemas without circular references
class ReservacionBase(BaseModel):
    FechaInicio: datetime = Field(..., description="Fecha de inicio de la reservación")
    FechaFin: datetime = Field(..., description="Fecha de fin de la reservación")
    IdUsuario: Optional[int] = Field(None, description="ID del usuario que hizo la reservación (para usuario final)")
    IdEmpleado: Optional[int] = Field(None, description="ID del empleado relacionado (para empresas)")
    IdEmpresa: Optional[int] = Field(None, description="ID de la empresa relacionada (para empresas)")
    ciudadinicioid: Optional[int] = Field(None, description="ID de la ciudad de inicio")
    ciudadfinid: Optional[int] = Field(None, description="ID de la ciudad de fin")
    RutaPersonalizada: Optional[str] = Field(None, description="Descripción de ruta personalizada")
    RequerimientosAdicionales: Optional[str] = Field(None, description="Requerimientos adicionales de la reservación")
    Estado: Optional[str] = Field("Pendiente", description="Estado de la reservación (Pendiente, Aprobada, Denegada)")

    model_config = ConfigDict(from_attributes=True)

class ReservacionCreate(ReservacionBase):
    """Modelo para crear una nueva reservación"""
    pass

class ReservacionUpdate(BaseModel):
    """Modelo para actualizar una reservación existente"""
    FechaInicio: Optional[datetime] = None
    FechaFin: Optional[datetime] = None
    IdUsuario: Optional[int] = None
    IdEmpleado: Optional[int] = None
    IdEmpresa: Optional[int] = None
    ciudadinicioid: Optional[int] = None
    ciudadfinid: Optional[int] = None
    RutaPersonalizada: Optional[str] = None
    RequerimientosAdicionales: Optional[str] = None
    Estado: Optional[str] = None
    FechaConfirmacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Simple models for related entities to avoid circular references
class UsuarioSimple(BaseModel):
    IdUsuario: int
    Nombre: str
    Apellido: str
    Email: str
    
    model_config = ConfigDict(from_attributes=True)

class UsuarioModificacion(BaseModel):
    """Información del usuario que realizó modificaciones a la reservación"""
    IdUsuario: int
    Nombre: str
    Apellido: str
    
    model_config = ConfigDict(from_attributes=True)

class EmpleadoSimple(BaseModel):
    IdEmpleado: int
    
    model_config = ConfigDict(from_attributes=True)

class EmpresaSimple(BaseModel):
    IdEmpresa: int
    Nombre: str
    
    model_config = ConfigDict(from_attributes=True)

# Approval and rejection models
class ReservacionApproval(BaseModel):
    """Modelo para aprobar una reservación"""
    IdUsuarioModificacion: int = Field(..., description="ID del usuario que aprueba la reservación")
    Comentario: Optional[str] = Field(None, description="Comentario sobre la aprobación")

class ReservacionRejection(BaseModel):
    """Modelo para denegar una reservación"""
    IdUsuarioModificacion: int = Field(..., description="ID del usuario que deniega la reservación")
    MotivoRechazo: str = Field(..., description="Motivo por el cual se rechaza la reservación", 
                              example="No hay vehículos disponibles para las fechas solicitadas")

class ReservacionAprobacionDenegacion(BaseModel):
    """Modelo unificado para aprobar o denegar una reservación"""
    IdUsuarioModificacion: int = Field(..., description="ID del usuario que procesa la reservación")
    MotivoRechazo: Optional[str] = Field(None, description="Motivo del rechazo (solo para denegación)")
    Comentario: Optional[str] = Field(None, description="Comentario adicional")

# Response models with relationships but avoiding deep nesting



class ReservacionResponse(BaseModel):
    IdReservacion: int
    FechaInicio: datetime
    FechaFin: datetime
    IdUsuario: Optional[int] = None
    IdEmpleado: Optional[int] = None
    IdEmpresa: Optional[int] = None
    ciudadinicioid: Optional[int] = None
    ciudadfinid: Optional[int] = None
    RutaPersonalizada: Optional[str] = None
    RequerimientosAdicionales: Optional[str] = None
    Estado: Optional[str] = "Pendiente"
    FechaReservacion: Optional[datetime] = None
    FechaConfirmacion: Optional[datetime] = None

    
    model_config = ConfigDict(from_attributes=True)

class ReservacionDetailResponse(ReservacionResponse):
    """Modelo extendido con detalles de la reservación"""
    Usuarios1: Optional[UsuarioSimple] = None
    Empleados1: Optional[EmpleadoSimple] = None
    Empresas1: Optional[EmpresaSimple] = None
    CiudadInicio: Optional[CiudadResponse] = None
    CiudadFin: Optional[CiudadResponse] = None
    FechaModificacion: Optional[datetime] = None
    MotivoRechazo: Optional[str] = None
    UsuarioModificacion: Optional[UsuarioModificacion] = None
    
    model_config = ConfigDict(from_attributes=True)
