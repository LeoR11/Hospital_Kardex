from base_de_datos import motor, Base, SesionLocal
import modelos

print("Creando la base de datos y las tablas...")

# Esto crea todas las tablas
Base.metadata.create_all(bind=motor)

print("Base de datos y tablas creadas exitosamente.")
print("Verificando/Poblando la tabla Kardex...")

#sesion temporal (para probar)
db = SesionLocal()

try:
    # 1 virifica si k1 existe
    k1_existe = db.query(modelos.Kardex).filter(modelos.Kardex.identificador == "K1").first()
    if not k1_existe:
        k1 = modelos.Kardex(
            nombre="Kardex 1 (Ubicaciones A-I)",
            identificador="K1",
            estado=modelos.EstadoKardex.operativo # Estado inicial
        )
        db.add(k1)
        print("Kardex 1 creado.")
    else:
        print("Kardex 1 ya existe.")

    # 2 verifica si k2 existe
    k2_existe = db.query(modelos.Kardex).filter(modelos.Kardex.identificador == "K2").first()
    if not k2_existe:
        k2 = modelos.Kardex(
            nombre="Kardex 2 (Ubicaciones J-R)",
            identificador="K2",
            estado=modelos.EstadoKardex.operativo # Estado inicial
        )
        db.add(k2)
        print("Kardex 2 creado.")
    else:
        print("Kardex 2 ya existe.")

    # 3guarda los cambios
    db.commit()
    print("Tabla Kardex verificada exitosamente.")

except Exception as e:
    print(f"Error al poblar la tabla Kardex: {e}")
    db.rollback()
finally:
    db.close()
