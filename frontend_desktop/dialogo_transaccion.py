import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QLineEdit, QPushButton, QMessageBox, 
                             QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt

class DialogoTransaccion(QDialog):
    def __init__(self, token, api_url, tipo_transaccion, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.tipo_transaccion = tipo_transaccion
        self.medicamentos = []

        titulo = "Registrar Devolucion" if tipo_transaccion == "devolucion" else "Registrar Reposicion a Servicio"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.medicamento_combo = QComboBox()
        self.cantidad_spinbox = QSpinBox()
        self.cantidad_spinbox.setRange(1, 9999)
        self.motivo_input = QLineEdit()

        form_layout.addRow("Medicamento:", self.medicamento_combo)
        form_layout.addRow("Cantidad:", self.cantidad_spinbox)
        form_layout.addRow("Motivo:", self.motivo_input)
        layout.addLayout(form_layout)

        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_confirmar = QPushButton("Confirmar")
        btn_confirmar.setDefault(True)
        btn_confirmar.clicked.connect(self.accept)
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(btn_confirmar)
        layout.addLayout(botones_layout)

        self.cargar_medicamentos()

    def cargar_medicamentos(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            resp_med = requests.get(f"{self.api_url}/medicamentos/", headers=headers)
            if resp_med.ok:
                self.medicamentos = resp_med.json()
                for m in self.medicamentos:
                    self.medicamento_combo.addItem(m['nombre'], m['id'])
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudieron cargar los medicamentos: {e}")

    def obtener_datos(self):
        cantidad = self.cantidad_spinbox.value()
        if self.tipo_transaccion != "devolucion":
            cantidad = -cantidad

        return {
            "tipo_transaccion": self.tipo_transaccion,
            "medicamento_id": self.medicamento_combo.currentData(),
            "cantidad": cantidad,
            "motivo": self.motivo_input.text()
        }