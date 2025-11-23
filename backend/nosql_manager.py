import pymongo
from datetime import datetime, date, time
import logging

MONGO_URI = "mongodb+srv://kardex_user:inacap2025@kardexdb.wdnq1gu.mongodb.net/?appName=KardexDB"


try:
    cliente = pymongo.MongoClient(MONGO_URI)

    cliente.admin.command('ping')
    print("--- Conexion a MongoDB Atlas exitosa ---")

    db = cliente["hospital_kardex_logs"]
    coleccion_trazabilidad = db["trazabilidad"]

except Exception as e:
    logging.error(f"Error al conectar con MongoDB: {e}")
    print("--- ERROR: No se pudo conectar a MongoDB Atlas ---")
    print("--- Revisa tu Cadena de Conexión en nosql_manager.py ---")
    cliente = None
    coleccion_trazabilidad = None

def registrar_log_auditoria(usuario_nombre: str, accion: str, detalles: dict):
    """
    Guarda un documento de log inmutable en la base de datos NoSQL.
    """
    if coleccion_trazabilidad is None:
        print("ERROR: No se puede registrar el log, no hay conexion a la BD NoSQL.")
        return

    try:
        log = {
            "fecha_hora": datetime.utcnow(),
            "usuario": usuario_nombre,
            "accion": accion,
            "detalles": detalles
        }
        coleccion_trazabilidad.insert_one(log)
        print(f"--- DEBUG (NoSQL): Log de '{accion}' guardado exitosamente. ---")
    except Exception as e:
        logging.error(f"Error al guardar log en NoSQL: {e}")
        print(f"--- DEBUG (NoSQL): ERROR al guardar log: {e} ---")


def obtener_logs_por_fecha(fecha_inicio: date, fecha_fin: date, accion: str = None):
    """
    Obtiene todos los logs de auditoria dentro de un rango de fechas (inclusivo).
    Puede filtrar opcionalmente por un tipo de 'accion' específica.
    """
    if coleccion_trazabilidad is None:
        print("ERROR: No se puede obtener logs, no hay conexión a NoSQL.")
        return []

    # Convertir las 'date' (fecha) de Python a 'datetime' (fecha y hora)
    # para que MongoDB pueda comparar correctamente.
    # .min = 00:00:00
    # .max = 23:59:59
    start_dt = datetime.combine(fecha_inicio, time.min)
    end_dt = datetime.combine(fecha_fin, time.max) 

    #query del  mongo
    query = {
        "fecha_hora": {
            "$gte": start_dt,
            "$lte": end_dt 
        }
    }
    
    if accion:
        query["accion"] = accion
    try:
        logs = list(coleccion_trazabilidad.find(query).sort("fecha_hora", 1))
        return logs
    except Exception as e:
        logging.error(f"Error al obtener logs NoSQL: {e}")
        return []
