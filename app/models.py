import enum
import uuid

from sqlalchemy import Column, DateTime, Float, String, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .database import Base


class AddressStatus(str, enum.Enum):
    PENDING = "pending"
    NORMALIZED = "normalized"
    VERIFIED = "verified"


class Address(Base):
    __tablename__ = "addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Direcciones
    original_address = Column(Text, nullable=False)
    normalized_address = Column(Text, nullable=True)  # La que se usa para geocodificar
    suggested_address = Column(Text, nullable=True)   # La que devuelve el geocodificador
    
    # --- Nuevos campos para datos estructurados por IA ---
    street_info = Column(Text, nullable=True)
    neighborhood = Column(Text, nullable=True)
    apartment_info = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    # ----------------------------------------------------

    # Datos geográficos
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    postal_code = Column(String(10), nullable=True)
    
    # Metadatos
    status = Column(Enum(AddressStatus), default=AddressStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
