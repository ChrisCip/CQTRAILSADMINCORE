from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Permisos
from schemas.permiso_schema import PermisoCreate, PermisoUpdate, PermisoResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/permisos",
    tags=["Permisos"],
    responses={404: {"description": "Permiso no encontrado"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[PermisoResponse]])
def get_permisos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all permissions"""
    permisos = db.query(Permisos).offset(skip).limit(limit).all()
    return ResponseBase[List[PermisoResponse]](data=permisos)

@router.get("/{permiso_id}", response_model=ResponseBase[PermisoResponse])
def get_permiso(permiso_id: int, db: Session = Depends(get_db)):
    """Get a permission by ID"""
    permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    return ResponseBase[PermisoResponse](data=permiso)

@router.post("/", response_model=ResponseBase[PermisoResponse], status_code=status.HTTP_201_CREATED)
def create_permiso(permiso: PermisoCreate, db: Session = Depends(get_db)):
    """Create a new permission"""
    db_permiso = Permisos(**permiso.model_dump())
    db.add(db_permiso)
    db.commit()
    db.refresh(db_permiso)
    return ResponseBase[PermisoResponse](
        message="Permiso creado exitosamente", 
        data=db_permiso
    )

@router.put("/{permiso_id}", response_model=ResponseBase[PermisoResponse])
def update_permiso(permiso_id: int, permiso: PermisoUpdate, db: Session = Depends(get_db)):
    """Update a permission"""
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    update_data = permiso.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_permiso, key, value)
    
    db.commit()
    db.refresh(db_permiso)
    return ResponseBase[PermisoResponse](
        message="Permiso actualizado exitosamente", 
        data=db_permiso
    )

@router.delete("/{permiso_id}", response_model=ResponseBase)
def delete_permiso(permiso_id: int, db: Session = Depends(get_db)):
    """Delete a permission"""
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    db.delete(db_permiso)
    db.commit()
    return ResponseBase(message="Permiso eliminado exitosamente")
