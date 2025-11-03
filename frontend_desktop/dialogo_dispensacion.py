import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
                             QFormLayout)
from PyQt6.QtCore import Qt

class DialogoDispensacion(QDialog):
    def __init__(self, token, api_url, receta_id, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = api_url
        self.receta_id = receta_id
        self.medicamentos = {}

        self.setWindowTitle(f"Detalle de Dispensacion - Receta #{receta_id}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # --- mOSTRAR INFO DEL CLIENTE Y FECHA
        info_layout = QFormLayout()
        self.label_paciente = QLabel("Cargando...")
        self.label_fecha = QLabel("Cargando...")
        
        info_layout.addRow("<b>Paciente (RUT):</b>", self.label_paciente)
        info_layout.addRow("<b>Fecha Emisión:</b>", self.label_fecha)
        layout.addLayout(info_layout)
        
        # --- MOSTRAR MEDICAMENTOS ---
        layout.addWidget(QLabel("<b>Medicamentos a Dispensar:</b>"))
        self.tabla_detalles = QTableWidget()
        self.tabla_detalles.setColumnCount(2)
        self.tabla_detalles.setHorizontalHeaderLabels(["Medicamento", "Cantidad a Retirar"])
        self.tabla_detalles.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_detalles.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Tabla de solo lectura
        layout.addWidget(self.tabla_detalles)

        # --- botonoes ---
        botones_layout = QHBoxLayout()
        botones_layout.addStretch() # Empuja los botones a la derecha
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_confirmar = QPushButton("Confirmar Dispensacion")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.clicked.connect(self.accept)
        
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(self.btn_confirmar)
        layout.addLayout(botones_layout)

        self.cargar_datos()

    def cargar_datos(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            resp_meds = requests.get(f"{self.api_url}/medicamentos/", headers=headers)
            if resp_meds.ok:
                for med in resp_meds.json():
                    self.medicamentos[med['id']] = med['nombre']
            
            resp_receta = requests.get(f"{self.api_url}/recetas/{self.receta_id}", headers=headers)
            
            if resp_receta.ok:
                receta = resp_receta.json()

                self.label_paciente.setText(receta['id_paciente'])
                self.label_fecha.setText(receta['fecha_emision'])

                detalles = receta.get('detalles', [])
                self.tabla_detalles.setRowCount(len(detalles))
                for fila, detalle in enumerate(detalles):
                    nombre_medicamento = self.medicamentos.get(detalle['medicamento_id'], "ID Desconocido")
                    self.tabla_detalles.setItem(fila, 0, QTableWidgetItem(nombre_medicamento))
                    self.tabla_detalles.setItem(fila, 1, QTableWidgetItem(str(detalle['cantidad'])))
            else:
                self.btn_confirmar.setDisabled(True)
                QMessageBox.critical(self, "Error", "No se pudieron cargar los detalles de la receta.")
        
        except requests.exceptions.RequestException as e:
            self.btn_confirmar.setDisabled(True)
            QMessageBox.critical(self, "Error de Conexion", f"Error al conectar con la API: {e}")