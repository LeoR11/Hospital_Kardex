from pydantic import BaseModel # type: ignore
from datetime import date, datetime
from typing import List, Optional, Dict
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
        
# --- Esquemas de Catalogo ---
class MedicamentoCatalogoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class MedicamentoCatalogoCrear(MedicamentoCatalogoBase):
    pass

class MedicamentoCatalogo(MedicamentoCatalogoBase):
    id: int
    stock_total: Optional[int] = 0
    demanda_estimada_30_dias: Optional[float] = None
    estado_ia: Optional[str] = "SIN_DATOS"
    
    class Config:
        from_attributes = True

# --- Esquemas de Inventario Fisico ---
class MedicamentoBase(BaseModel):
    catalogo_id: int
    ubicacion: str
    lote: str
    fecha_vencimiento: date
    stock_actual: int
    umbral_minimo: int

class Medicamento(MedicamentoBase):
    id: int
    catalogo: Optional[MedicamentoCatalogo] = None

    class Config:
        from_attributes = True

class TransaccionManual(BaseModel):
    tipo_transaccion: TipoTransaccion
    medicamento_id: int
    cantidad: int # Positivo o negativo manejado en frontend/backend
    motivo: str

# --- Esquemas de Paciente (HIS) ---
class PacienteBase(BaseModel):
    run: str
    nombre: str
    apellido: str
    fecha_nacimiento: date
    genero: str
    prevision: str
    alergias: Optional[str] = None

class PacienteCrear(PacienteBase):
    pass

class Paciente(PacienteBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Esquemas de Recetas ---
class DetalleRecetaBase(BaseModel):
    catalogo_id: int
    cantidad: int

class DetalleRecetaCrear(DetalleRecetaBase):
    pass

class DetalleReceta(DetalleRecetaBase):
    id: int
    catalogo: MedicamentoCatalogo

    class Config:
        from_attributes = True

class RecetaCrear(BaseModel):
    paciente_id: int
    profesional_id: int
    fecha_emision: date
    detalles: List[DetalleRecetaCrear]

class Receta(BaseModel):
    id: int
    paciente: Optional[Paciente]
    profesional: Optional[Profesional]
    fecha_emision: date
    estado: EstadoReceta
    detalles: List[DetalleReceta]

    class Config:
        from_attributes = True

# --- NUEVO: Esquema de Respuesta para Dispensacion ---
class RespuestaDispensacion(BaseModel):
    mensaje: str
    medicamentos_afectados: List[int]
    alertas: List[str]

# --- Esquemas de Pedidos ---
class DetallePedidoBase(BaseModel):
    catalogo_id: int
    cantidad: int

class DetallePedido(DetallePedidoBase):
    id: int
    catalogo: MedicamentoCatalogo
    
    class Config:
        from_attributes = True

class PedidoCrear(BaseModel):
    descripcion: str
    detalles: List[DetallePedidoBase]

class Pedido(BaseModel):
    id: int
    fecha_creacion: datetime
    descripcion: str
    estado: str
    detalles: List[DetallePedido]
    
    class Config:
        from_attributes = True

# Estructuras para la recepción compleja de pedidos
class ItemRecepcionNuevaUbicacion(BaseModel):
    catalogo_id: int
    ubicacion: str
    lote: str
    fecha_vencimiento: date
    stock_actual: int
    umbral_minimo: int

class ItemRecepcion(BaseModel):
    detalle_pedido_id: int
    accion: str # 'existing' o 'new'
    medicamento_id_ubicacion: Optional[int] = None # Si es existing
    nueva_ubicacion_data: Optional[ItemRecepcionNuevaUbicacion] = None # Si es new

class RecepcionPedido(BaseModel):
    items: List[ItemRecepcion]

# --- Esquemas de Kardex / Incidencias ---
class Kardex(BaseModel):
    id: int
    nombre: str
    identificador: str
    estado: EstadoKardex

    class Config:
        from_attributes = True

class IncidenciaKardexCrear(BaseModel):
    kardex_id: int 
    reporte_operario: str

class IncidenciaKardexResolver(BaseModel):
    respuesta_admin: str
    fecha_resolucion_programada: Optional[datetime] = None
    estado_incidencia: EstadoIncidencia
    
class IncidenciaKardex(BaseModel):
    id: int
    kardex_id: int
    fecha_reporte: datetime
    reporte_operario: str
    estado_incidencia: EstadoIncidencia
    respuesta_admin: Optional[str]
    kardex: Kardex
    kardex: Kardex
    usuario_reporta: Optional[Usuario] = None
    
    class Config:
        from_attributes = True