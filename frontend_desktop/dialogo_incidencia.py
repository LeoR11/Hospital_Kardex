import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QTextEdit, QPushButton, QMessageBox, 
                             QFormLayout)
from PyQt6.QtCore import Qt

class DialogoIncidencia(QDialog):
    """
    Diálogo para que el operario reporte una falla en un Kardex (K1 o K2).
    """
    def __init__(self, lista_kardex, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reportar Falla de Kardex")
        self.setMinimumWidth(450)

        self.lista_kardex = lista_kardex
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.label_instruccion = QLabel("Seleccione el Kardex con fallas y describa el problema.")
        layout.addWidget(self.label_instruccion)

        self.kardex_combo = QComboBox()
        self.kardex_combo.setMinimumHeight(30)
        
        self.reporte_texto = QTextEdit()
        self.reporte_texto.setMinimumHeight(100)
        self.reporte_texto.setPlaceholderText("Ej. El cajon A05 está atascado")

        form_layout.addRow("Kardex Afectado:", self.kardex_combo)
        form_layout.addRow("Descripcion de la Falla:", self.reporte_texto)
        layout.addLayout(form_layout)

        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_confirmar = QPushButton("Confirmar Reporte")
        btn_confirmar.setDefault(True)
        btn_confirmar.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        btn_confirmar.clicked.connect(self.validar_y_aceptar)
        
        botones_layout.addWidget(btn_cancelar)
        botones_layout.addWidget(btn_confirmar)
        layout.addLayout(botones_layout)

        self.cargar_kardex()

    def cargar_kardex(self):
        self.kardex_combo.addItem("Seleccione un Kardex...", -1)
        for kardex in self.lista_kardex:
            self.kardex_combo.addItem(kardex['nombre'], kardex['id'])

    def validar_y_aceptar(self):
        kardex_id_seleccionado = self.kardex_combo.currentData()
        reporte = self.reporte_texto.toPlainText().strip()

        if kardex_id_seleccionado == -1:
            QMessageBox.warning(self, "Datos incompletos", "Debe seleccionar el Kardex afectado.")
            return

        if not reporte:
            QMessageBox.warning(self, "Datos incompletos", "Debe describir la falla.")
            return
            
        self.accept()

    def obtener_datos(self):
        """
        Devuelve un diccionario listo para enviar como JSON al endpoint
        POST /kardex/reportar-falla/
        """
        return {
            "kardex_id": self.kardex_combo.currentData(),
            "reporte_operario": self.reporte_texto.toPlainText().strip()
        }