from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional
from modelos import (RolUsuario, EstadoReceta, TipoTransaccion, 
                     EstadoKardex, EstadoIncidencia)

# --- Esquemas de Usuario ---
class UsuarioBase(BaseModel):
    nombre_usuario: str
    nombre: str
    apellido: str

class UsuarioCrear(UsuarioBase):
    clave: str
    rol: RolUsuario

class Usuario(UsuarioBase):
    id: int
    rol: RolUsuario

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str

# --- Esquemas de Profesional ---
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
        
# --- Esquemas de MedicamentoCatalogo ---
class MedicamentoCatalogoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class MedicamentoCatalogoCrear(MedicamentoCatalogoBase):
    pass

class MedicamentoCatalogo(MedicamentoCatalogoBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Esquemas de Medicamento (Ubicacion) ---
class MedicamentoBase(BaseModel):
    ubicacion: str
    lote: str
    fecha_vencimiento: date
    stock_actual: int
    umbral_minimo: int

class MedicamentoCrear(MedicamentoBase):
    catalogo_id: int

class Medicamento(MedicamentoBase):
    id: int
    catalogo_id: int
    catalogo: MedicamentoCatalogo 

    class Config:
        from_attributes = True

# --- Esquemas de Receta ---
class DetalleRecetaBase(BaseModel):
    catalogo_id: int
    cantidad: int

class DetalleRecetaCrear(DetalleRecetaBase):
    pass

class DetalleReceta(DetalleRecetaBase):
    id: int
    receta_id: int
    catalogo: MedicamentoCatalogo

    class Config:
        from_attributes = True

class RecetaBase(BaseModel):
    id_paciente: str
    fecha_emision: date
    profesional_id: int

class RecetaCrear(RecetaBase):
    detalles: List[DetalleRecetaCrear]

class ProfesionalSimple(BaseModel): 
    nombre: str
    class Config:
        from_attributes = True

class Receta(RecetaBase):
    id: int
    estado: EstadoReceta
    detalles: List[DetalleReceta] = []
    profesional: Optional[ProfesionalSimple] = None 

    class Config:
        from_attributes = True

# --- Esquemas de Transaccion ---
class TransaccionBase(BaseModel):
    tipo_transaccion: TipoTransaccion
    medicamento_id: int 
    cantidad: int
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

class DispensarRespuesta(BaseModel):
    receta: Receta
    alertas: list[str]

# --- Esquemas de Pedido ---
class PedidoBase(BaseModel):
    descripcion: str

class DetallePedidoBase(BaseModel):
    catalogo_id: int 
    cantidad: int

class DetallePedidoCrear(DetallePedidoBase):
    pass

class DetallePedido(DetallePedidoBase):
    id: int
    pedido_id: int
    catalogo: MedicamentoCatalogo

    class Config:
        from_attributes = True

class PedidoCrear(PedidoBase):
    detalles: List[DetallePedidoCrear]

class Pedido(PedidoBase):
    id: int
    estado: str
    fecha_creacion: datetime
    detalles: List[DetallePedido] = []
    
    class Config:
        from_attributes = True

# --- Esquemas para Recepcion de Pedidos ---
class RecepcionItem(BaseModel):
    detalle_pedido_id: int
    accion: str 
    medicamento_id_ubicacion: Optional[int] = None 
    nueva_ubicacion_data: Optional[MedicamentoCrear] = None

class RecepcionPedidoPayload(BaseModel):
    items: List[RecepcionItem]

# --- Esquema para el asistente de reposicion (ia) --- 
#revisar archivo ia.py
class SugerenciaPedido(BaseModel):
    catalogo_id: int
    nombre_medicamento: str
    stock_actual: int
    demanda_estimada_30_dias: float
    cantidad_sugerida_a_pedir: float
    
    class Config:
        from_attributes = True

# --- Esquema para dashboard de catalogo---
#ia.py
class CatalogoDashboardItem(MedicamentoCatalogo):
    stock_total: int
    demanda_estimada_30_dias: Optional[float] = None
    estado_ia: str
    
    class Config:
        from_attributes = True

# --- Esquema para el asistenmte de preparacion---
#ia.py
class PrediccionDiariaItem(BaseModel):
    catalogo_id: int
    nombre_medicamento: str
    stock_actual: int
    demanda_estimada_hoy: float
    
    class Config:
        from_attributes = True

# --- esquemas para la gestion de los kardex ---
class KardexBase(BaseModel):
    nombre: str
    identificador: str

class Kardex(KardexBase):
    id: int
    estado: EstadoKardex

    class Config:
        from_attributes = True

class IncidenciaKardexBase(BaseModel):
    reporte_operario: str

class IncidenciaKardexCrear(IncidenciaKardexBase):
    kardex_id: int 

class IncidenciaKardexResolver(BaseModel):
    respuesta_admin: str
    fecha_resolucion_programada: Optional[datetime] = None
    estado_incidencia: EstadoIncidencia
    
class IncidenciaKardex(IncidenciaKardexBase):
    id: int
    kardex_id: int
    fecha_reporte: datetime
    estado_incidencia: EstadoIncidencia
    fecha_resolucion_programada: Optional[datetime] = None
    respuesta_admin: Optional[str] = None
    
    # se usa el esquema del usuario que hace la operacion para reportar o resolver
    usuario_reporta: Usuario 
    usuario_resuelve: Optional[Usuario] = None
    kardex: Kardex

    class Config:
        from_attributes = True