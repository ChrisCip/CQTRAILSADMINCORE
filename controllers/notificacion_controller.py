from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Notificaciones, Reservaciones, Usuarios, Ciudades
from schemas.notificacion_schema import NotificacionCreate, NotificacionUpdate, NotificacionResponse, NotificacionDetailResponse
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, require_admin
from services.email_service import email_service

# Create router for this controller
router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Acceso prohibido"},
        404: {"description": "Notificación no encontrada"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Función para enviar correo en segundo plano
def send_reservation_email_background(
    user_email: str, 
    user_name: str, 
    reservation_details: dict
):
    """Envía el correo de confirmación de reservación en segundo plano"""
    try:
        email_service.send_reservation_confirmation(
            user_email=user_email,
            user_name=user_name,
            reservation_details=reservation_details
        )
    except Exception as e:
        print(f"Error al enviar correo: {str(e)}")

@router.get("/", response_model=ResponseBase[List[NotificacionResponse]])
def get_notificaciones(
    skip: int = 0, 
    limit: int = 100, 
    id_reservacion: int = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all notifications with optional filters"""
    query = db.query(Notificaciones)
    
    if id_reservacion:
        query = query.filter(Notificaciones.IdReservacion == id_reservacion)
    
    notificaciones = query.offset(skip).limit(limit).all()
    return ResponseBase[List[NotificacionResponse]](data=notificaciones)

@router.get("/{notificacion_id}", response_model=ResponseBase[NotificacionDetailResponse])
def get_notificacion(
    notificacion_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a notification by ID with reservation details"""
    notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return ResponseBase[NotificacionDetailResponse](data=notificacion)

@router.post("/", response_model=ResponseBase[NotificacionResponse], status_code=status.HTTP_201_CREATED)
def create_notificacion(
    background_tasks: BackgroundTasks,
    notificacion: NotificacionCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new notification
    
    Si la notificación es sobre una reservación aceptada, se enviará
    un correo electrónico al usuario correspondiente.
    """
    # Check if reservation exists
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == notificacion.IdReservacion).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail=f"Reservación con ID {notificacion.IdReservacion} no encontrada")
    
    # Crear la notificación
    db_notificacion = Notificaciones(**notificacion.model_dump())
    db.add(db_notificacion)
    db.commit()
    db.refresh(db_notificacion)
    
    # Verificar si es una notificación de reserva aceptada
    if "aceptada" in notificacion.TipoNotificacion.lower() or "confirmada" in notificacion.TipoNotificacion.lower():
        # Obtener los datos del usuario
        usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == reservacion.IdUsuario).first()
        
        if usuario and usuario.Email:
            # Obtener los datos de las ciudades
            ciudad_inicio = None
            ciudad_fin = None
            
            if reservacion.ciudadinicioid:
                ciudad_inicio = db.query(Ciudades).filter(Ciudades.IdCiudad == reservacion.ciudadinicioid).first()
            
            if reservacion.ciudadfinid:
                ciudad_fin = db.query(Ciudades).filter(Ciudades.IdCiudad == reservacion.ciudadfinid).first()
            
            # Preparar los detalles completos de la reservación
            reservation_details = {
                "id": reservacion.IdReservacion,
                "estado": reservacion.Estado,
                "fecha_inicio": reservacion.FechaInicio.isoformat() if hasattr(reservacion, "FechaInicio") and reservacion.FechaInicio else None,
                "fecha_fin": reservacion.FechaFin.isoformat() if hasattr(reservacion, "FechaFin") and reservacion.FechaFin else None,
                "fecha_reservacion": reservacion.FechaReservacion.isoformat() if hasattr(reservacion, "FechaReservacion") and reservacion.FechaReservacion else None,
                "total": reservacion.Total,
                "subtotal": reservacion.SubTotal,
                "ruta": reservacion.RutaPersonalizada or "Estándar",
                "requerimientos": reservacion.RequerimientosAdicionales or "Ninguno",
                "ciudad_inicio": {
                    "IdCiudad": ciudad_inicio.IdCiudad if ciudad_inicio else None,
                    "Nombre": ciudad_inicio.Nombre if ciudad_inicio else "N/A",
                    "Estado": ciudad_inicio.Estado if ciudad_inicio else ""
                } if ciudad_inicio else {"Nombre": "N/A", "Estado": ""},
                "ciudad_fin": {
                    "IdCiudad": ciudad_fin.IdCiudad if ciudad_fin else None,
                    "Nombre": ciudad_fin.Nombre if ciudad_fin else "N/A",
                    "Estado": ciudad_fin.Estado if ciudad_fin else ""
                } if ciudad_fin else {"Nombre": "N/A", "Estado": ""},
            }
            
            # Enviar el correo en segundo plano
            background_tasks.add_task(
                send_reservation_email_background,
                user_email=usuario.Email,
                user_name=f"{usuario.Nombre} {usuario.Apellido}" if hasattr(usuario, "Apellido") else usuario.Nombre,
                reservation_details=reservation_details
            )
    
    return ResponseBase[NotificacionResponse](
        message="Notificación creada exitosamente", 
        data=db_notificacion
    )

@router.put("/{notificacion_id}", response_model=ResponseBase[NotificacionResponse])
def update_notificacion(
    notificacion_id: int, 
    notificacion: NotificacionUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a notification"""
    db_notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if db_notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    update_data = notificacion.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_notificacion, key, value)
    
    db.commit()
    db.refresh(db_notificacion)
    return ResponseBase[NotificacionResponse](
        message="Notificación actualizada exitosamente", 
        data=db_notificacion
    )

@router.patch("/{notificacion_id}/marcar-leida", response_model=ResponseBase[NotificacionResponse])
def marcar_notificacion_leida(
    notificacion_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark notification as read"""
    db_notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if db_notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    # NOTA: La columna 'Leida' no existe en el modelo actual.
    # Si necesitas marcar notificaciones como leídas, deberás agregar esta columna a la tabla
    # db_notificacion.Leida = True
    db.commit()
    db.refresh(db_notificacion)
    return ResponseBase[NotificacionResponse](
        message="Notificación actualizada exitosamente", 
        data=db_notificacion
    )

@router.delete("/{notificacion_id}", response_model=ResponseBase)
def delete_notificacion(
    notificacion_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Delete a notification"""
    db_notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if db_notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    db.delete(db_notificacion)
    db.commit()
    return ResponseBase(message="Notificación eliminada exitosamente")

# Endpoint para enviar correo de confirmación de reserva manualmente
@router.post("/{reservacion_id}/enviar-confirmacion", response_model=ResponseBase)
def enviar_confirmacion_reserva(
    reservacion_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Envía un correo de confirmación de reserva manualmente
    
    Útil en caso de que el envío automático haya fallado o 
    se requiera reenviar la confirmación.
    """
    # Verificar si la reservación existe
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == reservacion_id).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail=f"Reservación con ID {reservacion_id} no encontrada")
    
    # Obtener los datos del usuario
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == reservacion.IdUsuario).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {reservacion.IdUsuario} no encontrado")
    
    if not usuario.Email:
        raise HTTPException(status_code=400, detail="El usuario no tiene un correo electrónico registrado")
    
    # Obtener los datos de las ciudades
    ciudad_inicio = None
    ciudad_fin = None
    
    if reservacion.ciudadinicioid:
        ciudad_inicio = db.query(Ciudades).filter(Ciudades.IdCiudad == reservacion.ciudadinicioid).first()
    
    if reservacion.ciudadfinid:
        ciudad_fin = db.query(Ciudades).filter(Ciudades.IdCiudad == reservacion.ciudadfinid).first()
    
    # Preparar los detalles completos de la reservación
    reservation_details = {
        "id": reservacion.IdReservacion,
        "estado": reservacion.Estado,
        "fecha_inicio": reservacion.FechaInicio.isoformat() if hasattr(reservacion, "FechaInicio") and reservacion.FechaInicio else None,
        "fecha_fin": reservacion.FechaFin.isoformat() if hasattr(reservacion, "FechaFin") and reservacion.FechaFin else None,
        "fecha_reservacion": reservacion.FechaReservacion.isoformat() if hasattr(reservacion, "FechaReservacion") and reservacion.FechaReservacion else None,
        "total": reservacion.Total,
        "subtotal": reservacion.SubTotal,
        "ruta": reservacion.RutaPersonalizada or "Estándar",
        "requerimientos": reservacion.RequerimientosAdicionales or "Ninguno",
        "ciudad_inicio": {
            "IdCiudad": ciudad_inicio.IdCiudad if ciudad_inicio else None,
            "Nombre": ciudad_inicio.Nombre if ciudad_inicio else "N/A",
            "Estado": ciudad_inicio.Estado if ciudad_inicio else ""
        } if ciudad_inicio else {"Nombre": "N/A", "Estado": ""},
        "ciudad_fin": {
            "IdCiudad": ciudad_fin.IdCiudad if ciudad_fin else None,
            "Nombre": ciudad_fin.Nombre if ciudad_fin else "N/A",
            "Estado": ciudad_fin.Estado if ciudad_fin else ""
        } if ciudad_fin else {"Nombre": "N/A", "Estado": ""},
    }
    
    # Enviar el correo en segundo plano
    background_tasks.add_task(
        send_reservation_email_background,
        user_email=usuario.Email,
        user_name=f"{usuario.Nombre} {usuario.Apellido}" if hasattr(usuario, "Apellido") else usuario.Nombre,
        reservation_details=reservation_details
    )
    
    # Crear una notificación de envío de correo
    db_notificacion = Notificaciones(
        IdReservacion=reservacion_id,
        TipoNotificacion=f"Se ha enviado un correo de confirmación para la reservación #{reservacion_id}"
    )
    db.add(db_notificacion)
    db.commit()
    
    return ResponseBase(message="Correo de confirmación enviado exitosamente")
