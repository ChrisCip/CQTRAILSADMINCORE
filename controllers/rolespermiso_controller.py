from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import List, Dict, Any, Optional
from sqlalchemy.sql import text

from dbcontext.mydb import SessionLocal
from dbcontext.models import Roles, Permisos, t_RolesPermisos
from schemas.rolespermisos_schema import (
    RolPermisoCreate, 
    RolPermisoUpdate, 
    RolPermisoResponse, 
    PermisosResumen,
    RolPermisoByController
)
from schemas.base_schemas import ResponseBase
from dependencies.auth import get_current_user
from rolespermisosmiddleware import clear_permissions_cache

# Create router for this controller
router = APIRouter(
    prefix="/rolespermisos",
    tags=["RolesPermisos"],
    responses={
        401: {"description": "No autenticado"}, 
        403: {"description": "Acceso prohibido"},
        404: {"description": "No encontrado"}
    },
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# List all role permissions - Admin only
@router.get(
    "/", 
    response_model=ResponseBase[List[RolPermisoResponse]],
    summary="Listar todos los permisos de roles",
    description="Obtiene una lista de todos los permisos asignados a roles."
)
def get_roles_permisos(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos los permisos de roles"""
    # Consulta SQL utilizando join
    query = text("""
    SELECT 
        rp."IdRol", 
        rp."IdPermiso", 
        rp."Crear", 
        rp."Editar", 
        rp."Leer", 
        rp."Eliminar",
        r."NombreRol",
        p."NombrePermiso"
    FROM 
        miguel."RolesPermisos" rp
    JOIN 
        miguel."Roles" r ON rp."IdRol" = r."IdRol"
    JOIN 
        miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
    ORDER BY 
        r."NombreRol", p."NombrePermiso"
    OFFSET :skip LIMIT :limit
    """)
    
    result = db.execute(query, {"skip": skip, "limit": limit})
    
    # Mapear a modelo de respuesta
    permisos = []
    for row in result:
        permisos.append({
            "IdRol": row[0],
            "IdPermiso": row[1],
            "Crear": row[2],
            "Editar": row[3],
            "Leer": row[4],
            "Eliminar": row[5],
            "NombreRol": row[6],
            "NombrePermiso": row[7]
        })
    
    return ResponseBase[List[RolPermisoResponse]](data=permisos)

# Get role permissions by role ID - Admin only
@router.get(
    "/rol/{rol_id}", 
    response_model=ResponseBase[List[RolPermisoResponse]],
    summary="Obtener permisos por ID de rol",
    description="Obtiene todos los permisos asignados a un rol específico."
)
def get_permisos_by_rol(
    rol_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Obtiene permisos para un rol específico"""
    # Verificar que el rol existe
    rol = db.query(Roles).filter(Roles.IdRol == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail=f"Rol con ID {rol_id} no encontrado")
    
    # Consulta SQL utilizando join
    query = text("""
    SELECT 
        rp."IdRol", 
        rp."IdPermiso", 
        rp."Crear", 
        rp."Editar", 
        rp."Leer", 
        rp."Eliminar",
        r."NombreRol",
        p."NombrePermiso"
    FROM 
        miguel."RolesPermisos" rp
    JOIN 
        miguel."Roles" r ON rp."IdRol" = r."IdRol"
    JOIN 
        miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
    WHERE 
        rp."IdRol" = :rol_id
    ORDER BY 
        p."NombrePermiso"
    """)
    
    result = db.execute(query, {"rol_id": rol_id})
    
    # Mapear a modelo de respuesta
    permisos = []
    for row in result:
        permisos.append({
            "IdRol": row[0],
            "IdPermiso": row[1],
            "Crear": row[2],
            "Editar": row[3],
            "Leer": row[4],
            "Eliminar": row[5],
            "NombreRol": row[6],
            "NombrePermiso": row[7]
        })
    
    return ResponseBase[List[RolPermisoResponse]](data=permisos)

# Get role permissions by role name - Admin only
@router.get(
    "/rol/nombre/{nombre_rol}", 
    response_model=ResponseBase[PermisosResumen],
    summary="Obtener permisos por nombre de rol",
    description="Obtiene un resumen de todos los permisos asignados a un rol específico por su nombre."
)
def get_permisos_by_nombre_rol(
    nombre_rol: str, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Obtiene permisos para un rol por su nombre"""
    # Verificar que el rol existe
    rol = db.query(Roles).filter(Roles.NombreRol == nombre_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail=f"Rol '{nombre_rol}' no encontrado")
    
    # Consulta SQL utilizando join
    query = text("""
    SELECT 
        rp."IdRol", 
        rp."IdPermiso", 
        rp."Crear", 
        rp."Editar", 
        rp."Leer", 
        rp."Eliminar",
        r."NombreRol",
        p."NombrePermiso"
    FROM 
        miguel."RolesPermisos" rp
    JOIN 
        miguel."Roles" r ON rp."IdRol" = r."IdRol"
    JOIN 
        miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
    WHERE 
        r."NombreRol" = :nombre_rol
    ORDER BY 
        p."NombrePermiso"
    """)
    
    result = db.execute(query, {"nombre_rol": nombre_rol})
    
    # Mapear a modelo de resumen
    permisos_dict: Dict[str, RolPermisoByController] = {}
    
    for row in result:
        tabla = row[7]  # NombrePermiso
        permisos_dict[tabla] = {
            "tabla": tabla,
            "Crear": row[2],
            "Editar": row[3],
            "Leer": row[4],
            "Eliminar": row[5]
        }
    
    return ResponseBase[PermisosResumen](
        data={"controladores": permisos_dict}
    )

# Add or update role permission - Admin only
@router.post(
    "/", 
    response_model=ResponseBase,
    summary="Crear o actualizar permiso de rol",
    description="Crea o actualiza un permiso para un rol específico."
)
def create_or_update_rol_permiso(
    rol_permiso: RolPermisoCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crea o actualiza un permiso de rol"""
    # Verificar que el rol existe
    rol = db.query(Roles).filter(Roles.IdRol == rol_permiso.IdRol).first()
    if not rol:
        raise HTTPException(status_code=404, detail=f"Rol con ID {rol_permiso.IdRol} no encontrado")
    
    # Verificar que el permiso existe
    permiso = db.query(Permisos).filter(Permisos.IdPermiso == rol_permiso.IdPermiso).first()
    if not permiso:
        raise HTTPException(status_code=404, detail=f"Permiso con ID {rol_permiso.IdPermiso} no encontrado")
    
    # Verificar si ya existe la combinación
    existing_query = text("""
    SELECT 
        EXISTS(
            SELECT 1 
            FROM miguel."RolesPermisos" 
            WHERE "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
        )
    """)
    exists = db.execute(existing_query, {
        "rol_id": rol_permiso.IdRol,
        "permiso_id": rol_permiso.IdPermiso
    }).scalar()
    
    if exists:
        # Actualizar
        update_query = text("""
        UPDATE miguel."RolesPermisos" 
        SET 
            "Crear" = :crear,
            "Editar" = :editar,
            "Leer" = :leer,
            "Eliminar" = :eliminar
        WHERE 
            "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
        """)
        
        db.execute(update_query, {
            "crear": rol_permiso.Crear,
            "editar": rol_permiso.Editar,
            "leer": rol_permiso.Leer,
            "eliminar": rol_permiso.Eliminar,
            "rol_id": rol_permiso.IdRol,
            "permiso_id": rol_permiso.IdPermiso
        })
        
        message = "Permiso de rol actualizado correctamente"
    else:
        # Insertar nuevo
        insert_query = text("""
        INSERT INTO miguel."RolesPermisos" 
            ("IdRol", "IdPermiso", "Crear", "Editar", "Leer", "Eliminar")
        VALUES 
            (:rol_id, :permiso_id, :crear, :editar, :leer, :eliminar)
        """)
        
        db.execute(insert_query, {
            "rol_id": rol_permiso.IdRol,
            "permiso_id": rol_permiso.IdPermiso,
            "crear": rol_permiso.Crear,
            "editar": rol_permiso.Editar,
            "leer": rol_permiso.Leer,
            "eliminar": rol_permiso.Eliminar
        })
        
        message = "Permiso de rol creado correctamente"
    
    db.commit()
    
    # Limpiar caché de permisos
    clear_permissions_cache()
    
    return ResponseBase(message=message)

# Update role permission - Admin only
@router.put(
    "/{rol_id}/{permiso_id}", 
    response_model=ResponseBase,
    summary="Actualizar permiso de rol",
    description="Actualiza un permiso existente para un rol específico."
)
def update_rol_permiso(
    rol_id: int,
    permiso_id: int,
    rol_permiso: RolPermisoUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Actualiza un permiso de rol"""
    # Verificar si existe la combinación
    existing_query = text("""
    SELECT 
        "Crear", "Editar", "Leer", "Eliminar"
    FROM 
        miguel."RolesPermisos" 
    WHERE 
        "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
    """)
    
    existing = db.execute(existing_query, {
        "rol_id": rol_id,
        "permiso_id": permiso_id
    }).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Permiso de rol no encontrado")
    
    # Preparar los valores de actualización
    update_values = {}
    if rol_permiso.Crear is not None:
        update_values["Crear"] = rol_permiso.Crear
    else:
        update_values["Crear"] = existing[0]
        
    if rol_permiso.Editar is not None:
        update_values["Editar"] = rol_permiso.Editar
    else:
        update_values["Editar"] = existing[1]
        
    if rol_permiso.Leer is not None:
        update_values["Leer"] = rol_permiso.Leer
    else:
        update_values["Leer"] = existing[2]
        
    if rol_permiso.Eliminar is not None:
        update_values["Eliminar"] = rol_permiso.Eliminar
    else:
        update_values["Eliminar"] = existing[3]
    
    # Actualizar
    update_query = text("""
    UPDATE miguel."RolesPermisos" 
    SET 
        "Crear" = :crear,
        "Editar" = :editar,
        "Leer" = :leer,
        "Eliminar" = :eliminar
    WHERE 
        "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
    """)
    
    db.execute(update_query, {
        "crear": update_values["Crear"],
        "editar": update_values["Editar"],
        "leer": update_values["Leer"],
        "eliminar": update_values["Eliminar"],
        "rol_id": rol_id,
        "permiso_id": permiso_id
    })
    
    db.commit()
    
    # Limpiar caché de permisos
    clear_permissions_cache()
    
    return ResponseBase(message="Permiso de rol actualizado correctamente")

# Delete role permission - Admin only
@router.delete(
    "/{rol_id}/{permiso_id}", 
    response_model=ResponseBase,
    summary="Eliminar permiso de rol",
    description="Elimina un permiso específico para un rol."
)
def delete_rol_permiso(
    rol_id: int,
    permiso_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Elimina un permiso de rol"""
    # Verificar si existe la combinación
    existing_query = text("""
    SELECT 
        EXISTS(
            SELECT 1 
            FROM miguel."RolesPermisos" 
            WHERE "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
        )
    """)
    
    exists = db.execute(existing_query, {
        "rol_id": rol_id,
        "permiso_id": permiso_id
    }).scalar()
    
    if not exists:
        raise HTTPException(status_code=404, detail="Permiso de rol no encontrado")
    
    # Eliminar
    delete_query = text("""
    DELETE FROM miguel."RolesPermisos" 
    WHERE "IdRol" = :rol_id AND "IdPermiso" = :permiso_id
    """)
    
    db.execute(delete_query, {
        "rol_id": rol_id,
        "permiso_id": permiso_id
    })
    
    db.commit()
    
    # Limpiar caché de permisos
    clear_permissions_cache()
    
    return ResponseBase(message="Permiso de rol eliminado correctamente")

@router.get(
    "/diagnostico", 
    response_model=ResponseBase,
    summary="Diagnóstico de permisos",
    description="Realiza un diagnóstico de los permisos en el sistema para ayudar a depurar."
)
def diagnostico_permisos(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Realiza un diagnóstico del sistema de permisos"""
    try:
        # 1. Verificar todas las tablas
        tablas_query = text("""
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_schema = 'miguel'
        ORDER BY table_name
        """)
        tablas = db.execute(tablas_query).fetchall()
        
        # 2. Verificar roles
        roles_query = text("""
        SELECT "IdRol", "NombreRol", "Descripcion"
        FROM miguel."Roles"
        ORDER BY "IdRol"
        """)
        roles = db.execute(roles_query).fetchall()
        
        # 3. Verificar permisos
        permisos_query = text("""
        SELECT "IdPermiso", "NombrePermiso", "Descripcion"
        FROM miguel."Permisos"
        ORDER BY "IdPermiso"
        """)
        permisos = db.execute(permisos_query).fetchall()
        
        # 4. Verificar roles permisos
        roles_permisos_query = text("""
        SELECT rp."IdRol", r."NombreRol", rp."IdPermiso", p."NombrePermiso", 
               rp."Crear", rp."Editar", rp."Leer", rp."Eliminar"
        FROM miguel."RolesPermisos" rp
        JOIN miguel."Roles" r ON rp."IdRol" = r."IdRol"
        JOIN miguel."Permisos" p ON rp."IdPermiso" = p."IdPermiso"
        ORDER BY r."NombreRol", p."NombrePermiso"
        """)
        roles_permisos = db.execute(roles_permisos_query).fetchall()
        
        # Formatear los resultados
        results = {
            "tablas": [{"nombre": t[0]} for t in tablas],
            "roles": [{"id": r[0], "nombre": r[1], "descripcion": r[2]} for r in roles],
            "permisos": [{"id": p[0], "nombre": p[1], "descripcion": p[2]} for p in permisos],
            "roles_permisos": [
                {
                    "id_rol": rp[0], 
                    "rol": rp[1], 
                    "id_permiso": rp[2], 
                    "permiso": rp[3],
                    "crear": rp[4],
                    "editar": rp[5],
                    "leer": rp[6],
                    "eliminar": rp[7]
                } 
                for rp in roles_permisos
            ]
        }
        
        # 5. Comprobar si 'ciudades' existe en los permisos
        ciudades_exists = any(p[1].lower() == 'ciudades' for p in permisos)
        results["ciudades_exists"] = ciudades_exists
        
        # 6. Si el usuario es Empleado, verificar su rol y permisos
        if current_user.role == "Empleado":
            results["current_user"] = {
                "id": current_user.user_id,
                "email": current_user.email,
                "role": current_user.role,
                "permissions": current_user.permissions
            }
            
            # Verificar permisos específicos para este rol
            empleado_permisos = [rp for rp in roles_permisos if rp[1] == "Empleado"]
            results["empleado_permisos"] = [
                {
                    "permiso": rp[3],
                    "crear": rp[4],
                    "editar": rp[5],
                    "leer": rp[6],
                    "eliminar": rp[7]
                }
                for rp in empleado_permisos
            ]
        
        # Limpiar la caché de permisos para forzar recarga
        clear_permissions_cache()
        
        return ResponseBase(
            success=True,
            message="Diagnóstico completado",
            data=results
        )
    
    except Exception as e:
        print(f"Error en diagnóstico: {str(e)}")
        return ResponseBase(
            success=False,
            message=f"Error en diagnóstico: {str(e)}"
        )

@router.get(
    "/limpiar-cache", 
    response_model=ResponseBase,
    summary="Limpiar caché de permisos",
    description="Limpia el caché de permisos para forzar la recarga desde la base de datos."
)
def limpiar_cache_permisos(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Limpia el caché de permisos para forzar recarga desde DB"""
    # Verificar que el usuario sea Admin
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403, 
            detail="Solo los administradores pueden limpiar el caché"
        )
        
    # Limpiar el caché
    clear_permissions_cache()
    
    return ResponseBase(
        success=True,
        message="Caché de permisos limpiada correctamente"
    )

@router.get(
    "/limpiar-cache/{role}/{controller}", 
    response_model=ResponseBase,
    summary="Limpiar caché para un rol y controlador específicos",
    description="Limpia la caché de permisos para un rol y controlador específicos, forzando la recarga desde la base de datos."
)
def limpiar_cache_especifico(
    role: str,
    controller: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Limpia el caché de permisos para un rol y controlador específicos"""
    # Verificar que el usuario sea Admin
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403, 
            detail="Solo los administradores pueden limpiar el caché"
        )
    
    # Normalizar rol y controlador a minúsculas para buscar en la caché
    role_lower = role.lower()
    controller_lower = controller.lower()
    
    # Obtener claves del caché que coincidan con el patrón
    from rolespermisosmiddleware.middleware import permission_cache
    
    cache_keys = list(permission_cache.keys())
    removed_keys = []
    
    for key in cache_keys:
        if key.startswith(f"{role_lower}:{controller_lower}:"):
            removed_keys.append(key)
            del permission_cache[key]
            
    return ResponseBase(
        success=True,
        message=f"Caché limpiada para rol '{role}' y controlador '{controller}'",
        data={"keys_removed": removed_keys}
    ) 