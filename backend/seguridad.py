import bcrypt # type: ignore
from jose import JWTError, jwt # type: ignore
from datetime import datetime, timedelta
from typing import Optional

# --- CONFIGURACION (PARA EL TOKEN) ---
CLAVE_SECRETA = "una-clave-super-secreta-y-dificil-de-advininar"
ALGORITMO = "HS256"
TIEMPO_EXPIRACION_TOKEN_MINUTOS = 30

# --- GESTION DE CONTRASEÑAS (BCRYPT) ---

def verificar_clave(clave_plana: str, clave_hasheada: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su version hasheada.
    """
    return bcrypt.checkpw(clave_plana.encode('utf-8'), clave_hasheada.encode('utf-8'))

def obtener_clave_hasheada(clave: str) -> str:
    """
    Convierte una contraseña en texto plano a su version hasheada.
    """
    # Genera salt y hash
    hash_bytes = bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt())
    # Retorna hash como string para guardarlo en BD
    return hash_bytes.decode('utf-8')

# --- GESTION DE TOKENS (JWT) ---

def crear_token_acceso(datos: dict, expires_delta: Optional[timedelta] = None):
    """
    Crea un nuevo token de acceso JWT.
    Acepta un tiempo de expiracion opcional.
    """
    a_codificar = datos.copy()
    
    if expires_delta:
        expiracion = datetime.utcnow() + expires_delta
    else:
        # Por defecto 15 minutos si no se especifica
        expiracion = datetime.utcnow() + timedelta(minutes=15)
    
    a_codificar.update({"exp": expiracion})
    
    token_codificado = jwt.encode(a_codificar, CLAVE_SECRETA, algorithm=ALGORITMO)
    return token_codificado