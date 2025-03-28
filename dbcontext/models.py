from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal


class Base(DeclarativeBase):
    pass


class Ciudades(Base):
    __tablename__ = 'Ciudades'
    __table_args__ = (
        PrimaryKeyConstraint('IdCiudad', name='Ciudades_pkey'),
        {'schema': 'ciprian'}
    )

    IdCiudad: Mapped[int] = mapped_column(
        Integer,
        Identity(
            always=True,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=2147483647,
            cycle=False,
            cache=1
        ),
        primary_key=True
    )
    Nombre: Mapped[str] = mapped_column(String(20))
    Estado: Mapped[str] = mapped_column(String(20))


class Permisos(Base):
    __tablename__ = 'Permisos'
    __table_args__ = (
        PrimaryKeyConstraint('IdPermiso', name='Permisos_pkey'),
        {'schema': 'ciprian'}
    )

    IdPermiso: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    NombrePermiso: Mapped[str] = mapped_column(String(20))
    Descripcion: Mapped[Optional[str]] = mapped_column(String(100))

    # Relación muchos-a-muchos con Roles a través de la tabla intermedia RolesPermisos
    Roles: Mapped[List['Roles']] = relationship(
        'Roles',
        secondary='ciprian.RolesPermisos',
        back_populates='Permisos'
    )


class Roles(Base):
    __tablename__ = 'Roles'
    __table_args__ = (
        PrimaryKeyConstraint('IdRol', name='Roles_pkey'),
        {'schema': 'ciprian'}
    )

    IdRol: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    NombreRol: Mapped[str] = mapped_column(String(20))
    Descripcion: Mapped[Optional[str]] = mapped_column(String(200))

    Permisos: Mapped[List['Permisos']] = relationship(
        'Permisos',
        secondary='ciprian.RolesPermisos',
        back_populates='Roles'
    )

    # Relación uno-a-muchos con Usuarios
    Usuarios: Mapped[List['Usuarios']] = relationship('Usuarios', back_populates='Role')


# Tabla intermedia RolesPermisos (muchos-a-muchos)
t_RolesPermisos = Table(
    'RolesPermisos',
    Base.metadata,
    Column('IdRol', Integer, primary_key=True, nullable=False),
    Column('IdPermiso', Integer, primary_key=True, nullable=False),
    ForeignKeyConstraint(['IdPermiso'], ['ciprian.Permisos.IdPermiso'], name='RolesPermisos_IdPermiso_fkey'),
    ForeignKeyConstraint(['IdRol'], ['ciprian.Roles.IdRol'], name='RolesPermisos_IdRol_fkey'),
    PrimaryKeyConstraint('IdRol', 'IdPermiso', name='RolesPermisos_pkey'),
    schema='ciprian'
)


class Usuarios(Base):
    __tablename__ = 'Usuarios'
    __table_args__ = (
        ForeignKeyConstraint(['IdRol'], ['ciprian.Roles.IdRol'], name='Usuarios_IdRol_fkey'),
        PrimaryKeyConstraint('IdUsuario', name='Usuarios_pkey'),
        UniqueConstraint('Email', name='Usuarios_Email_key'),
        {'schema': 'ciprian'}
    )

    IdUsuario: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    Email: Mapped[str] = mapped_column(String(100))
    PasswordHash: Mapped[str] = mapped_column(String(255))
    Nombre: Mapped[str] = mapped_column(String(20))
    Apellido: Mapped[str] = mapped_column(String(30))
    IdRol: Mapped[int] = mapped_column(Integer)
    FechaRegistro: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    Activo: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        server_default=text('true')
    )

    Role: Mapped['Roles'] = relationship('Roles', back_populates='Usuarios')

    # Relación uno-a-muchos con Empleados y Reservaciones
    Empleados: Mapped[List['Empleados']] = relationship('Empleados', back_populates='Usuarios1')
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Usuarios1')


class Empresas(Base):
    __tablename__ = 'Empresas'
    __table_args__ = (
        PrimaryKeyConstraint('IdEmpresa', name='Empresas_pkey'),
        {'schema': 'ciprian'}
    )

    IdEmpresa: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    Nombre: Mapped[str] = mapped_column(String(20))
    ContactoEmail: Mapped[str] = mapped_column(String(100))
    ContactoTelefono: Mapped[str] = mapped_column(String(20))
    FechaRegistro: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    Activo: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    # Relación uno-a-muchos con Empleados y Reservaciones
    Empleados: Mapped[List['Empleados']] = relationship('Empleados', back_populates='Empresas1')
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Empresas1')


class Empleados(Base):
    __tablename__ = 'Empleados'
    __table_args__ = (
        ForeignKeyConstraint(['IdEmpresa'], ['ciprian.Empresas.IdEmpresa'], name='Empleados_IdEmpresa_fkey'),
        ForeignKeyConstraint(['IdUsuario'], ['ciprian.Usuarios.IdUsuario'], name='Empleados_IdUsuario_fkey'),
        PrimaryKeyConstraint('IdEmpleado', name='Empleados_pkey'),
        {'schema': 'ciprian'}
    )

    IdEmpleado: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    IdEmpresa: Mapped[int] = mapped_column(Integer)
    IdUsuario: Mapped[int] = mapped_column(Integer)

    Empresas1: Mapped['Empresas'] = relationship('Empresas', back_populates='Empleados')
    Usuarios1: Mapped['Usuarios'] = relationship('Usuarios', back_populates='Empleados')

    # Relación uno-a-muchos con Reservaciones
    Reservaciones: Mapped[List['Reservaciones']] = relationship('Reservaciones', back_populates='Empleados1')


class Reservaciones(Base):
    __tablename__ = 'Reservaciones'
    __table_args__ = (
        CheckConstraint(
            '"IdUsuario" IS NOT NULL AND "IdEmpleado" IS NULL AND "IdEmpresa" IS NULL '
            'OR "IdUsuario" IS NULL AND "IdEmpleado" IS NOT NULL AND "IdEmpresa" IS NOT NULL',
            name='CHK_Reservaciones_Asignacion'
        ),
        ForeignKeyConstraint(['IdEmpleado'], ['ciprian.Empleados.IdEmpleado'], name='Reservaciones_IdEmpleado_fkey'),
        ForeignKeyConstraint(['IdEmpresa'], ['ciprian.Empresas.IdEmpresa'], name='Reservaciones_IdEmpresa_fkey'),
        ForeignKeyConstraint(['IdUsuario'], ['ciprian.Usuarios.IdUsuario'], name='Reservaciones_IdUsuario_fkey'),
        PrimaryKeyConstraint('IdReservacion', name='Reservaciones_pkey'),
        {'schema': 'ciprian'}
    )

    IdReservacion: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    FechaInicio: Mapped[datetime.datetime] = mapped_column(DateTime)
    FechaFin: Mapped[datetime.datetime] = mapped_column(DateTime)
    IdUsuario: Mapped[Optional[int]] = mapped_column(Integer)
    IdEmpleado: Mapped[Optional[int]] = mapped_column(Integer)
    IdEmpresa: Mapped[Optional[int]] = mapped_column(Integer)
    RutaPersonalizada: Mapped[Optional[str]] = mapped_column(String(255))
    RequerimientosAdicionales: Mapped[Optional[str]] = mapped_column(String(255))
    Estado: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'Pendiente'::character varying"))
    FechaReservacion: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    FechaConfirmacion: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    # Relaciones hacia Empleados, Empresas y Usuarios
    Empleados1: Mapped[Optional['Empleados']] = relationship('Empleados', back_populates='Reservaciones')
    Empresas1: Mapped[Optional['Empresas']] = relationship('Empresas', back_populates='Reservaciones')
    Usuarios1: Mapped[Optional['Usuarios']] = relationship('Usuarios', back_populates='Reservaciones')

    # Otras relaciones uno-a-muchos
    Notificaciones: Mapped[List['Notificaciones']] = relationship('Notificaciones', back_populates='Reservaciones1')
    PreFacturas: Mapped[List['PreFacturas']] = relationship('PreFacturas', back_populates='Reservaciones1')
    VehiculosReservaciones: Mapped[List['VehiculosReservaciones']] = relationship(
        'VehiculosReservaciones',
        back_populates='Reservaciones1'
    )


class Vehiculos(Base):
    __tablename__ = 'Vehiculos'
    __table_args__ = (
        PrimaryKeyConstraint('IdVehiculo', name='Vehiculos_pkey'),
        {'schema': 'ciprian'}
    )

    IdVehiculo: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    Placa: Mapped[str] = mapped_column(String(20))
    Modelo: Mapped[str] = mapped_column(String(50))
    TipoVehiculo: Mapped[str] = mapped_column(String(20))
    Capacidad: Mapped[int] = mapped_column(Integer)
    Ano: Mapped[int] = mapped_column(Integer)
    Price: Mapped[int] = mapped_column(Integer)
    Disponible: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))

    # Relación uno-a-muchos con VehiculosReservaciones
    VehiculosReservaciones: Mapped[List['VehiculosReservaciones']] = relationship(
        'VehiculosReservaciones',
        back_populates='Vehiculos1'
    )


class Notificaciones(Base):
    __tablename__ = 'Notificaciones'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['ciprian.Reservaciones.IdReservacion'], name='Notificaciones_IdReservacion_fkey'),
        PrimaryKeyConstraint('IdNotificacion', name='Notificaciones_pkey'),
        {'schema': 'ciprian'}
    )

    IdNotificacion: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    IdReservacion: Mapped[int] = mapped_column(Integer)
    TipoNotificacion: Mapped[str] = mapped_column(String(50))
    FechaEnvio: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )

    Reservaciones1: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='Notificaciones')


class PreFacturas(Base):
    __tablename__ = 'PreFacturas'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['ciprian.Reservaciones.IdReservacion'], name='PreFacturas_IdReservacion_fkey'),
        PrimaryKeyConstraint('IdPreFactura', name='PreFacturas_pkey'),
        {'schema': 'ciprian'}
    )

    IdPreFactura: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647),
        primary_key=True
    )
    IdReservacion: Mapped[int] = mapped_column(Integer)
    CostoVehiculo: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2))
    CostoTotal: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2))
    CostoAdicional: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2), server_default=text('0'))
    FechaGeneracion: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    ArchivoPDF: Mapped[Optional[str]] = mapped_column(String(255))

    Reservaciones1: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='PreFacturas')


class VehiculosReservaciones(Base):
    __tablename__ = 'VehiculosReservaciones'
    __table_args__ = (
        ForeignKeyConstraint(['IdReservacion'], ['ciprian.Reservaciones.IdReservacion'], name='VehiculosReservaciones_IdReservacion_fkey'),
        ForeignKeyConstraint(['IdVehiculo'], ['ciprian.Vehiculos.IdVehiculo'], name='VehiculosReservaciones_IdVehiculo_fkey'),
        PrimaryKeyConstraint('IdVehiculo', 'IdReservacion', name='VehiculosReservaciones_pkey'),
        {'schema': 'ciprian'}
    )

    IdVehiculo: Mapped[int] = mapped_column(Integer, primary_key=True)
    IdReservacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    FechaAsignacion: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime,
        server_default=text('CURRENT_TIMESTAMP')
    )
    EstadoAsignacion: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'Activa'::character varying"))

    Reservaciones1: Mapped['Reservaciones'] = relationship('Reservaciones', back_populates='VehiculosReservaciones')
    Vehiculos1: Mapped['Vehiculos'] = relationship('Vehiculos', back_populates='VehiculosReservaciones')