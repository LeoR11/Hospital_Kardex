import pandas as pd # type: ignore
from sklearn.linear_model import LinearRegression # type: ignore
from sklearn.model_selection import train_test_split # type: ignore
import joblib
import os
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func # type: ignore
import modelos
from datetime import datetime

MODEL_DIR = "modelos_ia"
os.makedirs(MODEL_DIR, exist_ok=True)

#Primero obtiene los datos para el analisis
def obtener_datos_historicos(db: Session, catalogo_id: int):
    query = (
        db.query(
            modelos.TransaccionInventario.fecha_hora,
            func.sum(modelos.TransaccionInventario.cantidad).label("cantidad_total")
        )
        .join(modelos.Medicamento, modelos.TransaccionInventario.medicamento_id == modelos.Medicamento.id)
        .filter(
            modelos.Medicamento.catalogo_id == catalogo_id,
            modelos.TransaccionInventario.tipo_transaccion == modelos.TipoTransaccion.dispensacion
        )
        .group_by(modelos.TransaccionInventario.fecha_hora)
        .order_by(modelos.TransaccionInventario.fecha_hora)
    )
    
    df = pd.read_sql(query.statement, query.session.bind)
    if df.empty:
        return None

    df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
    df['cantidad'] = df['cantidad_total'].abs() 
    df = df.set_index('fecha_hora')
    
    df_diario = df.resample('D').sum()
    df_diario = df_diario.fillna(0)
    
    return df_diario

def entrenar_modelo_medicamento(catalogo_id: int, datos: pd.DataFrame):
    model_path = os.path.join(MODEL_DIR, f"modelo_catalogo_{catalogo_id}.joblib")
    
    datos['dia_del_anio'] = datos.index.dayofyear
    datos['dia_de_la_semana'] = datos.index.dayofweek
    
    X = datos[['dia_del_anio', 'dia_de_la_semana']]
    y = datos['cantidad']

    if len(X) < 3: 
        print(f"DEBUG IA: No hay suficientes datos (dias) para entrenar el modelo del catalogo {catalogo_id}. Se necesitan 3, se tienen {len(X)}")
        return False

    modelo = LinearRegression()
    modelo.fit(X, y)
    
    print(f"DEBUG IA: Modelo para catalogo {catalogo_id} entrenado.")
    
    joblib.dump(modelo, model_path)
    return True


def predecir_demanda_medicamento(catalogo_id: int, dias_a_predecir: int = 30):
    model_path = os.path.join(MODEL_DIR, f"modelo_catalogo_{catalogo_id}.joblib")

    if not os.path.exists(model_path):
        return None 

    modelo = joblib.load(model_path)
    
    fecha_hoy = datetime.now()
    fechas_futuras = pd.date_range(start=fecha_hoy, periods=dias_a_predecir)
    
    df_futuro = pd.DataFrame(index=fechas_futuras)
    df_futuro['dia_del_anio'] = df_futuro.index.dayofyear
    df_futuro['dia_de_la_semana'] = df_futuro.index.dayofweek
    
    X_futuro = df_futuro[['dia_del_anio', 'dia_de_la_semana']]
    
    predicciones = modelo.predict(X_futuro)
    predicciones[predicciones < 0] = 0
    prediccion_dia_1 = predicciones[0] if len(predicciones) > 0 else 0
    demanda_total = sum(predicciones)
    
    return {
        "catalogo_id": catalogo_id,
        "dias_predichos": dias_a_predecir,
        "prediccion_dia_1": round(prediccion_dia_1, 2),
        "demanda_total_estimada": round(demanda_total, 2)
    }