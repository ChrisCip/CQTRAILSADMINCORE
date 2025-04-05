from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

# Import necessary models and schemas
from dbcontext.mydb import SessionLocal
from dbcontext.models import Reservaciones, Usuarios, Empleados, Empresas, Roles
from schemas.reservacion_schema import (
    ReservacionCreate, ReservacionUpdate, ReservacionResponse, ReservacionDetailResponse,
    ReservacionApproval, ReservacionRejection
)
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, require_admin  # Añadir esta importación

# Create router for this controller
router = APIRouter(
    prefix="/reservaciones",
    tags=["Reservaciones"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Acceso prohibido"},
        404: {"description": "Reservación no encontrada"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Constantes para validación de roles
ROLES_PERMITIDOS = ["Administrador", "Gerente", "Empleado"]  # Roles que pueden modificar estados
ROL_USUARIO_COMUN = "Usuario"  # Rol de usuario común que no puede modificar

def verificar_permisos_usuario(usuario_id: int, db: Session) -> bool:
    """Verifica si un usuario tiene permisos para modificar estados de reservaciones"""
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if not usuario:
        return False
    
    # Obtener el rol del usuario
    rol = db.query(Roles).filter(Roles.IdRol == usuario.IdRol).first()
    if not rol:
        return False
        
    # Verificar si el usuario tiene un rol permitido
    return rol.NombreRol in ROLES_PERMITIDOS

@router.get("/", response_model=ResponseBase[List[ReservacionDetailResponse]])
def get_reservaciones(
    skip: int = Query(0, description="Número de registros a omitir", ge=0),
    limit: int = Query(100, description="Número máximo de registros a retornar", le=100),
    estado: Optional[str] = Query(None, description="Filtrar por estado (Pendiente, Aprobada, Denegada)"),
    fecha_inicio: Optional[datetime] = Query(None, description="Filtrar por fecha de inicio mínima"),
    fecha_fin: Optional[datetime] = Query(None, description="Filtrar por fecha fin máxima"),
    id_usuario: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    id_empresa: Optional[int] = Query(None, description="Filtrar por ID de empresa"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """
    Obtener todas las reservaciones con filtros opcionales
    
    Esta operación permite listar todas las reservaciones con paginación y filtros.
    """
    query = db.query(Reservaciones)
    
    if estado:
        query = query.filter(Reservaciones.Estado == estado)
    
    if fecha_inicio:
        query = query.filter(Reservaciones.FechaInicio >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(Reservaciones.FechaFin <= fecha_fin)
    
    if id_usuario:
        query = query.filter(Reservaciones.IdUsuario == id_usuario)
        
    if id_empresa:
        query = query.filter(Reservaciones.IdEmpresa == id_empresa)
    
    # Ordenar por fecha de reservación descendiente (las más nuevas primero)
    query = query.order_by(Reservaciones.FechaReservacion.desc())
    
    reservaciones = query.offset(skip).limit(limit).all()
    return ResponseBase[List[ReservacionDetailResponse]](data=reservaciones)

@router.get("/{reservacion_id}", response_model=ResponseBase[ReservacionDetailResponse])
def get_reservacion(
    reservacion_id: int = Path(..., description="ID único de la reservación", ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """
    Obtener información detallada de una reservación específica
    
    Esta operación permite consultar todos los datos de una reservación, incluyendo información
    sobre el usuario o empresa asociada, y el usuario que realizó modificaciones al estado de la reservación.
    """
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Incluimos el nombre del usuario que modificó en el mensaje si existe
    mensaje = "Detalles de la reservación"
    if reservacion.UsuarioModificacion:
        modificador = reservacion.UsuarioModificacion
        if reservacion.Estado == "Aprobada":
            mensaje = f"Reservación aprobada por {modificador.Nombre} {modificador.Apellido}"
        elif reservacion.Estado == "Denegada":
            mensaje = f"Reservación denegada por {modificador.Nombre} {modificador.Apellido}"
    
    return ResponseBase[ReservacionDetailResponse](
        message=mensaje,
        data=reservacion
    )

@router.post("/", response_model=ResponseBase[ReservacionResponse], status_code=status.HTTP_201_CREATED)
def create_reservacion(
    reservacion: ReservacionCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """Create a new reservation"""
    # Validate business logic constraints
    if (reservacion.IdUsuario is not None and 
        (reservacion.IdEmpleado is not None or reservacion.IdEmpresa is not None)):
        raise HTTPException(
            status_code=400, 
            detail="Una reservación debe ser de un usuario personal o empresa, no ambos"
        )
    
    if ((reservacion.IdEmpleado is None and reservacion.IdEmpresa is not None) or 
        (reservacion.IdEmpleado is not None and reservacion.IdEmpresa is None)):
        raise HTTPException(
            status_code=400, 
            detail="Las reservaciones empresariales requieren IdEmpleado e IdEmpresa"
        )
    
    # Check if referenced entities exist
    if reservacion.IdUsuario is not None:
        usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == reservacion.IdUsuario).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {reservacion.IdUsuario} no encontrado")
    
    if reservacion.IdEmpleado is not None:
        empleado = db.query(Empleados).filter(Empleados.IdEmpleado == reservacion.IdEmpleado).first()
        if empleado is None:
            raise HTTPException(status_code=404, detail=f"Empleado con ID {reservacion.IdEmpleado} no encontrado")
    
    if reservacion.IdEmpresa is not None:
        empresa = db.query(Empresas).filter(Empresas.IdEmpresa == reservacion.IdEmpresa).first()
        if empresa is None:
            raise HTTPException(status_code=404, detail=f"Empresa con ID {reservacion.IdEmpresa} no encontrada")
    
    # Validate dates
    if reservacion.FechaInicio >= reservacion.FechaFin:
        raise HTTPException(
            status_code=400, 
            detail="La fecha de inicio debe ser anterior a la fecha de fin"
        )
    
    if reservacion.FechaInicio < datetime.now():
        raise HTTPException(
            status_code=400, 
            detail="La fecha de inicio no puede ser en el pasado"
        )
    
    db_reservacion = Reservaciones(**reservacion.model_dump())
    db.add(db_reservacion)
    db.commit()
    db.refresh(db_reservacion)
    return ResponseBase[ReservacionResponse](
        message="Reservación creada exitosamente", 
        data=db_reservacion
    )

@router.put("/{reservacion_id}", response_model=ResponseBase[ReservacionResponse])
def update_reservacion(
    reservacion_id: int, 
    reservacion: ReservacionUpdate,
    id_usuario_modificacion: int = Query(..., description="ID del usuario que realiza la modificación"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """
    Actualizar una reservación
    
    Si se está actualizando el estado, solo usuarios con roles de empleado o superiores pueden hacerlo.
    """
    db_reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if db_reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Si se está cambiando el estado, verificar permisos
    if reservacion.Estado is not None and reservacion.Estado != db_reservacion.Estado:
        if not verificar_permisos_usuario(id_usuario_modificacion, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para cambiar el estado de reservaciones. Se requiere rol de Empleado o superior."
            )
    
    # Verificar si el usuario modificador existe
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == id_usuario_modificacion).first()
    if usuario_modificacion is None:
        raise HTTPException(status_code=404, detail=f"Usuario modificador con ID {id_usuario_modificacion} no encontrado")
    
    # Check references if they're being updated
    if reservacion.IdUsuario is not None:
        usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == reservacion.IdUsuario).first()
        if usuario is None:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {reservacion.IdUsuario} no encontrado")
    
    if reservacion.IdEmpleado is not None:
        empleado = db.query(Empleados).filter(Empleados.IdEmpleado == reservacion.IdEmpleado).first()
        if empleado is None:
            raise HTTPException(status_code=404, detail=f"Empleado con ID {reservacion.IdEmpleado} no encontrado")
    
    if reservacion.IdEmpresa is not None:
        empresa = db.query(Empresas).filter(Empresas.IdEmpresa == reservacion.IdEmpresa).first()
        if empresa is None:
            raise HTTPException(status_code=404, detail=f"Empresa con ID {reservacion.IdEmpresa} no encontrada")
    
    # Actualizar datos de la modificación
    update_data = reservacion.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_reservacion, key, value)
    
    # Registrar quién hizo la modificación y cuándo
    db_reservacion.IdUsuarioModificacion = id_usuario_modificacion
    db_reservacion.FechaModificacion = datetime.now()
    
    # If updating status to "Aprobada", set confirmation date
    if reservacion.Estado == "Aprobada" and db_reservacion.Estado != "Aprobada":
        db_reservacion.FechaConfirmacion = datetime.now()
    
    # Perform a final validation before committing
    if db_reservacion.IdUsuario is not None and (db_reservacion.IdEmpleado is not None or db_reservacion.IdEmpresa is not None):
        raise HTTPException(
            status_code=400, 
            detail="Una reservación debe ser de un usuario personal o empresa, no ambos"
        )
    
    if ((db_reservacion.IdEmpleado is None and db_reservacion.IdEmpresa is not None) or 
        (db_reservacion.IdEmpleado is not None and db_reservacion.IdEmpresa is None)):
        raise HTTPException(
            status_code=400, 
            detail="Las reservaciones empresariales requieren IdEmpleado e IdEmpresa"
        )
    
    db.commit()
    db.refresh(db_reservacion)
    return ResponseBase[ReservacionResponse](
        message="Reservación actualizada exitosamente", 
        data=db_reservacion
    )

@router.post("/{reservacion_id}/aprobar", response_model=ResponseBase[ReservacionDetailResponse])
def aprobar_reservacion(
    reservacion_id: int = Path(..., description="ID de la reservación a aprobar"),
    datos: ReservacionApproval = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente", "Empleado"]))  # Añadir protección JWT con roles
):
    """
    Aprobar una reservación
    
    Esta operación cambia el estado de una reservación a 'Aprobada' y registra quién realizó la aprobación.
    Solo usuarios con roles de empleado o superiores pueden realizar esta acción.
    """
    # Verificar permisos del usuario
    if not verificar_permisos_usuario(datos.IdUsuarioModificacion, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para aprobar reservaciones. Se requiere rol de Empleado o superior."
        )
    
    db_reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if db_reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Verificar que la reservación esté en estado pendiente
    if db_reservacion.Estado != "Pendiente":
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede aprobar la reservación porque su estado actual es '{db_reservacion.Estado}'"
        )
    
    # Verificar si el usuario aprobador existe
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == datos.IdUsuarioModificacion).first()
    if usuario_modificacion is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {datos.IdUsuarioModificacion} no encontrado")
    
    # Actualizar la reservación con información de quien aprobó
    db_reservacion.Estado = "Aprobada"
    db_reservacion.FechaConfirmacion = datetime.now()
    db_reservacion.IdUsuarioModificacion = datos.IdUsuarioModificacion
    db_reservacion.FechaModificacion = datetime.now()
    
    db.commit()
    db.refresh(db_reservacion)
    
    # Obtener el nombre completo del usuario modificador para el mensaje
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == datos.IdUsuarioModificacion).first()
    nombre_modificador = f"{usuario_modificacion.Nombre} {usuario_modificacion.Apellido}"
    rol_modificador = usuario_modificacion.Role.NombreRol
    
    return ResponseBase[ReservacionDetailResponse](
        message=f"Reservación aprobada exitosamente por {nombre_modificador} ({rol_modificador})",
        data=db_reservacion
    )

@router.post("/{reservacion_id}/denegar", response_model=ResponseBase[ReservacionDetailResponse])
def denegar_reservacion(
    reservacion_id: int = Path(..., description="ID de la reservación a denegar"),
    datos: ReservacionRejection = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente", "Empleado"]))  # Añadir protección JWT con roles
):
    """
    Denegar una reservación
    
    Esta operación cambia el estado de una reservación a 'Denegada' y registra el motivo del rechazo
    y quién realizó la denegación. Solo usuarios con roles de empleado o superiores pueden realizar esta acción.
    """
    # Verificar permisos del usuario
    if not verificar_permisos_usuario(datos.IdUsuarioModificacion, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para denegar reservaciones. Se requiere rol de Empleado o superior."
        )
    
    db_reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if db_reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Verificar que la reservación esté en estado pendiente
    if db_reservacion.Estado != "Pendiente":
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede denegar la reservación porque su estado actual es '{db_reservacion.Estado}'"
        )
    
    # Verificar si el usuario que deniega existe
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == datos.IdUsuarioModificacion).first()
    if usuario_modificacion is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {datos.IdUsuarioModificacion} no encontrado")
    
    # Actualizar la reservación con información de quien denegó y motivo
    db_reservacion.Estado = "Denegada"
    db_reservacion.MotivoRechazo = datos.MotivoRechazo
    db_reservacion.IdUsuarioModificacion = datos.IdUsuarioModificacion
    db_reservacion.FechaModificacion = datetime.now()
    
    db.commit()
    db.refresh(db_reservacion)
    
    # Obtener el nombre completo del usuario modificador para el mensaje
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == datos.IdUsuarioModificacion).first()
    nombre_modificador = f"{usuario_modificacion.Nombre} {usuario_modificacion.Apellido}"
    rol_modificador = usuario_modificacion.Role.NombreRol
    
    return ResponseBase[ReservacionDetailResponse](
        message=f"Reservación denegada exitosamente por {nombre_modificador} ({rol_modificador})",
        data=db_reservacion
    )

@router.delete("/{reservacion_id}", response_model=ResponseBase)
def delete_reservacion(
    reservacion_id: int = Path(..., description="ID de la reservación a eliminar"),
    id_usuario_modificacion: int = Query(..., description="ID del usuario que realiza la eliminación"),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)  # Añadir protección JWT solo admin
):
    """Delete a reservation"""
    db_reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if db_reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Verificar que el usuario exista
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == id_usuario_modificacion).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {id_usuario_modificacion} no encontrado")
    
    # Registrar la eliminación en el log (opcional)
    # Aquí podrías insertar un registro en una tabla de log antes de eliminar
    
    db.delete(db_reservacion)
    db.commit()
    return ResponseBase(message=f"Reservación eliminada exitosamente por {usuario.Nombre} {usuario.Apellido}")
