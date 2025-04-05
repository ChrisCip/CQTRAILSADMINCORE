from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import VehiculosReservaciones, Vehiculos, Reservaciones
from schemas.vehiculoreservacion_schema import VehiculoReservacionCreate, VehiculoReservacionUpdate, VehiculoReservacionResponse, VehiculoReservacionDetailResponse
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, require_admin  # Añadir esta importación

# Create router for this controller
router = APIRouter(
    prefix="/vehiculos-reservaciones",
    tags=["VehiculosReservaciones"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Acceso prohibido"},
        404: {"description": "Asignación de vehículo no encontrada"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[VehiculoReservacionDetailResponse]])
def get_vehiculos_reservaciones(
    skip: int = 0, 
    limit: int = 100, 
    id_vehiculo: int = None, 
    id_reservacion: int = None,
    estado: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Protección JWT
):
    """Get all vehicle-reservation assignments with optional filters"""
    query = db.query(VehiculosReservaciones)
    
    if id_vehiculo:
        query = query.filter(VehiculosReservaciones.IdVehiculo == id_vehiculo)
    
    if id_reservacion:
        query = query.filter(VehiculosReservaciones.IdReservacion == id_reservacion)
    
    if estado:
        query = query.filter(VehiculosReservaciones.EstadoAsignacion == estado)
    
    vehiculos_reservaciones = query.offset(skip).limit(limit).all()
    return ResponseBase[List[VehiculoReservacionDetailResponse]](data=vehiculos_reservaciones)

@router.get("/{id_vehiculo}/{id_reservacion}", response_model=ResponseBase[VehiculoReservacionDetailResponse])
def get_vehiculo_reservacion(
    id_vehiculo: int, 
    id_reservacion: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Protección JWT
):
    """Get a vehicle-reservation assignment by composite key"""
    vehiculo_reservacion = db.query(VehiculosReservaciones).filter(
        VehiculosReservaciones.IdVehiculo == id_vehiculo,
        VehiculosReservaciones.IdReservacion == id_reservacion
    ).first()
    
    if vehiculo_reservacion is None:
        raise HTTPException(status_code=404, detail="Asignación de vehículo no encontrada")
    
    return ResponseBase[VehiculoReservacionDetailResponse](data=vehiculo_reservacion)

@router.post("/", response_model=ResponseBase[VehiculoReservacionResponse], status_code=status.HTTP_201_CREATED)
def create_vehiculo_reservacion(
    vehiculo_reservacion: VehiculoReservacionCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente"]))  # Protección JWT con roles específicos
):
    """Create a new vehicle-reservation assignment"""
    # Check if vehicle exists and is available
    vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_reservacion.IdVehiculo).first()
    if vehiculo is None:
        raise HTTPException(status_code=404, detail=f"Vehículo con ID {vehiculo_reservacion.IdVehiculo} no encontrado")
    
    if not vehiculo.Disponible:
        raise HTTPException(status_code=400, detail="El vehículo no está disponible para asignación")
    
    # Check if reservation exists
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == vehiculo_reservacion.IdReservacion).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail=f"Reservación con ID {vehiculo_reservacion.IdReservacion} no encontrada")
    
    # Check if there's already an assignment
    existing_asignacion = db.query(VehiculosReservaciones).filter(
        VehiculosReservaciones.IdVehiculo == vehiculo_reservacion.IdVehiculo,
        VehiculosReservaciones.IdReservacion == vehiculo_reservacion.IdReservacion
    ).first()
    
    if existing_asignacion:
        raise HTTPException(status_code=400, detail="Ya existe una asignación para este vehículo y reservación")
    
    # Check if the vehicle is available during the reservation dates
    conflicting_reservaciones = db.query(VehiculosReservaciones).join(
        Reservaciones, 
        VehiculosReservaciones.IdReservacion == Reservaciones.IdReservacion
    ).filter(
        VehiculosReservaciones.IdVehiculo == vehiculo_reservacion.IdVehiculo,
        VehiculosReservaciones.EstadoAsignacion == "Activa",
        Reservaciones.FechaInicio < reservacion.FechaFin,
        Reservaciones.FechaFin > reservacion.FechaInicio
    ).all()
    
    if conflicting_reservaciones:
        raise HTTPException(
            status_code=400, 
            detail="El vehículo ya está asignado a otra reservación en el mismo período"
        )
    
    db_vehiculo_reservacion = VehiculosReservaciones(**vehiculo_reservacion.model_dump())
    db.add(db_vehiculo_reservacion)
    db.commit()
    db.refresh(db_vehiculo_reservacion)
    return ResponseBase[VehiculoReservacionResponse](
        message="Asignación de vehículo creada exitosamente", 
        data=db_vehiculo_reservacion
    )

@router.put("/{id_vehiculo}/{id_reservacion}", response_model=ResponseBase[VehiculoReservacionResponse])
def update_vehiculo_reservacion(
    id_vehiculo: int, 
    id_reservacion: int, 
    vehiculo_reservacion: VehiculoReservacionUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente"]))  # Protección JWT con roles específicos
):
    """Update a vehicle-reservation assignment"""
    db_vehiculo_reservacion = db.query(VehiculosReservaciones).filter(
        VehiculosReservaciones.IdVehiculo == id_vehiculo,
        VehiculosReservaciones.IdReservacion == id_reservacion
    ).first()
    
    if db_vehiculo_reservacion is None:
        raise HTTPException(status_code=404, detail="Asignación de vehículo no encontrada")
    
    update_data = vehiculo_reservacion.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vehiculo_reservacion, key, value)
    
    db.commit()
    db.refresh(db_vehiculo_reservacion)
    return ResponseBase[VehiculoReservacionResponse](
        message="Asignación de vehículo actualizada exitosamente", 
        data=db_vehiculo_reservacion
    )

@router.delete("/{id_vehiculo}/{id_reservacion}", response_model=ResponseBase)
def delete_vehiculo_reservacion(
    id_vehiculo: int, 
    id_reservacion: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador"]))  # Solo administradores pueden eliminar
):
    """Delete a vehicle-reservation assignment"""
    db_vehiculo_reservacion = db.query(VehiculosReservaciones).filter(
        VehiculosReservaciones.IdVehiculo == id_vehiculo,
        VehiculosReservaciones.IdReservacion == id_reservacion
    ).first()
    
    if db_vehiculo_reservacion is None:
        raise HTTPException(status_code=404, detail="Asignación de vehículo no encontrada")
    
    db.delete(db_vehiculo_reservacion)
    db.commit()
    return ResponseBase(message="Asignación de vehículo eliminada exitosamente")
