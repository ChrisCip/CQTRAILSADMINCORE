from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Empleados, Empresas, Usuarios
from schemas.empleado_schema import EmpleadoCreate, EmpleadoUpdate, EmpleadoResponse, EmpleadoDetailResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/empleados",
    tags=["Empleados"],
    responses={404: {"description": "Empleado no encontrado"}},
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[EmpleadoResponse]])
def get_empleados(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all employees"""
    empleados = db.query(Empleados).offset(skip).limit(limit).all()
    return ResponseBase[List[EmpleadoResponse]](data=empleados)

@router.get("/{empleado_id}", response_model=ResponseBase[EmpleadoDetailResponse])
def get_empleado(empleado_id: int, db: Session = Depends(get_db)):
    """Get an employee by ID with company and user details"""
    empleado = db.query(Empleados).filter(Empleados.IdEmpleado == empleado_id).first()
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return ResponseBase[EmpleadoDetailResponse](data=empleado)

@router.post("/", response_model=ResponseBase[EmpleadoResponse], status_code=status.HTTP_201_CREATED)
def create_empleado(empleado: EmpleadoCreate, db: Session = Depends(get_db)):
    """Create a new employee"""
    # Check if company exists
    db_empresa = db.query(Empresas).filter(Empresas.IdEmpresa == empleado.IdEmpresa).first()
    if db_empresa is None:
        raise HTTPException(status_code=404, detail=f"Empresa con ID {empleado.IdEmpresa} no encontrada")
    
    # Check if user exists
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == empleado.IdUsuario).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {empleado.IdUsuario} no encontrado")
    
    # Check if employee already exists for this user
    existing_empleado = db.query(Empleados).filter(Empleados.IdUsuario == empleado.IdUsuario).first()
    if existing_empleado:
        raise HTTPException(status_code=400, detail="Este usuario ya está registrado como empleado")
    
    db_empleado = Empleados(**empleado.model_dump())
    db.add(db_empleado)
    db.commit()
    db.refresh(db_empleado)
    return ResponseBase[EmpleadoResponse](
        message="Empleado creado exitosamente", 
        data=db_empleado
    )

@router.put("/{empleado_id}", response_model=ResponseBase[EmpleadoResponse])
def update_empleado(empleado_id: int, empleado: EmpleadoUpdate, db: Session = Depends(get_db)):
    """Update an employee"""
    db_empleado = db.query(Empleados).filter(Empleados.IdEmpleado == empleado_id).first()
    if db_empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    # Check if company exists if it's being updated
    if empleado.IdEmpresa is not None:
        db_empresa = db.query(Empresas).filter(Empresas.IdEmpresa == empleado.IdEmpresa).first()
        if db_empresa is None:
            raise HTTPException(status_code=404, detail=f"Empresa con ID {empleado.IdEmpresa} no encontrada")
    
    # Check if user exists if it's being updated
    if empleado.IdUsuario is not None:
        db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == empleado.IdUsuario).first()
        if db_usuario is None:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {empleado.IdUsuario} no encontrado")
        
        # Check if new user is already an employee
        if empleado.IdUsuario != db_empleado.IdUsuario:
            existing_empleado = db.query(Empleados).filter(Empleados.IdUsuario == empleado.IdUsuario).first()
            if existing_empleado:
                raise HTTPException(status_code=400, detail="Este usuario ya está registrado como empleado")
    
    update_data = empleado.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_empleado, key, value)
    
    db.commit()
    db.refresh(db_empleado)
    return ResponseBase[EmpleadoResponse](
        message="Empleado actualizado exitosamente", 
        data=db_empleado
    )

@router.delete("/{empleado_id}", response_model=ResponseBase)
def delete_empleado(empleado_id: int, db: Session = Depends(get_db)):
    """Delete an employee"""
    db_empleado = db.query(Empleados).filter(Empleados.IdEmpleado == empleado_id).first()
    if db_empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    db.delete(db_empleado)
    db.commit()
    return ResponseBase(message="Empleado eliminado exitosamente")
