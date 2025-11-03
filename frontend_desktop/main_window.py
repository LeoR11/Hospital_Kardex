import sys
import requests
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from dialogo_dispensacion import DialogoDispensacion
from dialogo_transaccion import DialogoTransaccion

class VentanaPrincipal(QMainWindow):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.api_url = "http://127.0.0.1:8000"
        self.setWindowTitle("Sistema de Gestion Kardex Hospital")
        self.setGeometry(100, 100, 1100, 700)
        self.todos_los_medicamentos = []

        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QWidget#panel_navegacion {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }
            QPushButton.nav-button {
                background-color: transparent;
                border: none;
                color: #495057;
                padding: 15px 20px;
                text-align: left;
                font-size: 16px;
                font-family: Arial;
            }
            QPushButton.nav-button:hover { background-color: #e9ecef; }
            QPushButton.nav-button:checked {
                background-color: #005A9C;
                color: white;
                font-weight: bold;
            }
            QLabel.titulo-contenido {
                font-size: 28px;
                font-weight: bold;
                color: #212529;
                margin-bottom: 20px;
            }
            QWidget#tarjeta_recetas {
                background-color: #0d6efd;
                border-radius: 8px;
                min-height: 120px;
                max-height: 120px;
                min-width: 250px;
            }
            QWidget#tarjeta_stock {
                background-color: #dc3545;
                border-radius: 8px;
                min-height: 120px;
                max-height: 120px;
                min-width: 250px;
            }
            QLabel.contador-numero {
                font-size: 42px;
                font-weight: bold;
                color: #ffffff;
            }
            QLabel.contador-label {
                font-size: 16px;
                color: #f8f9fa;
            }
            QLineEdit#busqueda_input {
                padding: 8px; border: 1px solid #ccc; border-radius: 4px;
                font-size: 14px; max-width: 300px;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                font-size: 14px;
                gridline-color: #dee2e6;
                background-color: #ffffff;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                color: #212529; 
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                padding: 12px;
                border: none;
                font-weight: bold;
                color: #495057;
            }
            QPushButton.btn-accion {
                background-color: #198754; color: white; border: none;
                border-radius: 4px; padding: 5px 10px; font-weight: bold;
            }
            QPushButton.btn-accion:hover { background-color: #146c43; }
            QPushButton#btn_devolucion { background-color: #0d6efd; color: white; padding: 8px 12px; font-weight: bold; border-radius: 4px; }
            QPushButton#btn_reposicion { background-color: #ffc107; color: #000; padding: 8px 12px; font-weight: bold; border-radius: 4px; }
        """)

        widget_central = QWidget()
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        panel_navegacion = QWidget()
        panel_navegacion.setObjectName("panel_navegacion")
        panel_navegacion.setFixedWidth(220)
        layout_navegacion = QVBoxLayout(panel_navegacion)
        layout_navegacion.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.btn_panel = QPushButton("Panel Principal")
        self.btn_recetas = QPushButton("Recetas")
        self.btn_inventario = QPushButton("Inventario")
        self.btn_pedidos = QPushButton("Pedidos")
        botones = [self.btn_panel, self.btn_recetas, self.btn_inventario, self.btn_pedidos]
        for boton in botones:
            boton.setCheckable(True)
            boton.setAutoExclusive(True)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setObjectName("nav-button")
            layout_navegacion.addWidget(boton)
        panel_contenido = QWidget()
        layout_contenido = QVBoxLayout(panel_contenido)
        layout_contenido.setContentsMargins(40, 40, 40, 40)
        self.paginas = QStackedWidget()
        layout_contenido.addWidget(self.paginas)
        
        self.pagina_panel = self.crear_pagina_panel_principal()
        self.pagina_recetas = self.crear_pagina_recetas()
        self.pagina_inventario = self.crear_pagina_inventario()
        self.pagina_pedidos = self.crear_pagina_pedidos()
        
        self.paginas.addWidget(self.pagina_panel)
        self.paginas.addWidget(self.pagina_recetas)
        self.paginas.addWidget(self.pagina_inventario)
        self.paginas.addWidget(self.pagina_pedidos)
        
        self.btn_panel.clicked.connect(self.actualizar_vista_panel)
        self.btn_recetas.clicked.connect(self.actualizar_vista_recetas)
        self.btn_inventario.clicked.connect(self.actualizar_vista_inventario)
        self.btn_pedidos.clicked.connect(self.actualizar_vista_pedidos)
        
        layout_principal.addWidget(panel_navegacion)
        layout_principal.addWidget(panel_contenido)
        self.setCentralWidget(widget_central)
        
        self.btn_panel.setChecked(True)
        self.actualizar_vista_panel()

    def crear_pagina_simple(self, titulo):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        label_titulo = QLabel(titulo)
        label_titulo.setObjectName("titulo-contenido")
        layout.addWidget(label_titulo)
        return pagina
    
    def crear_pagina_panel_principal(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        titulo = QLabel("Panel Principal")
        titulo.setObjectName("titulo-contenido")
        layout.addWidget(titulo)
        layout_tarjetas = QHBoxLayout()
        layout_tarjetas.setSpacing(20)
        tarjeta_recetas = QWidget()
        tarjeta_recetas.setObjectName("tarjeta_recetas")
        layout_tarjeta1 = QVBoxLayout(tarjeta_recetas)
        layout_tarjeta1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_recetas_numero = QLabel("...")
        self.label_recetas_numero.setObjectName("contador-numero")
        self.label_recetas_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_recetas_texto = QLabel("Recetas Pendientes")
        label_recetas_texto.setObjectName("contador-label")
        label_recetas_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_tarjeta1.addWidget(self.label_recetas_numero)
        layout_tarjeta1.addWidget(label_recetas_texto)
        tarjeta_stock = QWidget()
        tarjeta_stock.setObjectName("tarjeta_stock")
        layout_tarjeta2 = QVBoxLayout(tarjeta_stock)
        layout_tarjeta2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_stock_numero = QLabel("...")
        self.label_stock_numero.setObjectName("contador-numero")
        self.label_stock_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_stock_texto = QLabel("Medicamentos con Stock Bajo")
        label_stock_texto.setObjectName("contador-label")
        label_stock_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_tarjeta2.addWidget(self.label_stock_numero)
        layout_tarjeta2.addWidget(label_stock_texto)
        layout_tarjetas.addWidget(tarjeta_recetas)
        layout_tarjetas.addWidget(tarjeta_stock)
        layout_tarjetas.addStretch()
        layout.addLayout(layout_tarjetas)
        layout.addStretch()
        return pagina

    def crear_pagina_inventario(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        header_layout = QHBoxLayout()
        label_titulo = QLabel("Gestion de Inventario")
        label_titulo.setObjectName("titulo-contenido")
        self.busqueda_input = QLineEdit()
        self.busqueda_input.setObjectName("busqueda_input")
        self.busqueda_input.setPlaceholderText("Buscar medicamento por nombre...")
        self.busqueda_input.textChanged.connect(self.filtrar_tabla_inventario)
        btn_devolucion = QPushButton("Registrar Devolucion")
        btn_devolucion.setObjectName("btn_devolucion")
        btn_devolucion.clicked.connect(lambda: self.abrir_dialogo_transaccion("devolucion"))
        btn_reposicion = QPushButton("Registrar Reposicion a Servicio")
        btn_reposicion.setObjectName("btn_reposicion")
        btn_reposicion.clicked.connect(lambda: self.abrir_dialogo_transaccion("reposicion_servicio"))
        header_layout.addWidget(label_titulo)
        header_layout.addWidget(self.busqueda_input)
        header_layout.addStretch()
        header_layout.addWidget(btn_devolucion)
        header_layout.addWidget(btn_reposicion)
        layout.addLayout(header_layout)
        self.tabla_inventario = QTableWidget()
        self.tabla_inventario.setAlternatingRowColors(True)
        self.tabla_inventario.setColumnCount(6)
        self.tabla_inventario.setHorizontalHeaderLabels(["Medicamento", "Codigo", "Stock Actual", "Ubicacion", "Umbral Minimo", "Estado"])
        self.tabla_inventario.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_inventario.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_inventario)
        return pagina

    def crear_pagina_recetas(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        label_titulo = QLabel("Recetas Pendientes de Dispensacion")
        label_titulo.setObjectName("titulo-contenido")
        layout.addWidget(label_titulo)
        self.tabla_recetas = QTableWidget()
        self.tabla_recetas.setAlternatingRowColors(True)
        self.tabla_recetas.setColumnCount(5)
        self.tabla_recetas.setHorizontalHeaderLabels(["ID Receta", "Paciente (RUN)", "Fecha Emision", "Estado", "Accion"])
        self.tabla_recetas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_recetas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_recetas)
        return pagina

    def crear_pagina_pedidos(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        label_titulo = QLabel("Recepcion de Pedidos de Bodega")
        label_titulo.setObjectName("titulo-contenido")
        layout.addWidget(label_titulo)
        
        self.tabla_pedidos = QTableWidget()
        self.tabla_pedidos.setAlternatingRowColors(True)
        self.tabla_pedidos.setColumnCount(4)
        self.tabla_pedidos.setHorizontalHeaderLabels(["ID Pedido", "Descripcion", "Fecha Creacion", "Accion"])
        self.tabla_pedidos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_pedidos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.tabla_pedidos)
        return pagina

    def actualizar_vista_panel(self):
        self.paginas.setCurrentIndex(0)
        self.cargar_datos_panel()

    def actualizar_vista_inventario(self):
        self.paginas.setCurrentIndex(2)
        self.cargar_datos_inventario()

    def actualizar_vista_recetas(self):
        self.paginas.setCurrentIndex(1)
        self.cargar_datos_recetas()
        
    def actualizar_vista_pedidos(self):
        self.paginas.setCurrentIndex(3)
        self.cargar_datos_pedidos()

    def cargar_datos_panel(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp_recetas = requests.get(f"{self.api_url}/recetas/", headers=headers, timeout=5)
            if resp_recetas.ok:
                pendientes = [r for r in resp_recetas.json() if r['estado'] == 'pendiente']
                self.label_recetas_numero.setText(str(len(pendientes)))
            else:
                self.label_recetas_numero.setText("!")
            resp_meds = requests.get(f"{self.api_url}/medicamentos/", headers=headers, timeout=5)
            if resp_meds.ok:
                bajo_stock = [m for m in resp_meds.json() if m['stock_actual'] < m['umbral_minimo']]
                self.label_stock_numero.setText(str(len(bajo_stock)))
            else:
                self.label_stock_numero.setText("!")
        except requests.exceptions.RequestException:
            self.label_recetas_numero.setText("X")
            self.label_stock_numero.setText("X")

    def cargar_datos_inventario(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            respuesta = requests.get(f"{self.api_url}/medicamentos/", headers=headers)
            if respuesta.status_code == 200:
                self.todos_los_medicamentos = respuesta.json()
                self.llenar_tabla_inventario(self.todos_los_medicamentos)
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudo cargar el inventario: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")

    def llenar_tabla_inventario(self, medicamentos):
        self.tabla_inventario.setRowCount(0)
        self.tabla_inventario.setRowCount(len(medicamentos))
        for fila, med in enumerate(medicamentos):
            nombre = QTableWidgetItem(med['nombre'])
            id_med = QTableWidgetItem(str(med['id']))
            stock = QTableWidgetItem(str(med['stock_actual']))
            ubicacion = QTableWidgetItem("-")
            umbral = QTableWidgetItem(str(med['umbral_minimo']))
            item_estado = QTableWidgetItem("OK")
            if med['stock_actual'] < med['umbral_minimo']:
                item_estado.setText("Bajo Stock")
                item_estado.setForeground(QColor("red"))
                font = item_estado.font()
                font.setBold(True)
                item_estado.setFont(font)
            self.tabla_inventario.setItem(fila, 0, nombre)
            self.tabla_inventario.setItem(fila, 1, id_med)
            self.tabla_inventario.setItem(fila, 2, stock)
            self.tabla_inventario.setItem(fila, 3, ubicacion)
            self.tabla_inventario.setItem(fila, 4, umbral)
            self.tabla_inventario.setItem(fila, 5, item_estado)
            
    def filtrar_tabla_inventario(self):
        texto_busqueda = self.busqueda_input.text().lower()
        if not texto_busqueda:
            medicamentos_filtrados = self.todos_los_medicamentos
        else:
            medicamentos_filtrados = [
                med for med in self.todos_los_medicamentos
                if texto_busqueda in med['nombre'].lower()
            ]
        self.llenar_tabla_inventario(medicamentos_filtrados)

    def cargar_datos_recetas(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            respuesta = requests.get(f"{self.api_url}/recetas/", headers=headers)
            if respuesta.status_code == 200:
                recetas = respuesta.json()
                recetas_pendientes = [r for r in recetas if r['estado'] == 'pendiente']
                self.tabla_recetas.setRowCount(0)
                self.tabla_recetas.setRowCount(len(recetas_pendientes))
                for fila, receta in enumerate(recetas_pendientes):
                    id_receta = QTableWidgetItem(str(receta['id']))
                    paciente = QTableWidgetItem(receta['id_paciente'])
                    fecha = QTableWidgetItem(receta['fecha_emision'])
                    estado = QTableWidgetItem(receta['estado'].capitalize())
                    self.tabla_recetas.setItem(fila, 0, id_receta)
                    self.tabla_recetas.setItem(fila, 1, paciente)
                    self.tabla_recetas.setItem(fila, 2, fecha)
                    self.tabla_recetas.setItem(fila, 3, estado)
                    btn_dispensar = QPushButton("Dispensar")
                    btn_dispensar.setObjectName("btn-accion")
                    btn_dispensar.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_dispensar.clicked.connect(lambda checked, r_id=receta['id']: self.iniciar_dispensacion(r_id))
                    self.tabla_recetas.setCellWidget(fila, 4, btn_dispensar)
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudieron cargar las recetas: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")

    def iniciar_dispensacion(self, receta_id):
        dialogo = DialogoDispensacion(self.token, self.api_url, receta_id, self)
        if not dialogo.exec():
            return
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            respuesta = requests.post(f"{self.api_url}/recetas/{receta_id}/dispensar/", headers=headers)
            if respuesta.status_code == 200:
                resultado = respuesta.json()
                alertas = resultado.get("alertas", [])
                mensaje_exito = f"Receta #{receta_id} dispensada exitosamente."
                if alertas:
                    mensaje_exito += "\n\nSe generaron las siguientes alertas de stock bajo:\n" + "\n".join(alertas)
                QMessageBox.information(self, "Éxito", mensaje_exito)
                self.cargar_datos_recetas()
            else:
                error_detalle = respuesta.json().get('detail', 'Ocurrio un error desconocido.')
                QMessageBox.critical(self, "Error al Dispensar", f"No se pudo procesar la receta: {error_detalle}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")
            
    def abrir_dialogo_transaccion(self, tipo):
        dialogo = DialogoTransaccion(self.token, self.api_url, tipo, self)
        if dialogo.exec():
            datos = dialogo.obtener_datos()
            if datos:
                try:
                    headers = {'Authorization': f'Bearer {self.token}'}
                    respuesta = requests.post(f"{self.api_url}/inventario/transaccion/", headers=headers, json=datos)
                    if respuesta.status_code == 200:
                        QMessageBox.information(self, "Exito", "Transaccion registrada exitosamente.")
                        self.cargar_datos_inventario()
                    else:
                        error = respuesta.json().get('detail', 'Error desconocido')
                        QMessageBox.critical(self, "Error de API", f"No se pudo registrar la transaccion: {error}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")

    def cargar_datos_pedidos(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            respuesta = requests.get(f"{self.api_url}/pedidos/", headers=headers)
            
            if respuesta.status_code == 200:
                pedidos = respuesta.json()
                self.tabla_pedidos.setRowCount(0)
                self.tabla_pedidos.setRowCount(len(pedidos))

                for fila, pedido in enumerate(pedidos):
                    self.tabla_pedidos.setItem(fila, 0, QTableWidgetItem(str(pedido['id'])))
                    self.tabla_pedidos.setItem(fila, 1, QTableWidgetItem(pedido['descripcion']))
                    self.tabla_pedidos.setItem(fila, 2, QTableWidgetItem(pedido['fecha_creacion']))
                    
                    btn_recepcionar = QPushButton("Recepcionar")
                    btn_recepcionar.setObjectName("btn-accion")
                    btn_recepcionar.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_recepcionar.clicked.connect(lambda checked, p_id=pedido['id']: self.recepcionar_pedido(p_id))
                    self.tabla_pedidos.setCellWidget(fila, 3, btn_recepcionar)
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudieron cargar los pedidos: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexion", f"No se pudo conectar a la API: {e}")

    def recepcionar_pedido(self, pedido_id):
        confirmacion = QMessageBox.question(self, "Confirmar Recepcion", 
                                            f"¿Estas seguro de que deseas recepcionar el pedido #{pedido_id}?\nEsta accion aumentara el stock.",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirmacion == QMessageBox.StandardButton.No:
            return

        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            respuesta = requests.post(f"{self.api_url}/pedidos/{pedido_id}/recepcionar/", headers=headers)
            
            if respuesta.status_code == 200:
                QMessageBox.information(self, "Éxito", f"Pedido #{pedido_id} recepcionado exitosamente.")
                self.cargar_datos_pedidos()
            else:
                error_detalle = respuesta.json().get('detail', 'Ocurrio un error desconocido.')
                QMessageBox.critical(self, "Error al Recepcionar", f"No se pudo procesar el pedido: {error_detalle}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")