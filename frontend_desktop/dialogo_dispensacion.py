import requests # type: ignore
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,  # type: ignore
                             QPushButton, QMessageBox, QFormLayout, QComboBox,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QSize # type: ignore

class DialogoDispensacion(QDialog):
    def __init__(self, token, api_url, receta, todas_las_ubicaciones, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.receta = receta 
        self.todas_las_ubicaciones = todas_las_ubicaciones

        self.mapeo_dispensacion = {} 
        self.combos_seleccion = [] 

        self.setWindowTitle(f"Confirmar Dispensacion - Receta #{self.receta['id']}")
        self.setMinimumWidth(600)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        info_layout = QFormLayout()
        
        nombre_paciente = "Desconocido"
        if self.receta.get('paciente'):
            p = self.receta['paciente']
            nombre_paciente = f"{p['run']} - {p['nombre']} {p['apellido']}"
        
        self.label_paciente = QLabel(nombre_paciente)
        self.label_paciente.setStyleSheet("font-weight: bold;")
        
        self.label_profesional = QLabel("Sin informacion")
        if self.receta.get('profesional'):
            prof = self.receta['profesional']
            self.label_profesional.setText(prof['nombre'])

        info_layout.addRow("Paciente:", self.label_paciente)
        info_layout.addRow("Profesional:", self.label_profesional)
        info_layout.addRow("Fecha:", QLabel(self.receta['fecha_emision']))
        
        layout.addLayout(info_layout)
        layout.addWidget(QLabel("Asignacion de Lotes y Ubicaciones:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.contenedor_items = QWidget()
        self.layout_items = QVBoxLayout(self.contenedor_items)
        
        self.crear_campos_items()
        
        scroll.setWidget(self.contenedor_items)
        layout.addWidget(scroll)

        botones_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_confirmar = QPushButton("Confirmar Dispensacion")
        btn_confirmar.setDefault(True)
        btn_confirmar.setStyleSheet("background-color: #198754; color: white; font-weight: bold;")
        btn_confirmar.clicked.connect(self.validar_y_aceptar)
        
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(btn_confirmar)
        layout.addLayout(botones_layout)

    def crear_campos_items(self):
        detalles = self.receta.get('detalles', [])
        
        for detalle in detalles:
            catalogo = detalle['catalogo']
            cantidad_pedida = detalle['cantidad']
            
            item_widget = QWidget()
            item_widget.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; margin-bottom: 5px;")
            h_layout = QHBoxLayout(item_widget)
            
            info_label = QLabel(f"{catalogo['nombre']}\n(Cant: {cantidad_pedida})")
            info_label.setFixedWidth(200)
            
            combo_ubicacion = QComboBox()
            combo_ubicacion.addItem("Seleccione ubicacion...", -1)
            
            ubicaciones_compatibles = [
                u for u in self.todas_las_ubicaciones 
                if u['catalogo_id'] == catalogo['id'] and u['stock_actual'] > 0
            ]
            
            for u in ubicaciones_compatibles:
                texto_item = f"Ubic: {u['ubicacion']} | Lote: {u['lote']} | Stock: {u['stock_actual']} | Vence: {u['fecha_vencimiento']}"
                combo_ubicacion.addItem(texto_item, u['id'])
            
            h_layout.addWidget(info_label)
            h_layout.addWidget(combo_ubicacion)
            
            self.layout_items.addWidget(item_widget)
            
            self.combos_seleccion.append({
                "combo": combo_ubicacion,
                "detalle": detalle,
                "requerido": cantidad_pedida
            })

    def validar_y_aceptar(self):
        self.mapeo_dispensacion = {}
        
        for item in self.combos_seleccion:
            combo = item['combo']
            detalle = item['detalle']
            
            medicamento_id_ubicacion = combo.currentData() 
            detalle_receta_id = detalle['id'] 
            cantidad_pedida = detalle['cantidad']
            
            if medicamento_id_ubicacion == -1:
                QMessageBox.warning(self, "Seleccion Incompleta", 
                                    f"Debe seleccionar una ubicacion de origen para '{detalle['catalogo']['nombre']}'.")
                return 

            ubicacion_seleccionada = next(
                (u for u in self.todas_las_ubicaciones if u['id'] == medicamento_id_ubicacion), 
                None
            )
            
            if not ubicacion_seleccionada:
                 QMessageBox.critical(self, "Error de Datos", "La ubicacion seleccionada no se encontro.")
                 return

            if ubicacion_seleccionada['stock_actual'] < cantidad_pedida:
                QMessageBox.warning(self, "Stock Insuficiente", 
                                    f"Stock insuficiente para '{detalle['catalogo']['nombre']}' en la ubicacion {ubicacion_seleccionada['ubicacion']}.\n"
                                    f"Pedido: {cantidad_pedida}, Disponible: {ubicacion_seleccionada['stock_actual']}")
                return
            
            self.mapeo_dispensacion[str(detalle_receta_id)] = medicamento_id_ubicacion
            
        self.accept()

    def obtener_mapeo(self):
        return self.mapeo_dispensacion