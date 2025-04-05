from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from dbcontext.mydb import SessionLocal
from dbcontext.models import Vehiculos
from schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate, VehiculoResponse
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user, require_role, require_admin  # Añadir esta importación

# Create router for this controller
router = APIRouter(
    prefix="/vehiculos",
    tags=["Vehiculos"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Acceso prohibido"},
        404: {"description": "Vehículo no encontrado"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[VehiculoResponse]])
def get_vehiculos(
    skip: int = 0, 
    limit: int = 100, 
    disponible: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """Get all vehicles with optional filter by availability"""
    query = db.query(Vehiculos)
    
    if disponible is not None:
        query = query.filter(Vehiculos.Disponible == disponible)
    
    vehiculos = query.offset(skip).limit(limit).all()
    return ResponseBase[List[VehiculoResponse]](data=vehiculos)

@router.get("/{vehiculo_id}", response_model=ResponseBase[VehiculoResponse])
def get_vehiculo(
    vehiculo_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # Añadir protección JWT
):
    """Get a vehicle by ID"""
    vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return ResponseBase[VehiculoResponse](data=vehiculo)

@router.post("/", response_model=ResponseBase[VehiculoResponse], status_code=status.HTTP_201_CREATED)
def create_vehiculo(
    vehiculo: VehiculoCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente"]))  # Añadir protección JWT con roles
):
    """Create a new vehicle"""
    # Check if license plate already exists
    existing_placa = db.query(Vehiculos).filter(Vehiculos.Placa == vehiculo.Placa).first()
    if existing_placa:
        raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta placa")
    
    db_vehiculo = Vehiculos(**vehiculo.model_dump())
    db.add(db_vehiculo)
    db.commit()
    db.refresh(db_vehiculo)
    return ResponseBase[VehiculoResponse](
        message="Vehículo creado exitosamente", 
        data=db_vehiculo
    )

@router.put("/{vehiculo_id}", response_model=ResponseBase[VehiculoResponse])
def update_vehiculo(
    vehiculo_id: int, 
    vehiculo: VehiculoUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente"]))  # Añadir protección JWT con roles
):
    """Update a vehicle"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    # Check if license plate already exists if it's being updated
    if vehiculo.Placa is not None and vehiculo.Placa != db_vehiculo.Placa:
        existing_placa = db.query(Vehiculos).filter(Vehiculos.Placa == vehiculo.Placa).first()
        if existing_placa:
            raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta placa")
    
    update_data = vehiculo.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vehiculo, key, value)
    
    db.commit()
    db.refresh(db_vehiculo)
    return ResponseBase[VehiculoResponse](
        message="Vehículo actualizado exitosamente", 
        data=db_vehiculo
    )

@router.delete("/{vehiculo_id}", response_model=ResponseBase)
def delete_vehiculo(
    vehiculo_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)  # Añadir protección JWT solo admin
):
    """Delete a vehicle"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    db.delete(db_vehiculo)
    db.commit()
    return ResponseBase(message="Vehículo eliminado exitosamente")

@router.patch("/{vehiculo_id}/disponibilidad", response_model=ResponseBase[VehiculoResponse])
def actualizar_disponibilidad(
    vehiculo_id: int, 
    disponible: bool = Query(..., description="Nuevo estado de disponibilidad"), 
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["Administrador", "Gerente"]))  # Añadir protección JWT con roles
):
    """Update vehicle availability"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    db_vehiculo.Disponible = disponible
    db.commit()
    db.refresh(db_vehiculo)
    return ResponseBase[VehiculoResponse](
        message="Disponibilidad del vehículo actualizada exitosamente", 
        data=db_vehiculo
    )
