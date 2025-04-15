from typing import Optional

class ReservacionDetailResponse(ReservacionResponse):
    """Esquema para respuesta detallada de reservación"""
    IdUsuario: Optional[int] = None
    Usuario: Optional[UsuarioSimpleResponse] = None
    IdEmpleado: Optional[int] = None
    Empleado: Optional[EmpleadoResponse] = None
    IdEmpresa: Optional[int] = None
    Empresa: Optional[EmpresaResponse] = None
    IdUsuarioModificacion: Optional[int] = None
    UsuarioModificacion: Optional[UsuarioSimpleResponse] = None
    # Ciudad origen y destino
    CiudadInicio: Optional[CiudadResponse] = None
    CiudadFin: Optional[CiudadResponse] = None
    # ciudad_inicio: Optional[CiudadResponse] = None
    # ciudad_fin: Optional[CiudadResponse] = None

    class Config:
        orm_mode = True 