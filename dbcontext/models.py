from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKeyConstraint, Identity, Integer, Numeric, PrimaryKeyConstraint, String, Table, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    # Establecer el esquema por defecto para todas las tablas
    __table_args__ = {'schema': 'miguel'}


class Ciudades(Base):
    __tablename__ = 'Ciudades'
    __table_args__ = (
        PrimaryKeyConstraint('IdCiudad', name='Ciudades_pkey'),
        {'schema': 'miguel'}  # Especificar el esquema
    )

    IdCiudad: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    Nombre: Mapped[str] = mapped_column(String(20))
    Estado: Mapped[str] = mapped_column(String(20))


class Empresas(Base):
    __tablename__ = 'Empresas'
    __table_args__ = (
        PrimaryKeyConstraint('IdEmpresa', name='Empresas_pkey'),
        {'schema': 'miguel'}
    )

    IdEmpresa: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    Nombre: Mapped[str] = mapped_column(String(20))
    ContactoEmail: Mapped[str] = mapped_column(String(100))
    ContactoTelefono: Mapped[str] = mapped_column(String(20))
    FechaRegistro: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    Activo: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    Empleados: Mapped[List['Empleados']] = relationship('Empleados', back_populates='Empresas_')
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Empresas_')


# Primero, definir la tabla de asociación
t_RolesPermisos = Table(
    'RolesPermisos', Base.metadata,
    Column('IdRol', Integer, primary_key=True, nullable=False),
    Column('IdPermiso', Integer, primary_key=True, nullable=False),
    Column('Crear', Boolean, nullable=False, server_default=text('false')),
    Column('Editar', Boolean, nullable=False, server_default=text('false')),
    Column('Leer', Boolean, nullable=False, server_default=text('false')),
    Column('Eliminar', Boolean, nullable=False, server_default=text('false')),
    ForeignKeyConstraint(['IdPermiso'], ['miguel.Permisos.IdPermiso'], name='RolesPermisos_IdPermiso_fkey'),
    ForeignKeyConstraint(['IdRol'], ['miguel.Roles.IdRol'], name='RolesPermisos_IdRol_fkey'),
    PrimaryKeyConstraint('IdRol', 'IdPermiso', name='RolesPermisos_pkey'),
    schema='miguel'
)

class Permisos(Base):
    __tablename__ = 'Permisos'
    __table_args__ = (
        PrimaryKeyConstraint('IdPermiso', name='Permisos_pkey'),
        {'schema': 'miguel'}
    )

    IdPermiso: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    NombrePermiso: Mapped[str] = mapped_column(String(20))
    Descripcion: Mapped[Optional[str]] = mapped_column(String(100))

    Roles: Mapped[List['Roles']] = relationship('Roles', secondary=t_RolesPermisos, back_populates='Permisos_')


class Roles(Base):
    __tablename__ = 'Roles'
    __table_args__ = (
        PrimaryKeyConstraint('IdRol', name='Roles_pkey'),
        {'schema': 'miguel'}
    )

    IdRol: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    NombreRol: Mapped[str] = mapped_column(String(20))
    Descripcion: Mapped[Optional[str]] = mapped_column(String(200))

    Permisos_: Mapped[List['Permisos']] = relationship('Permisos', secondary=t_RolesPermisos, back_populates='Roles')
    Usuarios: Mapped[List['Usuarios']] = relationship('Usuarios', back_populates='Roles_')


class Vehiculos(Base):
    __tablename__ = 'Vehiculos'
    __table_args__ = (
        PrimaryKeyConstraint('IdVehiculo', name='Vehiculos_pkey'),
        {'schema': 'miguel'}
    )

    IdVehiculo: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    Placa: Mapped[str] = mapped_column(String(20))
    Modelo: Mapped[str] = mapped_column(String(50))
    TipoVehiculo: Mapped[str] = mapped_column(String(20))
    Capacidad: Mapped[int] = mapped_column(Integer)
    Ano: Mapped[int] = mapped_column(Integer)
    Disponible: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    Price: Mapped[Optional[int]] = mapped_column(Integer)
    Image_url: Mapped[Optional[dict]] = mapped_column(JSONB)

    VehiculosReservaciones: Mapped[List['VehiculosReservaciones']] = relationship('VehiculosReservaciones', back_populates='Vehiculos_')


class Usuarios(Base):
    __tablename__ = 'Usuarios'
    __table_args__ = (
        ForeignKeyConstraint(['IdRol'], ['miguel.Roles.IdRol'], name='Usuarios_IdRol_fkey'),
        PrimaryKeyConstraint('IdUsuario', name='Usuarios_pkey'),
        UniqueConstraint('Email', name='Usuarios_Email_key'),
        {'schema': 'miguel'}
    )

    IdUsuario: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    Email: Mapped[str] = mapped_column(String(100))
    PasswordHash: Mapped[str] = mapped_column(String(255))
    Nombre: Mapped[str] = mapped_column(String(20))
    Apellido: Mapped[str] = mapped_column(String(30))
    IdRol: Mapped[int] = mapped_column(Integer)
    FechaRegistro: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    Activo: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    Roles_: Mapped['Roles'] = relationship('Roles', back_populates='Usuarios')
    Empleados: Mapped[List['Empleados']] = relationship('Empleados', back_populates='Usuarios_')
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Usuarios_')


class Empleados(Base):
    __tablename__ = 'Empleados'
    __table_args__ = (
        ForeignKeyConstraint(['IdEmpresa'], ['miguel.Empresas.IdEmpresa'], name='Empleados_IdEmpresa_fkey'),
        ForeignKeyConstraint(['IdUsuario'], ['miguel.Usuarios.IdUsuario'], name='Empleados_IdUsuario_fkey'),
        PrimaryKeyConstraint('IdEmpleado', name='Empleados_pkey'),
        {'schema': 'miguel'}
    )

    IdEmpleado: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    IdEmpresa: Mapped[int] = mapped_column(Integer)
    IdUsuario: Mapped[int] = mapped_column(Integer)

    Empresas_: Mapped['Empresas'] = relationship('Empresas', back_populates='Empleados')
    Usuarios_: Mapped['Usuarios'] = relationship('Usuarios', back_populates='Empleados')
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Empleados_')


class Reservaciones(Base):
    __tablename__ = 'Reservaciones'
    __table_args__ = (
        CheckConstraint('"IdUsuario" IS NOT NULL AND "IdEmpleado" IS NULL AND "IdEmpresa" IS NULL OR "IdUsuario" IS NULL AND "IdEmpleado" IS NOT NULL AND "IdEmpresa" IS NOT NULL', name='CHK_Reservaciones_Asignacion'),
        ForeignKeyConstraint(['IdEmpleado'], ['miguel.Empleados.IdEmpleado'], name='Reservaciones_IdEmpleado_fkey'),
        ForeignKeyConstraint(['IdEmpresa'], ['miguel.Empresas.IdEmpresa'], name='Reservaciones_IdEmpresa_fkey'),
        ForeignKeyConstraint(['IdUsuario'], ['miguel.Usuarios.IdUsuario'], name='Reservaciones_IdUsuario_fkey'),
        ForeignKeyConstraint(['ciudadinicioid'], ['miguel.Ciudades.IdCiudad'], name='Reservaciones_ciudadinicioid_fkey'),
        ForeignKeyConstraint(['ciudadfinid'], ['miguel.Ciudades.IdCiudad'], name='Reservaciones_ciudadfinid_fkey'),
        PrimaryKeyConstraint('IdReservacion', name='Reservaciones_pkey'),
        {'schema': 'miguel'}
    )

    IdReservacion: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    FechaInicio: Mapped[datetime.date] = mapped_column(Date)
    FechaFin: Mapped[datetime.date] = mapped_column(Date)
    IdUsuario: Mapped[Optional[int]] = mapped_column(Integer)
    IdEmpleado: Mapped[Optional[int]] = mapped_column(Integer)
    IdEmpresa: Mapped[Optional[int]] = mapped_column(Integer)
    ciudadinicioid: Mapped[Optional[int]] = mapped_column(Integer)
    ciudadfinid: Mapped[Optional[int]] = mapped_column(Integer)
    RutaPersonalizada: Mapped[Optional[str]] = mapped_column(String(255))
    RequerimientosAdicionales: Mapped[Optional[str]] = mapped_column(String(255))
    Estado: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'Pendiente'::character varying"))
    FechaReservacion: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    FechaConfirmacion: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    Total: Mapped[Optional[int]] = mapped_column(Integer)
    SubTotal: Mapped[Optional[int]] = mapped_column(Integer)
    MotivoRechazo: Mapped[Optional[str]] = mapped_column(String)

    Empleados_: Mapped[Optional['Empleados']] = relationship('Empleados', back_populates='Reservaciones')
    Empresas_: Mapped[Optional['Empresas']] = relationship('Empresas', back_populates='Reservaciones')
    Usuarios_: Mapped[Optional['Usuarios']] = relationship('Usuarios', back_populates='Reservaciones', lazy='joined')
    CiudadInicio: Mapped[Optional['Ciudades']] = relationship('Ciudades', foreign_keys=[ciudadinicioid])
    CiudadFin: Mapped[Optional['Ciudades']] = relationship('Ciudades', foreign_keys=[ciudadfinid])
    Notificaciones: Mapped[List['Notificaciones']] = relationship('Notificaciones', back_populates='Reservaciones_')
    PreFacturas: Mapped[List['PreFacturas']] = relationship('PreFacturas', back_populates='Reservaciones_')
    VehiculosReservaciones: Mapped[List['VehiculosReservaciones']] = relationship('VehiculosReservaciones', back_populates='Reservaciones_')


class Notificaciones(Base):
    __tablename__ = 'Notificaciones'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['miguel.Reservaciones.IdReservacion'], name='Notificaciones_IdReservacion_fkey'),
        PrimaryKeyConstraint('IdNotificacion', name='Notificaciones_pkey'),
        {'schema': 'miguel'}
    )

    IdNotificacion: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    IdReservacion: Mapped[int] = mapped_column(Integer)
    TipoNotificacion: Mapped[str] = mapped_column(String(50))
    FechaEnvio: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    Reservaciones_: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='Notificaciones')


class PreFacturas(Base):
    __tablename__ = 'PreFacturas'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['miguel.Reservaciones.IdReservacion'], name='PreFacturas_IdReservacion_fkey'),
        PrimaryKeyConstraint('IdPreFactura', name='PreFacturas_pkey'),
        {'schema': 'miguel'}
    )

    IdPreFactura: Mapped[int] = mapped_column(Integer, Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1), primary_key=True)
    IdReservacion: Mapped[int] = mapped_column(Integer)
    CostoVehiculo: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2))
    CostoTotal: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2))
    CostoAdicional: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), server_default=text('0'))
    FechaGeneracion: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    ArchivoPDF: Mapped[Optional[str]] = mapped_column(String(255))

    Reservaciones_: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='PreFacturas')


class VehiculosReservaciones(Base):
    __tablename__ = 'VehiculosReservaciones'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['miguel.Reservaciones.IdReservacion'], name='VehiculosReservaciones_IdReservacion_fkey'),
        ForeignKeyConstraint(['IdVehiculo'], ['miguel.Vehiculos.IdVehiculo'], name='VehiculosReservaciones_IdVehiculo_fkey'),
        PrimaryKeyConstraint('IdVehiculo', 'IdReservacion', name='VehiculosReservaciones_pkey'),
        {'schema': 'miguel'}
    )

    IdVehiculo: Mapped[int] = mapped_column(Integer, primary_key=True)
    IdReservacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    FechaAsignacion: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    EstadoAsignacion: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'Activa'::character varying"))

    Reservaciones_: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='VehiculosReservaciones')
    Vehiculos_: Mapped['Vehiculos'] = relationship('Vehiculos', back_populates='VehiculosReservaciones')
