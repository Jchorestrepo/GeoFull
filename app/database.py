from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexión a la base de datos PostgreSQL.
# TODO: Mover esto a una configuración con variables de entorno.
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/geofull"

# El 'engine' es el punto de entrada a la base de datos.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

# Cada instancia de SessionLocal será una sesión de base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base que usarán nuestros modelos de SQLAlchemy para heredar.
Base = declarative_base()
