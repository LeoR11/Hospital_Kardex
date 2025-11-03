from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional
from modelos import RolUsuario, EstadoReceta, TipoTransaccion

# US8UARIOS

class UsuarioCrear(BaseModel):
    nombre_usuario: str
    clave: str
    rol: RolUsuario

class Usuario(BaseModel):
    id: int
    nombre_usuario: str
    rol: RolUsuario

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

#PROFESIONALES

class ProfesionalBase(BaseModel):
    nombre: str
    run: str
    profesion: str

class ProfesionalCrear(ProfesionalBase):
    pass

class Profesional(ProfesionalBase):
    id: int

    class Config:
        from_attributes = True

#MEDICAMENTOS

class MedicamentoBase(BaseModel):
    nombre: str
    lote: str
    fecha_vencimiento: date
    stock_actual: int
    umbral_minimo: int

class MedicamentoCrear(MedicamentoBase):
    pass

class Medicamento(MedicamentoBase):
    id: int

    class Config:
        from_attributes = True

# RECETAS
class DetalleRecetaBase(BaseModel):
    medicamento_id: int
    cantidad: int

class DetalleRecetaCrear(DetalleRecetaBase):
    pass


class RecetaBase(BaseModel):
    id_paciente: str
    fecha_emision: date
    profesional_id: int

class RecetaCrear(RecetaBase):
    detalles: List[DetalleRecetaCrear]


class DetalleReceta(DetalleRecetaBase):
    id: int
    receta_id: int

    class Config:
        from_attributes = True


class Receta(RecetaBase):
    id: int
    estado: EstadoReceta
    detalles: List[DetalleReceta] = []

    class Config:
        from_attributes = True
        
# TRANSACCIONES DE INVENTARIO

class TransaccionBase(BaseModel):
    tipo_transaccion: TipoTransaccion
    medicamento_id: int
    cantidad: int # POSITIVO ENTRADAS / NEGATIVO SALIDAS
    motivo: Optional[str] = None

class TransaccionCrear(TransaccionBase):
    pass

class TransaccionInventario(TransaccionBase):
    id: int
    fecha_hora: datetime
    usuario_id: int
    receta_id: Optional[int] = None

    class Config:
        from_attributes = True

#RESPUESTAS DE LA DISPENSION

class DispensarRespuesta(BaseModel):
    receta: Receta
    alertas: list[str]

#PEDIDOS

class DetallePedidoBase(BaseModel):
    medicamento_id: int
    cantidad: int

class DetallePedidoCrear(DetallePedidoBase):
    pass

class DetallePedido(DetallePedidoBase):
    id: int
    pedido_id: int
    class Config:
        from_attributes = True

class PedidoBase(BaseModel):
    descripcion: str

class PedidoCrear(PedidoBase):
    detalles: List[DetallePedidoCrear]

class Pedido(PedidoBase):
    id: int
    estado: str
    fecha_creacion: datetime
    detalles: List[DetallePedido] = []
    
    class Config:
        from_attributes = True