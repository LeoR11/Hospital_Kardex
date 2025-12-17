from base_de_datos import motor, Base, SesionLocal
import modelos
import seguridad
from datetime import date, timedelta
import random

def poblar_db():
    print("--- INICIANDO PROCESO DE SEEDING (DATOS SEMILLA) ---")
    
    # 1. Crear Tablas
    Base.metadata.drop_all(bind=motor) # OJO: Borra todo lo anterior para empezar limpio
    Base.metadata.create_all(bind=motor)
    print("1. Tablas creadas (Esquema limpio).")

    db = SesionLocal()

    try:
        # 2. Usuarios
        # Admin
        admin = modelos.Usuario(
            nombre_usuario="admin",
            clave_hasheada=seguridad.obtener_clave_hasheada("admin"),
            rol=modelos.RolUsuario.administrador,
            nombre="Administrador",
            apellido="Sistema"
        )
        # Funcionario
        func = modelos.Usuario(
            nombre_usuario="fparra",
            clave_hasheada=seguridad.obtener_clave_hasheada("1234"),
            rol=modelos.RolUsuario.funcionario,
            nombre="Fernando",
            apellido="Parra"
        )
        db.add(admin)
        db.add(func)
        db.commit()
        print("2. Usuarios creados: 'admin' y 'fparra'.")

        # 3. Kardex
        k1 = modelos.Kardex(nombre="Kardex 1 (A-I)", identificador="K1", estado=modelos.EstadoKardex.operativo)
        k2 = modelos.Kardex(nombre="Kardex 2 (J-Z)", identificador="K2", estado=modelos.EstadoKardex.operativo)
        db.add(k1)
        db.add(k2)
        db.commit()
        print("3. Equipos Kardex inicializados.")

        # 4. Profesionales
        profs = [
            modelos.Profesional(nombre="Dr. Gregory House", run="11.111.111-1", profesion="Diagnosta"),
            modelos.Profesional(nombre="Dra. Meredith Grey", run="22.222.222-2", profesion="Cirujana"),
            modelos.Profesional(nombre="Dr. Shaun Murphy", run="33.333.333-3", profesion="Cirujano")
        ]
        db.add_all(profs)
        db.commit()
        print("4. Profesionales medicos registrados.")

        # 5. Catalogo de Medicamentos
        items_catalogo = [
            {"nombre": "Paracetamol 500mg", "desc": "Analgesico y antipiretico"},
            {"nombre": "Ibuprofeno 400mg", "desc": "Antiinflamatorio no esteroideo"},
            {"nombre": "Amoxicilina 500mg", "desc": "Antibiotico de amplio espectro"},
            {"nombre": "Omeprazol 20mg", "desc": "Inhibidor de bomba de protones"},
            {"nombre": "Ketorolaco 30mg", "desc": "Analgesico potente (inyectable)"}
        ]
        
        objs_catalogo = []
        for i in items_catalogo:
            obj = modelos.MedicamentoCatalogo(nombre=i["nombre"], descripcion=i["desc"])
            db.add(obj)
            objs_catalogo.append(obj)
        db.commit() # Commit para obtener IDs
        
        print("5. Catalogo maestro cargado.")

        # 6. Inventario Fisico (Stock Inicial)
        # Vamos a crear stock variado para probar escenarios
        
        # Paracetamol: Mucho stock (Varias ubicaciones)
        stock_paracetamol_1 = modelos.Medicamento(
            catalogo_id=objs_catalogo[0].id, # Paracetamol
            ubicacion="A-01-01",
            lote="L-PARA-2024",
            fecha_vencimiento=date.today() + timedelta(days=365),
            stock_actual=500,
            umbral_minimo=100
        )
        stock_paracetamol_2 = modelos.Medicamento(
            catalogo_id=objs_catalogo[0].id,
            ubicacion="A-01-02",
            lote="L-PARA-2025",
            fecha_vencimiento=date.today() + timedelta(days=700),
            stock_actual=300,
            umbral_minimo=100
        )

        # Ibuprofeno: Stock medio
        stock_ibuprofeno = modelos.Medicamento(
            catalogo_id=objs_catalogo[1].id, # Ibuprofeno
            ubicacion="B-05-10",
            lote="L-IBU-EXP",
            fecha_vencimiento=date.today() + timedelta(days=120),
            stock_actual=150,
            umbral_minimo=50
        )

        # Amoxicilina: Stock CRITICO (Para probar alertas y Pedidos)
        stock_amoxi = modelos.Medicamento(
            catalogo_id=objs_catalogo[2].id, 
            ubicacion="C-02-01",
            lote="L-AMOX-LOW",
            fecha_vencimiento=date.today() + timedelta(days=60),
            stock_actual=15, # Muy bajo
            umbral_minimo=50
        )

        db.add(stock_paracetamol_1)
        db.add(stock_paracetamol_2)
        db.add(stock_ibuprofeno)
        db.add(stock_amoxi)
        
        # Agregar los otros vacios o con poco stock
        db.commit()
        print("6. Inventario fisico inicializado (Incluye casos de Stock Critico).")

        print("\n--- BASE DE DATOS CREADA Y POBLADA EXITOSAMENTE ---")
        print("Ya puedes iniciar el backend (main.py) y probar el sistema.")

    except Exception as e:
        print(f"ERROR DURANTE EL SEEDING: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    poblar_db()