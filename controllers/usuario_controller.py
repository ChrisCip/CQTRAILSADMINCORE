from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import bcrypt

from dbcontext.mydb import SessionLocal
from dbcontext.models import Usuarios, Roles
from schemas.usuario_schema import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UsuarioDetailResponse
from schemas.base_schemas import ResponseBase

# Create router for this controller
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    responses={404: {"description": "Usuario no encontrado"}},
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

@router.get("/", response_model=ResponseBase[List[UsuarioResponse]])
def get_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users"""
    usuarios = db.query(Usuarios).offset(skip).limit(limit).all()
    return ResponseBase[List[UsuarioResponse]](data=usuarios)

@router.get("/{usuario_id}", response_model=ResponseBase[UsuarioDetailResponse])
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Get a user by ID with role details"""
    usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return ResponseBase[UsuarioDetailResponse](data=usuario)

@router.post("/", response_model=ResponseBase[UsuarioResponse], status_code=status.HTTP_201_CREATED)
def create_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Create a new user"""
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
        message="Usuario creado exitosamente", 
        data=db_usuario
    )

@router.put("/{usuario_id}", response_model=ResponseBase[UsuarioResponse])
def update_usuario(usuario_id: int, usuario: UsuarioUpdate, db: Session = Depends(get_db)):
    """Update a user"""
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
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
    
    update_data = usuario.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_usuario, key, value)
    
    db.commit()
    db.refresh(db_usuario)
    return ResponseBase[UsuarioResponse](
        message="Usuario actualizado exitosamente", 
        data=db_usuario
    )

@router.delete("/{usuario_id}", response_model=ResponseBase)
def delete_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Delete a user"""
    db_usuario = db.query(Usuarios).filter(Usuarios.IdUsuario == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    db.delete(db_usuario)
    db.commit()
    return ResponseBase(message="Usuario eliminado exitosamente")
