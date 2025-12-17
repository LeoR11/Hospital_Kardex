import requests # type: ignore
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,  # type: ignore
                             QPushButton, QMessageBox, QFormLayout, QComboBox,
                             QScrollArea, QWidget, QRadioButton, QLineEdit,
                             QDateEdit, QButtonGroup, QSpinBox)
from PyQt6.QtCore import Qt, QDate # type: ignore

class _ItemRecepcionWidget(QWidget):
    def __init__(self, detalle_pedido, ubicaciones_compatibles):
        super().__init__()
        self.detalle_pedido = detalle_pedido 
        self.ubicaciones_compatibles = ubicaciones_compatibles 
        
        self.catalogo_nombre = self.detalle_pedido['catalogo']['nombre']
        self.cantidad_recibida = self.detalle_pedido['cantidad']
        self.catalogo_id = self.detalle_pedido['catalogo_id'] 

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        label_titulo = QLabel(f"{self.catalogo_nombre} (Cantidad: {self.cantidad_recibida})")
        label_titulo.setStyleSheet("font-weight: bold; padding: 5px; background-color: #e9ecef;")
        layout.addWidget(label_titulo)

        self.grupo_radios = QButtonGroup(self)
        
        self.radio_existente = QRadioButton("Sumar a ubicacion existente")
        self.radio_nueva = QRadioButton("Crear nueva ubicacion")
        
        self.grupo_radios.addButton(self.radio_existente)
        self.grupo_radios.addButton(self.radio_nueva)
        
        layout.addWidget(self.radio_existente)
        layout.addWidget(self.radio_nueva)

        self.widget_existente = QWidget()
        layout_existente = QVBoxLayout(self.widget_existente)
        layout_existente.setContentsMargins(20, 0, 0, 0)
        self.combo_ubicaciones = QComboBox()
        self.combo_ubicaciones.addItem("Seleccione ubicacion...", -1)
        for u in self.ubicaciones_compatibles:
            texto = f"Ubic: {u['ubicacion']} | Lote: {u['lote']} | Vence: {u['fecha_vencimiento']}"
            self.combo_ubicaciones.addItem(texto, u['id'])
        layout_existente.addWidget(self.combo_ubicaciones)
        
        self.widget_nueva = QWidget()
        layout_nueva = QFormLayout(self.widget_nueva)
        layout_nueva.setContentsMargins(20, 0, 0, 0)
        
        self.input_ubicacion = QLineEdit()
        self.input_lote = QLineEdit()
        self.input_vencimiento = QDateEdit()
        self.input_vencimiento.setDate(QDate.currentDate().addYears(1))
        self.input_vencimiento.setCalendarPopup(True)
        self.input_umbral = QSpinBox()
        self.input_umbral.setRange(0, 1000)
        self.input_umbral.setValue(10)

        layout_nueva.addRow("Ubicacion (Coord):", self.input_ubicacion)
        layout_nueva.addRow("Lote:", self.input_lote)
        layout_nueva.addRow("Vencimiento:", self.input_vencimiento)
        layout_nueva.addRow("Stock Minimo:", self.input_umbral)

        layout.addWidget(self.widget_existente)
        layout.addWidget(self.widget_nueva)

        self.radio_existente.toggled.connect(self.actualizar_visibilidad)
        self.radio_nueva.toggled.connect(self.actualizar_visibilidad)
        
        if self.ubicaciones_compatibles:
            self.radio_existente.setChecked(True)
        else:
            self.radio_existente.setDisabled(True)
            self.radio_nueva.setChecked(True)
            
        self.actualizar_visibilidad()
        
        self.setStyleSheet("border: 1px solid #ced4da; border-radius: 4px; margin-bottom: 5px;")
        self.widget_existente.setStyleSheet("border: none;")
        self.widget_nueva.setStyleSheet("border: none;")

    def actualizar_visibilidad(self):
        self.widget_existente.setVisible(self.radio_existente.isChecked())
        self.widget_nueva.setVisible(self.radio_nueva.isChecked())

    def obtener_item_payload(self):
        if self.radio_existente.isChecked():
            ubic_id = self.combo_ubicaciones.currentData()
            if ubic_id == -1:
                return None
            return {
                "detalle_pedido_id": self.detalle_pedido['id'],
                "accion": "existing",
                "medicamento_id_ubicacion": ubic_id,
                "nueva_ubicacion_data": None
            }
        else:
            ubic = self.input_ubicacion.text().strip()
            lote = self.input_lote.text().strip()
            if not ubic or not lote:
                return None
            
            fecha_venc = self.input_vencimiento.date().toString("yyyy-MM-dd")
            
            return {
                "detalle_pedido_id": self.detalle_pedido['id'],
                "accion": "new",
                "medicamento_id_ubicacion": None,
                "nueva_ubicacion_data": {
                    "catalogo_id": self.catalogo_id, 
                    "ubicacion": ubic,
                    "lote": lote,
                    "fecha_vencimiento": fecha_venc,
                    "stock_actual": 0, 
                    "umbral_minimo": self.input_umbral.value()
                }
            }

class DialogoRecepcion(QDialog):
    def __init__(self, token, api_url, pedido, todas_las_ubicaciones, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.pedido = pedido
        self.todas_las_ubicaciones = todas_las_ubicaciones
        self.payload_final = None

        self.setWindowTitle(f"Recepcionar Pedido #{self.pedido['id']}")
        self.setMinimumWidth(550)
        self.resize(550, 600)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Configure el destino de cada item recibido:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenedor = QWidget()
        self.layout_items = QVBoxLayout(contenedor)
        
        self.widgets_items = []
        for detalle in self.pedido['detalles']:
            cat_id = detalle['catalogo']['id']
            compatibles = [u for u in self.todas_las_ubicaciones if u['catalogo_id'] == cat_id]
            
            widget = _ItemRecepcionWidget(detalle, compatibles)
            self.layout_items.addWidget(widget)
            self.widgets_items.append(widget)

        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

        botones = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_confirmar = QPushButton("Confirmar Recepcion")
        btn_confirmar.setDefault(True)
        btn_confirmar.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;")
        btn_confirmar.clicked.connect(self.validar_y_aceptar)
        
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_confirmar)
        layout.addLayout(botones)

    def validar_y_aceptar(self):
        items_payload = []
        ubicaciones_nuevas_temp = set()

        for w in self.widgets_items:
            data = w.obtener_item_payload()
            if data is None:
                QMessageBox.warning(self, "Datos Incompletos", 
                                    f"Falta informacion para el item '{w.catalogo_nombre}'.\n"
                                    "Seleccione una ubicacion existente o complete los datos de la nueva.")
                return
            
            if data['accion'] == 'new':
                nueva_ubic = data['nueva_ubicacion_data']['ubicacion']
                if nueva_ubic in ubicaciones_nuevas_temp:
                    QMessageBox.warning(self, "Ubicacion Duplicada", 
                                        f"Esta intentando crear la ubicacion '{nueva_ubic}' dos veces en este pedido.")
                    return
                ubicaciones_nuevas_temp.add(nueva_ubic)
                
            items_payload.append(data)

        self.payload_final = {"items": items_payload}
        self.accept()

    def obtener_payload(self):
        return self.payload_final