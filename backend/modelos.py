from sqlalchemy import Column, Integer, String, Enum, ForeignKey # type: ignore
from base_de_datos import Base
import enum

#Enum para definir los roles posibles
class RolUsuario(str, enum.Enum):
    administrador = "administrador"
    funcionario = "funcionario"

class EstadoReceta(str, enum.Enum):
    pendiente = "pendiente"
    en_proceso = "en_proceso"
    completada = "completada"

# Modelo para la tabla de uuarios
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String, unique=True, index=True)
    clave_hasheada = Column(String)
    rol = Column(Enum(RolUsuario))

# Modelo para la tabla de medicamentos
class Medicamento(Base):
    __tablename__ = "medicamentos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    stock_actual = Column(Integer)
    umbral_minimo = Column(Integer)

# Modelo para la tabla de Recetas
class Receta(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(String, index=True)
    estado = Column(Enum(EstadoReceta), default=EstadoReceta.pendiente)

# Modelo para la tabla de "Detalle de Receta"
class DetalleReceta(Base):
    __tablename__ = "detalles_receta"

    id = Column(Integer, primary_key=True, index=True)
    receta_id = Column(Integer, ForeignKey("recetas.id"))
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    cantidad = Column(Integer)