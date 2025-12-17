import pandas as pd # type: ignore
from sklearn.linear_model import LinearRegression # type: ignore
import joblib # type: ignore
import os
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func # type: ignore
import modelos
from datetime import datetime

# Directorio para guardar los modelos entrenados (.joblib)
MODEL_DIR = "modelos_ia"
os.makedirs(MODEL_DIR, exist_ok=True)

def obtener_datos_historicos(db: Session, catalogo_id: int):
    """
    Obtiene el historial de dispensaciones para un producto del catálogo.f
    Agrupa por fecha y suma las cantidades.
    """
    query = (
        db.query(
            func.date(modelos.TransaccionInventario.fecha_hora).label("fecha"),
            func.sum(modelos.TransaccionInventario.cantidad).label("cantidad_total")
        )
        .join(modelos.Medicamento, modelos.TransaccionInventario.medicamento_id == modelos.Medicamento.id)
        .filter(
            modelos.Medicamento.catalogo_id == catalogo_id,
            modelos.TransaccionInventario.tipo_transaccion == modelos.TipoTransaccion.dispensacion
        )
        .group_by(func.date(modelos.TransaccionInventario.fecha_hora))
        .order_by("fecha")
    )
    
    try:
        df = pd.read_sql(query.statement, query.session.bind)
    except Exception as e:
        print(f"DEBUG IA: Error al leer SQL con Pandas: {e}")
        return None

    if df.empty:
        return None

    # Preprocesamiento
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['cantidad'] = df['cantidad_total'].abs() # Convertir negativos a positivos
    
    # Crear Features (X)
    df['dia_del_anio'] = df['fecha'].dt.dayofyear
    df['dia_de_la_semana'] = df['fecha'].dt.dayofweek
    
    return df

def entrenar_modelo_medicamento(db: Session, medicamento_fisico_id: int):
    """
    Entrena el modelo de regresión lineal para predecir demanda futura.
    Recibe el ID físico, busca su catálogo y entrena.
    """
    # 1. Buscar a qué catálogo pertenece este medicamento físico
    med_fisico = db.query(modelos.Medicamento).filter(modelos.Medicamento.id == medicamento_fisico_id).first()
    if not med_fisico:
        print(f"DEBUG IA: Medicamento fisico ID {medicamento_fisico_id} no encontrado.")
        return False
    
    catalogo_id = med_fisico.catalogo_id
    model_path = os.path.join(MODEL_DIR, f"modelo_catalogo_{catalogo_id}.joblib")

    # 2. Obtener datos históricos del catálogo completo
    datos = obtener_datos_historicos(db, catalogo_id)
    
    if datos is None or len(datos) < 3:
        # Se necesitan al menos 3 días de datos para una regresión mínimamente válida
        print(f"DEBUG IA: Datos insuficientes para catálogo {catalogo_id}. No se entrena.")
        return False

    # 3. Preparar X e y
    X = datos[['dia_del_anio', 'dia_de_la_semana']]
    y = datos['cantidad']

    try:
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        # 4. Guardar modelo
        joblib.dump(modelo, model_path)
        print(f"DEBUG IA: Modelo actualizado para Catalogo ID {catalogo_id}")
        return True
    except Exception as e:
        print(f"DEBUG IA: Error entrenando modelo: {e}")
        return False

def predecir_demanda_medicamento(catalogo_id: int, dias_a_predecir: int = 7):
    """
    Carga el modelo guardado y predice la demanda para los próximos días.
    """
    model_path = os.path.join(MODEL_DIR, f"modelo_catalogo_{catalogo_id}.joblib")

    if not os.path.exists(model_path):
        return None 

    try:
        modelo = joblib.load(model_path)
        
        fecha_hoy = datetime.now()
        fechas_futuras = pd.date_range(start=fecha_hoy, periods=dias_a_predecir)
        
        df_futuro = pd.DataFrame(index=fechas_futuras)
        df_futuro['dia_del_anio'] = df_futuro.index.dayofyear
        df_futuro['dia_de_la_semana'] = df_futuro.index.dayofweek
        
        X_futuro = df_futuro[['dia_del_anio', 'dia_de_la_semana']]
        
        predicciones = modelo.predict(X_futuro)
        
        # Evitar predicciones negativas
        df_futuro['demanda_predicha'] = [max(0, p) for p in predicciones]
        
        return df_futuro
    except Exception as e:
        print(f"DEBUG IA: Error en predicción: {e}")
        return None