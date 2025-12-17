from fastapi import FastAPI, Depends, HTTPException, status # type: ignore
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer # type: ignore
from sqlalchemy.orm import Session # type: ignore
from jose import JWTError, jwt # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from typing import List, Optional, Dict
from fastapi.responses import StreamingResponse  # type: ignore
from datetime import date, timedelta 
import io 
import csv 
import json 
import modelos, esquemas, crud, seguridad
from modelos import EstadoIncidencia
import ia
import nosql_manager 
from base_de_datos import motor, SesionLocal
from crud import StockInsuficienteError, RecetaProcesadaError, UbicacionDuplicadaError, PedidoProcesadoError, EntidadNoEncontradaError

modelos.Base.metadata.create_all(bind=motor)

aplicacion = FastAPI(
    title="API del Sistema de Gestion para la Farmacia Unidosis",
    version="4.0.0", 
    description="Una API modular para gestionar el sistema de farmacia hospitalaria."
)

origenes = ["*"]
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def obtener_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(obtener_db)):
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, seguridad.CLAVE_SECRETA, algorithms=[seguridad.ALGORITMO])
        username: str = payload.get("sub")
        if username is None:
            raise credenciales_exception
    except JWTError:
        raise credenciales_exception
    
    usuario = crud.obtener_usuario_por_nombre(db, username)
    if usuario is None:
        raise credenciales_exception
    return usuario

def obtener_usuario_admin(usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    if usuario_actual.rol != modelos.RolUsuario.administrador:
        raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador")
    return usuario_actual

@aplicacion.post("/token", response_model=esquemas.Token)
def login_para_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(obtener_db)):
    usuario = crud.obtener_usuario_por_nombre(db, form_data.username)
    if not usuario or not seguridad.verificar_clave(form_data.password, usuario.clave_hasheada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tiempo_expiracion = timedelta(minutes=seguridad.TIEMPO_EXPIRACION_TOKEN_MINUTOS)
    
    token_acceso = seguridad.crear_token_acceso(
        datos={"sub": usuario.nombre_usuario, "rol": usuario.rol},
        expires_delta=tiempo_expiracion
    )
    return {"access_token": token_acceso, "token_type": "bearer", "rol": usuario.rol}

@aplicacion.post("/usuarios/", response_model=esquemas.Usuario, tags=["Usuarios"])
def crear_usuario(usuario: esquemas.UsuarioCrear, db: Session = Depends(obtener_db), admin: esquemas.Usuario = Depends(obtener_usuario_admin)):
    db_usuario = crud.obtener_usuario_por_nombre(db, usuario.nombre_usuario)
    if db_usuario:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    return crud.crear_usuario(db, usuario)

@aplicacion.get("/usuarios/", response_model=List[esquemas.Usuario], tags=["Usuarios"])
def leer_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(obtener_db), admin: esquemas.Usuario = Depends(obtener_usuario_admin)):
    return crud.obtener_usuarios(db, skip=skip, limit=limit)

@aplicacion.post("/profesionales/", response_model=esquemas.Profesional, tags=["Profesionales"])
def crear_profesional(profesional: esquemas.ProfesionalCrear, db: Session = Depends(obtener_db), admin: esquemas.Usuario = Depends(obtener_usuario_admin)):
    return crud.crear_profesional(db, profesional)

@aplicacion.get("/profesionales/", response_model=List[esquemas.Profesional], tags=["Profesionales"])
def leer_profesionales(skip: int = 0, limit: int = 100, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_profesionales(db, skip=skip, limit=limit)

@aplicacion.post("/catalogo/", response_model=esquemas.MedicamentoCatalogo, tags=["Catalogo"])
def crear_item_catalogo(item: esquemas.MedicamentoCatalogoCrear, db: Session = Depends(obtener_db), admin: esquemas.Usuario = Depends(obtener_usuario_admin)):
    return crud.crear_medicamento_catalogo(db, item)

@aplicacion.get("/catalogo/", response_model=List[esquemas.MedicamentoCatalogo], tags=["Catalogo"])
def leer_catalogo(skip: int = 0, limit: int = 100, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    catalogo = crud.obtener_catalogo(db, skip=skip, limit=limit)
    
    resultado = []
    for item in catalogo:
        item_dict = esquemas.MedicamentoCatalogo.model_validate(item)
        
        stock_total = 0
        try:
            if item.medicamentos_fisicos:
                stock_total = sum(m.stock_actual for m in item.medicamentos_fisicos)
        except Exception:
            pass
        item_dict.stock_total = stock_total
        
        try:
            prediccion = ia.predecir_demanda_medicamento(item.id, dias_a_predecir=7)
            if prediccion is not None:
                 demanda_proyectada = prediccion['demanda_predicha'].sum()
                 item_dict.demanda_estimada_30_dias = round(demanda_proyectada, 2)
                 
                 if stock_total < demanda_proyectada:
                     item_dict.estado_ia = "STOCK_CRITICO_PROYECTADO"
                 elif stock_total < (demanda_proyectada * 1.2):
                     item_dict.estado_ia = "STOCK_BAJO"
                 else:
                     item_dict.estado_ia = "OPTIMO"
            else:
                item_dict.estado_ia = "SIN_DATOS_SUFICIENTES"
        except Exception as e:
            print(f"Error IA en catalogo: {e}")
            item_dict.estado_ia = "ERROR_IA"
            
        resultado.append(item_dict)
        
    return resultado

@aplicacion.post("/recetas/", response_model=esquemas.Receta, tags=["Recetas"])
def registrar_receta(
    receta: esquemas.RecetaCrear, 
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        nueva_receta = crud.crear_receta(db, receta)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_actual.nombre_usuario,
            accion="RECETA_CREADA",
            detalles={
                "receta_id": nueva_receta.id,
                "paciente_id": nueva_receta.paciente_id,
                "items": len(receta.detalles)
            }
        )
        
        return nueva_receta
    except Exception as e:
        print(f"Error al crear receta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion.get("/recetas/", response_model=List[esquemas.Receta], tags=["Recetas"])
def leer_recetas(skip: int = 0, limit: int = 100, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_recetas(db, skip=skip, limit=limit)

@aplicacion.post("/recetas/{receta_id}/dispensar/", response_model=esquemas.RespuestaDispensacion, tags=["Recetas"])
def dispensar_receta_endpoint(
    receta_id: int, 
    mapeo: Dict[str, int], 
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        resultado = crud.dispensar_receta(db, receta_id, mapeo, usuario_actual.id)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_actual.nombre_usuario,
            accion="RECETA_DISPENSADA",
            detalles={"receta_id": receta_id, "alertas": resultado["alertas"]}
        )
        
        # INTENTO DE ENTRENAMIENTO IA (Protegido)
        # Si la IA falla, NO debe detener la dispensación
        try:
            for med_id in resultado["medicamentos_afectados"]:
                 ia.entrenar_modelo_medicamento(db, med_id)
        except Exception as e_ia:
            print(f"Advertencia: Fallo el re-entrenamiento IA: {e_ia}")
            # No lanzamos error, dejamos que continue
             
        return resultado
        
    except StockInsuficienteError:
        raise HTTPException(status_code=409, detail="Stock insuficiente en una o más ubicaciones seleccionadas.")
    except RecetaProcesadaError:
        raise HTTPException(status_code=400, detail="La receta ya fue procesada o cancelada.")
    except EntidadNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@aplicacion.get("/medicamentos/", response_model=List[esquemas.Medicamento], tags=["Inventario"])
def leer_medicamentos_fisicos(skip: int = 0, limit: int = 100, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_medicamentos_fisicos(db, skip=skip, limit=limit)

@aplicacion.post("/inventario/transaccion/", tags=["Inventario"])
def registrar_transaccion_manual(
    transaccion: esquemas.TransaccionManual,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        crud.registrar_movimiento_stock(
            db=db,
            medicamento_id=transaccion.medicamento_id,
            cantidad_delta=transaccion.cantidad,
            tipo=transaccion.tipo_transaccion,
            usuario_id=usuario_actual.id,
            motivo=transaccion.motivo
        )
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_actual.nombre_usuario,
            accion=f"TRANSACCION_{transaccion.tipo_transaccion.upper()}",
            detalles={"medicamento_id": transaccion.medicamento_id, "cantidad": transaccion.cantidad}
        )
        
        return {"mensaje": "Transacción registrada exitosamente"}
    except StockInsuficienteError:
         raise HTTPException(status_code=409, detail="No hay stock suficiente para realizar esta operación.")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@aplicacion.post("/pedidos/", response_model=esquemas.Pedido, tags=["Pedidos"])
def crear_pedido_bodega(
    pedido: esquemas.PedidoCrear,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_admin)
):
    nuevo_pedido = crud.crear_pedido(db, pedido)
    return nuevo_pedido

@aplicacion.get("/pedidos/", response_model=List[esquemas.Pedido], tags=["Pedidos"])
def leer_pedidos(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_pedidos(db)

@aplicacion.post("/pedidos/{pedido_id}/recepcionar/", tags=["Pedidos"])
def recepcionar_pedido_endpoint(
    pedido_id: int,
    datos: esquemas.RecepcionPedido,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        crud.recepcionar_pedido(db, pedido_id, datos.items, usuario_actual.id)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_actual.nombre_usuario,
            accion="PEDIDO_RECEPCIONADO",
            detalles={"pedido_id": pedido_id}
        )
        return {"mensaje": "Pedido recepcionado correctamente"}
        
    except PedidoProcesadoError:
        raise HTTPException(status_code=400, detail="El pedido ya fue recepcionado.")
    except UbicacionDuplicadaError:
        raise HTTPException(status_code=409, detail="Intenta crear una ubicación que ya existe.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion.get("/kardex/status/", response_model=List[esquemas.Kardex], tags=["Kardex"])
def obtener_estado_kardex(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_kardex_status(db)

@aplicacion.post("/kardex/reportar-falla/", tags=["Kardex"])
def reportar_falla_kardex(
    reporte: esquemas.IncidenciaKardexCrear,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        incidencia = crud.crear_incidencia(db, reporte, usuario_actual.id)
        return {"mensaje": "Falla reportada", "incidencia_id": incidencia.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion.get("/kardex/incidencias/", response_model=List[esquemas.IncidenciaKardex], tags=["Kardex"])
def leer_incidencias(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_admin)):
    return crud.obtener_incidencias_abiertas(db)

@aplicacion.post("/kardex/incidencias/{incidencia_id}/resolver/", tags=["Kardex"])
def resolver_incidencia(
    incidencia_id: int,
    resolucion: esquemas.IncidenciaKardexResolver,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_admin)
):
    try:
        crud.resolver_incidencia(db, incidencia_id, resolucion, usuario_actual.id)
        return {"mensaje": "Incidencia actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@aplicacion.get("/reportes/auditoria-sistema/", tags=["Reportes"])
def descargar_reporte_auditoria(
    fecha_inicio: date, 
    fecha_fin: date, 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_admin)
):
    logs = nosql_manager.obtener_logs_por_fecha(fecha_inicio, fecha_fin)
    
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Fecha/Hora", "Usuario", "Accion", "Detalles"])
    
    for log in logs:
        writer.writerow([
            log.get("fecha_hora"),
            log.get("usuario"),
            log.get("accion"),
            json.dumps(log.get("detalles", {}))
        ])
        
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=auditoria_{fecha_inicio}_{fecha_fin}.csv"
    return response
@aplicacion.get("/reportes/trazabilidad-inventario/", tags=["Reportes"])
def descargar_reporte_trazabilidad(
    fecha_inicio: date, 
    fecha_fin: date, 
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_admin)
):
    # 1. Consultar datos
    transacciones = crud.obtener_transacciones_por_fecha(db, fecha_inicio, fecha_fin)
    
    # 2. Generar CSV en memoria
    stream = io.StringIO()
    writer = csv.writer(stream)
    # Encabezados del CSV
    writer.writerow(["ID Transaccion", "Fecha/Hora", "Medicamento", "Ubicacion", "Tipo Movimiento", "Cantidad", "Usuario", "Motivo"])
    
    for t in transacciones:
        # Manejo seguro de datos relacionados para evitar errores si algo se borró
        nombre_med = t.medicamento.catalogo.nombre if (t.medicamento and t.medicamento.catalogo) else "Desconocido/Borrado"
        ubicacion = t.medicamento.ubicacion if t.medicamento else "N/A"
        nombre_usuario = t.usuario.nombre_usuario if t.usuario else "Sistema"
        
        writer.writerow([
            t.id,
            t.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
            nombre_med,
            ubicacion,
            t.tipo_transaccion,
            t.cantidad,
            nombre_usuario,
            t.motivo
        ])
        
    # 3. Preparar respuesta de descarga
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=trazabilidad_stock_{fecha_inicio}_{fecha_fin}.csv"
    return response

@aplicacion.get("/his/pacientes/buscar/{run}", response_model=esquemas.Paciente, tags=["HIS - Pacientes"])
def buscar_paciente_por_run(
    run: str, 
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    paciente = crud.obtener_paciente_por_run(db, run=run)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado en el sistema de admisión.")
    return paciente

@aplicacion.post("/his/pacientes/", response_model=esquemas.Paciente, tags=["HIS - Pacientes"])
def registrar_paciente_admision(
    paciente: esquemas.PacienteCrear,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    db_paciente = crud.obtener_paciente_por_run(db, run=paciente.run)
    if db_paciente:
        raise HTTPException(status_code=400, detail="El paciente ya está registrado.")
    
    nuevo_paciente = crud.crear_paciente(db, paciente)

    nosql_manager.registrar_log_auditoria(
        usuario_nombre=usuario_actual.nombre_usuario,
        accion="HIS_PACIENTE_CREADO",
        detalles={"paciente_id": nuevo_paciente.id, "run": nuevo_paciente.run}
    )
    return nuevo_paciente