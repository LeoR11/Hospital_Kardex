# backend/semilla_ia.py
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session # type: ignore
from base_de_datos import SesionLocal, motor
import modelos
import ia

# Aseguramos que las tablas existan
modelos.Base.metadata.create_all(bind=motor)

def generar_datos_historicos():
    db: Session = SesionLocal()
    print("--- INICIANDO GENERACIÓN DE DATOS HISTÓRICOS PARA IA ---")

    try:
        # 1. Asegurar que exista un usuario para asociar las transacciones
        usuario = db.query(modelos.Usuario).first()
        if not usuario:
            print("Creando usuario 'admin' por defecto...")
            import seguridad
            usuario = modelos.Usuario(
                nombre_usuario="admin",
                clave_hasheada=seguridad.obtener_clave_hasheada("admin"),
                rol=modelos.RolUsuario.administrador,
                nombre="Admin",
                apellido="Sistema"
            )
            db.add(usuario)
            db.commit()
            db.refresh(usuario)

        # 2. Definir los medicamentos clave para la Demo
        # Formato: (Nombre, Stock Inicial, Media Diaria, Variabilidad)
        lista_meds = [
            {"nombre": "Paracetamol 500mg", "stock": 5000, "media": 50, "var": 10},
            {"nombre": "Ibuprofeno 400mg", "stock": 3000, "media": 30, "var": 15},
            {"nombre": "Amoxicilina 500mg", "stock": 1000, "media": 20, "var": 5},
            {"nombre": "Salbutamol Inhalador", "stock": 200, "media": 5, "var": 2},
            {"nombre": "Losartan 50mg", "stock": 2000, "media": 40, "var": 5}
        ]

        ids_catalogo_para_entrenar = []

        for info in lista_meds:
            # A. Buscar o Crear en Catalogo
            item_cat = db.query(modelos.MedicamentoCatalogo).filter_by(nombre=info["nombre"]).first()
            if not item_cat:
                item_cat = modelos.MedicamentoCatalogo(nombre=info["nombre"], descripcion="Generado por Script IA")
                db.add(item_cat)
                db.commit()
                db.refresh(item_cat)
            
            ids_catalogo_para_entrenar.append(item_cat.id)

            # B. Buscar o Crear Ubicación Física (Necesaria para registrar transacciones)
            med_fisico = db.query(modelos.Medicamento).filter_by(catalogo_id=item_cat.id).first()
            if not med_fisico:
                ubicacion_random = f"{chr(random.randint(65, 90))}-{random.randint(1,99):02d}" # Ej: A-05
                med_fisico = modelos.Medicamento(
                    catalogo_id=item_cat.id,
                    ubicacion=ubicacion_random,
                    lote="LOTE-IA-INIT",
                    fecha_vencimiento=datetime.now().date() + timedelta(days=365),
                    stock_actual=info["stock"],
                    umbral_minimo=100
                )
                db.add(med_fisico)
                db.commit()
                db.refresh(med_fisico)

            # C. GENERAR HISTORIA (Viaje al pasado)
            # Vamos a generar datos para los últimos 180 días (6 meses)
            fecha_inicio = datetime.now() - timedelta(days=180)
            
            print(f"Generando historia para: {info['nombre']}...")
            
            transacciones_a_crear = []
            
            for dias in range(180):
                fecha_actual = fecha_inicio + timedelta(days=dias)
                
                # Simulación de comportamiento inteligente
                cantidad_dia = int(random.gauss(info["media"], info["var"]))
                
                # Reglas de negocio falsas para dar realismo:
                dia_semana = fecha_actual.weekday() # 0=Lunes, 6=Domingo
                
                # Ej: El Ibuprofeno se pide más los lunes (post fin de semana)
                if "Ibuprofeno" in info["nombre"] and dia_semana == 0:
                    cantidad_dia += 15
                
                # Ej: En invierno (aprox dias 150-240 del año) sube la Amoxicilina
                dia_anio = fecha_actual.timetuple().tm_yday
                if "Amoxicilina" in info["nombre"] and 150 < dia_anio < 240:
                    cantidad_dia += 10

                # Asegurar que no sea negativo
                if cantidad_dia < 0: cantidad_dia = 0

                # Crear la transacción simulada
                # Usamos una inserción directa o modelo, pero OJO:
                # SQLAlchemy maneja fechas automáticamente en func.now(), 
                # así que para 'falsificar' la fecha necesitamos pasarla explícitamente.
                # Como tu modelo tiene server_default=func.now(), lo sobreescribimos.
                
                t = modelos.TransaccionInventario(
                    medicamento_id=med_fisico.id,
                    tipo_transaccion=modelos.TipoTransaccion.dispensacion,
                    cantidad=cantidad_dia,
                    usuario_id=usuario.id,
                    motivo="Simulacion IA",
                    fecha_hora=fecha_actual # Aquí está el truco
                )
                db.add(t)
            
            # Guardamos lotes de transacciones para no saturar
            db.commit()

        print("--- HISTORIA GENERADA EXITOSAMENTE ---")
        print("Entrenando modelos de IA ahora...")

        # 3. Entrenar la IA con los datos nuevos
        for cat_id in ids_catalogo_para_entrenar:
            exito = ia.entrenar_modelo_medicamento(db, cat_id)
            estado = "OK" if exito else "FALLO"
            print(f"Modelo ID {cat_id}: {estado}")

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generar_datos_historicos()