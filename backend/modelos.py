from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Date, DateTime # type: ignore
from sqlalchemy.orm import relationship # type: ignore # Importante para las relaciones
from sqlalchemy.sql import func # type: ignore
from base_de_datos import Base
import enum

# --- Enums para controlar los tipos de datos ---
class RolUsuario(str, enum.Enum):
    administrador = "administrador"
    funcionario = "funcionario"

class EstadoReceta(str, enum.Enum):
    pendiente = "pendiente"
    completada = "completada"
    cancelada = "cancelada"

class TipoTransaccion(str, enum.Enum):
    dispensacion = "dispensacion"         
    devolucion = "devolucion"              
    reposicion = "reposicion_servicio"     
    ajuste_manual = "ajuste_manual"        
    compra = "compra"                      

# FORMATO DE LAS TABLAS

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String, unique=True, index=True)
    clave_hasheada = Column(String)
    rol = Column(Enum(RolUsuario))

class Profesional(Base):
    __tablename__ = "profesionales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    run = Column(String, unique=True, index=True)
    profesion = Column(String)

class Receta(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True, index=True)
    id_paciente = Column(String, index=True) # RUT DEL APCIENTE
    fecha_emision = Column(Date, default=func.now())
    estado = Column(Enum(EstadoReceta), default=EstadoReceta.pendiente)
    
    # RELACION = CONECTA RECETA / PROFESIONAL
    profesional_id = Column(Integer, ForeignKey("profesionales.id"))


    detalles = relationship("DetalleReceta")

class Medicamento(Base):
    __tablename__ = "medicamentos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    lote = Column(String)
    fecha_vencimiento = Column(Date)
    stock_actual = Column(Integer)
    umbral_minimo = Column(Integer)

#TABLAS DE RLACION Y TRAZABILIDAD

class DetalleReceta(Base):
    __tablename__ = "detalles_receta"

    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer)
    
    receta_id = Column(Integer, ForeignKey("recetas.id"))
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))

class TransaccionInventario(Base):
    __tablename__ = "transacciones_inventario"

    id = Column(Integer, primary_key=True, index=True)
    tipo_transaccion = Column(Enum(TipoTransaccion))
    cantidad = Column(Integer) 
    motivo = Column(String, nullable=True) 
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    
  
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    receta_id = Column(Integer, ForeignKey("recetas.id"), nullable=True) 




class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    estado = Column(String, default="pendiente") 
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    
    detalles = relationship("DetallePedido")

class DetallePedido(Base):
    __tablename__ = "detalles_pedido"
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Integer)
    
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))