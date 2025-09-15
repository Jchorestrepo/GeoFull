from sqlalchemy.orm import Session
import uuid

from . import models, schemas


def get_address(db: Session, address_id: uuid.UUID):
    """Obtiene una dirección por su ID."""
    return db.query(models.Address).filter(models.Address.id == address_id).first()


def get_address_by_original_address(db: Session, original_address: str):
    """Obtiene una dirección por su contenido original."""
    return db.query(models.Address).filter(models.Address.original_address == original_address).first()


def get_addresses(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene una lista de direcciones."""
    return db.query(models.Address).offset(skip).limit(limit).all()


def create_address(db: Session, address: schemas.AddressCreate):
    """Crea una nueva dirección en la base de datos."""
    # Crea una instancia del modelo SQLAlchemy a partir de los datos del schema
    db_address = models.Address(original_address=address.original_address)
    
    # Añade la instancia a la sesión de la base de datos
    db.add(db_address)
    
    # Confirma los cambios para guardarlos en la base de datos
    db.commit()
    
    # Refresca la instancia para obtener los valores generados por la base de datos (como el id)
    db.refresh(db_address)
    
    return db_address

def update_address(db: Session, address_id: uuid.UUID, address_update: schemas.AddressUpdate):
    """Actualiza una dirección existente."""
    db_address = get_address(db, address_id=address_id)
    if not db_address:
        return None

    update_data = address_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_address, key, value)

    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address


def delete_address(db: Session, address_id: uuid.UUID):
    """Elimina una dirección."""
    db_address = get_address(db, address_id=address_id)
    if not db_address:
        return None
    
    db.delete(db_address)
    db.commit()
    return db_address

def get_all_addresses(db: Session):
    """Obtiene TODAS las direcciones de la base de datos, sin paginación."""
    return db.query(models.Address).all()
