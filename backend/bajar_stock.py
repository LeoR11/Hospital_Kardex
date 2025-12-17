# backend/bajar_stock.py
from base_de_datos import SesionLocal
import modelos

def sabotear_stock():
    db = SesionLocal()
    print("--- INICIANDO SABOTAJE DE STOCK (Para forzar alertas IA) ---")

    # Lista de victimas para bajarles el stock
    # (Nombre del catalogo, Nuevo stock bajo)
    objetivos = [
        ("Paracetamol 500mg", 50),   # La IA espera vender ~350, si pones 50 -> CRITICO
        ("Amoxicilina 500mg", 10),   # La IA espera vender ~140 -> CRITICO
        ("Ibuprofeno 400mg", 200)    # La IA espera vender ~210 -> BAJO (Amarillo)
    ]

    for nombre_med, nuevo_stock in objetivos:
        # 1. Buscar el ID del catalogo
        catalogo = db.query(modelos.MedicamentoCatalogo).filter(
            modelos.MedicamentoCatalogo.nombre.like(f"%{nombre_med}%")
        ).first()

        if catalogo:
            # 2. Buscar la caja fisica y actualizar stock
            med_fisico = db.query(modelos.Medicamento).filter_by(catalogo_id=catalogo.id).first()
            if med_fisico:
                print(f"Bajando stock de {nombre_med} de {med_fisico.stock_actual} a {nuevo_stock}...")
                med_fisico.stock_actual = nuevo_stock
                db.add(med_fisico)
            else:
                print(f"No encontre ubicacion fisica para {nombre_med}")
        else:
            print(f"No encontre en catalogo: {nombre_med}")

    db.commit()
    db.close()
    print("--- SABOTAJE COMPLETADO: Ahora la IA deberia pedir compra. ---")

if __name__ == "__main__":
    sabotear_stock()