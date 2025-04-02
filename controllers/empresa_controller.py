from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Empresas
from schemas.empresa_schema import EmpresaCreate, EmpresaUpdate, EmpresaResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"],
    responses={404: {"description": "Empresa no encontrada"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[EmpresaResponse]])
def get_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all companies"""
    empresas = db.query(Empresas).offset(skip).limit(limit).all()
    return ResponseBase[List[EmpresaResponse]](data=empresas)

@router.get("/{empresa_id}", response_model=ResponseBase[EmpresaResponse])
def get_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Get a company by ID"""
    empresa = db.query(Empresas).filter(Empresas.IdEmpresa == empresa_id).first()
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return ResponseBase[EmpresaResponse](data=empresa)

@router.post("/", response_model=ResponseBase[EmpresaResponse], status_code=status.HTTP_201_CREATED)
def create_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    """Create a new company"""
    db_empresa = Empresas(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return ResponseBase[EmpresaResponse](
        message="Empresa creada exitosamente", 
        data=db_empresa
    )

@router.put("/{empresa_id}", response_model=ResponseBase[EmpresaResponse])
def update_empresa(empresa_id: int, empresa: EmpresaUpdate, db: Session = Depends(get_db)):
    """Update a company"""
    db_empresa = db.query(Empresas).filter(Empresas.IdEmpresa == empresa_id).first()
    if db_empresa is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    update_data = empresa.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_empresa, key, value)
    
    db.commit()
    db.refresh(db_empresa)
    return ResponseBase[EmpresaResponse](
        message="Empresa actualizada exitosamente", 
        data=db_empresa
    )

@router.delete("/{empresa_id}", response_model=ResponseBase)
def delete_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Delete a company"""
    db_empresa = db.query(Empresas).filter(Empresas.IdEmpresa == empresa_id).first()
    if db_empresa is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    db.delete(db_empresa)
    db.commit()
    return ResponseBase(message="Empresa eliminada exitosamente")
