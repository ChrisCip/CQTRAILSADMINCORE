from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from dbcontext.mydb import SessionLocal
from dbcontext.models import Roles, Permisos, Usuarios
from schemas.rol_schema import RolCreate, RolUpdate, RolResponse, RolDetailResponse
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user

# Create router for this controller
router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    responses={
        401: {"description": "No autenticado"}, 
        403: {"description": "Acceso prohibido"},
        404: {"description": "Rol no encontrado"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# List roles - Admin/Manager access
@router.get(
    "/", 
    response_model=ResponseBase[List[RolResponse]],
    summary="Listar todos los roles",
    description="Obtiene una lista de todos los roles disponibles en el sistema."
)
def get_roles(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos los roles"""
    roles = db.query(Roles).offset(skip).limit(limit).all()
    return ResponseBase[List[RolResponse]](data=roles)

# Get role details - Admin/Manager access
@router.get(
    "/{rol_id}", 
    response_model=ResponseBase[RolDetailResponse],
    summary="Obtener rol por ID",
    description="Obtiene información detallada de un rol específico incluyendo permisos."
)
def get_rol(
    rol_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Obtiene detalles de un rol específico"""
    rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return ResponseBase[RolDetailResponse](data=rol)

# Create new role - Admin only
@router.post(
    "/", 
    response_model=ResponseBase[RolResponse], 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo rol",
    description="Crea un nuevo rol en el sistema."
)
def create_rol(
    rol: RolCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crea un nuevo rol"""
    # Check if role name already exists
    existing_role = db.query(Roles).filter(Roles.NombreRol == rol.NombreRol).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un rol con el nombre '{rol.NombreRol}'"
        )
    
    db_rol = Roles(**rol.model_dump())
    db.add(db_rol)
    db.commit()
    db.refresh(db_rol)
    
    return ResponseBase[RolResponse](
        message="Rol creado exitosamente", 
        data=db_rol
    )

# Update role - Admin only
@router.put(
    "/{rol_id}", 
    response_model=ResponseBase[RolResponse],
    summary="Actualizar rol",
    description="Actualiza información de un rol existente."
)
def update_rol(
    rol_id: int, 
    rol: RolUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Actualiza un rol"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    # Check system roles protection
    if db_rol.NombreRol in ["Administrador", "Usuario"] and rol.NombreRol != db_rol.NombreRol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cambiar el nombre del rol '{db_rol.NombreRol}' por ser un rol del sistema"
        )
    
    # Update role
    update_data = rol.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rol, key, value)
    
    db.commit()
    db.refresh(db_rol)
    
    return ResponseBase[RolResponse](
        message="Rol actualizado exitosamente", 
        data=db_rol
    )

# Delete role - Admin only
@router.delete(
    "/{rol_id}", 
    response_model=ResponseBase,
    summary="Eliminar rol",
    description="Elimina un rol del sistema."
)
def delete_rol(
    rol_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Elimina un rol"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    # Protect system roles
    if db_rol.NombreRol in ["Administrador", "Usuario"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el rol '{db_rol.NombreRol}' por ser un rol del sistema"
        )
    
    # Check if any users are using this role
    usuarios_con_rol = db.query(Usuarios).filter(Usuarios.IdRol == rol_id).count()
    if usuarios_con_rol > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el rol porque hay {usuarios_con_rol} usuarios asignados a este rol"
        )
    
    db.delete(db_rol)
    db.commit()
    
    return ResponseBase(message="Rol eliminado exitosamente")

# Manage role permissions - Admin only
@router.post(
    "/{rol_id}/permisos/{permiso_id}", 
    response_model=ResponseBase,
    summary="Agregar permiso a rol",
    description="Asigna un permiso a un rol existente."
)
def add_permiso_to_rol(
    rol_id: int, 
    permiso_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Agrega un permiso a un rol"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    # Check if permission is already assigned
    if db_permiso in db_rol.Permisos_:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El permiso '{db_permiso.NombrePermiso}' ya está asignado a este rol"
        )
    
    db_rol.Permisos_.append(db_permiso)
    db.commit()
    
    return ResponseBase(message=f"Permiso '{db_permiso.NombrePermiso}' agregado al rol '{db_rol.NombreRol}' exitosamente")

@router.delete(
    "/{rol_id}/permisos/{permiso_id}", 
    response_model=ResponseBase,
    summary="Eliminar permiso de rol",
    description="Elimina un permiso de un rol existente."
)
def remove_permiso_from_rol(
    rol_id: int, 
    permiso_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Elimina un permiso de un rol"""
    db_rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    db_permiso = db.query(Permisos).filter(Permisos.IdPermiso == permiso_id).first()
    if db_permiso is None:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    
    if db_permiso in db_rol.Permisos_:
        db_rol.Permisos_.remove(db_permiso)
        db.commit()
        return ResponseBase(message=f"Permiso '{db_permiso.NombrePermiso}' eliminado del rol '{db_rol.NombreRol}' exitosamente")
    else:
        raise HTTPException(status_code=404, detail="El permiso no está asignado a este rol")
