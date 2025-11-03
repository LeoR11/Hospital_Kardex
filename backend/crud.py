from sqlalchemy.orm import Session # type: ignore
import modelos, esquemas, seguridad

# FUNCIONES DEL CRUD PA LOS USUARIOS

def obtener_usuario_por_nombre(db: Session, nombre_usuario: str):
    return db.query(modelos.Usuario).filter(modelos.Usuario.nombre_usuario == nombre_usuario).first()

def crear_usuario(db: Session, usuario: esquemas.UsuarioCrear):
    clave_hasheada = seguridad.obtener_clave_hasheada(usuario.clave)
    db_usuario = modelos.Usuario(
        nombre_usuario=usuario.nombre_usuario,
        clave_hasheada=clave_hasheada,
        rol=usuario.rol.value
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# FUNCIONES DEL CRUD PARA LOS PROFESIONALES (MEDICOS)

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

# FUNCIONES DEL CRUD PARA LOS REMEDIOS

def obtener_medicamento_por_id(db: Session, medicamento_id: int):
    return db.query(modelos.Medicamento).filter(modelos.Medicamento.id == medicamento_id).first()

def crear_medicamento(db: Session, medicamento: esquemas.MedicamentoCrear):
    db_medicamento = modelos.Medicamento(**medicamento.model_dump())
    db.add(db_medicamento)
    db.commit()
    db.refresh(db_medicamento)
    return db_medicamento

def obtener_medicamentos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Medicamento).offset(skip).limit(limit).all()

# FUNCIONES DEL CRUD PARA LS RECETAS

def obtener_recetas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Receta).offset(skip).limit(limit).all()

def crear_receta_completa(db: Session, receta: esquemas.RecetaCrear):
    # CREACION DEL OBJETO BASE DE LA RECETA (EL PRINCIPAL)
    db_receta = modelos.Receta(
        id_paciente=receta.id_paciente,
        fecha_emision=receta.fecha_emision,
        profesional_id=receta.profesional_id
    )
    db.add(db_receta)
    db.commit()
    db.refresh(db_receta)

    # ACA ITERA LOS DETALLES Y LÑA CREA
    for detalle in receta.detalles:
        db_detalle = modelos.DetalleReceta(
            receta_id=db_receta.id,
            medicamento_id=detalle.medicamento_id,
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)
    
    db.commit()
    db.refresh(db_receta)
    return db_receta

def obtener_receta_por_id(db: Session, receta_id: int):
    """Busca una receta especifica por su ID."""
    return db.query(modelos.Receta).filter(modelos.Receta.id == receta_id).first()

# FUNCIONES LOGICAS Y DE LA TRAZABILIDAD DE LOS DASTOS

def crear_transaccion_inventario(db: Session, transaccion: esquemas.TransaccionCrear, usuario_id: int, receta_id: int = None):
    """Funcion central para registrar cualquier movimiento de inventario."""
    db_transaccion = modelos.TransaccionInventario(
        **transaccion.model_dump(),
        usuario_id=usuario_id,
        receta_id=receta_id
    )
    db.add(db_transaccion)
    db.commit()
    db.refresh(db_transaccion)
    return db_transaccion

def dispensar_receta(db: Session, receta_id: int, usuario_id: int):
    """Procesa la dispensacion de una receta ya existente."""
    db_receta = db.query(modelos.Receta).filter(modelos.Receta.id == receta_id).first()
    if not db_receta or db_receta.estado != modelos.EstadoReceta.pendiente:
        return None 

    detalles = db.query(modelos.DetalleReceta).filter(modelos.DetalleReceta.receta_id == receta_id).all()
    alertas = []

    for detalle in detalles:
        db_medicamento = obtener_medicamento_por_id(db, medicamento_id=detalle.medicamento_id)
        if db_medicamento and db_medicamento.stock_actual >= detalle.cantidad:
            # 1. DESCUENTA EL STOCK
            db_medicamento.stock_actual -= detalle.cantidad
            
            # 2. REGISTRA LA SALIDA
            transaccion = esquemas.TransaccionCrear(
                tipo_transaccion=modelos.TipoTransaccion.dispensacion,
                medicamento_id=db_medicamento.id,
                cantidad=-detalle.cantidad, 
            )
            crear_transaccion_inventario(db, transaccion, usuario_id, receta_id)

            # 3. EN CASO DE, NOTIFICA SI ES NECESARIO CREAR UNA ALERTA
            if db_medicamento.stock_actual < db_medicamento.umbral_minimo:
                alertas.append(f"¡Alerta! Stock bajo para {db_medicamento.nombre}. Restante: {db_medicamento.stock_actual}")
        else:
            # MANEJO EN CASO ERROR DE STOCK INSUFICIENTE
            raise Exception(f"Stock insuficiente para el medicamento ID {detalle.medicamento_id}")

    # 4. ACTUALIZA EL ESTADO DE LA RECETA
    db_receta.estado = modelos.EstadoReceta.completada
    db.commit()
    db.refresh(db_receta)
    
    return {"receta": db_receta, "alertas": alertas}

def registrar_transaccion_stock(db: Session, transaccion: esquemas.TransaccionCrear, usuario_id: int):
    """Registra una devolucion o reposicion y actualiza el stock."""
    db_medicamento = obtener_medicamento_por_id(db, medicamento_id=transaccion.medicamento_id)
    if not db_medicamento:
        return None # SI EL MEDICAMENTO NO EXISTE

    db_medicamento.stock_actual += transaccion.cantidad
    
    crear_transaccion_inventario(db, transaccion, usuario_id)
    
    db.commit()
    db.refresh(db_medicamento)
    return db_medicamento

# FUNCIONES CRUD DE LOS PEDIDOS

def crear_pedido(db: Session, pedido: esquemas.PedidoCrear):
    """Crea un nuevo pedido de abastecimiento."""
    db_pedido = modelos.Pedido(descripcion=pedido.descripcion)
    db.add(db_pedido)
    db.commit()
    db.refresh(db_pedido)

    for detalle in pedido.detalles:
        db_detalle = modelos.DetallePedido(
            pedido_id=db_pedido.id,
            medicamento_id=detalle.medicamento_id,
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)
    
    db.commit()
    db.refresh(db_pedido)
    return db_pedido

def obtener_pedidos(db: Session, estado: str = None):
    """Obtiene una lista de pedidos, opcionalmente filtrados por estado."""
    consulta = db.query(modelos.Pedido)
    if estado:
        consulta = consulta.filter(modelos.Pedido.estado == estado)
    return consulta.all()

def recepcionar_pedido(db: Session, pedido_id: int, usuario_id: int):
    """Procesa la recepcion de un pedido y actualiza el stock."""
    db_pedido = db.query(modelos.Pedido).filter(modelos.Pedido.id == pedido_id).first()
    if not db_pedido or db_pedido.estado != "pendiente":
        return None 

    detalles = db_pedido.detalles
    
    for detalle in detalles:
        db_medicamento = obtener_medicamento_por_id(db, medicamento_id=detalle.medicamento_id)
        if db_medicamento:

            db_medicamento.stock_actual += detalle.cantidad

            transaccion = esquemas.TransaccionCrear(
                tipo_transaccion=modelos.TipoTransaccion.compra,
                medicamento_id=db_medicamento.id,
                cantidad=detalle.cantidad, 
                motivo=f"Recepción Pedido #{pedido_id}"
            )
            crear_transaccion_inventario(db, transaccion, usuario_id)
        
   
    db_pedido.estado = "recibido"
    db.commit()
    db.refresh(db_pedido)
    return db_pedido