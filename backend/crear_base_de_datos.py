from base_de_datos import motor, Base
import modelos

print("Creando la base de datos y las tablas...")

Base.metadata.create_all(bind=motor)

print("Base de datos y tablas creadas exitosamente")