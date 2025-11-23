import requests
from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.token = None
        self.setWindowTitle("Iniciar Sesion - Sistema Kardex")
        self.setFixedSize(380, 250)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
                font-family: Arial;
            }
            QLabel#titulo_label {
                font-size: 14px;
                color: #555;
                margin-bottom: 15px;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                color: #000000; 
            }
            QPushButton {
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#btn_ingresar {
                background-color: #0d6efd;
                color: white;
            }
            QPushButton#btn_ingresar:hover {
                background-color: #0b5ed7;
            }
            QPushButton#btn_cancelar {
                background-color: #e9ecef;
                border: 1px solid #ccc;
                color: #333;
            }
        """)

        layout_principal = QVBoxLayout()
        layout_principal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        titulo = QLabel("Ingrese sus credenciales para acceder")
        titulo.setObjectName("titulo_label")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.usuario_input = QLineEdit()
        self.usuario_input.setPlaceholderText("Usuario")
        
        self.clave_input = QLineEdit()
        self.clave_input.setPlaceholderText("Contraseña")
        self.clave_input.setEchoMode(QLineEdit.EchoMode.Password)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_cancelar")
        btn_cancelar.clicked.connect(self.close)

        btn_ingresar = QPushButton("INGRESAR")
        btn_ingresar.setObjectName("btn_ingresar")
        btn_ingresar.clicked.connect(self.iniciar_sesion)
        
        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(btn_ingresar)

        layout_principal.addWidget(titulo)
        layout_principal.addWidget(self.usuario_input)
        layout_principal.addWidget(self.clave_input)
        layout_principal.addSpacing(15)
        layout_principal.addLayout(layout_botones)

        self.setLayout(layout_principal)

    def iniciar_sesion(self):
        url_api = "http://127.0.0.1:8000/token"
        usuario = self.usuario_input.text()
        clave = self.clave_input.text()
        if not usuario or not clave:
            QMessageBox.warning(self, "Error", "El nombre de usuario y la contraseña son obligatorios.")
            return
        try:
            datos = {'username': usuario, 'password': clave}
            respuesta = requests.post(url_api, data=datos)
            if respuesta.status_code == 200:
                self.token = respuesta.json()['access_token']
                self.accept()
            else:
                error = respuesta.json().get('detail', 'Credenciales incorrectas')
                QMessageBox.critical(self, "Error de Autenticación", error)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")
    
    def accept(self):
        self.close()