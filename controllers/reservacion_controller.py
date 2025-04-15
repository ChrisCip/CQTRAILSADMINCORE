from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, text, desc, case, cast, Float
from sqlalchemy.sql import operators

# Import necessary models and schemas
from dbcontext.mydb import SessionLocal
from dbcontext.models import Reservaciones, Usuarios, Empleados, Empresas, Roles, Vehiculos, VehiculosReservaciones, Ciudades
from schemas.reservacion_schema import (
    ReservacionCreate, ReservacionUpdate, ReservacionResponse, ReservacionDetailResponse,
    ReservacionApproval, ReservacionRejection, ReservacionAprobacionDenegacion
)
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user

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
    ciudadinicioid: Optional[int] = Query(None, description="Filtrar por ID de ciudad de inicio"),
    ciudadfinid: Optional[int] = Query(None, description="Filtrar por ID de ciudad de fin"),
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
        
    if ciudadinicioid:
        query = query.filter(Reservaciones.ciudadinicioid == ciudadinicioid)
        
    if ciudadfinid:
        query = query.filter(Reservaciones.ciudadfinid == ciudadfinid)
    
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
    reservacion_id: int = Path(..., description="ID de la reservación a aprobar", ge=1),
    aprobacion: ReservacionAprobacionDenegacion = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Aprobar una reservación
    
    Esta operación cambia el estado de una reservación a 'Aprobada' y registra quién realizó la aprobación.
    Solo usuarios con roles de empleado o superiores pueden realizar esta acción.
    """
    # Verificar permisos del usuario
    if not verificar_permisos_usuario(aprobacion.IdUsuarioModificacion, db):
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
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == aprobacion.IdUsuarioModificacion).first()
    if usuario_modificacion is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {aprobacion.IdUsuarioModificacion} no encontrado")
    
    # Actualizar la reservación con información de quien aprobó
    db_reservacion.Estado = "Aprobada"
    db_reservacion.FechaConfirmacion = datetime.now()
    db_reservacion.IdUsuarioModificacion = aprobacion.IdUsuarioModificacion
    db_reservacion.FechaModificacion = datetime.now()
    
    db.commit()
    db.refresh(db_reservacion)
    
    # Obtener el nombre completo del usuario modificador para el mensaje
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == aprobacion.IdUsuarioModificacion).first()
    nombre_modificador = f"{usuario_modificacion.Nombre} {usuario_modificacion.Apellido}"
    rol_modificador = usuario_modificacion.Role.NombreRol
    
    return ResponseBase[ReservacionDetailResponse](
        message=f"Reservación aprobada exitosamente por {nombre_modificador} ({rol_modificador})",
        data=db_reservacion
    )

@router.post("/{reservacion_id}/denegar", response_model=ResponseBase[ReservacionDetailResponse])
def denegar_reservacion(
    reservacion_id: int = Path(..., description="ID de la reservación a denegar", ge=1),
    denegacion: ReservacionAprobacionDenegacion = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Denegar una reservación
    
    Esta operación cambia el estado de una reservación a 'Denegada' y registra el motivo del rechazo
    y quién realizó la denegación. Solo usuarios con roles de empleado o superiores pueden realizar esta acción.
    """
    # Verificar permisos del usuario
    if not verificar_permisos_usuario(denegacion.IdUsuarioModificacion, db):
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
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == denegacion.IdUsuarioModificacion).first()
    if usuario_modificacion is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {denegacion.IdUsuarioModificacion} no encontrado")
    
    # Actualizar la reservación con información de quien denegó y motivo
    db_reservacion.Estado = "Denegada"
    db_reservacion.MotivoRechazo = denegacion.MotivoRechazo
    db_reservacion.IdUsuarioModificacion = denegacion.IdUsuarioModificacion
    db_reservacion.FechaModificacion = datetime.now()
    
    db.commit()
    db.refresh(db_reservacion)
    
    # Obtener el nombre completo del usuario modificador para el mensaje
    usuario_modificacion = db.query(Usuarios).filter(Usuarios.IdUsuario == denegacion.IdUsuarioModificacion).first()
    nombre_modificador = f"{usuario_modificacion.Nombre} {usuario_modificacion.Apellido}"
    rol_modificador = usuario_modificacion.Role.NombreRol
    
    return ResponseBase[ReservacionDetailResponse](
        message=f"Reservación denegada exitosamente por {nombre_modificador} ({rol_modificador})",
        data=db_reservacion
    )

@router.delete("/{reservacion_id}", response_model=ResponseBase)
def delete_reservacion(
    reservacion_id: int = Path(..., description="ID de la reservación a eliminar", ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a reservation"""
    db_reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if db_reservacion is None:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    
    # Verificar que el usuario exista
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == current_user.IdUsuario).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {current_user.IdUsuario} no encontrado")
    
    # Registrar la eliminación en el log (opcional)
    # Aquí podrías insertar un registro en una tabla de log antes de eliminar
    
    db.delete(db_reservacion)
    db.commit()
    return ResponseBase(message=f"Reservación eliminada exitosamente por {usuario.Nombre} {usuario.Apellido}")

@router.get("/estadisticas/crecimiento-semanal", response_model=ResponseBase)
def get_crecimiento_semanal(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtiene el crecimiento semanal de reservaciones
    
    Calcula el porcentaje de incremento o decremento en reservas comparado con la semana anterior
    """
    # Fecha actual
    today = date.today()
    
    # Cálculo de semana actual y anterior
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start - timedelta(days=1)
    
    # Contar reservaciones de la semana actual
    current_week_count = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= current_week_start,
        Reservaciones.FechaReservacion <= current_week_end
    ).scalar() or 0
    
    # Contar reservaciones de la semana anterior
    previous_week_count = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= previous_week_start,
        Reservaciones.FechaReservacion <= previous_week_end
    ).scalar() or 0
    
    # Calcular el porcentaje de crecimiento
    if previous_week_count == 0:
        growth_percentage = 100 if current_week_count > 0 else 0
    else:
        growth_percentage = ((current_week_count - previous_week_count) / previous_week_count) * 100
    
    # Formatear el resultado
    growth_sign = "+" if growth_percentage >= 0 else ""
    
    return ResponseBase(
        message=f"{growth_sign}{growth_percentage:.1f}%",
        data={
            "current_week_count": current_week_count,
            "previous_week_count": previous_week_count,
            "growth_percentage": growth_percentage,
            "period": {
                "current_week": {
                    "start": current_week_start,
                    "end": current_week_end
                },
                "previous_week": {
                    "start": previous_week_start,
                    "end": previous_week_end
                }
            }
        }
    )

@router.get("/estadisticas/destinos-populares", response_model=ResponseBase)
def get_destinos_populares(
    limite: int = Query(1, description="Número de destinos populares a retornar", ge=1),
    periodo_dias: int = Query(30, description="Período en días para calcular destinos populares", ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtiene los destinos más populares en las reservaciones
    
    Analiza la ruta personalizada de las reservaciones para determinar los destinos
    más frecuentes y su porcentaje sobre el total de reservaciones.
    """
    # Fecha límite para el período
    date_limit = datetime.now() - timedelta(days=periodo_dias)
    
    # Total de reservaciones en el período
    total_reservaciones = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= date_limit
    ).scalar() or 0
    
    if total_reservaciones == 0:
        return ResponseBase(
            message="No hay reservaciones en el período especificado",
            data={"destinos": [], "total_reservaciones": 0}
        )
    
    # Consulta para agrupar y contar por destino (RutaPersonalizada)
    destinos = db.query(
        Reservaciones.RutaPersonalizada.label('destino'),
        func.count(Reservaciones.IdReservacion).label('total'),
        (func.count(Reservaciones.IdReservacion) * 100 / total_reservaciones).label('porcentaje')
    ).filter(
        Reservaciones.FechaReservacion >= date_limit,
        Reservaciones.RutaPersonalizada.isnot(None),
        Reservaciones.RutaPersonalizada != ''
    ).group_by(
        Reservaciones.RutaPersonalizada
    ).order_by(
        desc('total')
    ).limit(limite).all()
    
    # Formatear los resultados
    resultados = []
    for destino in destinos:
        resultados.append({
            "destino": destino.destino,
            "total": destino.total,
            "porcentaje": round(destino.porcentaje, 2)
        })
    
    # Si hay resultados, preparar mensaje con el primer destino
    mensaje = ""
    if resultados:
        top_destino = resultados[0]
        mensaje = f"{top_destino['destino']}\n\n{top_destino['porcentaje']}% de todas las reservas"
    
    return ResponseBase(
        message=mensaje,
        data={
            "destinos": resultados,
            "total_reservaciones": total_reservaciones,
            "periodo_dias": periodo_dias
        }
    )

@router.get("/estadisticas/dashboard", response_model=ResponseBase)
def get_estadisticas_dashboard(
    periodo_dias: int = Query(30, description="Período en días para calcular estadísticas", ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtiene un dashboard completo de estadísticas para reservaciones
    
    Incluye crecimiento semanal, vehículo más reservado y destino más popular
    en un solo endpoint para mostrar en el dashboard.
    """
    # Fecha actual
    today = date.today()
    
    # Crecimiento semanal
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start - timedelta(days=1)
    
    current_week_count = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= current_week_start,
        Reservaciones.FechaReservacion <= current_week_end
    ).scalar() or 0
    
    previous_week_count = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= previous_week_start,
        Reservaciones.FechaReservacion <= previous_week_end
    ).scalar() or 0
    
    if previous_week_count == 0:
        growth_percentage = 100 if current_week_count > 0 else 0
    else:
        growth_percentage = ((current_week_count - previous_week_count) / previous_week_count) * 100
    
    growth_sign = "+" if growth_percentage >= 0 else ""
    
    # Fecha límite para el resto de estadísticas
    date_limit = datetime.now() - timedelta(days=periodo_dias)
    
    # Destino más popular
    total_reservaciones = db.query(func.count(Reservaciones.IdReservacion)).filter(
        Reservaciones.FechaReservacion >= date_limit
    ).scalar() or 0
    
    destino_popular = None
    if total_reservaciones > 0:
        destino = db.query(
            Reservaciones.RutaPersonalizada.label('destino'),
            func.count(Reservaciones.IdReservacion).label('total'),
            (func.count(Reservaciones.IdReservacion) * 100 / total_reservaciones).label('porcentaje')
        ).filter(
            Reservaciones.FechaReservacion >= date_limit,
            Reservaciones.RutaPersonalizada.isnot(None),
            Reservaciones.RutaPersonalizada != ''
        ).group_by(
            Reservaciones.RutaPersonalizada
        ).order_by(
            desc('total')
        ).first()
        
        if destino:
            destino_popular = {
                "destino": destino.destino,
                "total": destino.total,
                "porcentaje": round(destino.porcentaje, 2)
            }
    
    # Vehículo más reservado
    vehiculo_popular = None
    vehiculo = db.query(
        Vehiculos.IdVehiculo,
        Vehiculos.Modelo,
        Vehiculos.Placa,
        Vehiculos.TipoVehiculo,
        func.count(VehiculosReservaciones.IdReservacion).label('total_reservas')
    ).join(
        VehiculosReservaciones, 
        Vehiculos.IdVehiculo == VehiculosReservaciones.IdVehiculo
    ).join(
        Reservaciones,
        VehiculosReservaciones.IdReservacion == Reservaciones.IdReservacion
    ).filter(
        Reservaciones.FechaReservacion >= date_limit
    ).group_by(
        Vehiculos.IdVehiculo,
        Vehiculos.Modelo,
        Vehiculos.Placa,
        Vehiculos.TipoVehiculo
    ).order_by(
        desc('total_reservas')
    ).first()
    
    if vehiculo:
        vehiculo_popular = {
            "id_vehiculo": vehiculo.IdVehiculo,
            "modelo": vehiculo.Modelo,
            "placa": vehiculo.Placa,
            "tipo_vehiculo": vehiculo.TipoVehiculo,
            "total_reservas": vehiculo.total_reservas
        }
    
    return ResponseBase(
        message="Dashboard de estadísticas",
        data={
            "crecimiento_semanal": {
                "porcentaje": growth_percentage,
                "porcentaje_formateado": f"{growth_sign}{growth_percentage:.1f}%",
                "mensaje": f"Incremento en reservas comparado con la semana anterior",
                "current_week_count": current_week_count,
                "previous_week_count": previous_week_count
            },
            "vehiculo_mas_reservado": vehiculo_popular,
            "destino_popular": destino_popular,
            "total_reservaciones": total_reservaciones,
            "periodo_dias": periodo_dias
        }
    )

@router.get("/estadisticas/reservaciones-semana-actual", response_model=ResponseBase)
def get_reservaciones_semana_actual(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtiene las reservaciones hechas en la semana actual agrupadas por día
    
    Devuelve el detalle de reservaciones para cada día de la semana actual
    (domingo, lunes, martes, miércoles, jueves, viernes, sábado)
    """
    # Fecha actual
    today = date.today()
    
    # Obtener el primer día de la semana (domingo)
    start_of_week = today - timedelta(days=today.weekday() + 1)  # +1 para que sea domingo
    
    # Crear lista de días de la semana
    days_of_week = []
    for i in range(7):
        days_of_week.append(start_of_week + timedelta(days=i))
    
    # Nombres de los días en español
    day_names = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    
    # Resultado para cada día
    week_data = []
    
    # Consultar reservaciones para cada día
    for i, day in enumerate(days_of_week):
        # Hora de inicio y fin del día
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        # Contar reservaciones del día
        count = db.query(func.count(Reservaciones.IdReservacion)).filter(
            Reservaciones.FechaReservacion >= day_start,
            Reservaciones.FechaReservacion <= day_end
        ).scalar() or 0
        
        # Obtener las reservaciones del día - convertir a ReservacionResponse
        reservaciones_db = db.query(Reservaciones).filter(
            Reservaciones.FechaReservacion >= day_start,
            Reservaciones.FechaReservacion <= day_end
        ).all()
        
        # Convertir modelos de DB a respuestas de esquema Pydantic
        reservaciones = []
        for res in reservaciones_db:
            reservaciones.append({
                "IdReservacion": res.IdReservacion,
                "FechaInicio": res.FechaInicio,
                "FechaFin": res.FechaFin,
                "IdUsuario": res.IdUsuario,
                "IdEmpleado": res.IdEmpleado,
                "IdEmpresa": res.IdEmpresa,
                "RutaPersonalizada": res.RutaPersonalizada,
                "RequerimientosAdicionales": res.RequerimientosAdicionales,
                "Estado": res.Estado,
                "FechaReservacion": res.FechaReservacion,
                "FechaConfirmacion": res.FechaConfirmacion
            })
        
        # Determinar si es el día actual
        is_today = day == today
        
        week_data.append({
            "dia": day_names[i],
            "fecha": day.strftime("%Y-%m-%d"),
            "total_reservaciones": count,
            "es_hoy": is_today,
            "reservaciones": reservaciones
        })
    
    return ResponseBase(
        message="Reservaciones de la semana actual",
        data={
            "semana_actual": {
                "inicio": start_of_week.strftime("%Y-%m-%d"),
                "fin": (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d")
            },
            "dias": week_data
        }
    )
