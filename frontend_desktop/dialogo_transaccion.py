import requests # type: ignore
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,  # type: ignore
                             QComboBox, QLineEdit, QPushButton, QMessageBox, 
                             QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt # type: ignore

class DialogoTransaccion(QDialog):
    def __init__(self, token, api_url, tipo_transaccion, todas_las_ubicaciones, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.tipo_transaccion = tipo_transaccion
        self.todas_las_ubicaciones = todas_las_ubicaciones
        self.medicamento_id_seleccionado = -1 

        titulo = "Registrar Devolucion" if tipo_transaccion == "devolucion" else "Registrar Reposicion a Servicio"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.medicamento_combo = QComboBox()
        self.medicamento_combo.setMinimumHeight(30)
        self.cantidad_spinbox = QSpinBox()
        self.cantidad_spinbox.setMinimumHeight(30)
        self.cantidad_spinbox.setRange(1, 9999)
        self.motivo_input = QLineEdit()
        self.motivo_input.setMinimumHeight(30)
        if tipo_transaccion == "devolucion":
            self.motivo_input.setPlaceholderText("Ej. Paciente dado de alta")
        else:
            self.motivo_input.setPlaceholderText("Ej. Reposicion de urgencia a sala")

        form_layout.addRow("Medicamento (Ubicacion):", self.medicamento_combo)
        form_layout.addRow("Cantidad:", self.cantidad_spinbox)
        form_layout.addRow("Motivo:", self.motivo_input)
        
        layout.addLayout(form_layout)

        botones_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_confirmar = QPushButton("Confirmar Transaccion")
        btn_confirmar.setDefault(True)
        btn_confirmar.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;")
        btn_confirmar.clicked.connect(self.validar_y_aceptar)
        
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(btn_confirmar)
        layout.addLayout(botones_layout)

        self.crear_combo_medicamentos()

    def crear_combo_medicamentos(self):
        self.medicamento_combo.addItem("Seleccione una ubicacion...", -1)
        for m in self.todas_las_ubicaciones:
            nombre_cat = m['catalogo']['nombre'] if m.get('catalogo') else "Sin Nombre"
            texto = f"{nombre_cat} - {m['ubicacion']} (Stock: {m['stock_actual']})"
            self.medicamento_combo.addItem(texto, m['id'])

    def validar_y_aceptar(self):
        self.medicamento_id_seleccionado = self.medicamento_combo.currentData()
        
        if self.medicamento_id_seleccionado == -1:
            QMessageBox.warning(self, "Error", "Debe seleccionar una ubicacion de medicamento.")
            return
        
        if not self.motivo_input.text().strip():
             QMessageBox.warning(self, "Error", "Debe ingresar un motivo para la transaccion.")
             return
        
        if self.tipo_transaccion != "devolucion":
            cantidad_a_restar = self.cantidad_spinbox.value()
            ubicacion_seleccionada = next(
                (u for u in self.todas_las_ubicaciones if u['id'] == self.medicamento_id_seleccionado), 
                None
            )
            if ubicacion_seleccionada and ubicacion_seleccionada['stock_actual'] < cantidad_a_restar:
                QMessageBox.warning(self, "Stock Insuficiente", 
                    f"No hay stock suficiente en la ubicacion '{ubicacion_seleccionada['ubicacion']}'.\n"
                    f"Solicitado: {cantidad_a_restar}, Disponible: {ubicacion_seleccionada['stock_actual']}")
                return

        self.accept() 

    def obtener_datos(self):
        cantidad = self.cantidad_spinbox.value()
        
        if self.tipo_transaccion != "devolucion":
            cantidad = -abs(cantidad)
        else:
            cantidad = abs(cantidad)

        return {
            "tipo_transaccion": self.tipo_transaccion,
            "medicamento_id": self.medicamento_id_seleccionado,
            "cantidad": cantidad,
            "motivo": self.motivo_input.text()
        }