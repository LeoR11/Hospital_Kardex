#Definiciones de errores para etidad,stock,receta,pedido y ubicacion
class EntidadNoEncontradaError(Exception):
    """Error lanzado cuando no se encuentra un ID"""
    pass

class StockInsuficienteError(Exception):
    """Error lanzado cuando el stock no es suficiente para la operacion"""
    pass

class RecetaProcesadaError(Exception):
    """Error lanzado al intentar dispensar una receta que ya esta completada/cancelada"""
    pass

class PedidoProcesadoError(Exception):
    """Error lanzado al intentar recepcionar un pedido que ya esta recibido"""
    pass
    
class UbicacionDuplicadaError(Exception):
    """Error lanzado al crear una ubicacion que ya existe"""
    pass
# -----------------------------------------------------------------------------------------

from sqlalchemy.orm import Session, joinedload # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore
from sqlalchemy import func # type: ignore
import modelos, esquemas, seguridad
import nosql_manager
from typing import List, Dict, Any

# --- CRUD de Usuario ---

def obtener_usuario_por_nombre(db: Session, nombre_usuario: str):
    return db.query(modelos.Usuario).filter(modelos.Usuario.nombre_usuario == nombre_usuario).first()

def obtener_usuario_por_id(db: Session, usuario_id: int):
    return db.query(modelos.Usuario).filter(modelos.Usuario.id == usuario_id).first()

def obtener_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Usuario).offset(skip).limit(limit).all()

def buscar_usuarios_por_nombre(db: Session, nombre_busqueda: str):
    filtro = f"%{nombre_busqueda.lower()}%"
    return db.query(modelos.Usuario).filter(
        (modelos.Usuario.nombre_usuario.ilike(filtro)) |
        (modelos.Usuario.nombre.ilike(filtro)) |
        (modelos.Usuario.apellido.ilike(filtro))
    ).all()

def crear_usuario(db: Session, usuario: esquemas.UsuarioCrear):
    clave_hasheada = seguridad.obtener_clave_hasheada(usuario.clave)
    db_usuario = modelos.Usuario(
        nombre_usuario=usuario.nombre_usuario,
        clave_hasheada=clave_hasheada,
        rol=usuario.rol.value,
        nombre=usuario.nombre,
        apellido=usuario.apellido
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def eliminar_usuario(db: Session, usuario_id: int):
    db_usuario = db.query(modelos.Usuario).filter(modelos.Usuario.id == usuario_id).first()
    if db_usuario:
        db.delete(db_usuario)
        db.commit()
        return True
    return False

# --- CRUD de Profesional ---

def obtener_profesional_por_run(db: Session, run: str):
    return db.query(modelos.Profesional).filter(modelos.Profesional.run == run).first()

def crear_profesional(db: Session, profesional: esquemas.ProfesionalCrear):
    db_profesional = modelos.Profesional(**profesional.model_dump())
    db.add(db_profesional)
    db.commit()
    db.refresh(db_profesional)
    return db_profesional

def obtener_profesionales(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Profesional).offset(skip).limit(limit).all()

def buscar_profesionales(db: Session, busqueda: str):
    filtro = f"%{busqueda.lower()}%"
    return db.query(modelos.Profesional).filter(
        (modelos.Profesional.nombre.ilike(filtro)) |
        (modelos.Profesional.run.ilike(filtro))
    ).all()

def eliminar_profesional(db: Session, profesional_id: int):
    db_profesional = db.query(modelos.Profesional).filter(modelos.Profesional.id == profesional_id).first()
    if db_profesional:
        db.delete(db_profesional)
        db.commit()
        return True
    return False

# --- CRUD MedicamentoCatalogo ---

def obtener_catalogo_por_id(db: Session, catalogo_id: int):
    return db.query(modelos.MedicamentoCatalogo).filter(modelos.MedicamentoCatalogo.id == catalogo_id).first()

def crear_item_catalogo(db: Session, item: esquemas.MedicamentoCatalogoCrear):
    db_item_existente = db.query(modelos.MedicamentoCatalogo).filter(modelos.MedicamentoCatalogo.nombre == item.nombre).first()
    if db_item_existente:
        raise IntegrityError(f"El nombre '{item.nombre}' ya existe en el catalogo.", params=None, orig=None)
        
    db_item = modelos.MedicamentoCatalogo(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def obtener_catalogo(db: Session):
    return db.query(modelos.MedicamentoCatalogo).all()

def eliminar_item_catalogo(db: Session, catalogo_id: int):
    db_catalogo = obtener_catalogo_por_id(db, catalogo_id)
    if not db_catalogo:
        raise EntidadNoEncontradaError("Item de catalogo no encontrado.")
    
    if db_catalogo.ubicaciones:
        raise ValueError("No se puede eliminar: Este catalogo tiene ubicaciones fisicas en el Kardex que ya estan asociadas.")
        
    db.delete(db_catalogo)
    db.commit()
    return True


# --- CRUD Medicamento (Ubicaciones) ---

def obtener_medicamento_por_id(db: Session, medicamento_id: int):
    """Obtiene una UBICACION especifica por su ID"""
    return db.query(modelos.Medicamento).filter(modelos.Medicamento.id == medicamento_id).first()

def crear_medicamento(db: Session, medicamento: esquemas.MedicamentoCrear):
    """Crea una nueva UBICACION de medicamento"""
    db_ubicacion_existente = db.query(modelos.Medicamento).filter(modelos.Medicamento.ubicacion == medicamento.ubicacion).first()
    if db_ubicacion_existente:
        raise UbicacionDuplicadaError(f"La ubicacion '{medicamento.ubicacion}' ya esta en uso.")

    db_medicamento = modelos.Medicamento(**medicamento.model_dump())
    db.add(db_medicamento)
    db.commit()
    db.refresh(db_medicamento)
    return db_medicamento

def obtener_medicamentos(db: Session):
    """Obtiene TODAS las UBICACIONES de medicamentos"""
    return db.query(modelos.Medicamento).all()

def eliminar_medicamento(db: Session, medicamento_id: int):
    """Elimina una UBICACION de medicamento"""
    db_medicamento = obtener_medicamento_por_id(db, medicamento_id)
    if not db_medicamento:
        raise EntidadNoEncontradaError("Ubicacion no encontrada.")
        
    if db_medicamento.stock_actual > 0:
        raise ValueError("No se puede eliminar: La ubicacion aun tiene stock.")
    
    db.delete(db_medicamento)
    db.commit()
    return True

def obtener_stock_total_por_catalogo(db: Session, catalogo_id: int) -> int:
    """
    Suma el stock_actual de TODAS las ubicaciones que pertenecen
    a un mismo item de catalogo.
    """
    stock_total = (
        db.query(func.sum(modelos.Medicamento.stock_actual))
        .filter(modelos.Medicamento.catalogo_id == catalogo_id)
        .scalar()
    )
    return stock_total or 0

# --- CRUD Recetas ---

def obtener_recetas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Receta).order_by(modelos.Receta.estado, modelos.Receta.id.desc()).offset(skip).limit(limit).all()

def crear_receta_completa(db: Session, receta: esquemas.RecetaCrear):
    """Crea una receta apuntando a IDs del Catalogo"""
    db_receta = modelos.Receta(
        id_paciente=receta.id_paciente,
        fecha_emision=receta.fecha_emision,
        profesional_id=receta.profesional_id,
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

def obtener_receta_por_id(db: Session, receta_id: int):
    return db.query(modelos.Receta).filter(modelos.Receta.id == receta_id).first()

# registra los datos necesario para el informe de auditoria
def crear_transaccion_inventario(db: Session, transaccion: esquemas.TransaccionCrear, usuario_id: int, receta_id: int = None):
    try:
        usuario_nombre = obtener_usuario_por_id(db, usuario_id).nombre_usuario
        db_medicamento = obtener_medicamento_por_id(db, transaccion.medicamento_id)
        if not db_medicamento:
             raise Exception("Medicamento (ubicacion) no encontrado para la transaccion.")
    except Exception as e:
        print(f"Error al obtener datos para el log: {e}")
        usuario_nombre = "Sistema"
        db_medicamento = None

    db_transaccion = modelos.TransaccionInventario(
        **transaccion.model_dump(),
        usuario_id=usuario_id,
        receta_id=receta_id
    )
    db.add(db_transaccion)
    db.commit()
    db.refresh(db_transaccion)

    try:
        if db_medicamento:
            paciente_id = None
            
            if receta_id:
                db_receta = db.get(modelos.Receta, receta_id) 
                if db_receta:
                    paciente_id = db_receta.id_paciente
            
            vencimiento_str = db_medicamento.fecha_vencimiento.isoformat() if db_medicamento.fecha_vencimiento else None

            log_detalles = {
                "tipo_transaccion": db_transaccion.tipo_transaccion.value,
                "medicamento_id": db_transaccion.medicamento_id,
                "nombre_catalogo": db_medicamento.catalogo.nombre,
                "cantidad": db_transaccion.cantidad,
                "lote": db_medicamento.lote,
                "fecha_vencimiento": vencimiento_str,
                "ubicacion": db_medicamento.ubicacion,
                "stock_resultante": db_medicamento.stock_actual,
                "motivo": db_transaccion.motivo,
                "receta_id": db_transaccion.receta_id,
                "paciente_id": paciente_id
            }

            nosql_manager.registrar_log_auditoria(
                usuario_nombre=usuario_nombre,
                accion="TRANSACCION_STOCK", 
                detalles=log_detalles
            )
    except Exception as e:
        print(f"ERROR: Fallo al guardar el log para transaccion: {e}")

    return db_transaccion


def dispensar_receta(db: Session, receta_id: int, usuario_id: int, mapeo_dispensacion: Dict[str, int]):
    db_receta = obtener_receta_por_id(db, receta_id=receta_id)
    if not db_receta:
        raise EntidadNoEncontradaError(f"Receta ID {receta_id} no encontrada.")
    if db_receta.estado != modelos.EstadoReceta.pendiente:
        raise RecetaProcesadaError(f"Receta ID {receta_id} ya fue procesada (Estado: {db_receta.estado.value}).")

    detalles_receta = db_receta.detalles
    alertas = []
    
    usuario_nombre = obtener_usuario_por_id(db, usuario_id).nombre_usuario
    log_detalles_items = [] 

    for detalle in detalles_receta:
        medicamento_id_elegido = mapeo_dispensacion.get(str(detalle.id))
        
        if not medicamento_id_elegido:
            raise Exception(f"No se especifico una ubicacion para el item {detalle.catalogo.nombre} (Detalle ID: {detalle.id})")

        db_medicamento = obtener_medicamento_por_id(db, medicamento_id=medicamento_id_elegido)
        
        if not db_medicamento:
            raise EntidadNoEncontradaError(f"La ubicacion ID {medicamento_id_elegido} no existe.")
            
        if db_medicamento.catalogo_id != detalle.catalogo_id:
            raise Exception(f"La ubicacion {db_medicamento.ubicacion} no corresponde al medicamento {detalle.catalogo.nombre}")

        if db_medicamento.stock_actual >= detalle.cantidad:
            db_medicamento.stock_actual -= detalle.cantidad
            
            transaccion = esquemas.TransaccionCrear(
                tipo_transaccion=modelos.TipoTransaccion.dispensacion,
                medicamento_id=db_medicamento.id, 
                cantidad=-detalle.cantidad, 
                motivo=f"Dispensacion Receta #{receta_id}" 
            )
            crear_transaccion_inventario(db, transaccion, usuario_id, receta_id)
            
            log_detalles_items.append({
                "catalogo_id": detalle.catalogo_id,
                "nombre": detalle.catalogo.nombre,
                "cantidad_dispensada": detalle.cantidad,
                "ubicacion_usada": db_medicamento.ubicacion,
                "stock_resultante": db_medicamento.stock_actual
            })
            
            if db_medicamento.stock_actual < db_medicamento.umbral_minimo:
                alertas.append(f"Alerta de Stock bajo para {detalle.catalogo.nombre} en {db_medicamento.ubicacion}. Restante: {db_medicamento.stock_actual}")
        else:
            raise StockInsuficienteError(f"Stock insuficiente para {detalle.catalogo.nombre} en la ubicacion {db_medicamento.ubicacion} (Necesita: {detalle.cantidad}, Hay: {db_medicamento.stock_actual})")

    db_receta.estado = modelos.EstadoReceta.completada
    db.commit()
# datos para los informes
    try:
        log_detalles_dispensacion = {
            "receta_id": db_receta.id,
            "paciente_id": db_receta.id_paciente,
            "profesional_id": db_receta.profesional_id,
            "items_dispensados": log_detalles_items
        }
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_nombre,
            accion="DISPENSAR_RECETA_COMPLETA",
            detalles=log_detalles_dispensacion
        )
    except Exception as e:
        print(f"ERROR: Fallo al guardar el log  para dispensacion: {e}")
    
    db.refresh(db_receta)
    return {"receta": db_receta, "alertas": alertas}


def registrar_transaccion_stock(db: Session, transaccion: esquemas.TransaccionCrear, usuario_id: int):
    db_medicamento = obtener_medicamento_por_id(db, medicamento_id=transaccion.medicamento_id)
    if not db_medicamento:
        raise EntidadNoEncontradaError("Ubicacion de medicamento no encontrada.")

    if transaccion.cantidad < 0:
        if db_medicamento.stock_actual < abs(transaccion.cantidad):
            raise StockInsuficienteError(
                f"Stock insuficiente para {db_medicamento.catalogo.nombre} en {db_medicamento.ubicacion}.\n"
                f"Solicitado: {abs(transaccion.cantidad)}, Disponible: {db_medicamento.stock_actual}")

    db_medicamento.stock_actual += transaccion.cantidad
    
    crear_transaccion_inventario(db, transaccion, usuario_id)

    db.commit()
    db.refresh(db_medicamento)
    return db_medicamento

# --- CRUD Pedidos ---

def obtener_detalle_pedido_por_id(db: Session, detalle_id: int):
    return db.query(modelos.DetallePedido).filter(modelos.DetallePedido.id == detalle_id).first()

def crear_pedido(db: Session, pedido: esquemas.PedidoCrear):
    db_pedido = modelos.Pedido(descripcion=pedido.descripcion, estado="pendiente")
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)

    for detalle in pedido.detalles:
        db_detalle = modelos.DetallePedido(
            pedido_id=db_pedido.id,
            catalogo_id=detalle.catalogo_id, 
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)
    
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def obtener_pedidos(db: Session, estado: str = None):
    consulta = db.query(modelos.Pedido)
    if estado:
        consulta = consulta.filter(modelos.Pedido.estado == estado)
    return consulta.all()

def recepcionar_pedido(
    db: Session, 
    pedido_id: int, 
    usuario_id: int, 
    payload: esquemas.RecepcionPedidoPayload
):
    db_pedido = db.query(modelos.Pedido).filter(modelos.Pedido.id == pedido_id).first()
    if not db_pedido:
        raise EntidadNoEncontradaError(f"Pedido ID {pedido_id} no encontrado.")
    if db_pedido.estado != "pendiente":
        raise PedidoProcesadaError(f"Pedido ID {pedido_id} ya fue procesado.") # type: ignore

    for item in payload.items:
        detalle_pedido = obtener_detalle_pedido_por_id(db, item.detalle_pedido_id)
        if not detalle_pedido or detalle_pedido.pedido_id != pedido_id:
            raise Exception(f"Detalle de pedido ID {item.detalle_pedido_id} no pertenece al pedido {pedido_id}.")
        
        cantidad_a_sumar = detalle_pedido.cantidad
        medicamento_id_destino = None 

        if item.accion == "existing":
            if not item.medicamento_id_ubicacion:
                raise Exception("Accion 'existing' requiere 'medicamento_id_ubicacion'.")
            
            db_medicamento = obtener_medicamento_por_id(db, item.medicamento_id_ubicacion)
            if not db_medicamento:
                raise EntidadNoEncontradaError(f"Ubicación ID {item.medicamento_id_ubicacion} no encontrada.")
            
            if db_medicamento.catalogo_id != detalle_pedido.catalogo_id:
                raise Exception(f"La ubicacioyy n {db_medicamento.ubicacion} no corresponde al medicamento {detalle_pedido.catalogo.nombre}.")
            
            db_medicamento.stock_actual += cantidad_a_sumar
            medicamento_id_destino = db_medicamento.id

        elif item.accion == "new":
            if not item.nueva_ubicacion_data:
                raise Exception("Accion 'new' requiere 'nueva_ubicacion_data'.")
            
            item.nueva_ubicacion_data.catalogo_id = detalle_pedido.catalogo_id
            item.nueva_ubicacion_data.stock_actual = cantidad_a_sumar
            
            try:
                db_medicamento_nuevo = crear_medicamento(db, item.nueva_ubicacion_data)
                medicamento_id_destino = db_medicamento_nuevo.id
            except UbicacionDuplicadaError as e:
                raise UbicacionDuplicadaError(f"La ubicacion '{item.nueva_ubicacion_data.ubicacion}' esta ocupada.")

        else:
            raise Exception(f"Accion de recepcion desconocida: {item.accion}")

        if medicamento_id_destino:
            transaccion = esquemas.TransaccionCrear(
                tipo_transaccion=modelos.TipoTransaccion.compra,
                medicamento_id=medicamento_id_destino,
                cantidad=cantidad_a_sumar, 
                motivo=f"Recepcion Pedido #{pedido_id}"
            )
            crear_transaccion_inventario(db, transaccion, usuario_id)

    db_pedido.estado = "recibido"
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

# --- CRUD DEE KARDEX E INCIDENCIAS ---
def obtener_kardex_todos(db: Session):
    """Obtiene todos los Kardex (K1, K2) y su estado actual."""
    return db.query(modelos.Kardex).options(
        joinedload(modelos.Kardex.incidencias)
    ).all()

def obtener_incidencias(db: Session, estado: modelos.EstadoIncidencia = None):
    """
    Obtiene incidencias, filtradas por estado (abierta/resuelta).
    Ordena por las mas nuevas primero.
    """
    consulta = db.query(modelos.IncidenciaKardex)
    if estado:
        consulta = consulta.filter(
            modelos.IncidenciaKardex.estado_incidencia == estado
        )
    return consulta.order_by(modelos.IncidenciaKardex.fecha_reporte.desc()).all()


def obtener_incidencia_por_id(db: Session, incidencia_id: int):
    """Obtiene una incidencia especifica por su ID"""
    return db.query(modelos.IncidenciaKardex).filter(modelos.IncidenciaKardex.id == incidencia_id).first()

def crear_incidencia_kardex(db: Session, incidencia: esquemas.IncidenciaKardexCrear, usuario_id: int):
    """
    Reporta una nueva incidencia y pone el Kardex 'en_falla'.
    """
    # 1. Encontrar el Kardex (K1 o K2)
    db_kardex = db.get(modelos.Kardex, incidencia.kardex_id)
    if not db_kardex:
        raise EntidadNoEncontradaError("Kardex no encontrado.") #si pasa revisar que se creo el kardex (en el.bat y crear_base_de_datos.py)

    # 2. Crea la incidencia
    db_incidencia = modelos.IncidenciaKardex(
        kardex_id=incidencia.kardex_id,
        reporte_operario=incidencia.reporte_operario,
        usuario_reporta_id=usuario_id,
        estado_incidencia=modelos.EstadoIncidencia.abierta
    )
    db.add(db_incidencia)
    
    # 3. Pone el Kardex en estado "en_falla"
    db_kardex.estado = modelos.EstadoKardex.en_falla
    
    db.commit()
    db.refresh(db_incidencia)
    
    # 4. Registra en Log de audiotia para reportes
    try:
        usuario_nombre = db_incidencia.usuario_reporta.nombre_usuario
    except Exception:
        usuario_nombre = "UsuarioDesconocido"
        
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=usuario_nombre,
        accion="INCIDENCIA_REPORTADA",
        detalles={
            "incidencia_id": db_incidencia.id,
            "kardex_afectado": db_kardex.identificador,
            "reporte": db_incidencia.reporte_operario
        }
    )
    
    return db_incidencia

def resolver_incidencia_kardex(
    db: Session, 
    incidencia_id: int, 
    datos_resolucion: esquemas.IncidenciaKardexResolver, 
    usuario_id: int
):
    """
    Resuelve o actualiza una incidencia y, si se resuelve,
    pone el Kardex de nuevo en 'operativo'.
    """
    # 1. Encontrar la incidencia
    db_incidencia = obtener_incidencia_por_id(db, incidencia_id)
    if not db_incidencia:
        raise EntidadNoEncontradaError("Incidencia no encontrada.")
        
    # 2. Actualiza datos de la incidencia
    db_incidencia.respuesta_admin = datos_resolucion.respuesta_admin
    db_incidencia.fecha_resolucion_programada = datos_resolucion.fecha_resolucion_programada
    db_incidencia.estado_incidencia = datos_resolucion.estado_incidencia
    db_incidencia.usuario_resuelve_id = usuario_id
    
    #3. en caso de resolver o no
    if datos_resolucion.estado_incidencia == modelos.EstadoIncidencia.resuelta:
        db_incidencia.kardex.estado = modelos.EstadoKardex.operativo
        accion_log = "INCIDENCIA_RESUELTA"
    else:
        db_incidencia.kardex.estado = modelos.EstadoKardex.en_mantencion
        accion_log = "INCIDENCIA_ACTUALIZADA"

    db.commit()
    db.refresh(db_incidencia)
    
    # 4. Registrar en Log  parfa la auditoria
    try:
        usuario_nombre = db_incidencia.usuario_resuelve.nombre_usuario
    except Exception:
         usuario_nombre = "UsuarioDesconocido"
         
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=usuario_nombre,
        accion=accion_log,
        detalles={
            "incidencia_id": db_incidencia.id,
            "kardex_afectado": db_incidencia.kardex.identificador,
            "respuesta": db_incidencia.respuesta_admin,
            "nuevo_estado_kardex": db_incidencia.kardex.estado.value
        }
    )
    
    return db_incidencia