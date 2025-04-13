from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import bcrypt
from pydantic import EmailStr

from dbcontext.mydb import SessionLocal
from dbcontext.models import Usuarios, Roles
from schemas.usuario_schema import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UsuarioDetailResponse, UsuarioCambioRol, UsuarioActivacion, UsuarioCambioPassword
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user

# Create router for this controller
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    responses={
        401: {"description": "No autenticado"}, 
        403: {"description": "Acceso prohibido"},
        404: {"description": "Usuario no encontrado"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    """Hash a password for storage"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Protected endpoint - Admin/Manager access
@router.get(
    "/", 
    response_model=ResponseBase[List[UsuarioResponse]],
    summary="Listar todos los usuarios",
    description="Obtiene una lista de todos los usuarios registrados en el sistema."
)
def get_usuarios(
    skip: int = Query(0, description="Número de registros a omitir", ge=0),
    limit: int = Query(100, description="Número máximo de registros a retornar", le=100),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos los usuarios (requiere rol Administrador o Gerente)"""
    usuarios = db.query(Usuarios).offset(skip).limit(limit).all()
    return ResponseBase[List[UsuarioResponse]](data=usuarios)

# Protected endpoint - any authenticated user can get themselves,
# but only admins/managers can get others
@router.get(
    "/{usuario_id}", 
    response_model=ResponseBase[UsuarioDetailResponse],
    summary="Obtener usuario por ID",
    description="Obtiene información detallada de un usuario específico."
)
def get_usuario(
    usuario_id: int = Path(..., description="ID del usuario a consultar"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtiene detalles de un usuario específico
    
    - Si el usuario es administrador o gerente, puede acceder a cualquier usuario
    - Otros usuarios solo pueden ver su propia información
    """
    # Check if user has permission to access this user's data
    if current_user.role not in ["Administrador", "Gerente"] and current_user.user_id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver información de este usuario"
        )
    
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return ResponseBase[UsuarioDetailResponse](data=usuario)

# Protected endpoint - Admin only
@router.post(
    "/", 
    response_model=ResponseBase[UsuarioResponse], 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    description="Crea un nuevo usuario en el sistema."
)
def create_usuario(
    usuario: UsuarioCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crea un nuevo usuario (solo administradores)"""
    # Check if role exists
    db_rol = db.query(Roles).filter(Roles.IdRol == usuario.IdRol).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail=f"Rol con ID {usuario.IdRol} no encontrado")
    
    # Check if email already exists
    db_usuario = db.query(Usuarios).filter(Usuarios.Email == usuario.Email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Email ya está registrado")
    
    # Hash password
    hashed_password = hash_password(usuario.Password)
    
    # Create user without the plain password
    user_data = usuario.model_dump(exclude={"Password"})
    db_usuario = Usuarios(**user_data, PasswordHash=hashed_password)
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    
    return ResponseBase[UsuarioResponse](
        message=f"Usuario creado exitosamente por el administrador {current_user.email}", 
        data=db_usuario
    )

# Protected endpoint - Admin can update anyone, users can update themselves
@router.put(
    "/{usuario_id}", 
    response_model=ResponseBase[UsuarioResponse],
    summary="Actualizar usuario",
    description="Actualiza información de un usuario existente."
)
def update_usuario(
    usuario_id: int, 
    usuario: UsuarioUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Actualiza un usuario existente
    
    - Los administradores pueden actualizar cualquier usuario
    - Los usuarios normales solo pueden actualizar su propio perfil
    - Solo los administradores pueden cambiar roles
    """
    # Check if user exists
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Check permissions - only admin can update other users
    if current_user.role != "Administrador" and current_user.user_id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para actualizar a este usuario"
        )
    
    # Check permissions - only admin can update roles
    if usuario.IdRol is not None and current_user.role != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden cambiar roles"
        )
    
    # Check if role exists if it's being updated
    if usuario.IdRol is not None:
        db_rol = db.query(Roles).filter(Roles.IdRol == usuario.IdRol).first()
        if db_rol is None:
            raise HTTPException(status_code=404, detail=f"Rol con ID {usuario.IdRol} no encontrado")
    
    # Check if email exists if it's being updated
    if usuario.Email is not None and usuario.Email != db_usuario.Email:
        existing_email = db.query(Usuarios).filter(Usuarios.Email == usuario.Email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email ya está registrado")
    
    # Update fields
    update_data = usuario.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_usuario, key, value)
    
    db.commit()
    db.refresh(db_usuario)
    
    return ResponseBase[UsuarioResponse](
        message="Usuario actualizado exitosamente", 
        data=db_usuario
    )

# Protected endpoint - Admin only
@router.delete(
    "/{usuario_id}", 
    response_model=ResponseBase,
    summary="Eliminar usuario",
    description="Elimina un usuario del sistema."
)
def delete_usuario(
    usuario_id: int = Path(..., description="ID único del usuario a eliminar", ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Elimina un usuario (solo administradores)"""
    # Check if user exists
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Don't allow deleting yourself
    if db_usuario.IdUsuario == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta de administrador"
        )
    
    # Delete user
    db.delete(db_usuario)
    db.commit()
    
    return ResponseBase(message=f"Usuario eliminado exitosamente por el administrador {current_user.email}")

# Admin endpoint to change user's role
@router.put(
    "/{usuario_id}/rol", 
    response_model=ResponseBase[UsuarioResponse],
    summary="Cambiar rol de usuario",
    description="Actualiza el rol asignado a un usuario."
)
def update_usuario_rol(
    usuario_id: int = Path(..., description="ID único del usuario a modificar", ge=1),
    cambio_rol: UsuarioCambioRol = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cambia el rol de un usuario (solo administradores)"""
    # Check if user exists
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Check if role exists
    db_rol = db.query(Roles).filter(Roles.IdRol == cambio_rol.IdRol).first()
    if db_rol is None:
        raise HTTPException(status_code=404, detail=f"Rol con ID {cambio_rol.IdRol} no encontrado")
    
    # Update role
    db_usuario.IdRol = cambio_rol.IdRol
    db.commit()
    db.refresh(db_usuario)
    
    return ResponseBase[UsuarioResponse](
        message=f"Rol del usuario actualizado a '{db_rol.NombreRol}' exitosamente", 
        data=db_usuario
    )

# Admin endpoints to activate/deactivate users
@router.patch(
    "/{usuario_id}/activar", 
    response_model=ResponseBase[UsuarioResponse],
    summary="Activar usuario",
    description="Activa un usuario desactivado."
)
def activar_usuario(
    usuario_id: int = Path(..., description="ID único del usuario a activar", ge=1),
    activacion: UsuarioActivacion = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Activa una cuenta de usuario (solo administradores)"""
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    db_usuario.Activo = True
    db.commit()
    db.refresh(db_usuario)
    
    return ResponseBase[UsuarioResponse](
        message="Usuario activado exitosamente", 
        data=db_usuario
    )

@router.patch(
    "/{usuario_id}/desactivar", 
    response_model=ResponseBase[UsuarioResponse],
    summary="Desactivar usuario",
    description="Desactiva una cuenta de usuario (solo administradores)."
)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Desactiva una cuenta de usuario (solo administradores)"""
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Don't allow deactivating yourself
    if db_usuario.IdUsuario == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta de administrador"
        )
    
    db_usuario.Activo = False
    db.commit()
    db.refresh(db_usuario)
    
    return ResponseBase[UsuarioResponse](
        message="Usuario desactivado exitosamente", 
        data=db_usuario
    )

@router.patch(
    "/{usuario_id}/password", 
    response_model=ResponseBase,
    summary="Cambiar contraseña",
    description="Cambia la contraseña de un usuario (solo el propio usuario o un administrador pueden hacerlo)."
)
def cambiar_password(
    usuario_id: int = Path(..., description="ID único del usuario", ge=1),
    cambio_password: UsuarioCambioPassword = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cambia la contraseña de un usuario"""
    # Verificar que el usuario existe
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Solo el propio usuario o un admin pueden cambiar la contraseña
    if current_user.user_id != usuario_id and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permiso para cambiar la contraseña de otro usuario"
        )
    
    # Generar hash de la nueva contraseña
    hashed_password = bcrypt.hashpw(
        cambio_password.nueva_password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Actualizar contraseña
    db_usuario.Password = hashed_password
    db.commit()
    
    return ResponseBase(message="Contraseña actualizada exitosamente")
