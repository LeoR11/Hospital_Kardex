import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QFormLayout, QComboBox,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QSize

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

        layout = QVBoxLayout(self)

        # --- Info Paciente/Profesional ---
        info_layout = QFormLayout()
        profesional_nombre = "No asignado"
        if self.receta.get('profesional'):
            profesional_nombre = self.receta['profesional']['nombre']
            
        self.label_paciente = QLabel(self.receta['id_paciente'])
        self.label_fecha = QLabel(self.receta['fecha_emision'])
        self.label_profesional = QLabel(profesional_nombre)
        
        info_layout.addRow("<b>Paciente (RUT):</b>", self.label_paciente)
        info_layout.addRow("<b>Fecha Emision:</b>", self.label_fecha)
        info_layout.addRow("<b>Profesional:</b>", self.label_profesional)
        layout.addLayout(info_layout)
        
        layout.addWidget(QLabel("<b>Seleccione la ubicacion de origen para cada medicamento:</b>"))

        # --- areas de seleccion de ubicaciones ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.layout_items = QFormLayout(scroll_content)
        self.layout_items.setSpacing(15)
        scroll_area.setWidget(scroll_content)
        
        layout.addWidget(scroll_area)

        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_confirmar = QPushButton("Confirmar Dispensacion")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.clicked.connect(self.validar_y_aceptar) 
        
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(self.btn_confirmar)
        layout.addLayout(botones_layout)
        self.cargar_items_receta()

    def _obtener_kardex_id(self, ubicacion_str):
        """Funcion helper para identificar el Kardex basado en la regla del negocio."""
        if not ubicacion_str: return "?"
        letra = ubicacion_str[0].upper()
        if 'A' <= letra <= 'I': return "K1"
        if 'J' <= letra <= 'R': return "K2"
        return "K?" 

    def cargar_items_receta(self):
        detalles_receta = self.receta.get('detalles', [])
        todo_ok = True

        if not detalles_receta:
            todo_ok = False
            self.layout_items.addRow(QLabel("Esta receta no tiene medicamentos asignados."))

        for detalle in detalles_receta:
            catalogo_id = detalle['catalogo_id'] 
            catalogo_nombre = detalle['catalogo']['nombre']
            cantidad_pedida = detalle['cantidad']
            
            label_item = QLabel(f"{catalogo_nombre} (Pedido: {cantidad_pedida})")
            label_item.setStyleSheet("font-weight: bold; color: #212529;")
            
            combo_ubicaciones = QComboBox()
            combo_ubicaciones.setMinimumHeight(30)

            ubicaciones_disponibles = [
                ubic for ubic in self.todas_las_ubicaciones 
                if ubic['catalogo_id'] == catalogo_id
            ]

            if not ubicaciones_disponibles:
                combo_ubicaciones.addItem("¡SIN STOCK EN KARDEX!", -1)
                combo_ubicaciones.setStyleSheet("color: red;")
                todo_ok = False
            else:
                combo_ubicaciones.addItem("Seleccione una ubicacion...", -1)
                for ubic in ubicaciones_disponibles:

                    ubic_str = ubic['ubicacion']
                    kardex_id = self._obtener_kardex_id(ubic_str)
                    texto_opcion = f"{kardex_id} / {ubic_str} (Stock: {ubic['stock_actual']})"
                    
                    combo_ubicaciones.addItem(texto_opcion, ubic['id'])

            self.combos_seleccion.append({
                "combo": combo_ubicaciones,
                "detalle": detalle
            })
            
            self.layout_items.addRow(label_item, combo_ubicaciones)

        if not todo_ok:
            self.btn_confirmar.setDisabled(True)
            self.btn_confirmar.setText("No se puede dispensar")

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
                 QMessageBox.critical(self, "Error de Datos", "La ubicacion seleccionada no se encontró.")
                 return

            if ubicacion_seleccionada['stock_actual'] < cantidad_pedida:
                QMessageBox.warning(self, "Stock Insuficiente", 
                                    f"Stock insuficiente para '{detalle['catalogo']['nombre']}' en la ubicación {ubicacion_seleccionada['ubicacion']}.\n"
                                    f"Pedido: {cantidad_pedida}, Disponible: {ubicacion_seleccionada['stock_actual']}")
                return
            self.mapeo_dispensacion[str(detalle_receta_id)] = medicamento_id_ubicacion
        self.accept()

    def obtener_mapeo(self):
        return self.mapeo_dispensacion