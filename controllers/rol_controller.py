from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Roles, Permisos
from schemas.rol_schema import RolCreate, RolUpdate, RolResponse, RolDetailResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    responses={404: {"description": "Rol no encontrado"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[RolResponse]])
def get_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all roles"""
    roles = db.query(Roles).offset(skip).limit(limit).all()
    return ResponseBase[List[RolResponse]](data=roles)

@router.get("/{rol_id}", response_model=ResponseBase[RolDetailResponse])
def get_rol(rol_id: int, db: Session = Depends(get_db)):
    """Get a role by ID with its permissions"""
    rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return ResponseBase[RolDetailResponse](data=rol)

@router.post("/", response_model=ResponseBase[RolResponse], status_code=status.HTTP_201_CREATED)
def create_rol(rol: RolCreate, db: Session = Depends(get_db)):
    """Create a new role"""
    db_rol = Roles(**rol.model_dump())
    db.add(db_rol)
    db.commit()
    db.refresh(db_rol)
    return ResponseBase[RolResponse](
        message="Rol creado exitosamente", 
        data=db_rol
    )

@router.put("/{rol_id}", response_model=ResponseBase[RolResponse])
def update_rol(rol_id: int, rol: RolUpdate, db: Session = Depends(get_db)):
    """Update a role"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    update_data = rol.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rol, key, value)
    
    db.commit()
    db.refresh(db_rol)
    return ResponseBase[RolResponse](
        message="Rol actualizado exitosamente", 
        data=db_rol
    )

@router.delete("/{rol_id}", response_model=ResponseBase)
def delete_rol(rol_id: int, db: Session = Depends(get_db)):
    """Delete a role"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    db.delete(db_rol)
    db.commit()
    return ResponseBase(message="Rol eliminado exitosamente")

@router.post("/{rol_id}/permisos/{permiso_id}", response_model=ResponseBase)
def add_permiso_to_rol(rol_id: int, permiso_id: int, db: Session = Depends(get_db)):
    """Add a permission to a role"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    db_rol.Permisos.append(db_permiso)
    db.commit()
    return ResponseBase(message="Permiso agregado al rol exitosamente")

@router.delete("/{rol_id}/permisos/{permiso_id}", response_model=ResponseBase)
def remove_permiso_from_rol(rol_id: int, permiso_id: int, db: Session = Depends(get_db)):
    """Remove a permission from a role"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    if db_permiso in db_rol.Permisos:
        db_rol.Permisos.remove(db_permiso)
        db.commit()
        return ResponseBase(message="Permiso eliminado del rol exitosamente")
    else:
        raise HTTPException(status_code=404, detail="El permiso no está asignado a este rol")
