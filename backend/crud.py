from sqlalchemy.orm import Session, joinedload # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore
from sqlalchemy import func # type: ignore
import modelos as modelos # A veces importado como modelos o models, asegurate que tu archivo se llama modelos.py
import modelos # Aseguramos importacion
import esquemas, seguridad
import nosql_manager
from typing import List, Dict, Any
from datetime import datetime, date

# Definicion de Errores Personalizados
class EntidadNoEncontradaError(Exception): pass
class StockInsuficienteError(Exception): pass
class RecetaProcesadaError(Exception): pass
class PedidoProcesadoError(Exception): pass
class UbicacionDuplicadaError(Exception): pass

# --- Usuarios ---
def obtener_usuario_por_nombre(db: Session, nombre_usuario: str):
    return db.query(modelos.Usuario).filter(modelos.Usuario.nombre_usuario == nombre_usuario).first()

def crear_usuario(db: Session, usuario: esquemas.UsuarioCrear):
    db_usuario = modelos.Usuario(
        nombre_usuario=usuario.nombre_usuario,
        clave_hasheada=seguridad.obtener_clave_hasheada(usuario.clave),
        rol=usuario.rol,
        nombre=usuario.nombre,
        apellido=usuario.apellido
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def obtener_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Usuario).offset(skip).limit(limit).all()

# --- Profesionales ---
def crear_profesional(db: Session, profesional: esquemas.ProfesionalCrear):
    db_prof = modelos.Profesional(**profesional.dict())
    db.add(db_prof)
    db.commit()
    db.refresh(db_prof)
    return db_prof

def obtener_profesionales(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Profesional).offset(skip).limit(limit).all()

# --- Catalogo ---
def crear_medicamento_catalogo(db: Session, item: esquemas.MedicamentoCatalogoCrear):
    db_item = modelos.MedicamentoCatalogo(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def obtener_catalogo(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.MedicamentoCatalogo).offset(skip).limit(limit).all()

# --- Pacientes (HIS) ---
def crear_paciente(db: Session, paciente: esquemas.PacienteCrear):
    db_paciente = modelos.Paciente(**paciente.dict())
    db.add(db_paciente)
    db.commit()
    db.refresh(db_paciente)
    return db_paciente

def obtener_paciente_por_run(db: Session, run: str):
    return db.query(modelos.Paciente).filter(modelos.Paciente.run == run).first()

# --- Recetas ---
def crear_receta(db: Session, receta: esquemas.RecetaCrear):
    # Verificar Paciente
    paciente = db.query(modelos.Paciente).filter(modelos.Paciente.id == receta.paciente_id).first()
    if not paciente:
        raise EntidadNoEncontradaError(f"Paciente ID {receta.paciente_id} no encontrado")

    db_receta = modelos.Receta(
        paciente_id=receta.paciente_id,
        profesional_id=receta.profesional_id,
        fecha_emision=receta.fecha_emision,
        estado=modelos.EstadoReceta.pendiente
    )
    db.add(db_receta)
    db.commit()
    db.refresh(db_receta)

    for detalle in receta.detalles:
        db_detalle = modelos.DetalleReceta(
            receta_id=db_receta.id,
            catalogo_id=detalle.catalogo_id,
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)
    
    db.commit()
    db.refresh(db_receta)
    return db_receta

def obtener_recetas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Receta)\
             .options(joinedload(modelos.Receta.detalles).joinedload(modelos.DetalleReceta.catalogo),
                      joinedload(modelos.Receta.paciente),
                      joinedload(modelos.Receta.profesional))\
             .offset(skip).limit(limit).all()

def dispensar_receta(db: Session, receta_id: int, mapeo_dispensacion: Dict[str, int], usuario_id: int):
    """
    Logica compleja de dispensacion.
    mapeo_dispensacion: {'id_detalle_receta': 'id_medicamento_fisico_ubicacion'}
    """
    receta = db.query(modelos.Receta).filter(modelos.Receta.id == receta_id).first()
    if not receta:
        raise EntidadNoEncontradaError("Receta no encontrada")
    
    if receta.estado != modelos.EstadoReceta.pendiente:
        raise RecetaProcesadaError("La receta ya no esta pendiente")

    alertas = []
    medicamentos_afectados = []

    try:
        for detalle in receta.detalles:
            # Buscar que ubicacion eligio el usuario para este detalle
            id_ubicacion_fisica = mapeo_dispensacion.get(str(detalle.id))
            
            if not id_ubicacion_fisica:
                # Si el usuario no mando mapeo para este item, asumimos error o logica parcial
                # Aqui forzamos que debe venir todo
                raise EntidadNoEncontradaError(f"Falta asignacion para el medicamento {detalle.catalogo.nombre}")

            # Obtener el objeto fisico (ubicacion)
            medicamento_fisico = db.query(modelos.Medicamento).filter(modelos.Medicamento.id == id_ubicacion_fisica).with_for_update().first()
            
            if not medicamento_fisico:
                raise EntidadNoEncontradaError(f"Ubicacion ID {id_ubicacion_fisica} no encontrada")
            
            if medicamento_fisico.stock_actual < detalle.cantidad:
                raise StockInsuficienteError(f"Stock insuficiente en {medicamento_fisico.ubicacion}")

            # 1. Descontar Stock
            medicamento_fisico.stock_actual -= detalle.cantidad
            medicamentos_afectados.append(medicamento_fisico.id)

            # 2. Registrar Transaccion
            transaccion = modelos.TransaccionInventario(
                medicamento_id=medicamento_fisico.id,
                tipo_transaccion=modelos.TipoTransaccion.dispensacion,
                cantidad=-detalle.cantidad,
                usuario_id=usuario_id,
                motivo=f"Dispensacion Receta #{receta.id}"
            )
            db.add(transaccion)

            # 3. Verificar Alerta Stock Critico
            if medicamento_fisico.stock_actual <= medicamento_fisico.umbral_minimo:
                alertas.append(f"ALERTA: {medicamento_fisico.catalogo.nombre} en {medicamento_fisico.ubicacion} bajo stock minimo ({medicamento_fisico.stock_actual})")

        # Marcar receta completada
        receta.estado = modelos.EstadoReceta.completada
        db.commit()
        
        return {
            "mensaje": "Dispensación exitosa", 
            "alertas": alertas,
            "medicamentos_afectados": medicamentos_afectados
        }

    except Exception as e:
        db.rollback()
        raise e

# --- Inventario ---
def obtener_medicamentos_fisicos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Medicamento).options(joinedload(modelos.Medicamento.catalogo)).offset(skip).limit(limit).all()

def registrar_movimiento_stock(db: Session, medicamento_id: int, cantidad_delta: int, tipo: str, usuario_id: int, motivo: str):
    med = db.query(modelos.Medicamento).filter(modelos.Medicamento.id == medicamento_id).with_for_update().first()
    if not med:
        raise EntidadNoEncontradaError("Medicamento no encontrado")
    
    nuevo_stock = med.stock_actual + cantidad_delta
    if nuevo_stock < 0:
        raise StockInsuficienteError("El stock no puede ser negativo")
    
    med.stock_actual = nuevo_stock
    
    transaccion = modelos.TransaccionInventario(
        medicamento_id=med.id,
        tipo_transaccion=tipo,
        cantidad=cantidad_delta,
        usuario_id=usuario_id,
        motivo=motivo
    )
    db.add(transaccion)
    db.commit()
    return med

# --- Pedidos ---
def crear_pedido(db: Session, pedido: esquemas.PedidoCrear):
    nuevo_pedido = modelos.Pedido(
        descripcion=pedido.descripcion,
        estado="pendiente"
    )
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)
    
    for det in pedido.detalles:
        d = modelos.DetallePedido(
            pedido_id=nuevo_pedido.id,
            catalogo_id=det.catalogo_id,
            cantidad=det.cantidad
        )
        db.add(d)
    
    db.commit()
    db.refresh(nuevo_pedido)
    return nuevo_pedido

def obtener_pedidos(db: Session):
    return db.query(modelos.Pedido).options(joinedload(modelos.Pedido.detalles).joinedload(modelos.DetallePedido.catalogo)).all()

def recepcionar_pedido(db: Session, pedido_id: int, items_recepcion: List[esquemas.ItemRecepcion], usuario_id: int):
    pedido = db.query(modelos.Pedido).filter(modelos.Pedido.id == pedido_id).first()
    if not pedido:
        raise EntidadNoEncontradaError("Pedido no encontrado")
    
    if pedido.estado != "pendiente":
        raise PedidoProcesadoError("El pedido ya no esta pendiente")

    try:
        for item in items_recepcion:
            # Buscar el detalle del pedido para saber cuanto debia llegar (opcional, validacion)
            detalle_pedido = db.query(modelos.DetallePedido).filter(modelos.DetallePedido.id == item.detalle_pedido_id).first()
            if not detalle_pedido:
                continue 

            cantidad = detalle_pedido.cantidad

            if item.accion == 'existing':
                # Sumar a existente
                med = db.query(modelos.Medicamento).filter(modelos.Medicamento.id == item.medicamento_id_ubicacion).with_for_update().first()
                if med:
                    med.stock_actual += cantidad
                    # Registrar transaccion
                    transaccion = modelos.TransaccionInventario(
                        medicamento_id=med.id,
                        tipo_transaccion=modelos.TipoTransaccion.compra,
                        cantidad=cantidad,
                        usuario_id=usuario_id,
                        motivo=f"Recepcion Pedido #{pedido.id}"
                    )
                    db.add(transaccion)
            
            elif item.accion == 'new':
                # Crear nueva ubicacion
                data = item.nueva_ubicacion_data
                
                # Verificar duplicidad
                existe = db.query(modelos.Medicamento).filter(modelos.Medicamento.ubicacion == data.ubicacion).first()
                if existe:
                    raise UbicacionDuplicadaError(f"La ubicacion {data.ubicacion} ya existe")
                
                nuevo_med = modelos.Medicamento(
                    catalogo_id=data.catalogo_id,
                    ubicacion=data.ubicacion,
                    lote=data.lote,
                    fecha_vencimiento=data.fecha_vencimiento,
                    stock_actual=cantidad, # Se inicia con lo que llego
                    umbral_minimo=data.umbral_minimo
                )
                db.add(nuevo_med)
                db.flush() # para obtener ID
                
                transaccion = modelos.TransaccionInventario(
                    medicamento_id=nuevo_med.id,
                    tipo_transaccion=modelos.TipoTransaccion.compra,
                    cantidad=cantidad,
                    usuario_id=usuario_id,
                    motivo=f"Recepcion Pedido #{pedido.id} (Nueva Ubicacion)"
                )
                db.add(transaccion)

        pedido.estado = "recibido"
        db.commit()
    
    except Exception as e:
        db.rollback()
        raise e

# --- Kardex / Incidencias ---
def obtener_kardex_status(db: Session):
    return db.query(modelos.Kardex).all()

def crear_incidencia(db: Session, reporte: esquemas.IncidenciaKardexCrear, usuario_id: int):
    # Obtener Kardex
    kardex = db.query(modelos.Kardex).filter(modelos.Kardex.id == reporte.kardex_id).first()
    if not kardex:
        raise EntidadNoEncontradaError("Kardex no encontrado")
    
    # Cambiar estado del Kardex a Fallo
    kardex.estado = modelos.EstadoKardex.en_falla
    
    nueva_incidencia = modelos.IncidenciaKardex(
        kardex_id=reporte.kardex_id,
        reporte_operario=reporte.reporte_operario,
        usuario_reporta_id=usuario_id,
        estado_incidencia=modelos.EstadoIncidencia.abierta
    )
    db.add(nueva_incidencia)
    db.commit()
    db.refresh(nueva_incidencia)
    return nueva_incidencia

def obtener_incidencias_abiertas(db: Session):
    return db.query(modelos.IncidenciaKardex)\
             .filter(modelos.IncidenciaKardex.estado_incidencia == modelos.EstadoIncidencia.abierta)\
             .options(
                 joinedload(modelos.IncidenciaKardex.kardex),
                 joinedload(modelos.IncidenciaKardex.usuario_reporta)
             ).all()

def resolver_incidencia(db: Session, incidencia_id: int, datos: esquemas.IncidenciaKardexResolver, usuario_id: int):
    incidencia = db.query(modelos.IncidenciaKardex).filter(modelos.IncidenciaKardex.id == incidencia_id).first()
    if not incidencia:
        raise EntidadNoEncontradaError("Incidencia no encontrada")
    
    incidencia.respuesta_admin = datos.respuesta_admin
    incidencia.fecha_resolucion_programada = datos.fecha_resolucion_programada
    incidencia.estado_incidencia = datos.estado_incidencia
    
    # Si se resuelve, volver kardex a operativo
    if datos.estado_incidencia == modelos.EstadoIncidencia.resuelta:
        incidencia.kardex.estado = modelos.EstadoKardex.operativo
    else:
        # Si se pone en proceso/mantencion
        incidencia.kardex.estado = modelos.EstadoKardex.en_mantencion
        
    db.commit()
    db.refresh(incidencia)
    return incidencia

# --- EN CRUD.PY ---

def obtener_transacciones_por_fecha(db: Session, fecha_inicio: date, fecha_fin: date): # type: ignore
    return db.query(modelos.TransaccionInventario)\
             .filter(func.date(modelos.TransaccionInventario.fecha_hora) >= fecha_inicio,
                     func.date(modelos.TransaccionInventario.fecha_hora) <= fecha_fin)\
             .options(joinedload(modelos.TransaccionInventario.medicamento).joinedload(modelos.Medicamento.catalogo),
                      joinedload(modelos.TransaccionInventario.usuario))\
             .order_by(modelos.TransaccionInventario.fecha_hora.desc())\
             .all()