from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional



from dbcontext.mydb import SessionLocal
from dbcontext.models import Vehiculos
from schemas.vehiculo_schema import VehiculoCreate, VehiculoUpdate, VehiculoResponse, VehiculoDisponibilidad
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user
from utils.image_storage import ImageStorage
from utils.image_handler import validate_and_format_images

image_storage = ImageStorage()

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
    current_user = Depends(get_current_user)
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
    current_user = Depends(get_current_user)
):
    """Get a vehicle by ID"""
    vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return ResponseBase[VehiculoResponse](data=vehiculo)





@router.post("/", response_model=ResponseBase[VehiculoResponse])
async def create_vehiculo(
        vehiculo: VehiculoCreate = Depends(),
        files: List[UploadFile] = File(default=None),
        db: Session = Depends(get_db),
        current_user = Depends(get_current_user)
):
    """Create a new vehicle with optional image uploads"""
    # Check if license plate exists
    existing_placa = db.query(Vehiculos).filter(Vehiculos.Placa == vehiculo.Placa).first()
    if existing_placa:
        raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta placa")

    # Create vehicle first to get ID
    vehicle_data = vehiculo.model_dump()
    vehicle_data["Image_url"] = None
    db_vehiculo = Vehiculos(**vehicle_data)
    db.add(db_vehiculo)
    db.commit()
    db.refresh(db_vehiculo)

    # Handle image uploads if any
    if files:
        try:
            image_urls = await image_storage.save_images(files, db_vehiculo.IdVehiculo)
            db_vehiculo.Image_url = image_urls
            db.commit()
            db.refresh(db_vehiculo)
        except Exception as e:
            # Rollback on error
            db.delete(db_vehiculo)
            db.commit()
            raise HTTPException(status_code=400, detail=str(e))

    return ResponseBase[VehiculoResponse](
        message="Vehículo creado exitosamente",
        data=db_vehiculo
    )

@router.put("/{vehiculo_id}", response_model=ResponseBase[VehiculoResponse])
async def update_vehiculo(
    vehiculo_id: int,
    vehiculo: VehiculoUpdate = Depends(),
    files: List[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update vehicle properties and optionally its images"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    # Check if license plate already exists if it's being updated
    if vehiculo.Placa is not None and vehiculo.Placa != db_vehiculo.Placa:
        existing_placa = db.query(Vehiculos).filter(Vehiculos.Placa == vehiculo.Placa).first()
        if existing_placa:
            raise HTTPException(status_code=400, detail="Ya existe un vehículo con esta placa")

    # Handle image uploads if any
    if files:
        try:
            # Delete existing images
            if db_vehiculo.Image_url:
                image_storage.delete_images(db_vehiculo.Image_url)
            
            # Save new images
            image_urls = await image_storage.save_images(files, vehiculo_id)
            vehiculo.Image_url = image_urls
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Update vehicle properties
    update_data = vehiculo.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vehiculo, key, value)

    db.commit()
    db.refresh(db_vehiculo)

    return ResponseBase[VehiculoResponse](
        message="Vehículo actualizado exitosamente",
        data=db_vehiculo
    )


@router.get(
    "/tipos/count",
    response_model=ResponseBase[dict],
    summary="Contar vehículos por tipo",
    description="Obtiene un conteo de vehículos agrupados por tipo."
)
def count_by_tipo(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get count of vehicles by type"""
    from sqlalchemy import func
    
    counts = db.query(
        Vehiculos.TipoVehiculo,
        func.count(Vehiculos.IdVehiculo).label('count')
    ).group_by(Vehiculos.TipoVehiculo).all()
    
    # Convert result to dictionary
    result = {tipo: count for tipo, count in counts}
    
    return ResponseBase[dict](
        message="Conteo de vehículos por tipo obtenido exitosamente",
        data=result
    )

















@router.delete("/{vehiculo_id}", response_model=ResponseBase)
def delete_vehiculo(
    vehiculo_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a vehicle"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    db.delete(db_vehiculo)
    db.commit()
    return ResponseBase(message="Vehículo eliminado exitosamente")

@router.patch("/{vehiculo_id}/disponibilidad", response_model=ResponseBase[VehiculoResponse])
def update_disponibilidad(
    vehiculo_id: int, 
    disponibilidad: VehiculoDisponibilidad, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update vehicle availability"""
    db_vehiculo = db.query(Vehiculos).filter(Vehiculos.IdVehiculo == vehiculo_id).first()
    if db_vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    
    db_vehiculo.Disponible = disponibilidad.disponible
    db.commit()
    db.refresh(db_vehiculo)
    return ResponseBase[VehiculoResponse](
        message="Disponibilidad del vehículo actualizada exitosamente", 
        data=db_vehiculo
    )
