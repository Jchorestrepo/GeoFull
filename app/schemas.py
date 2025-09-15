import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .models import AddressStatus


# Schema base con los campos compartidos
class AddressBase(BaseModel):
    original_address: str
    normalized_address: str | None = None
    suggested_address: str | None = None

    # Campos estructurados por IA
    street_info: str | None = None
    neighborhood: str | None = None
    apartment_info: str | None = None
    notes: str | None = None

    latitude: float | None = None
    longitude: float | None = None
    postal_code: str | None = None
    status: AddressStatus = AddressStatus.PENDING


# Schema para la creación de una dirección (lo que el usuario envía)
class AddressCreate(BaseModel):
    original_address: str


# Schema para actualizar una dirección (todos los campos son opcionales)
class AddressUpdate(BaseModel):
    original_address: str | None = None
    normalized_address: str | None = None
    suggested_address: str | None = None

    # Campos estructurados por IA
    street_info: str | None = None
    neighborhood: str | None = None
    apartment_info: str | None = None
    notes: str | None = None

    latitude: float | None = None
    longitude: float | None = None
    postal_code: str | None = None
    status: AddressStatus | None = None


# Schema para leer/devolver una dirección desde la API (incluye campos de la DB)
class Address(AddressBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None

    # Configuración para que Pydantic pueda leer el modelo de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
