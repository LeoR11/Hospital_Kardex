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
    description="Una API modular para gestionar."
)

origenes = ["*"]
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencias ---
def obtener_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="token")

#Para detectar quien loggeo y sacar auditoria
def obtener_usuario_actual(db: Session = Depends(obtener_db), token: str = Depends(esquema_oauth2)):
    credenciales_excepcion = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, seguridad.CLAVE_SECRETA, algorithms=[seguridad.ALGORITMO])
        nombre_usuario: str = payload.get("sub")
        if nombre_usuario is None:
            raise credenciales_excepcion
    except JWTError:
        raise credenciales_excepcion
    
    usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=nombre_usuario)
    if usuario is None:
        raise credenciales_excepcion
    return usuario

def obtener_admin_actual(usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    if usuario_actual.rol != modelos.RolUsuario.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acción no permitida. Se requieren privilegios de administrador."
        )
    return usuario_actual

# --- Endpoints: Usuarios (Con Auditoria)
@aplicacion.post("/usuarios/", response_model=esquemas.Usuario, tags=["Usuarios"])
def registrar_usuario(
    usuario: esquemas.UsuarioCrear, 
    db: Session = Depends(obtener_db),
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    db_usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=usuario.nombre_usuario)
    if db_usuario:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya esta registrado en el sistema")
    
    nuevo_usuario = crud.crear_usuario(db=db, usuario=usuario)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="USUARIO_CREADO",
        detalles={
            "usuario_creado": nuevo_usuario.nombre_usuario,
            "rol_asignado": nuevo_usuario.rol.value
        }
    )
    return nuevo_usuario

@aplicacion.get("/usuarios/", response_model=List[esquemas.Usuario], tags=["Usuarios"])
def leer_usuarios(
    search: Optional[str] = None, 
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    if search:
        usuarios = crud.buscar_usuarios_por_nombre(db, nombre_busqueda=search)
    else:
        usuarios = crud.obtener_usuarios(db)
    return usuarios

@aplicacion.delete("/usuarios/{usuario_id}", tags=["Usuarios"])
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(obtener_db),
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    db_usuario = crud.obtener_usuario_por_id(db, usuario_id=usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if db_usuario.rol == modelos.RolUsuario.administrador:
        raise HTTPException(status_code=403, detail="No se permite eliminar a otros administradores")

    if db_usuario.id == admin_actual.id:
        raise HTTPException(status_code=403, detail="No se puede eliminar a si mismo")

    nombre_usuario_eliminado = db_usuario.nombre_usuario
    crud.eliminar_usuario(db=db, usuario_id=usuario_id)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="USUARIO_ELIMINADO",
        detalles={
            "usuario_eliminado_id": usuario_id,
            "usuario_eliminado_nombre": nombre_usuario_eliminado
        }
    )
    return {"mensaje": "Usuario eliminado exitosamente"}

@aplicacion.post("/token", response_model=esquemas.Token, tags=["Usuarios"])
def iniciar_sesion(db: Session = Depends(obtener_db), form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=form_data.username)
    if not usuario or not seguridad.verificar_clave(form_data.password, usuario.clave_hasheada):
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=form_data.username, 
            accion="LOGIN_FALLIDO",
            detalles={"motivo": "Nombre de usuario o contraseña incorrectos"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = seguridad.crear_token_acceso(
        datos={"sub": usuario.nombre_usuario}
    )
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=usuario.nombre_usuario,
        accion="LOGIN_EXITOSO",
        detalles={"rol": usuario.rol.value}
    )
    return {"access_token": token, "token_type": "bearer", "rol": usuario.rol.value}

@aplicacion.get("/usuarios/yo/", response_model=esquemas.Usuario, tags=["Usuarios"])
def leer_usuario_actual(usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return usuario_actual

# --- Endpoints: Profesionales (Con Auditoria)

@aplicacion.post("/profesionales/", response_model=esquemas.Profesional, tags=["Profesionales"])
def crear_nuevo_profesional(
    profesional: esquemas.ProfesionalCrear, 
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual) 
):
    db_profesional_existente = crud.obtener_profesional_por_run(db, run=profesional.run)
    if db_profesional_existente:
        raise HTTPException(status_code=400, detail="El RUT del profesional ya esta registrado")
    
    db_profesional = crud.crear_profesional(db=db, profesional=profesional)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="PROFESIONAL_CREADO",
        detalles={
            "profesional_id": db_profesional.id,
            "nombre": db_profesional.nombre,
            "run": db_profesional.run
        }
    )
    return db_profesional

@aplicacion.get("/profesionales/", response_model=List[esquemas.Profesional], tags=["Profesionales"])
def leer_profesionales(
    search: Optional[str] = None,
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual) 
):
    if search:
        profesionales = crud.buscar_profesionales(db, busqueda=search)
    else:
        profesionales = crud.obtener_profesionales(db)
    return profesionales

@aplicacion.delete("/profesionales/{profesional_id}", tags=["Profesionales"])
def eliminar_profesional(
    profesional_id: int,
    db: Session = Depends(obtener_db),
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual) 
):
    db_profesional = db.get(modelos.Profesional, profesional_id)
    if not db_profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    
    detalles_log = {
        "profesional_id": profesional_id,
        "nombre": db_profesional.nombre,
        "run": db_profesional.run
    }
    
    if not crud.eliminar_profesional(db=db, profesional_id=profesional_id):
        raise HTTPException(status_code=404, detail="Profesional no encontrado") 

    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="PROFESIONAL_ELIMINADO",
        detalles=detalles_log
    )
    return {"mensaje": "Profesional eliminado exitosamente"}

# --- Endpoints: Recetas (Con Auditoria)
@aplicacion.post("/recetas/", response_model=esquemas.Receta, tags=["Recetas"])
def crear_nueva_receta_completa(
    receta: esquemas.RecetaCrear, 
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    nueva_receta = crud.crear_receta_completa(db=db, receta=receta)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=usuario_actual.nombre_usuario,
        accion="RECETA_CREADA",
        detalles={
            "receta_id": nueva_receta.id,
            "paciente_id": nueva_receta.id_paciente,
            "profesional_id": nueva_receta.profesional_id,
            "items_count": len(nueva_receta.detalles)
        }
    )
    return nueva_receta

@aplicacion.get("/recetas/", response_model=List[esquemas.Receta], tags=["Recetas"])
def leer_recetas(
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.obtener_recetas(db)

@aplicacion.get("/recetas/{receta_id}", response_model=esquemas.Receta, tags=["Recetas"])
def leer_receta_unica(
    receta_id: int, 
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    db_receta = crud.obtener_receta_por_id(db, receta_id=receta_id)
    if db_receta is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return db_receta

@aplicacion.post("/recetas/{receta_id}/dispensar/", response_model=esquemas.DispensarRespuesta, tags=["Recetas"])
def dispensar_receta_existente(
    receta_id: int, 
    mapeo_dispensacion: Dict[str, int], 
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        resultado = crud.dispensar_receta(
            db=db, 
            receta_id=receta_id, 
            usuario_id=usuario_actual.id,
            mapeo_dispensacion=mapeo_dispensacion
        )
        return resultado
    except (RecetaProcesadaError, EntidadNoEncontradaError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StockInsuficienteError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")



# --- Endpoints: Inventario (Con Auditoria e IA)
@aplicacion.get("/catalogo/dashboard/", response_model=List[esquemas.CatalogoDashboardItem], tags=["Inventario - Catalogo"])
def leer_catalogo_dashboard_ia(
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    items_catalogo = crud.obtener_catalogo(db)
    dashboard_items = []

    for item in items_catalogo:
        catalogo_id = item.id
        stock_total = crud.obtener_stock_total_por_catalogo(db, catalogo_id)
        prediccion_data = ia.predecir_demanda_medicamento(catalogo_id, dias_a_predecir=30)
        
        demanda_estimada = None
        estado_ia = "SIN DATOS" 
        
        if prediccion_data:
            demanda_estimada = prediccion_data["demanda_total_estimada"]
            if stock_total < demanda_estimada:
                estado_ia = "REQUIERE PEDIDO"
            else:
                estado_ia = "OK"
        
        dashboard_item = {
            "id": item.id,
            "nombre": item.nombre,
            "descripcion": item.descripcion,
            "stock_total": stock_total,
            "demanda_estimada_30_dias": demanda_estimada,
            "estado_ia": estado_ia
        }
        dashboard_items.append(dashboard_item)
        
    return dashboard_items


@aplicacion.post("/catalogo/", response_model=esquemas.MedicamentoCatalogo, tags=["Inventario - Catalogo"])
def crear_item_catalogo(
    catalogo_item: esquemas.MedicamentoCatalogoCrear,
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    nuevo_item = crud.crear_item_catalogo(db=db, item=catalogo_item)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="CATALOGO_CREADO",
        detalles={
            "catalogo_id": nuevo_item.id,
            "nombre": nuevo_item.nombre
        }
    )
    return nuevo_item

@aplicacion.get("/catalogo/", response_model=List[esquemas.MedicamentoCatalogo], tags=["Inventario - Catálogo"])
def leer_catalogo(
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual) 
):
    return crud.obtener_catalogo(db)

@aplicacion.delete("/catalogo/{catalogo_id}", tags=["Inventario - Catalogo"])
def eliminar_item_catalogo(
    catalogo_id: int,
    db: Session = Depends(obtener_db),
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    db_catalogo = crud.obtener_catalogo_por_id(db, catalogo_id)
    if not db_catalogo:
        raise HTTPException(status_code=404, detail="Item de catalogo no encontrado.")
    
    detalles_log = {
        "catalogo_id": catalogo_id,
        "nombre": db_catalogo.nombre
    }

    try:
        crud.eliminar_item_catalogo(db=db, catalogo_id=catalogo_id)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=admin_actual.nombre_usuario,
            accion="CATALOGO_ELIMINADO",
            detalles=detalles_log
        )
        return {"mensaje": "Item del catalogo eliminado exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EntidadNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))


@aplicacion.post("/medicamentos/", response_model=esquemas.Medicamento, tags=["Inventario - Ubicaciones"])
def crear_nueva_ubicacion_medicamento(
    medicamento: esquemas.MedicamentoCrear, 
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    try:
        nueva_ubicacion = crud.crear_medicamento(db=db, medicamento=medicamento)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=admin_actual.nombre_usuario,
            accion="UBICACION_CREADA",
            detalles={
                "medicamento_id": nueva_ubicacion.id,
                "catalogo_id": nueva_ubicacion.catalogo_id,
                "ubicacion": nueva_ubicacion.ubicacion,
                "lote": nueva_ubicacion.lote,
                "fecha_vencimiento": nueva_ubicacion.fecha_vencimiento.isoformat()
            }
        )
        return nueva_ubicacion
    except UbicacionDuplicadaError as e:
        raise HTTPException(status_code=400, detail=str(e))

@aplicacion.get("/medicamentos/", response_model=List[esquemas.Medicamento], tags=["Inventario - Ubicaciones"])
def leer_ubicaciones_medicamentos(
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.obtener_medicamentos(db)

@aplicacion.delete("/medicamentos/{medicamento_id}", tags=["Inventario - Ubicaciones"])
def eliminar_ubicacion_medicamento(
    medicamento_id: int,
    db: Session = Depends(obtener_db),
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    db_medicamento = crud.obtener_medicamento_por_id(db, medicamento_id)
    if not db_medicamento:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada.")

    detalles_log = {
        "medicamento_id": medicamento_id,
        "catalogo_id": db_medicamento.catalogo_id,
        "nombre_catalogo": db_medicamento.catalogo.nombre,
        "ubicacion": db_medicamento.ubicacion,
        "lote": db_medicamento.lote,
        "stock_al_eliminar": db_medicamento.stock_actual
    }
    
    try:
        crud.eliminar_medicamento(db=db, medicamento_id=medicamento_id)
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=admin_actual.nombre_usuario,
            accion="UBICACION_ELIMINADA",
            detalles=detalles_log
        )
        return {"mensaje": "Ubicacion de medicamento eliminada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EntidadNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))

@aplicacion.post("/inventario/transaccion/", response_model=esquemas.Medicamento, tags=["Inventario - Ubicaciones"])
def registrar_nueva_transaccion_stock(
    transaccion: esquemas.TransaccionCrear,
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        resultado = crud.registrar_transaccion_stock(
            db=db, 
            transaccion=transaccion, 
            usuario_id=usuario_actual.id
        )
        return resultado
    except StockInsuficienteError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except EntidadNoEncontradaError as e:
         raise HTTPException(status_code=404, detail=str(e))

# --- Endpoints: Pedidos (Con Auditoria)
@aplicacion.post("/pedidos/", response_model=esquemas.Pedido, tags=["Pedidos"])
def crear_nuevo_pedido(
    pedido: esquemas.PedidoCrear,
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    nuevo_pedido = crud.crear_pedido(db=db, pedido=pedido)
    
    nosql_manager.registrar_log_auditoria(
        usuario_nombre=admin_actual.nombre_usuario,
        accion="PEDIDO_CREADO",
        detalles={
            "pedido_id": nuevo_pedido.id,
            "descripcion": nuevo_pedido.descripcion,
            "items_count": len(nuevo_pedido.detalles)
        }
    )
    return nuevo_pedido

@aplicacion.get("/pedidos/", response_model=List[esquemas.Pedido], tags=["Pedidos"])
def leer_pedidos_pendientes(
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.obtener_pedidos(db, estado="pendiente")

@aplicacion.post("/pedidos/{pedido_id}/recepcionar/", response_model=esquemas.Pedido, tags=["Pedidos"])
def recepcionar_pedido_existente(
    pedido_id: int,
    payload: esquemas.RecepcionPedidoPayload,
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    try:
        resultado = crud.recepcionar_pedido(
            db=db, 
            pedido_id=pedido_id, 
            usuario_id=usuario_actual.id,
            payload=payload
        )
        
        nosql_manager.registrar_log_auditoria(
            usuario_nombre=usuario_actual.nombre_usuario,
            accion="PEDIDO_RECEPCIONADO",
            detalles={
                "pedido_id": pedido_id,
                "items_procesados": len(payload.items)
            }
        )
        return resultado
    except (PedidoProcesadoError, EntidadNoEncontradaError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UbicacionDuplicadaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

# --- Endpoints: Gestion de los Kardex (Incidencias)
@aplicacion.get("/kardex/incidencias/", response_model=List[esquemas.IncidenciaKardex], tags=["Gestion de Kardex"])
def leer_incidencias(
    estado: Optional[EstadoIncidencia] = None,
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    """
    Obtiene una lista de todas las incidencias,
    usado por el panel de admin.
    """
    return crud.obtener_incidencias(db=db, estado=estado)

@aplicacion.post("/kardex/reportar-falla/", response_model=esquemas.IncidenciaKardex, tags=["Gestion de Kardex"])
def reportar_falla_kardex(
    incidencia: esquemas.IncidenciaKardexCrear,
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    """
    Endpoint para que el operario (app de escritorio) reporte una falla.
    Esto automaticamente pone el Kardex en estado "en_falla".
    """
    try:
        return crud.crear_incidencia_kardex(
            db=db, 
            incidencia=incidencia, 
            usuario_id=usuario_actual.id
        )
    except EntidadNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@aplicacion.put("/kardex/incidencias/{incidencia_id}/resolver/", response_model=esquemas.IncidenciaKardex, tags=["Gestion de Kardex"])
def resolver_actualizar_incidencia(
    incidencia_id: int,
    datos_resolucion: esquemas.IncidenciaKardexResolver,
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    """
    Endpoint para que el admin (web) actualice o resuelva una incidencia.
    Si se marca como "resuelta", pone el Kardex "operativo".
    """
    try:
        return crud.resolver_incidencia_kardex(
            db=db,
            incidencia_id=incidencia_id,
            datos_resolucion=datos_resolucion,
            usuario_id=admin_actual.id
        )
    except EntidadNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

# --- Endpoints: Reportes
@aplicacion.get("/reportes/trazabilidad-inventario/", tags=["Reportes"])
def descargar_reporte_trazabilidad_inventario(
    fecha_inicio: date, 
    fecha_fin: date,
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    logs = nosql_manager.obtener_logs_por_fecha(
        fecha_inicio=fecha_inicio, 
        fecha_fin=fecha_fin,
        accion="TRANSACCION_STOCK" 
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Fecha", "Hora", "Usuario", "Accion", "Medicamento", "Lote", 
        "Vencimiento", "Cantidad", "Ubicacion", "Stock_Resultante", 
        "ID_Paciente", "ID_Receta", "Motivo"
    ])
    for log in logs:
        detalles = log.get("detalles", {})
        fecha_hora_utc = log.get("fecha_hora")
        fecha_local_str, hora_local_str = "N/A", "N/A"
        if fecha_hora_utc:
            fecha_local = fecha_hora_utc - timedelta(hours=3) 
            fecha_local_str = fecha_local.strftime("%Y-%m-%d")
            hora_local_str = fecha_local.strftime("%H:%M:%S")
        writer.writerow([
            fecha_local_str,
            hora_local_str,
            log.get("usuario"),
            detalles.get("tipo_transaccion"),
            detalles.get("nombre_catalogo"),
            detalles.get("lote"),
            detalles.get("fecha_vencimiento"),
            detalles.get("cantidad"),
            detalles.get("ubicacion"),
            detalles.get("stock_resultante"),
            detalles.get("paciente_id"),
            detalles.get("receta_id"),
            detalles.get("motivo")
        ])
    output.seek(0) 
    headers = {
        "Content-Disposition": f"attachment; filename=reporte_trazabilidad_{fecha_inicio}_a_{fecha_fin}.csv"
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")


@aplicacion.get("/reportes/auditoria-sistema/", tags=["Reportes"])
def descargar_reporte_auditoria_sistema(
    fecha_inicio: date, 
    fecha_fin: date,
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    logs = nosql_manager.obtener_logs_por_fecha(
        fecha_inicio=fecha_inicio, 
        fecha_fin=fecha_fin
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Fecha", "Hora", "Usuario", "Accion", 
        "Sujeto_Principal", 
        "Datos_Adicionales (JSON)"
    ])
    
    for log in logs:
        detalles_copia = log.get("detalles", {}).copy() 
        accion = log.get("accion")
        sujeto_principal = "" 

        if accion == "LOGIN_EXITOSO":
            sujeto_principal = f"Rol: {detalles_copia.pop('rol', 'N/A')}"
        elif accion == "LOGIN_FALLIDO":
            sujeto_principal = f"Motivo: {detalles_copia.pop('motivo', 'N/A')}"
        elif accion == "USUARIO_CREADO":
            sujeto_principal = f"Usuario: {detalles_copia.pop('usuario_creado', 'N/A')}, Rol: {detalles_copia.pop('rol_asignado', 'N/A')}"
        elif accion == "USUARIO_ELIMINADO":
            sujeto_principal = f"ID: {detalles_copia.pop('usuario_eliminado_id', 'N/A')}, Nombre: {detalles_copia.pop('usuario_eliminado_nombre', 'N/A')}"
        elif accion == "PROFESIONAL_CREADO":
            sujeto_principal = f"Nombre: {detalles_copia.pop('nombre', 'N/A')}, RUN: {detalles_copia.pop('run', 'N/A')}"
        elif accion == "PROFESIONAL_ELIMINADO":
            sujeto_principal = f"ID: {detalles_copia.pop('profesional_id', 'N/A')}, Nombre: {detalles_copia.pop('nombre', 'N/A')}"
        elif accion == "RECETA_CREADA":
            sujeto_principal = f"Receta ID: {detalles_copia.pop('receta_id', 'N/A')}, Paciente: {detalles_copia.pop('paciente_id', 'N/A')}"
        elif accion == "DISPENSAR_RECETA_COMPLETA":
            sujeto_principal = f"Receta ID: {detalles_copia.pop('receta_id', 'N/A')}, Paciente: {detalles_copia.pop('paciente_id', 'N/A')}"
        elif accion == "CATALOGO_CREADO" or accion == "CATALOGO_ELIMINADO":
            sujeto_principal = f"ID: {detalles_copia.pop('catalogo_id', 'N/A')}, Nombre: {detalles_copia.pop('nombre', 'N/A')}"
        elif accion == "UBICACION_CREADA":
            sujeto_principal = f"Ubic: {detalles_copia.pop('ubicacion', 'N/A')}, Lote: {detalles_copia.pop('lote', 'N/A')}, Venc: {detalles_copia.pop('fecha_vencimiento', 'N/A')}"
        elif accion == "UBICACION_ELIMINADA":
            sujeto_principal = f"Ubic: {detalles_copia.pop('ubicacion', 'N/A')}, Nombre: {detalles_copia.pop('nombre_catalogo', 'N/A')}"
        elif accion == "PEDIDO_CREADO":
            sujeto_principal = f"Pedido ID: {detalles_copia.pop('pedido_id', 'N/A')}, Desc: {detalles_copia.pop('descripcion', 'N/A')}"
        elif accion == "PEDIDO_RECEPCIONADO":
            sujeto_principal = f"Pedido ID: {detalles_copia.pop('pedido_id', 'N/A')}, Items: {detalles_copia.pop('items_procesados', 'N/A')}"
        elif accion == "TRANSACCION_STOCK":
            sujeto_principal = (
                f"Med: {detalles_copia.pop('nombre_catalogo', 'N/A')}, "
                f"Cant: {detalles_copia.pop('cantidad', 'N/A')}, "
                f"Ubic: {detalles_copia.pop('ubicacion', 'N/A')}, "
                f"Lote: {detalles_copia.pop('lote', 'N/A')}"
            )
        elif accion == "INCIDENCIA_REPORTADA":
             sujeto_principal = f"Kardex: {detalles_copia.pop('kardex_afectado', 'N/A')}, Reporte: {detalles_copia.pop('reporte', 'N/A')}"
        elif accion == "INCIDENCIA_RESUELTA" or accion == "INCIDENCIA_ACTUALIZADA":
             sujeto_principal = f"Kardex: {detalles_copia.pop('kardex_afectado', 'N/A')}, Estado: {detalles_copia.pop('nuevo_estado_kardex', 'N/A')}"
        else:
            sujeto_principal = "Ver detalles"

        fecha_hora_utc = log.get("fecha_hora")
        fecha_local_str, hora_local_str = "N/A", "N/A"
        if fecha_hora_utc:
            fecha_local = fecha_hora_utc - timedelta(hours=3) 
            fecha_local_str = fecha_local.strftime("%Y-%m-%d")
            hora_local_str = fecha_local.strftime("%H:%M:%S")

        writer.writerow([
            fecha_local_str,
            hora_local_str,
            log.get("usuario"),
            accion,
            sujeto_principal, 
            json.dumps(detalles_copia) 
        ])
    output.seek(0)
    headers = {
        "Content-Disposition": f"attachment; filename=reporte_auditoria_sistema_{fecha_inicio}_a_{fecha_fin}.csv"
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")


# --- Endpoints: IA y General
@aplicacion.post("/ia/entrenar/catalogo/{catalogo_id}", tags=["IA - Prediccion"])
def entrenar_modelo_ia_catalogo(
    catalogo_id: int, 
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    datos = ia.obtener_datos_historicos(db, catalogo_id)
    if datos is None or datos.empty:
        raise HTTPException(status_code=404, detail="No hay suficientes datos historicos para este item del catalogo.")
    
    exito = ia.entrenar_modelo_medicamento(catalogo_id, datos)
    if not exito:
        raise HTTPException(status_code=400, detail="No se pudo entrenar el modelo (datos insuficientes).")
        
    return {"mensaje": f"Modelo para el catálogo {catalogo_id} entrenado exitosamente."}

@aplicacion.get("/ia/predecir/catalogo/{catalogo_id}", tags=["IA - Prediccion"])
def predecir_demanda_ia_catalogo(
    catalogo_id: int, 
    dias: int = 30, 
    usuario_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    prediccion = ia.predecir_demanda_medicamento(catalogo_id, dias)
    if prediccion is None:
        raise HTTPException(status_code=404, detail="No se encontro un modelo entrenado para este catalogo. Por favor, entrene el modelo primero.")
    
    return prediccion

@aplicacion.get("/ia/sugerencias-pedido/", response_model=List[esquemas.SugerenciaPedido], tags=["IA - Prediccion"])
def obtener_sugerencias_pedido(
    dias_a_predecir: int = 30,
    db: Session = Depends(obtener_db), 
    admin_actual: esquemas.Usuario = Depends(obtener_admin_actual)
):
    items_catalogo = crud.obtener_catalogo(db)
    sugerencias = []

    for item in items_catalogo:
        catalogo_id = item.id
        stock_actual = crud.obtener_stock_total_por_catalogo(db, catalogo_id)
        prediccion_data = ia.predecir_demanda_medicamento(catalogo_id, dias_a_predecir)
        
        if prediccion_data:
            demanda_estimada = prediccion_data["demanda_total_estimada"]
            stock_faltante = round(demanda_estimada - stock_actual)
            
            if stock_faltante > 0:
                sugerencias.append({
                    "catalogo_id": catalogo_id,
                    "nombre_medicamento": item.nombre,
                    "stock_actual": stock_actual,
                    "demanda_estimada_30_dias": demanda_estimada,
                    "cantidad_sugerida_a_pedir": stock_faltante
                })
                
    return sugerencias

@aplicacion.get("/ia/prediccion-diaria/", response_model=List[esquemas.PrediccionDiariaItem], tags=["IA - Prediccion"])
def obtener_prediccion_diaria(
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    items_catalogo = crud.obtener_catalogo(db)
    predicciones_diarias = []

    for item in items_catalogo:
        catalogo_id = item.id
        stock_actual = crud.obtener_stock_total_por_catalogo(db, catalogo_id)
        prediccion_data = ia.predecir_demanda_medicamento(catalogo_id, dias_a_predecir=1)
        
        if prediccion_data:
            demanda_hoy = prediccion_data["prediccion_dia_1"]
            if demanda_hoy > 0:
                predicciones_diarias.append({
                    "catalogo_id": catalogo_id,
                    "nombre_medicamento": item.nombre,
                    "stock_actual": stock_actual,
                    "demanda_estimada_hoy": demanda_hoy
                })
                
    predicciones_diarias.sort(key=lambda x: x['demanda_estimada_hoy'], reverse=True)
    return predicciones_diarias

# --- endpoint del estado del kardex ---
@aplicacion.get("/kardex/status/", response_model=List[esquemas.Kardex], tags=["Gestion de Kardex"])
def obtener_estado_kardex(
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    """
    Obtiene el estado actual (real) de todos los Kardex desde la BD.
    """
    return crud.obtener_kardex_todos(db)

# mensaje de verificcion del server de la API (nada importante)
@aplicacion.get("/", tags=["General"])
def leer_raiz():
    return {"mensaje": "API del Kardex v4.0 El servidor esta funcionando."}