from fastapi import FastAPI, Depends, HTTPException, status # type: ignore
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer # type: ignore
from sqlalchemy.orm import Session # type: ignore
from jose import JWTError, jwt # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore # <--- NUEVA IMPORTACIÓN

import modelos, esquemas, crud, seguridad
from base_de_datos import motor, SesionLocal

modelos.Base.metadata.create_all(bind=motor)

aplicacion = FastAPI(
    title="API del Sistema de Gestión Hospitalaria",
    version="1.0.0"
)

# --- CORS ---
origenes = ["*"]

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#8=====================================================================================D
#O=====================================================================================8

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

# --- Endpoint de Autenticacin y Usuarios ---
@aplicacion.post("/usuarios/", response_model=esquemas.Usuario)
def registrar_usuario(usuario: esquemas.UsuarioCrear, db: Session = Depends(obtener_db)):
    db_usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=usuario.nombre_usuario)
    if db_usuario:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    return crud.crear_usuario(db=db, usuario=usuario)

@aplicacion.post("/token", response_model=esquemas.Token)
def iniciar_sesion(db: Session = Depends(obtener_db), form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = crud.obtener_usuario_por_nombre(db, nombre_usuario=form_data.username)
    if not usuario or not seguridad.verificar_clave(form_data.password, usuario.clave_hasheada):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = seguridad.crear_token_acceso(
        datos={"sub": usuario.nombre_usuario}
    )
    return {"access_token": token, "token_type": "bearer"}

@aplicacion.get("/usuarios/yo/", response_model=esquemas.Usuario)
def leer_usuario_actual(usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)):
    return usuario_actual

# --- Endpoint de Recetas ---
@aplicacion.post("/recetas/", response_model=esquemas.Receta)
def crear_nueva_receta(
    receta: esquemas.RecetaCrear, 
    db: Session = Depends(obtener_db), 
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.crear_receta(db=db, receta=receta)

@aplicacion.get("/recetas/", response_model=list[esquemas.Receta])
def leer_recetas(
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.obtener_recetas(db)

# --- Endpoint (Dispensación) ---
@aplicacion.post("/recetas/{receta_id}/dispensar/", response_model=esquemas.DispensarRespuesta)
def dispensar_nueva_receta(
    receta_id: int,
    detalles: list[esquemas.DetalleReceta],
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    resultado = crud.dispensar_receta(db=db, receta_id=receta_id, detalles=detalles)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return resultado

# --- Endpoints de Medicamentos (Inventario) ---
@aplicacion.post("/medicamentos/", response_model=esquemas.Medicamento)
def crear_nuevo_medicamento(
    medicamento: esquemas.MedicamentoCrear,
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.crear_medicamento(db=db, medicamento=medicamento)

@aplicacion.get("/medicamentos/", response_model=list[esquemas.Medicamento])
def leer_medicamentos(
    db: Session = Depends(obtener_db),
    usuario_actual: esquemas.Usuario = Depends(obtener_usuario_actual)
):
    return crud.obtener_medicamentos(db)

# --- mensaje de prueba ---
@aplicacion.get("/")
def leer_raiz():
    return {"mensaje": "Hola el servidor esta funcionando."}