from sqlalchemy import create_engine # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore


URL_BASE_DE_DATOS = "sqlite:///./kardex.db"

motor = create_engine(
    URL_BASE_DE_DATOS, connect_args={"check_same_thread": False}
)

# fabrica de sesiones.
SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)


#    Crea la clase Base
# TOIDOS LOS MODELOS LA HEREDAN
Base = declarative_base()