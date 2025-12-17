from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Date, DateTime # type: ignore
from sqlalchemy.orm import relationship # type: ignore
from sqlalchemy.sql import func # type: ignore
from base_de_datos import Base
import enum

# --- Enums (Enumeradores) ---
# Estos deben estar definidos ANTES de usarse en las clases
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
    reposicion_servicio = "reposicion_servicio"
    ajuste_manual = "ajuste_manual"
    compra = "compra"

class EstadoKardex(str, enum.Enum):
    operativo = "operativo"
    en_falla = "en_falla"
    en_mantencion = "en_mantencion"

class EstadoIncidencia(str, enum.Enum):
    abierta = "abierta"
    resuelta = "resuelta"

# --- Modelos de Base de Datos (Tablas) ---

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_usuario = Column(String, unique=True, index=True)
    clave_hasheada = Column(String)
    rol = Column(Enum(RolUsuario))
    nombre = Column(String, index=True)
    apellido = Column(String, index=True)

class Profesional(Base):
    __tablename__ = "profesionales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    run = Column(String, unique=True, index=True)
    profesion = Column(String)

class MedicamentoCatalogo(Base):
    __tablename__ = "medicamentos_catalogo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String)

    # Relaciones
    medicamentos_fisicos = relationship("Medicamento", back_populates="catalogo")
    detalles_receta = relationship("DetalleReceta", back_populates="catalogo")
    detalles_pedido = relationship("DetallePedido", back_populates="catalogo")

class Medicamento(Base):
    __tablename__ = "medicamentos"

    id = Column(Integer, primary_key=True, index=True)
    catalogo_id = Column(Integer, ForeignKey("medicamentos_catalogo.id"))
    ubicacion = Column(String, unique=True, index=True) 
    lote = Column(String)
    fecha_vencimiento = Column(Date)
    stock_actual = Column(Integer, default=0)
    umbral_minimo = Column(Integer, default=10)

    catalogo = relationship("MedicamentoCatalogo", back_populates="medicamentos_fisicos")

class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    run = Column(String, unique=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    fecha_nacimiento = Column(Date)
    genero = Column(String)
    prevision = Column(String)
    alergias = Column(String)

class Receta(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    profesional_id = Column(Integer, ForeignKey("profesionales.id"))
    fecha_emision = Column(Date, default=func.now())
    estado = Column(Enum(EstadoReceta), default=EstadoReceta.pendiente)

    paciente = relationship("Paciente")
    profesional = relationship("Profesional")
    detalles = relationship("DetalleReceta", back_populates="receta")

class DetalleReceta(Base):
    __tablename__ = "detalles_receta"

    id = Column(Integer, primary_key=True, index=True)
    receta_id = Column(Integer, ForeignKey("recetas.id"))
    catalogo_id = Column(Integer, ForeignKey("medicamentos_catalogo.id"))
    cantidad = Column(Integer)

    receta = relationship("Receta", back_populates="detalles")
    catalogo = relationship("MedicamentoCatalogo", back_populates="detalles_receta")

class TransaccionInventario(Base):
    __tablename__ = "transacciones_inventario"

    id = Column(Integer, primary_key=True, index=True)
    medicamento_id = Column(Integer, ForeignKey("medicamentos.id"))
    tipo_transaccion = Column(Enum(TipoTransaccion))
    cantidad = Column(Integer)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    motivo = Column(String)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())

    medicamento = relationship("Medicamento")
    usuario = relationship("Usuario")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    descripcion = Column(String)
    estado = Column(String, default="pendiente") 

    detalles = relationship("DetallePedido", back_populates="pedido")

class DetallePedido(Base):
    __tablename__ = "detalles_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    catalogo_id = Column(Integer, ForeignKey("medicamentos_catalogo.id"))
    cantidad = Column(Integer)

    pedido = relationship("Pedido", back_populates="detalles")
    catalogo = relationship("MedicamentoCatalogo", back_populates="detalles_pedido")

class Kardex(Base):
    __tablename__ = "kardex"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    identificador = Column(String, unique=True)
    estado = Column(Enum(EstadoKardex), default=EstadoKardex.operativo)
    
    incidencias = relationship("IncidenciaKardex", back_populates="kardex")

class IncidenciaKardex(Base):
    __tablename__ = "incidencias_kardex"
    
    id = Column(Integer, primary_key=True, index=True)
    kardex_id = Column(Integer, ForeignKey("kardex.id"))
    
    fecha_reporte = Column(DateTime(timezone=True), server_default=func.now())
    reporte_operario = Column(String)
    estado_incidencia = Column(Enum(EstadoIncidencia), default=EstadoIncidencia.abierta)
    
    fecha_resolucion_programada = Column(DateTime(timezone=True), nullable=True)
    respuesta_admin = Column(String, nullable=True)
    
    usuario_reporta_id = Column(Integer, ForeignKey("usuarios.id"))
    
    kardex = relationship("Kardex", back_populates="incidencias")
    usuario_reporta = relationship("Usuario")