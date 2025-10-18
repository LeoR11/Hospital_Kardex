from sqlalchemy.orm import Session # type: ignore
import modelos, esquemas, seguridad

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

def crear_receta(db: Session, receta: esquemas.RecetaCrear):
    db_receta = modelos.Receta(id_paciente=receta.id_paciente)
    db.add(db_receta)
    db.commit()
    db.refresh(db_receta)
    return db_receta

def obtener_recetas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Receta).offset(skip).limit(limit).all()

def crear_medicamento(db: Session, medicamento: esquemas.MedicamentoCrear):
    db_medicamento = modelos.Medicamento(**medicamento.model_dump())
    db.add(db_medicamento)
    db.commit()
    db.refresh(db_medicamento)
    return db_medicamento

def obtener_medicamentos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(modelos.Medicamento).offset(skip).limit(limit).all()

def obtener_medicamento_por_id(db: Session, medicamento_id: int):
    return db.query(modelos.Medicamento).filter(modelos.Medicamento.id == medicamento_id).first()

def dispensar_receta(db: Session, receta_id: int, detalles: list[esquemas.DetalleReceta]):
    db_receta = db.query(modelos.Receta).filter(modelos.Receta.id == receta_id).first()
    if not db_receta:
        return None

    alertas = []

    for detalle in detalles:
        db_detalle = modelos.DetalleReceta(
            receta_id=receta_id,
            medicamento_id=detalle.medicamento_id,
            cantidad=detalle.cantidad
        )
        db.add(db_detalle)

        db_medicamento = obtener_medicamento_por_id(db, medicamento_id=detalle.medicamento_id)
        if db_medicamento and db_medicamento.stock_actual >= detalle.cantidad:
            db_medicamento.stock_actual -= detalle.cantidad
            if db_medicamento.stock_actual < db_medicamento.umbral_minimo:
                alertas.append(f"¡Alerta! Stock bajo para {db_medicamento.nombre}. Restante: {db_medicamento.stock_actual}")
    
    db_receta.estado = modelos.EstadoReceta.completada
    
    db.commit()
    db.refresh(db_receta)
    
    return {"receta": db_receta, "alertas": alertas}