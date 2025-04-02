from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Generic, TypeVar
from datetime import datetime

# Generic type for response models
T = TypeVar('T')

class ResponseBase(BaseModel, Generic[T]):
    """
    Modelo base de respuesta para todas las operaciones API.
    
    Proporciona una estructura consistente para todas las respuestas de la API,
    incluyendo un campo de éxito, un mensaje y los datos (opcional).
    """
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    message: str = Field("Operation successful", description="Mensaje informativo sobre el resultado de la operación")
    data: Optional[T] = Field(None, description="Datos retornados por la operación (si aplica)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operación realizada con éxito",
                "data": "Depende del tipo de respuesta"
            }
        }
    )
