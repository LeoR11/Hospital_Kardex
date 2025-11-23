import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QFormLayout, QComboBox,
                             QScrollArea, QWidget, QRadioButton, QLineEdit,
                             QDateEdit, QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QDate
from datetime import date


class _ItemRecepcionWidget(QWidget):
    """
    Un widget que maneja la logica para 1 solo item del pedido.
    (ej. 100 unidades de "Paracetamol 500mg")
    """
    def __init__(self, detalle_pedido, ubicaciones_compatibles):
        super().__init__()
        self.detalle_pedido = detalle_pedido 
        self.ubicaciones_compatibles = ubicaciones_compatibles 
        
        self.catalogo_nombre = self.detalle_pedido['catalogo']['nombre']
        self.cantidad_recibida = self.detalle_pedido['cantidad']
        self.catalogo_id = self.detalle_pedido['catalogo_id'] 

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label_titulo = QLabel(f"<b>{self.catalogo_nombre}</b> (Cantidad a recibir: {self.cantidad_recibida})")
        label_titulo.setStyleSheet("font-size: 16px; padding: 5px; background-color: #f0f0f0; border-radius: 4px; color: #212529;")
        layout.addWidget(label_titulo)

        self.radio_existente = QRadioButton("1. Sumar a ubicacion existente")
        self.radio_nuevo = QRadioButton("2. Crear nueva ubicacion")
        layout_radios = QHBoxLayout()
        layout_radios.addWidget(self.radio_existente)
        layout_radios.addWidget(self.radio_nuevo)
        layout.addLayout(layout_radios)


        self.stack = QStackedWidget()
        self.widget_existente = QWidget()
        self.widget_nuevo = QWidget()
        
        self.stack.addWidget(self.widget_existente)
        self.stack.addWidget(self.widget_nuevo)
        layout.addWidget(self.stack)

  
        layout_existente = QFormLayout(self.widget_existente)
        self.combo_ubicaciones_existentes = QComboBox()
        self.combo_ubicaciones_existentes.setMinimumHeight(30)
        self.combo_ubicaciones_existentes.addItem("Seleccione ubicacion...", -1)
        if not self.ubicaciones_compatibles:
            self.radio_existente.setDisabled(True)
            self.radio_existente.setText("1. (No hay ubicaciones existentes para este item)")
        else:
            for ubic in self.ubicaciones_compatibles:
                ubic_str = ubic['ubicacion']
                kardex_id = self._obtener_kardex_id(ubic_str)
                texto = f"{kardex_id} / {ubic_str} (Stock actual: {ubic['stock_actual']})"
                
                self.combo_ubicaciones_existentes.addItem(texto, ubic['id'])
        layout_existente.addRow("Ubicacion de destino:", self.combo_ubicaciones_existentes)
        
        layout_nuevo = QFormLayout(self.widget_nuevo)
        self.line_ubicacion = QLineEdit()
        self.line_ubicacion.setMinimumHeight(30)
        self.line_ubicacion.setPlaceholderText("Ej. A06, K15")
        self.line_lote = QLineEdit()
        self.line_lote.setMinimumHeight(30)
        self.line_vencimiento = QDateEdit()
        self.line_vencimiento.setMinimumHeight(30)
        self.line_vencimiento.setCalendarPopup(True)
        self.line_vencimiento.setDate(QDate.currentDate().addYears(1))
        self.line_vencimiento.setMinimumDate(QDate.currentDate())
        self.line_umbral = QLineEdit("10")
        self.line_umbral.setMinimumHeight(30)

        layout_nuevo.addRow("Nueva Ubicacion (A01-R99):", self.line_ubicacion)
        layout_nuevo.addRow("Lote:", self.line_lote)
        layout_nuevo.addRow("Fecha Vencimiento:", self.line_vencimiento)
        layout_nuevo.addRow("Umbral Minimo:", self.line_umbral)

        self.radio_existente.toggled.connect(self.actualizar_interfaz)
        
        if self.ubicaciones_compatibles:
            self.radio_existente.setChecked(True)
        else:
            self.radio_nuevo.setChecked(True)
        self.actualizar_interfaz()

    def _obtener_kardex_id(self, ubicacion_str):
        """Funcion helper para identificar el Kardex basado en la regla del negocio."""
        if not ubicacion_str: return "?"
        letra = ubicacion_str[0].upper()
        if 'A' <= letra <= 'I': return "K1"
        if 'J' <= letra <= 'R': return "K2"
        return "K?"

    def actualizar_interfaz(self):
        if self.radio_existente.isChecked():
            self.stack.setCurrentIndex(0) 
        else:
            self.stack.setCurrentIndex(1) 

    def obtener_item_payload(self):
        """
        Valida los datos de este widget y devuelve el diccionario 
        para el payload final (esquemas.RecepcionItem).
        """
        detalle_pedido_id = self.detalle_pedido['id']

        if self.radio_existente.isChecked():
            medicamento_id_ubicacion = self.combo_ubicaciones_existentes.currentData()
            if medicamento_id_ubicacion == -1:
                QMessageBox.warning(self, "Error de Validacion",
                    f"Para '{self.catalogo_nombre}', debe seleccionar una ubicacion existente.")
                return None
            
            return {
                "detalle_pedido_id": detalle_pedido_id,
                "accion": "existing",
                "medicamento_id_ubicacion": medicamento_id_ubicacion,
                "nueva_ubicacion_data": None
            }

        elif self.radio_nuevo.isChecked():
            ubicacion = self.line_ubicacion.text().strip().upper()
            lote = self.line_lote.text().strip()
            fecha_vencimiento_str = self.line_vencimiento.date().toString("yyyy-MM-dd")
            umbral_str = self.line_umbral.text().strip()

            if not ubicacion or not lote or not umbral_str:
                QMessageBox.warning(self, "Error de Validacion",
                    f"Para '{self.catalogo_nombre}', debe completar todos los campos de la nueva ubicacion.")
                return None

            if not (len(ubicacion) > 1 and 'A' <= ubicacion[0] <= 'R' and ubicacion[1:].isdigit() and len(ubicacion) <= 5):
                QMessageBox.warning(self, "Error de Formato",
                    f"Para '{self.catalogo_nombre}', la ubicación '{ubicacion}' es invalida. "
                    "Debe ser una letra (A-R) seguida de numeros (ej. A01, C23, K10).")
                return None

            try:
                umbral = int(umbral_str)
            except ValueError:
                QMessageBox.warning(self, "Error de Validacion",
                    f"Para '{self.catalogo_nombre}', el umbral minimo debe ser un numero.")
                return None

            return {
                "detalle_pedido_id": detalle_pedido_id,
                "accion": "new",
                "medicamento_id_ubicacion": None,
                "nueva_ubicacion_data": {
                    "catalogo_id": self.catalogo_id, 
                    "ubicacion": ubicacion,
                    "lote": lote,
                    "fecha_vencimiento": fecha_vencimiento_str,
                    "stock_actual": self.cantidad_recibida, 
                    "umbral_minimo": umbral
                }
            }
        return None

class DialogoRecepcion(QDialog):
    def __init__(self, token, api_url, pedido_obj, todas_las_ubicaciones, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.pedido = pedido_obj
        self.todas_las_ubicaciones = todas_las_ubicaciones
        self.item_widgets = []
        self.payload_final = None

        self.setWindowTitle(f"Recepcionar Pedido #{self.pedido['id']}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        label_titulo = QLabel(f"<b>Pedido:</b> {self.pedido['descripcion']}")
        label_titulo.setStyleSheet("font-size: 18px; color: #212529;")
        layout.addWidget(label_titulo)
        layout.addWidget(QLabel("Asigne una ubicacion de destino para cada item del pedido:"))


        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        layout_scroll = QVBoxLayout(scroll_content)
        layout_scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_content)
        
        layout.addWidget(scroll_area)
   
        detalles_pedido = self.pedido.get('detalles', [])
        if not detalles_pedido:
             layout_scroll.addWidget(QLabel("Este pedido no tiene items."))
        else:
            for detalle in detalles_pedido:
                if not detalle.get('catalogo'): continue 
                
                catalogo_id = detalle['catalogo_id']
                
                ubicaciones_compatibles = [
                    ubic for ubic in self.todas_las_ubicaciones
                    if ubic['catalogo_id'] == catalogo_id
                ]
                
                item_widget = _ItemRecepcionWidget(detalle, ubicaciones_compatibles)
                layout_scroll.addWidget(item_widget)
                self.item_widgets.append(item_widget) 

        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_confirmar = QPushButton("Confirmar Recepcion")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.clicked.connect(self.validar_y_aceptar)
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(self.btn_confirmar)
        layout.addLayout(botones_layout)
        
        if not detalles_pedido:
            self.btn_confirmar.setDisabled(True)

    def validar_y_aceptar(self):
        items_payload = []
        
        for widget in self.item_widgets:
            payload_item = widget.obtener_item_payload()
            
            if payload_item is None:
                return 
            
            items_payload.append(payload_item)

        ubicaciones_nuevas = set()
        for item in items_payload:
            if item['accion'] == 'new':
                ubic_str = item['nueva_ubicacion_data']['ubicacion']
                if ubic_str in ubicaciones_nuevas:
                    QMessageBox.warning(self, "Error de Duplicado",
                        f"La ubicacion '{ubic_str}' se ha asignado mas de una vez en este mismo pedido.\n"
                        "Por favor, asigne cada nuevo item a una ubicación unica.")
                    return
                ubicaciones_nuevas.add(ubic_str)

        self.payload_final = {"items": items_payload}
        self.accept()

    def obtener_payload(self):
        return self.payload_final