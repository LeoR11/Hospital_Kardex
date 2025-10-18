import bcrypt # type: ignore
from jose import JWTError, jwt # type: ignore
from datetime import datetime, timedelta

# --- CONFIGURACIon (PARA EL TOKEN) ---
CLAVE_SECRETA = "una-clave-super-secreta-y-dificil-de-advininar"
ALGORITMO = "HS256"
TIEMPO_EXPIRACION_TOKEN_MINUTOS = 30

# --- GESTIN DE CONTRASEÑAS (BCRYPT) ---

def verificar_clave(clave_plana: str, clave_hasheada: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su versión hasheada.
    """
    return bcrypt.checkpw(clave_plana.encode('utf-8'), clave_hasheada.encode('utf-8'))

def obtener_clave_hasheada(clave: str) -> str:
    """
    Convierte una contraseña en texto plano a su version hasheada.
    """
    #salt y hash a la clave
    hash_bytes = bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt())
    # retorna hash como un string para guardarlo en la base de datos
    return hash_bytes.decode('utf-8')

# --- GESTIoN DE TOKENS (JWT) ---
def crear_token_acceso(datos: dict):
    """Crea un nuevo token de acceso JWT."""
    a_codificar = datos.copy()
    expira = datetime.utcnow() + timedelta(minutes=TIEMPO_EXPIRACION_TOKEN_MINUTOS)
    a_codificar.update({"exp": expira})
    token_codificado = jwt.encode(a_codificar, CLAVE_SECRETA, algorithm=ALGORITMO)
    return token_codificado