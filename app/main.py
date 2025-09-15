import uuid
import pandas as pd
import io
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from . import crud, models, schemas, processing
from .database import SessionLocal, engine

# Crea la tabla en la base de datos si no existe.
# Nota: Para producción, es mejor usar un sistema de migraciones como Alembic.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GeoFull API",
    description="Backend para normalización y geocodificación de direcciones.",
    version="0.1.0",
)

# --- Dependencias ---

def get_db():
    """Dependencia de FastAPI para obtener una sesión de DB por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"project": "GeoFull API", "status": "ok"}


@app.post("/addresses/", response_model=schemas.Address, tags=["Addresses"])
def create_address_endpoint(
    address: schemas.AddressCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva dirección y lanza el pipeline de procesamiento en segundo plano.
    
    La respuesta es inmediata, y el procesamiento (normalización y geocodificación)
    ocurre automáticamente.
    """
    db_address = crud.get_address_by_original_address(db, original_address=address.original_address)
    if db_address:
        raise HTTPException(status_code=400, detail="Address already registered")
    
    new_address = crud.create_address(db=db, address=address)
    
    # Añade el pipeline de procesamiento como una tarea en segundo plano
    background_tasks.add_task(processing.run_processing_pipeline, address_id=new_address.id)
    
    print(f"Address {new_address.id} created. Processing task added to background.")
    
    return new_address


@app.get("/addresses/", response_model=list[schemas.Address], tags=["Addresses"])
def read_addresses_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Obtiene una lista de direcciones, con paginación.
    """
    addresses = crud.get_addresses(db, skip=skip, limit=limit)
    return addresses


@app.get("/addresses/{address_id}", response_model=schemas.Address, tags=["Addresses"])
def read_address_endpoint(address_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Obtiene una dirección específica por su ID.
    """
    db_address = crud.get_address(db, address_id=address_id)
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return db_address


@app.put("/addresses/{address_id}", response_model=schemas.Address, tags=["Addresses"])
def update_address_endpoint(address_id: uuid.UUID, address_update: schemas.AddressUpdate, db: Session = Depends(get_db)):
    """
    Actualiza una dirección existente por su ID.
    
    Permite actualizaciones parciales.
    """
    db_address = crud.update_address(db, address_id=address_id, address_update=address_update)
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return db_address


@app.delete("/addresses/{address_id}", response_model=schemas.Address, tags=["Addresses"])
def delete_address_endpoint(address_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Elimina una dirección por su ID.
    """
    db_address = crud.delete_address(db, address_id=address_id)
    if db_address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    return db_address


@app.post("/upload", tags=["Files"])
async def upload_file_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Sube un archivo, crea las nuevas direcciones e inicia su procesamiento en segundo plano.
    """
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use .xlsx o .csv")

    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file.file)
        else:
            df = pd.read_csv(file.file)

        address_col = None
        for col in ['direccion', 'address', 'Dirección', 'Address']:
            if col in df.columns:
                address_col = col
                break
        
        if not address_col:
            raise HTTPException(status_code=400, detail="El archivo debe contener una columna llamada 'direccion' o 'address'.")

        created_count = 0
        skipped_count = 0

        for address_str in df[address_col].dropna():
            db_address = crud.get_address_by_original_address(db, original_address=address_str)
            if db_address:
                skipped_count += 1
            else:
                address_schema = schemas.AddressCreate(original_address=address_str)
                new_address = crud.create_address(db=db, address=address_schema)
                created_count += 1
                # Añade la tarea de procesamiento para la nueva dirección
                background_tasks.add_task(processing.run_processing_pipeline, address_id=new_address.id)

        return {
            "message": f"Archivo '{file.filename}' aceptado. Se iniciaron {created_count} nuevas tareas de procesamiento.",
            "rows_found": len(df),
            "new_addresses_created": created_count,
            "addresses_skipped (duplicates)": skipped_count,
        }

    except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {e}")


@app.get("/export/csv", tags=["Utilities"])
async def export_addresses_to_csv(db: Session = Depends(get_db)):
    """
    Exporta todas las direcciones procesadas a un archivo CSV.
    """
    addresses = crud.get_all_addresses(db) # Obtiene todas las direcciones

    # Convierte los objetos SQLAlchemy a diccionarios usando el schema Pydantic
    # Esto asegura que todos los campos estén presentes y en el formato correcto
    addresses_data = [
        schemas.Address.model_validate(addr).model_dump(mode='json') 
        for addr in addresses
    ]

    if not addresses_data:
        raise HTTPException(status_code=404, detail="No hay direcciones para exportar.")

    # Crea un DataFrame de pandas
    df = pd.DataFrame(addresses_data)

    # Reordena las columnas para que las más importantes estén al principio
    # y las nuevas columnas de IA sean visibles
    ordered_columns = [
        'id',
        'original_address',
        'normalized_address',
        'suggested_address',
        'latitude',
        'longitude',
        'postal_code',
        'street_info',
        'neighborhood',
        'apartment_info',
        'notes',
        'status',
        'created_at',
        'updated_at',
    ]
    # Asegura que todas las columnas existan, si no, las añade al final
    df = df[ordered_columns + [col for col in df.columns if col not in ordered_columns]]

    # Crea un buffer en memoria para el CSV
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)

    # Prepara la respuesta para la descarga del archivo
    headers = {
        'Content-Disposition': 'attachment; filename="addresses_export.csv"',
        'Content-Type': 'text/csv; charset=utf-8',
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")



