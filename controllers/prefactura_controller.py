from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import PreFacturas, Reservaciones
from schemas.prefactura_schema import PreFacturaCreate, PreFacturaUpdate, PreFacturaResponse, PreFacturaDetailResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/prefacturas",
    tags=["PreFacturas"],
    responses={404: {"description": "PreFactura no encontrada"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[PreFacturaResponse]])
def get_prefacturas(skip: int = 0, limit: int = 100, id_reservacion: int = None, db: Session = Depends(get_db)):
    """Get all pre-invoices with optional filters"""
    query = db.query(PreFacturas)
    
    if id_reservacion:
        query = query.filter(PreFacturas.IdReservacion == id_reservacion)
    
    prefacturas = query.offset(skip).limit(limit).all()
    return ResponseBase[List[PreFacturaResponse]](data=prefacturas)

@router.get("/{prefactura_id}", response_model=ResponseBase[PreFacturaDetailResponse])
def get_prefactura(prefactura_id: int, db: Session = Depends(get_db)):
    """Get a pre-invoice by ID with reservation details"""
    prefactura = db.query(PreFacturas).filter(PreFacturas.IdPreFactura == prefactura_id).first()
    if prefactura is None:
        raise HTTPException(status_code=404, detail="PreFactura no encontrada")
    return ResponseBase[PreFacturaDetailResponse](data=prefactura)

@router.post("/", response_model=ResponseBase[PreFacturaResponse], status_code=status.HTTP_201_CREATED)
def create_prefactura(prefactura: PreFacturaCreate, db: Session = Depends(get_db)):
    """Create a new pre-invoice"""
    # Check if reservation exists
    reservacion = db.query(Reservaciones).filter(Reservaciones.IdReservacion == prefactura.IdReservacion).first()
    if reservacion is None:
        raise HTTPException(status_code=404, detail=f"Reservación con ID {prefactura.IdReservacion} no encontrada")
    
    # Check if pre-invoice already exists for this reservation
    existing_prefactura = db.query(PreFacturas).filter(PreFacturas.IdReservacion == prefactura.IdReservacion).first()
    if existing_prefactura:
        raise HTTPException(status_code=400, detail="Ya existe una prefactura para esta reservación")
    
    # Validate costs
    if prefactura.CostoTotal < prefactura.CostoVehiculo + prefactura.CostoAdicional:
        raise HTTPException(
            status_code=400, 
            detail="El costo total debe ser mayor o igual a la suma del costo del vehículo y adicionales"
        )
    
    db_prefactura = PreFacturas(**prefactura.model_dump())
    db.add(db_prefactura)
    db.commit()
    db.refresh(db_prefactura)
    return ResponseBase[PreFacturaResponse](
        message="PreFactura creada exitosamente", 
        data=db_prefactura
    )

@router.put("/{prefactura_id}", response_model=ResponseBase[PreFacturaResponse])
def update_prefactura(prefactura_id: int, prefactura: PreFacturaUpdate, db: Session = Depends(get_db)):
    """Update a pre-invoice"""
    db_prefactura = db.query(PreFacturas).filter(PreFacturas.IdPreFactura == prefactura_id).first()
    if db_prefactura is None:
        raise HTTPException(status_code=404, detail="PreFactura no encontrada")
    
    update_data = prefactura.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_prefactura, key, value)
    
    # Re-validate costs if they are changed
    if 'CostoVehiculo' in update_data or 'CostoAdicional' in update_data or 'CostoTotal' in update_data:
        if db_prefactura.CostoTotal < db_prefactura.CostoVehiculo + db_prefactura.CostoAdicional:
            raise HTTPException(
                status_code=400, 
                detail="El costo total debe ser mayor o igual a la suma del costo del vehículo y adicionales"
            )
    
    db.commit()
    db.refresh(db_prefactura)
    return ResponseBase[PreFacturaResponse](
        message="PreFactura actualizada exitosamente", 
        data=db_prefactura
    )

@router.delete("/{prefactura_id}", response_model=ResponseBase)
def delete_prefactura(prefactura_id: int, db: Session = Depends(get_db)):
    """Delete a pre-invoice"""
    db_prefactura = db.query(PreFacturas).filter(PreFacturas.IdPreFactura == prefactura_id).first()
    if db_prefactura is None:
        raise HTTPException(status_code=404, detail="PreFactura no encontrada")
    
    db.delete(db_prefactura)
    db.commit()
    return ResponseBase(message="PreFactura eliminada exitosamente")
