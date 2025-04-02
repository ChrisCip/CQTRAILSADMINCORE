from pydantic import BaseModel, Field
from typing import Optional, List

class CiudadBase(BaseModel):
    Nombre: str = Field(..., 
        description="Nombre de la ciudad", 
        example="Cancún",
        min_length=2,
        max_length=20
    )
    Estado: str = Field(..., 
        description="Estado donde se encuentra la ciudad", 
        example="Quintana Roo",
        min_length=2,
        max_length=20
    )

class CiudadCreate(CiudadBase):
    """
    Modelo para crear una nueva ciudad
    """
    pass

class CiudadUpdate(BaseModel):
    """
    Modelo para actualizar una ciudad existente
    """
    Nombre: Optional[str] = Field(None, 
        description="Nombre de la ciudad", 
        example="Playa del Carmen",
        min_length=2,
        max_length=20
    )
    Estado: Optional[str] = Field(None, 
        description="Estado donde se encuentra la ciudad", 
        example="Quintana Roo",
        min_length=2,
        max_length=20
    )

class CiudadResponse(CiudadBase):
    """
    Modelo para respuesta de ciudad con su ID
    """
    IdCiudad: int = Field(..., description="ID único de la ciudad", example=1)
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "IdCiudad": 1,
                "Nombre": "Cancún",
                "Estado": "Quintana Roo"
            }
        }
