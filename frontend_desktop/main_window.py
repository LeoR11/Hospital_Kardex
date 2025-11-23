import sys
import requests
import json 
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QTableWidget, 
                             QTableWidgetItem, QTreeWidget, QTreeWidgetItem, 
                             QHeaderView, QMessageBox, QLineEdit,
                             QSpacerItem, QSizePolicy, QFrame)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

from dialogo_dispensacion import DialogoDispensacion
from dialogo_transaccion import DialogoTransaccion
from dialogo_recepcion import DialogoRecepcion 
from dialogo_incidencia import DialogoIncidencia 

class VentanaPrincipal(QMainWindow):
    def __init__(self, token):
        super().__init__()
        
        self.token = token 
        self.api_url = "http://127.0.0.1:8000"
        self.setWindowTitle("Sistema de Gestion del Kardex para Farmacia Unidosis")
        self.setGeometry(100, 100, 1100, 700)
        
        self.todas_las_ubicaciones = [] 
        self.pedidos_pendientes = [] 
        self.recetas_pendientes = []
        self.lista_kardex_estado = []

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
            QLabel.titulo-ia {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-top: 25px;
                margin-bottom: 10px;
            }
            /* Tarjetas Panel Principal */
            QWidget.tarjeta-panel {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                min-height: 120px;
                max-height: 120px;
            }
            QWidget#tarjeta_recetas {
                background-color: #0d6efd;
            }
            QWidget#tarjeta_stock {
                background-color: #dc3545;
            }
            QWidget#tarjeta_estado {
                background-color: #f8f9fa;
            }
            QLabel.estado-kardex-titulo {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                margin-bottom: 8px;
            }
            QLabel.estado-kardex-status {
                font-size: 14px;
                font-weight: bold;
            }
            /* --- FIN NUEVOS ESTILOS --- */
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
            QTableWidget, QTreeWidget {
                border: 1px solid #dee2e6;
                font-size: 14px;
                gridline-color: #dee2e6;
                background-color: #ffffff;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item, QTreeWidgetItem {
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
            QPushButton.btn-accion-secundario {
                background-color: #0d6efd; color: white; padding: 8px 12px; 
                font-weight: bold; border-radius: 4px; border: none;
                min-height: 35px; /* MODIFICACIÓN: Altura mínima para el botón de lote */
            }
            QPushButton.btn-accion-alerta {
                background-color: #ffc107; color: #000; padding: 8px 12px; 
                font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton#btn-accion-falla {
                background-color: #dc3545; color: white; padding: 8px 12px; 
                font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton#btn-accion-falla:hover {
                background-color: #b02a37;
            }
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
        

        layout_navegacion.addStretch() #
        self.btn_reportar_falla = QPushButton("Reportar Falla de Kardex")
        self.btn_reportar_falla.setObjectName("btn-accion-falla")
        self.btn_reportar_falla.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reportar_falla.setContentsMargins(10, 10, 10, 10)
 
        self.btn_reportar_falla.clicked.connect(self.abrir_dialogo_falla)
        layout_navegacion.addWidget(self.btn_reportar_falla)
        layout_navegacion.addSpacing(10)
      
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
        self.cargar_datos_inventario()
        self.actualizar_vista_panel() 


    def _obtener_kardex_id(self, ubicacion_str):
        if not ubicacion_str: return "?"
        letra = ubicacion_str[0].upper()
        if 'A' <= letra <= 'I': return "K1"
        if 'J' <= letra <= 'R': return "K2"
        return "K?"


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
        tarjeta_recetas.setProperty("class", "tarjeta-panel")
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
        tarjeta_stock.setProperty("class", "tarjeta-panel")
        layout_tarjeta2 = QVBoxLayout(tarjeta_stock)
        layout_tarjeta2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_stock_numero = QLabel("...")
        self.label_stock_numero.setObjectName("contador-numero")
        self.label_stock_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_stock_texto = QLabel("Items con Stock Crítico")
        label_stock_texto.setObjectName("contador-label")
        label_stock_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_tarjeta2.addWidget(self.label_stock_numero)
        layout_tarjeta2.addWidget(label_stock_texto)
        

        tarjeta_estado = QWidget()
        tarjeta_estado.setObjectName("tarjeta_estado")
        tarjeta_estado.setProperty("class", "tarjeta-panel")
        layout_tarjeta3 = QVBoxLayout(tarjeta_estado)
        layout_tarjeta3.setContentsMargins(20, 15, 20, 15)
        
        label_estado_titulo = QLabel("Estado del Sistema Kardex")
        label_estado_titulo.setObjectName("estado-kardex-titulo")
        label_estado_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
 
        layout_k1 = QHBoxLayout()
        label_k1_titulo = QLabel("Kardex 1 (A-I):")
        self.label_k1_estado = QLabel("Cargando...")
        self.label_k1_estado.setObjectName("estado-kardex-status")
        layout_k1.addWidget(label_k1_titulo)
        layout_k1.addStretch()
        layout_k1.addWidget(self.label_k1_estado)
        

        layout_k2 = QHBoxLayout()
        label_k2_titulo = QLabel("Kardex 2 (J-R):")
        self.label_k2_estado = QLabel("Cargando...")
        self.label_k2_estado.setObjectName("estado-kardex-status")
        layout_k2.addWidget(label_k2_titulo)
        layout_k2.addStretch()
        layout_k2.addWidget(self.label_k2_estado)
        
        layout_tarjeta3.addWidget(label_estado_titulo)
        layout_tarjeta3.addSpacing(10)
        layout_tarjeta3.addLayout(layout_k1)
        layout_tarjeta3.addLayout(layout_k2)
        # --- FIN NUEVA TARJETA ---

        layout_tarjetas.addWidget(tarjeta_recetas)
        layout_tarjetas.addWidget(tarjeta_stock)
        layout_tarjetas.addWidget(tarjeta_estado) 
        layout_tarjetas.addStretch()
        layout.addLayout(layout_tarjetas)
        

        label_titulo_ia = QLabel("Predccion para hoy del asistente IA")
        label_titulo_ia.setObjectName("titulo-ia")
        layout.addWidget(label_titulo_ia)
        
        self.tabla_ia_diaria = QTableWidget()
        self.tabla_ia_diaria.setAlternatingRowColors(True)
        self.tabla_ia_diaria.setColumnCount(4)
        self.tabla_ia_diaria.setHorizontalHeaderLabels([
            "Medicamento", "Demanda Estimada (Hoy)", "Stock Total Actual", "Estado"
        ])
        self.tabla_ia_diaria.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_ia_diaria.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_ia_diaria.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.tabla_ia_diaria)
        
        layout.addStretch()
        return pagina

    def crear_pagina_recetas(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        
        layout_header = QHBoxLayout()
        label_titulo = QLabel("Recetas Pendientes de Dispensacion")
        label_titulo.setObjectName("titulo-contenido")
        
        layout_header.addWidget(label_titulo)
        layout_header.addStretch()
        
        self.btn_dispensar_lote = QPushButton("Dispensar Lote (Asistente)")
        self.btn_dispensar_lote.setObjectName("btn-accion-secundario") 
        self.btn_dispensar_lote.clicked.connect(self.iniciar_dispensacion_asistente) 
        
        layout_header.addWidget(self.btn_dispensar_lote)
        
        layout.addLayout(layout_header)

        self.tabla_recetas = QTableWidget() 
        self.tabla_recetas.setAlternatingRowColors(True)
        
        self.tabla_recetas.setColumnCount(6)
        self.tabla_recetas.setHorizontalHeaderLabels(["Lote", "ID Receta", "Paciente (RUN)", "Profesional", "Fecha Emision", "Acción Individual"])

        self.tabla_recetas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_recetas.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_recetas.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_recetas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_recetas)
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
        self.busqueda_input.textChanged.connect(self.filtrar_arbol_inventario)
        header_layout.addWidget(label_titulo)
        header_layout.addWidget(self.busqueda_input)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        self.arbol_inventario = QTreeWidget() 
        self.arbol_inventario.setAlternatingRowColors(True)
        self.arbol_inventario.setColumnCount(6)
        self.arbol_inventario.setHeaderLabels([
            "Medicamento / (Kardex / Ubicación)", "Lote", "Vencimiento",
            "Stock", "Umbral", "Estado"
        ])
        self.arbol_inventario.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.arbol_inventario.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.arbol_inventario.header().setMinimumSectionSize(180) 
        layout.addWidget(self.arbol_inventario)
        return pagina


    def crear_pagina_pedidos(self):
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        header_layout = QHBoxLayout()
        label_titulo = QLabel("Pedidos y Transacciones")
        label_titulo.setObjectName("titulo-contenido")
        btn_devolucion = QPushButton("Registrar Devolución")
        btn_devolucion.setObjectName("btn-accion-secundario")
        btn_devolucion.clicked.connect(lambda: self.abrir_dialogo_transaccion("devolucion"))
        btn_reposicion = QPushButton("Registrar Reposicion de Servicio")
        btn_reposicion.setObjectName("btn-accion-alerta")
        btn_reposicion.clicked.connect(lambda: self.abrir_dialogo_transaccion("reposicion_servicio"))
        header_layout.addWidget(label_titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_devolucion)
        header_layout.addWidget(btn_reposicion)
        layout.addLayout(header_layout)
        label_subtitulo = QLabel("Pedidos Pendientes de Recepcion (Bodega)")
        label_subtitulo.setStyleSheet("font-size: 18px; margin-top: 15px; color: #333;")
        layout.addWidget(label_subtitulo)
        self.tabla_pedidos = QTableWidget()
        self.tabla_pedidos.setAlternatingRowColors(True)
        self.tabla_pedidos.setColumnCount(5)
        self.tabla_pedidos.setHorizontalHeaderLabels(["ID Pedido", "Descripción", "Items", "Fecha Creación", "Acción"])
        self.tabla_pedidos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_pedidos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_pedidos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_pedidos)
        return pagina


    
    def get_headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def actualizar_vista_panel(self):
        self.paginas.setCurrentIndex(0)
        self.cargar_datos_panel_async()
        self.cargar_prediccion_diaria()
        self.cargar_estado_kardex()

    def actualizar_vista_recetas(self):
        self.paginas.setCurrentIndex(1)
        self.cargar_datos_recetas()

    def actualizar_vista_inventario(self):
        self.paginas.setCurrentIndex(2)
        self.llenar_arbol_inventario(self.todas_las_ubicaciones)
        
    def actualizar_vista_pedidos(self):
        self.paginas.setCurrentIndex(3)
        self.cargar_datos_pedidos()

    def cargar_datos_panel_async(self):
        try:
            recetas_pend_count = len(self.recetas_pendientes)
            stock_critico_count = len([
                m for m in self.todas_las_ubicaciones 
                if m['stock_actual'] < m['umbral_minimo']
            ])
            self.label_recetas_numero.setText(str(recetas_pend_count))
            self.label_stock_numero.setText(str(stock_critico_count))
        except Exception as e:
            print(f"Error actualizando contadores del panel: {e}")
            self.label_recetas_numero.setText("?")
            self.label_stock_numero.setText("?")

    def cargar_prediccion_diaria(self):
        color_rojo = QColor("#dc3545")
        color_verde = QColor("#198754")
        color_texto_oscuro = QColor("#212529")
        font_bold = QFont()
        font_bold.setBold(True)
        try:
            respuesta = requests.get(
                f"{self.api_url}/ia/prediccion-diaria/", 
                headers=self.get_headers()
            )
            if respuesta.status_code == 200:
                predicciones = respuesta.json()
                self.tabla_ia_diaria.setRowCount(0)
                self.tabla_ia_diaria.setRowCount(len(predicciones))
                for fila, item in enumerate(predicciones):
                    demanda_hoy = item['demanda_estimada_hoy']
                    stock_actual = item['stock_actual']
                    item_nombre = QTableWidgetItem(item['nombre_medicamento'])
                    item_demanda = QTableWidgetItem(f"{demanda_hoy:.0f} Uds.")
                    item_stock = QTableWidgetItem(f"{stock_actual} Uds.")
                    item_estado = QTableWidgetItem()
                    
                    if stock_actual < demanda_hoy:
                        item_estado.setText("POSIBLE FALTANTE")
                        item_estado.setForeground(color_rojo)
                        item_estado.setFont(font_bold)
                    else:
                        item_estado.setText("SUFICIENTE")
                        item_estado.setForeground(color_verde)
                    item_nombre.setForeground(color_texto_oscuro)
                    item_demanda.setForeground(color_texto_oscuro)
                    item_stock.setForeground(color_texto_oscuro)
                    self.tabla_ia_diaria.setItem(fila, 0, item_nombre)
                    self.tabla_ia_diaria.setItem(fila, 1, item_demanda)
                    self.tabla_ia_diaria.setItem(fila, 2, item_stock)
                    self.tabla_ia_diaria.setItem(fila, 3, item_estado)
            else:
                print(f"Error de IA: {respuesta.text}")
                self.tabla_ia_diaria.setRowCount(1)
                self.tabla_ia_diaria.setItem(0, 0, QTableWidgetItem("Error al cargar prediccion de la IA."))
        except requests.exceptions.RequestException as e:
            print(f"Error de Conexion IA: {e}")
            self.tabla_ia_diaria.setRowCount(1)
            self.tabla_ia_diaria.setItem(0, 0, QTableWidgetItem("Error de conexion con API de IA."))

    def cargar_estado_kardex(self):
        """
        Llama al endpoint GET /kardex/status/ para obtener el estado REAL
        de los Kardex desde la base de datos.
        """
        try:
            respuesta = requests.get(f"{self.api_url}/kardex/status/", headers=self.get_headers())
            
            if respuesta.status_code == 200:
                self.lista_kardex_estado = respuesta.json()
                for kardex in self.lista_kardex_estado:
                    label_estado = None
                    if kardex['identificador'] == 'K1':
                        label_estado = self.label_k1_estado
                    elif kardex['identificador'] == 'K2':
                        label_estado = self.label_k2_estado
                    
                    if label_estado:
                        estado = kardex['estado']
                        if estado == 'operativo':
                            label_estado.setText("OPERATIVO")
                            label_estado.setStyleSheet("color: #198754; font-weight: bold;")
                        elif estado == 'en_falla':
                            label_estado.setText("EN FALLA")
                            label_estado.setStyleSheet("color: #dc3545; font-weight: bold;")
                        elif estado == 'en_mantencion':
                            label_estado.setText("MANTENCIÓN")
                            label_estado.setStyleSheet("color: #ffc107; font-weight: bold;")
                        else:
                            label_estado.setText("Desconocido")
                            label_estado.setStyleSheet("color: #6c757d; font-weight: bold;")
            else:
                self.label_k1_estado.setText("Error API")
                self.label_k2_estado.setText("Error API")
                self.lista_kardex_estado = []
        except requests.exceptions.RequestException as e:
            print(f"Error de Conexión Estado Kardex: {e}")
            self.label_k1_estado.setText("Error Conexión")
            self.label_k2_estado.setText("Error Conexión")
            self.lista_kardex_estado = []

    def cargar_datos_recetas(self):
        try:
            respuesta = requests.get(f"{self.api_url}/recetas/", headers=self.get_headers())
            if respuesta.status_code == 200:
                todas_las_recetas = respuesta.json()
                self.recetas_pendientes = [r for r in todas_las_recetas if r['estado'] == 'pendiente']
                self.tabla_recetas.setRowCount(0)
                self.tabla_recetas.setRowCount(len(self.recetas_pendientes))
                
                for fila, receta in enumerate(self.recetas_pendientes):
                    profesional = receta.get('profesional', {}) or {}
                    prof_nombre = profesional.get('nombre', 'N/A')
                    

                    item_check = QTableWidgetItem()
                    item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    item_check.setCheckState(Qt.CheckState.Unchecked)
                    self.tabla_recetas.setItem(fila, 0, item_check)
 
                    
           
                    self.tabla_recetas.setItem(fila, 1, QTableWidgetItem(str(receta['id'])))
                    self.tabla_recetas.setItem(fila, 2, QTableWidgetItem(receta['id_paciente']))
                    self.tabla_recetas.setItem(fila, 3, QTableWidgetItem(prof_nombre))
                    self.tabla_recetas.setItem(fila, 4, QTableWidgetItem(receta['fecha_emision']))
                    
                    btn_dispensar = QPushButton("Dispensar")
                    btn_dispensar.setObjectName("btn-accion")
                    btn_dispensar.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_dispensar.clicked.connect(lambda checked, r=receta: self.iniciar_dispensacion(r))
                    
            
                    self.tabla_recetas.setCellWidget(fila, 5, btn_dispensar)
                
                self.cargar_datos_panel_async()
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudieron cargar las recetas: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")

    def cargar_datos_inventario(self):
        try:
            respuesta = requests.get(f"{self.api_url}/medicamentos/", headers=self.get_headers())
            if respuesta.status_code == 200:
                self.todas_las_ubicaciones = respuesta.json()
                self.llenar_arbol_inventario(self.todas_las_ubicaciones)
                self.cargar_datos_panel_async()
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudo cargar el inventario: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")

    def llenar_arbol_inventario(self, ubicaciones: list):
        self.arbol_inventario.clear()
        
        font_bold = QFont()
        font_bold.setBold(True)
        color_oscuro = QColor("#212529")
        color_rojo = QColor("#dc3545")
        color_naranja = QColor("#fd7e14")
        color_gris = QColor("#6c757d")

        medicamentos_agrupados = {}
        for ubic in ubicaciones:
            if not ubic.get('catalogo'): continue 
            cat_nombre = ubic['catalogo'].get('nombre', 'Sin Catálogo')
            if cat_nombre not in medicamentos_agrupados:
                medicamentos_agrupados[cat_nombre] = {
                    "items": [], "stock_total": 0, "es_critico": False
                }
            medicamentos_agrupados[cat_nombre]["items"].append(ubic)
            medicamentos_agrupados[cat_nombre]["stock_total"] += ubic['stock_actual']
            if ubic['stock_actual'] < ubic['umbral_minimo']:
                medicamentos_agrupados[cat_nombre]["es_critico"] = True

        for nombre_catalogo, data in sorted(medicamentos_agrupados.items()):
            item_padre = QTreeWidgetItem(self.arbol_inventario)
            item_padre.setText(0, nombre_catalogo)
            item_padre.setText(3, str(data['stock_total']))
            item_padre.setFont(0, font_bold)
            item_padre.setFont(3, font_bold)
            item_padre.setForeground(0, color_oscuro)
            item_padre.setForeground(3, color_oscuro)

            if data['es_critico']:
                item_padre.setText(5, "¡STOCK BAJO!")
                item_padre.setForeground(5, color_rojo)
            else:
                 item_padre.setText(5, "OK")
                 item_padre.setForeground(5, color_oscuro)
            
            for ubic in data['items']:
                item_hijo = QTreeWidgetItem(item_padre)
                ubic_str = ubic['ubicacion']
                kardex_id = self._obtener_kardex_id(ubic_str)
                texto_ubicacion = f"    └ {kardex_id} / {ubic_str}" 
                item_hijo.setText(0, texto_ubicacion) 
                item_hijo.setText(1, ubic['lote'])
                item_hijo.setText(2, ubic['fecha_vencimiento'])
                item_hijo.setText(3, str(ubic['stock_actual']))
                item_hijo.setText(4, str(ubic['umbral_minimo']))
                item_hijo.setForeground(0, color_oscuro)
                item_hijo.setForeground(1, color_gris)
                item_hijo.setForeground(2, color_gris)
                item_hijo.setForeground(3, color_oscuro)
                item_hijo.setForeground(4, color_oscuro)
                if ubic['stock_actual'] < ubic['umbral_minimo']:
                    item_hijo.setText(5, "Bajo Stock")
                    item_hijo.setForeground(5, color_naranja)
                else:
                    item_hijo.setForeground(5, color_oscuro)

        self.arbol_inventario.expandAll()

    def filtrar_arbol_inventario(self):
        texto_busqueda = self.busqueda_input.text().lower()
        root = self.arbol_inventario.invisibleRootItem()
        for i in range(root.childCount()):
            item_padre = root.child(i)
            nombre_medicamento = item_padre.text(0).lower()
            
            if texto_busqueda in nombre_medicamento:
                item_padre.setHidden(False)
                for j in range(item_padre.childCount()):
                    item_padre.child(j).setHidden(False)
            else:
                item_padre.setHidden(True)
                hijo_coincide = False
                for j in range(item_padre.childCount()):
                    item_hijo = item_padre.child(j)
                    texto_hijo = item_hijo.text(0).lower()
                    if texto_busqueda in texto_hijo:
                        item_hijo.setHidden(False)
                        hijo_coincide = True
                    else:
                        item_hijo.setHidden(True)
                if hijo_coincide:
                    item_padre.setHidden(False) 

    def cargar_datos_pedidos(self):
        try:
            respuesta = requests.get(f"{self.api_url}/pedidos/", headers=self.get_headers())
            if respuesta.status_code == 200:
                self.pedidos_pendientes = respuesta.json()
                self.tabla_pedidos.setRowCount(0)
                self.tabla_pedidos.setRowCount(len(self.pedidos_pendientes))
                for fila, pedido in enumerate(self.pedidos_pendientes):
                    items_count = len(pedido.get('detalles', []))
                    self.tabla_pedidos.setItem(fila, 0, QTableWidgetItem(str(pedido['id'])))
                    self.tabla_pedidos.setItem(fila, 1, QTableWidgetItem(pedido['descripcion']))
                    self.tabla_pedidos.setItem(fila, 2, QTableWidgetItem(str(items_count)))
                    self.tabla_pedidos.setItem(fila, 3, QTableWidgetItem(pedido['fecha_creacion'].split('T')[0]))
                    btn_recepcionar = QPushButton("Recepcionar")
                    btn_recepcionar.setObjectName("btn-accion")
                    btn_recepcionar.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_recepcionar.clicked.connect(lambda checked, p=pedido: self.recepcionar_pedido(p))
                    self.tabla_pedidos.setCellWidget(fila, 4, btn_recepcionar)
            else:
                QMessageBox.critical(self, "Error de API", f"No se pudieron cargar los pedidos: {respuesta.text}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")


    def iniciar_dispensacion(self, receta_obj):
        if not self.todas_las_ubicaciones:
            QMessageBox.critical(self, "Error", "La lista de inventario no está cargada.")
            self.cargar_datos_inventario() 
            return
        

        ubicaciones_operativas = []
        kardex_en_falla = []

        for kardex_estado in self.lista_kardex_estado:
            if kardex_estado['estado'] != 'operativo':
                kardex_en_falla.append(kardex_estado['identificador'])


        if not kardex_en_falla:
            ubicaciones_operativas = self.todas_las_ubicaciones
        else:
            QMessageBox.warning(self, "Plan de Contingencia Activado",
                f"¡Atención! El/Los Kardex {', '.join(kardex_en_falla)} está(n) reportado(s) como 'en falla' o 'en mantención'.\n"
                "Solo se mostrarán ubicaciones de los kardex operativos.")
            
            for ubic in self.todas_las_ubicaciones:
                kardex_id_de_ubicacion = self._obtener_kardex_id(ubic['ubicacion'])
        
                if kardex_id_de_ubicacion not in kardex_en_falla:
                    ubicaciones_operativas.append(ubic)

        dialogo = DialogoDispensacion(
            token=self.token,
            api_url=self.api_url,
            receta=receta_obj, 
            todas_las_ubicaciones=ubicaciones_operativas,
            parent=self
        )
        
        if not dialogo.exec():
            return 
        mapeo_final = dialogo.obtener_mapeo()
        if not mapeo_final:
            QMessageBox.critical(self, "Error Interno", "No se pudo obtener el mapeo de dispensación.")
            return

        try:
            headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
            receta_id = receta_obj['id']
            respuesta = requests.post(
                f"{self.api_url}/recetas/{receta_id}/dispensar/", 
                headers=headers,
                data=json.dumps(mapeo_final) 
            )
            if respuesta.status_code == 200:
                resultado = respuesta.json()
                alertas = resultado.get("alertas", [])
                mensaje_exito = f"Receta #{receta_id} dispensada exitosamente."
                if alertas:
                    mensaje_exito += "\n\nAlertas de stock bajo:\n" + "\n".join(alertas)
                QMessageBox.information(self, "Éxito", mensaje_exito)
                self.cargar_datos_recetas()
                self.cargar_datos_inventario() 
            else:
                error_detalle = respuesta.json().get('detail', 'Ocurrió un error desconocido.')
                QMessageBox.critical(self, "Error al Dispensar", f"No se pudo procesar la receta: {error_detalle}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")
            

    def iniciar_dispensacion_asistente(self):
        recetas_a_procesar = []
        for fila in range(self.tabla_recetas.rowCount()):
            item_check = self.tabla_recetas.item(fila, 0)
            if item_check and item_check.checkState() == Qt.CheckState.Checked:
                receta_id = int(self.tabla_recetas.item(fila, 1).text())
                
                receta_obj = next((r for r in self.recetas_pendientes if r['id'] == receta_id), None)
                if receta_obj:
                    recetas_a_procesar.append(receta_obj)

        if not recetas_a_procesar:
            QMessageBox.warning(self, "Nada seleccionado", "Debe seleccionar al menos una receta (marcando la casilla) para iniciar el asistente.")
            return

        ubicaciones_operativas = []
        kardex_en_falla = [k['identificador'] for k in self.lista_kardex_estado if k['estado'] != 'operativo']

        if not kardex_en_falla:
            ubicaciones_operativas = self.todas_las_ubicaciones
        else:
            QMessageBox.warning(self, "Plan de Contingencia Activado",
                f"¡Atención! Kardex {', '.join(kardex_en_falla)} está(n) 'en falla'.\n"
                "Solo se mostrarán ubicaciones de los kardex operativos.")
            for ubic in self.todas_las_ubicaciones:
                kardex_id_de_ubicacion = self._obtener_kardex_id(ubic['ubicacion'])
                if kardex_id_de_ubicacion not in kardex_en_falla:
                    ubicaciones_operativas.append(ubic)

        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        errores = []
        exitos_count = 0
        total_recetas = len(recetas_a_procesar)

        for i, receta_obj in enumerate(recetas_a_procesar):
            
            dialogo = DialogoDispensacion(
                token=self.token,
                api_url=self.api_url,
                receta=receta_obj, 
                todas_las_ubicaciones=ubicaciones_operativas,
                parent=self
            )
            

            dialogo.setWindowTitle(f"Asistente ({i+1}/{total_recetas}) - Receta #{receta_obj['id']}")
            
            if not dialogo.exec():

                QMessageBox.information(self, "Lote Cancelado", f"Dispensación en lote cancelada por el usuario. {exitos_count} recetas fueron procesadas.")
                break 

            mapeo_final = dialogo.obtener_mapeo()
            if not mapeo_final:
                errores.append(f"Receta #{receta_obj['id']}: No se pudo obtener el mapeo.")
                continue 
            try:
                receta_id = receta_obj['id']
                respuesta = requests.post(
                    f"{self.api_url}/recetas/{receta_id}/dispensar/", 
                    headers=headers,
                    data=json.dumps(mapeo_final) 
                )
                if respuesta.status_code == 200:
                    exitos_count += 1
                else:
                    error_detalle = respuesta.json().get('detail', 'Error desconocido')
                    errores.append(f"Receta #{receta_id}: {error_detalle}")
            except requests.exceptions.RequestException as e:
                errores.append(f"Receta #{receta_id}: Error de conexión ({e})")
        
        mensaje_final = f"Asistente de lote terminado.\n\n"
        mensaje_final += f"Recetas dispensadas exitosamente: {exitos_count}\n"
        mensaje_final += f"Recetas con errores o saltadas: {len(errores)}\n"
        
        if errores:
            mensaje_final += "\nDetalle de errores:\n" + "\n".join(errores)
            QMessageBox.warning(self, "Asistente Terminado con Errores", mensaje_final)
        else:
            QMessageBox.information(self, "Asistente Terminado", mensaje_final)


        self.cargar_datos_recetas()
        self.cargar_datos_inventario()
            
    def abrir_dialogo_transaccion(self, tipo):
        if not self.todas_las_ubicaciones:
            QMessageBox.critical(self, "Error", "La lista de inventario no está cargada.")
            self.cargar_datos_inventario()
            return

        dialogo = DialogoTransaccion(
            token=self.token, 
            api_url=self.api_url, 
            tipo_transaccion=tipo, 
            todas_las_ubicaciones=self.todas_las_ubicaciones, 
            parent=self
        )
        if dialogo.exec():
            datos_payload = dialogo.obtener_datos()
            if datos_payload:
                try:
                    headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
                    respuesta = requests.post(
                        f"{self.api_url}/inventario/transaccion/", 
                        headers=headers, 
                        data=json.dumps(datos_payload)
                    )
                    if respuesta.status_code == 200:
                        QMessageBox.information(self, "Éxito", "Transacción registrada exitosamente.")
                        self.cargar_datos_inventario() 
                    else:
                        error = respuesta.json().get('detail', 'Error desconocido')
                        QMessageBox.critical(self, "Error de API", f"No se pudo registrar la transacción: {error}")
                except requests.exceptions.RequestException as e:
                    QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")

    def recepcionar_pedido(self, pedido_obj):
        pedido_id = pedido_obj['id']
        if not self.todas_las_ubicACIONES:
            QMessageBox.critical(self, "Error", "La lista de inventario no está cargada.")
            self.cargar_datos_inventario()
            return

        dialogo = DialogoRecepcion(
            token=self.token,
            api_url=self.api_url,
            pedido_obj=pedido_obj,
            todas_las_ubicaciones=self.todas_las_ubicaciones,
            parent=self
        )
        if not dialogo.exec():
            return 
        payload_final = dialogo.obtener_payload()
        if not payload_final:
            QMessageBox.critical(self, "Error Interno", "No se pudo generar el payload de recepción.")
            return

        try:
            headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
            respuesta = requests.post(
                f"{self.api_url}/pedidos/{pedido_id}/recepcionar/", 
                headers=headers,
                data=json.dumps(payload_final) 
            )
            if respuesta.status_code == 200:
                QMessageBox.information(self, "Éxito", f"Pedido #{pedido_id} recepcionado exitosamente.")
                self.cargar_datos_pedidos() 
                self.cargar_datos_inventario() 
            else:
                error_detalle = respuesta.json().get('detail', 'Ocurrió un error desconocido.')
                QMessageBox.critical(self, "Error al Recepcionar", 
                    f"No se pudo procesar el pedido: {error_detalle}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")
            
    # --- ¡NUEVA FUNCIÓN AÑADIDA! (Reportar Falla) ---
    def abrir_dialogo_falla(self):
        """
        Abre el diálogo para reportar una incidencia de Kardex.
        """

        if not self.lista_kardex_estado:
            QMessageBox.warning(self, "Error", "No se pudo cargar la lista de Kardex. Revise la conexión.")
            self.cargar_estado_kardex() 
            return

        dialogo = DialogoIncidencia(lista_kardex=self.lista_kardex_estado, parent=self)
        
        if not dialogo.exec():
            return 
            
        datos_payload = dialogo.obtener_datos()
        
        try:
            headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
            respuesta = requests.post(
                f"{self.api_url}/kardex/reportar-falla/", 
                headers=headers,
                data=json.dumps(datos_payload)
            )
            
            if respuesta.status_code == 200:
                QMessageBox.information(self, "Éxito", 
                    "Falla reportada exitosamente. El administrador ha sido notificado y el Kardex figura 'En Falla'.")
                self.cargar_estado_kardex()
            else:
                error = respuesta.json().get('detail', 'Error desconocido')
                QMessageBox.critical(self, "Error de API", f"No se pudo reportar la falla: {error}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la API: {e}")