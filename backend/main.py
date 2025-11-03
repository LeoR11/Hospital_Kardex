from fastapi import FastAPI, Depends, HTTPException, status # type: ignore
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer # type: ignore
from sqlalchemy.orm import Session # type: ignore
from jose import JWTError, jwt # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from typing import List

import modelos, esquemas, crud, seguridad
from base_de_datos import motor, SesionLocal

modelos.Base.metadata.create_all(bind=motor)

aplicacion = FastAPI(
    title="API del Sistema de Gestión Hospitalaria",
    version="2.0.0",
    description="Una API modular para gestionar Recetas, Inventario y Trazabilidad."
)

# --- CONFIGURACIÓN DE CORS ---
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

# --- Endopinrt de autenticación y usuarios ---
@aplicacion.post("/usuarios/", response_model=esquemas.Usuario, tags=["Usuarios"])
def registrar_usuario(usuario: esquemas.UsuarioCrear, db: Session = Depends(obtener_db)):
    db_usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=usuario.nombre_usuario)
    if db_usuario:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya esta registrado")
    return crud.crear_usuario(db=db, usuario=usuario)

@aplicacion.post("/token", response_model=esquemas.Token, tags=["Usuarios"])
def iniciar_sesion(db: Session = Depends(obtener_db), form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=form_data.username)
    if not usuario or not seguridad.verificar_clave(form_data.password, usuario.clave_hasheada):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nombre de usuario o contraseña incorrectos")
    token = seguridad.crear_token_acceso(datos={"sub": usuario.nombre_usuario})
    return {"access_token": token, "token_type": "bearer"}

@aplicacion.get("/usuarios/yo/", response_model=esquemas.Usuario, tags=["Usuarios"])
def leer_usuario_actual(usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return usuario_actual

# EP PROFESIONALES
@aplicacion.post("/profesionales/", response_model=esquemas.Profesional, tags=["Profesionales"])
def crear_nuevo_profesional(profesional: esquemas.ProfesionalCrear, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    db_profesional = crud.obtener_profesional_por_run(db, run=profesional.run)
    if db_profesional:
        raise HTTPException(status_code=400, detail="El RUN del profesional ya esta registrado")
    return crud.crear_profesional(db=db, profesional=profesional)

@aplicacion.get("/profesionales/", response_model=List[esquemas.Profesional], tags=["Profesionales"])
def leer_profesionales(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_profesionales(db)

#EP RECETAS
@aplicacion.post("/recetas/", response_model=esquemas.Receta, tags=["Recetas"])
def crear_nueva_receta_completa(receta: esquemas.RecetaCrear, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.crear_receta_completa(db=db, receta=receta)

@aplicacion.get("/recetas/", response_model=List[esquemas.Receta], tags=["Recetas"])
def leer_recetas(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_recetas(db)

@aplicacion.get("/recetas/{receta_id}", response_model=esquemas.Receta, tags=["Recetas"])
def leer_receta_unica(receta_id: int, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    db_receta = crud.obtener_receta_por_id(db, receta_id=receta_id)
    if db_receta is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return db_receta

@aplicacion.post("/recetas/{receta_id}/dispensar/", response_model=esquemas.DispensarRespuesta, tags=["Recetas"])
def dispensar_receta_existente(receta_id: int, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    resultado = crud.dispensar_receta(db=db, receta_id=receta_id, usuario_id=usuario_actual.id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada o ya procesada")
    return resultado

# EP INVENTARIO Y TRAZABILIDAD
@aplicacion.post("/medicamentos/", response_model=esquemas.Medicamento, tags=["Inventario"])
def crear_nuevo_medicamento(medicamento: esquemas.MedicamentoCrear, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.crear_medicamento(db=db, medicamento=medicamento)

@aplicacion.get("/medicamentos/", response_model=List[esquemas.Medicamento], tags=["Inventario"])
def leer_medicamentos(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_medicamentos(db)

@aplicacion.post("/inventario/transaccion/", response_model=esquemas.Medicamento, tags=["Inventario"])
def registrar_nueva_transaccion_stock(transaccion: esquemas.TransaccionCrear, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    resultado = crud.registrar_transaccion_stock(db=db, transaccion=transaccion, usuario_id=usuario_actual.id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    return resultado


# # EP PEDIDOS DE SUMINISTROS
@aplicacion.post("/pedidos/", response_model=esquemas.Pedido, tags=["Pedidos"])
def crear_nuevo_pedido(pedido: esquemas.PedidoCrear, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.crear_pedido(db=db, pedido=pedido)

@aplicacion.get("/pedidos/", response_model=List[esquemas.Pedido], tags=["Pedidos"])
def leer_pedidos_pendientes(db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return crud.obtener_pedidos(db, estado="pendiente")

@aplicacion.post("/pedidos/{pedido_id}/recepcionar/", response_model=esquemas.Pedido, tags=["Pedidos"])
def recepcionar_pedido_existente(pedido_id: int, db: Session = Depends(obtener_db), usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    resultado = crud.recepcionar_pedido(db=db, pedido_id=pedido_id, usuario_id=usuario_actual.id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado o ya procesado")
    return resultado


# EP DE BIENVENIDA (SOLO UNA VERIFICACION)
@aplicacion.get("/", tags=["General"])
def leer_raiz():
    return {"mensaje": "API del Kardex v2.0 El servidor esta funcionando."}