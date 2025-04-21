from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Notificaciones, Reservaciones
from schemas.notificacion_schema import NotificacionCreate, NotificacionUpdate, NotificacionResponse, NotificacionDetailResponse
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, require_admin  # Añadir esta importación

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

@router.get("/", response_model=ResponseBase[List[NotificacionResponse]])
def get_notificaciones(
    skip: int = 0, 
    limit: int = 100, 
    id_reservacion: int = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
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
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """Get a notification by ID with reservation details"""
    notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return ResponseBase[NotificacionDetailResponse](data=notificacion)

@router.post("/", response_model=ResponseBase[NotificacionResponse], status_code=status.HTTP_201_CREATED)
def create_notificacion(
    notificacion: NotificacionCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Permitir a cualquier usuario autenticado
):
    """Create a new notification"""
    # Check if reservation exists
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == notificacion.IdReservacion).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail=f"Reservación con ID {notificacion.IdReservacion} no encontrada")
    
    db_notificacion = Notificaciones(**notificacion.model_dump())
    db.add(db_notificacion)
    db.commit()
    db.refresh(db_notificacion)
    return ResponseBase[NotificacionResponse](
        message="Notificación creada exitosamente", 
        data=db_notificacion
    )

@router.put("/{notificacion_id}", response_model=ResponseBase[NotificacionResponse])
def update_notificacion(
    notificacion_id: int, 
    notificacion: NotificacionUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
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
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """Mark notification as read"""
    db_notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if db_notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    db_notificacion.Leida = True
    db.commit()
    db.refresh(db_notificacion)
    return ResponseBase[NotificacionResponse](
        message="Notificación marcada como leída", 
        data=db_notificacion
    )

@router.delete("/{notificacion_id}", response_model=ResponseBase)
def delete_notificacion(
    notificacion_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)  # Añadir protección JWT solo admin
):
    """Delete a notification"""
    db_notificacion = db.query(Notificaciones).filter(Notificaciones.IdNotificacion == notificacion_id).first()
    if db_notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    db.delete(db_notificacion)
    db.commit()
    return ResponseBase(message="Notificación eliminada exitosamente")
