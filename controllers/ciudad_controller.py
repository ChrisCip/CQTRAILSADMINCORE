from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Ciudades
from schemas.ciudad_schema import CiudadCreate, CiudadUpdate, CiudadResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/ciudades",
    tags=["Ciudades"],
    responses={
        404: {"description": "Ciudad no encontrada"},
        500: {"description": "Error interno del servidor"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=ResponseBase[List[CiudadResponse]])
def get_ciudades(
    skip: int = Query(0, description="Número de registros a omitir", ge=0),
    limit: int = Query(100, description="Número máximo de registros a retornar", le=100),
    db: Session = Depends(get_db)
):
    """
    Obtener todas las ciudades registradas en el sistema.
    
    Esta operación permite listar todas las ciudades con paginación.
    
    - **skip**: Cuántos registros omitir (útil para paginación)
    - **limit**: Máximo número de registros a retornar
    
    Returns:
        List[CiudadResponse]: Lista de ciudades
    """
    ciudades = db.query(Ciudades).offset(skip).limit(limit).all()
    return ResponseBase[List[CiudadResponse]](data=ciudades)

@router.get("/{ciudad_id}", response_model=ResponseBase[CiudadResponse])
def get_ciudad(
    ciudad_id: int = Path(..., description="ID único de la ciudad a consultar", ge=1),
    db: Session = Depends(get_db)
):
    """
    Obtener información detallada de una ciudad específica por su ID.
    
    Esta operación permite consultar los datos de una ciudad mediante su identificador único.
    
    - **ciudad_id**: ID único de la ciudad
    
    Returns:
        CiudadResponse: Datos de la ciudad solicitada
        
    Raises:
        HTTPException: 404 si la ciudad no existe
    """
    ciudad = db.query(Ciudades).filter(Ciudades.IdCiudad == ciudad_id).first()
    if ciudad is None:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return ResponseBase[CiudadResponse](data=ciudad)

@router.post("/", response_model=ResponseBase[CiudadResponse], status_code=status.HTTP_201_CREATED)
def create_ciudad(
    ciudad: CiudadCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una nueva ciudad en el sistema.
    
    Esta operación permite registrar una nueva ciudad con su nombre y estado.
    
    - **ciudad**: Datos de la ciudad a crear
    
    Returns:
        CiudadResponse: Datos de la ciudad creada con su ID asignado
    """
    db_ciudad = Ciudades(**ciudad.model_dump())
    db.add(db_ciudad)
    db.commit()
    db.refresh(db_ciudad)
    return ResponseBase[CiudadResponse](
        message="Ciudad creada exitosamente", 
        data=db_ciudad
    )

@router.put("/{ciudad_id}", response_model=ResponseBase[CiudadResponse])
def update_ciudad(
    ciudad_id: int = Path(..., description="ID único de la ciudad a actualizar", ge=1),
    ciudad: CiudadUpdate = None,
    db: Session = Depends(get_db)
):
    """
    Actualizar información de una ciudad existente.
    
    Esta operación permite modificar los datos de una ciudad mediante su identificador único.
    Solo se actualizarán los campos incluidos en la solicitud.
    
    - **ciudad_id**: ID único de la ciudad a actualizar
    - **ciudad**: Datos de la ciudad a actualizar (campos opcionales)
    
    Returns:
        CiudadResponse: Datos actualizados de la ciudad
        
    Raises:
        HTTPException: 404 si la ciudad no existe
    """
    db_ciudad = db.query(Ciudades).filter(Ciudades.IdCiudad == ciudad_id).first()
    if db_ciudad is None:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    
    update_data = ciudad.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ciudad, key, value)
    
    db.commit()
    db.refresh(db_ciudad)
    return ResponseBase[CiudadResponse](
        message="Ciudad actualizada exitosamente", 
        data=db_ciudad
    )

@router.delete("/{ciudad_id}", response_model=ResponseBase)
def delete_ciudad(
    ciudad_id: int = Path(..., description="ID único de la ciudad a eliminar", ge=1),
    db: Session = Depends(get_db)
):
    """
    Eliminar una ciudad del sistema.
    
    Esta operación permite eliminar permanentemente una ciudad mediante su identificador único.
    
    - **ciudad_id**: ID único de la ciudad a eliminar
    
    Returns:
        ResponseBase: Mensaje de confirmación
        
    Raises:
        HTTPException: 404 si la ciudad no existe
    """
    db_ciudad = db.query(Ciudades).filter(Ciudades.IdCiudad == ciudad_id).first()
    if db_ciudad is None:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    
    db.delete(db_ciudad)
    db.commit()
    return ResponseBase(message="Ciudad eliminada exitosamente")
