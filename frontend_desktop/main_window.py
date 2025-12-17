import sys
import requests # type: ignore
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, # type: ignore
                             QPushButton, QLabel, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
                             QAbstractItemView)
from PyQt6.QtGui import QCursor # type: ignore
from PyQt6.QtCore import Qt # type: ignore

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
        self.setGeometry(100, 100, 1150, 700)
        
        self.todas_las_ubicaciones = []
        self.pedidos_pendientes = []
        self.recetas_pendientes = []
        self.lista_kardex_estado = []

        self.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #ffffff; 
                color: #000000; 
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #000000;
            }
            QWidget#panel_navegacion {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }
            QPushButton {
                color: #000000;
                border: 1px solid #ccc;
                padding: 5px;
                border-radius: 4px;
                background-color: #e9ecef;
            }
            QPushButton.nav-btn {
                text-align: left;
                padding: 12px 20px;
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #333333;
            }
            QPushButton.nav-btn:hover {
                background-color: #e9ecef;
                color: #000000;
            }
            QPushButton.nav-btn:checked {
                background-color: #e7f1ff;
                color: #0d6efd;
                font-weight: bold;
                border-left: 4px solid #0d6efd;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                gridline-color: #f0f0f0;
                color: #000000;
                background-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #000000;
                padding: 5px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: bold;
            }
            QTableWidgetItem {
                color: #000000;
            }
        """)

        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        contenedor_central = QWidget()
        contenedor_central.setLayout(layout_principal)
        self.setCentralWidget(contenedor_central)

        self.panel_navegacion = QWidget()
        self.panel_navegacion.setObjectName("panel_navegacion")
        self.panel_navegacion.setFixedWidth(220)
        layout_nav = QVBoxLayout(self.panel_navegacion)
        layout_nav.setContentsMargins(0, 20, 0, 20)
        layout_nav.setSpacing(5)

        self.btn_recetas = self.crear_boton_nav("Recetas Pendientes")
        self.btn_inventario = self.crear_boton_nav("Inventario y Stock")
        self.btn_recepcion = self.crear_boton_nav("Recepcion Pedidos")
        self.btn_kardex = self.crear_boton_nav("Estado Kardex / Fallas")
        
        layout_nav.addWidget(self.btn_recetas)
        layout_nav.addWidget(self.btn_inventario)
        layout_nav.addWidget(self.btn_recepcion)
        layout_nav.addWidget(self.btn_kardex)
        layout_nav.addStretch()

        btn_salir = QPushButton("Cerrar Sesion")
        btn_salir.setStyleSheet("""
            background-color: #dc3545; color: white; border-radius: 4px; padding: 8px; margin: 10px; border: none;
        """)
        btn_salir.clicked.connect(self.close)
        layout_nav.addWidget(btn_salir)

        layout_principal.addWidget(self.panel_navegacion)

        self.stack_paginas = QStackedWidget()
        layout_principal.addWidget(self.stack_paginas)

        self.pagina_recetas = self.crear_pagina_recetas()
        self.pagina_inventario = self.crear_pagina_inventario()
        self.pagina_recepcion = self.crear_pagina_recepcion()
        self.pagina_kardex = self.crear_pagina_kardex()

        self.stack_paginas.addWidget(self.pagina_recetas)
        self.stack_paginas.addWidget(self.pagina_inventario)
        self.stack_paginas.addWidget(self.pagina_recepcion)
        self.stack_paginas.addWidget(self.pagina_kardex)

        self.btn_recetas.clicked.connect(lambda: self.cambiar_pagina(0, self.btn_recetas))
        self.btn_inventario.clicked.connect(lambda: self.cambiar_pagina(1, self.btn_inventario))
        self.btn_recepcion.clicked.connect(lambda: self.cambiar_pagina(2, self.btn_recepcion))
        self.btn_kardex.clicked.connect(lambda: self.cambiar_pagina(3, self.btn_kardex))

        self.cambiar_pagina(0, self.btn_recetas)
        self.cargar_datos_iniciales()

    def crear_boton_nav(self, texto):
        btn = QPushButton(texto)
        btn.setCheckable(True)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setProperty("class", "nav-btn") 
        return btn

    def cambiar_pagina(self, indice, boton_sender):
        self.stack_paginas.setCurrentIndex(indice)
        
        for btn in [self.btn_recetas, self.btn_inventario, self.btn_recepcion, self.btn_kardex]:
            btn.setChecked(False)
        boton_sender.setChecked(True)
        
        if indice == 0:
            self.cargar_recetas()
        elif indice == 1:
            self.cargar_inventario()
        elif indice == 2:
            self.cargar_pedidos_pendientes()
        elif indice == 3:
            self.cargar_estado_kardex()

    def crear_pagina_recetas(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header_layout = QHBoxLayout()
        lbl_titulo = QLabel("Gestion de Recetas Pendientes")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.clicked.connect(self.cargar_recetas)
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_actualizar)
        
        self.tabla_recetas = QTableWidget()
        self.tabla_recetas.setColumnCount(6)
        self.tabla_recetas.setHorizontalHeaderLabels(["Sel.", "ID Receta", "Paciente", "Fecha", "Estado", "Items"])
        self.tabla_recetas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_recetas.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tabla_recetas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_recetas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        btn_dispensar = QPushButton("Procesar Recetas Marcadas (Secuencial)")
        btn_dispensar.setStyleSheet("background-color: #198754; color: white; padding: 10px; font-weight: bold; border: none;")
        btn_dispensar.clicked.connect(self.iniciar_dispensacion)

        layout.addLayout(header_layout)
        layout.addWidget(self.tabla_recetas)
        layout.addWidget(btn_dispensar)
        return widget

    def crear_pagina_inventario(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header_layout = QHBoxLayout()
        lbl_titulo = QLabel("Inventario Fisico y Stock")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.clicked.connect(self.cargar_inventario)
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_actualizar)

        self.tabla_inventario = QTableWidget()
        self.tabla_inventario.setColumnCount(5)
        self.tabla_inventario.setHorizontalHeaderLabels(["ID", "Medicamento", "Ubicacion", "Lote", "Stock"])
        self.tabla_inventario.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_inventario.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_inventario.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        botones_layout = QHBoxLayout()
        btn_devolucion = QPushButton("Registrar Devolucion")
        btn_devolucion.setStyleSheet("background-color: #ffc107; color: black; padding: 8px; border: none;")
        btn_devolucion.clicked.connect(self.abrir_dialogo_devolucion)
        
        btn_reposicion = QPushButton("Reponer a Servicio (Manual)")
        btn_reposicion.setStyleSheet("background-color: #0d6efd; color: white; padding: 8px; border: none;")
        btn_reposicion.clicked.connect(self.abrir_dialogo_reposicion)

        botones_layout.addWidget(btn_devolucion)
        botones_layout.addWidget(btn_reposicion)

        layout.addLayout(header_layout)
        layout.addWidget(self.tabla_inventario)
        layout.addLayout(botones_layout)
        return widget

    def crear_pagina_recepcion(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header_layout = QHBoxLayout()
        lbl_titulo = QLabel("Recepcion de Pedidos de Bodega")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        btn_actualizar = QPushButton("Actualizar Lista")
        btn_actualizar.clicked.connect(self.cargar_pedidos_pendientes)
        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()
        header_layout.addWidget(btn_actualizar)

        self.tabla_pedidos = QTableWidget()
        self.tabla_pedidos.setColumnCount(4)
        self.tabla_pedidos.setHorizontalHeaderLabels(["ID Pedido", "Descripcion", "Estado", "Items"])
        self.tabla_pedidos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_pedidos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_pedidos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        btn_recepcionar = QPushButton("Recepcionar Pedido Seleccionado")
        btn_recepcionar.setStyleSheet("background-color: #0d6efd; color: white; padding: 10px; font-weight: bold; border: none;")
        btn_recepcionar.clicked.connect(self.abrir_dialogo_recepcion)

        layout.addLayout(header_layout)
        layout.addWidget(self.tabla_pedidos)
        layout.addWidget(btn_recepcionar)
        return widget

    def crear_pagina_kardex(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl_titulo = QLabel("Estado de Equipos Kardex")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        
        self.lbl_status_k1 = QLabel("Kardex 1: Cargando...")
        self.lbl_status_k2 = QLabel("Kardex 2: Cargando...")
        
        self.lbl_status_k1.setStyleSheet("font-size: 16px; padding: 10px; border: 1px solid #ccc; margin: 5px; color: #000000;")
        self.lbl_status_k2.setStyleSheet("font-size: 16px; padding: 10px; border: 1px solid #ccc; margin: 5px; color: #000000;")

        btn_reportar = QPushButton("Reportar Falla de Equipo")
        btn_reportar.setStyleSheet("background-color: #dc3545; color: white; padding: 15px; font-size: 14px; font-weight: bold; border: none;")
        btn_reportar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_reportar.clicked.connect(self.abrir_dialogo_falla)

        btn_refresh = QPushButton("Refrescar Estados")
        btn_refresh.clicked.connect(self.cargar_estado_kardex)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.lbl_status_k1)
        layout.addWidget(self.lbl_status_k2)
        layout.addStretch()
        layout.addWidget(btn_reportar)
        layout.addWidget(btn_refresh)
        return widget

    def cargar_datos_iniciales(self):
        self.cargar_recetas()
        self.cargar_inventario()

    def cargar_recetas(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.get(f"{self.api_url}/recetas/", headers=headers)
            if resp.status_code == 200:
                todas = resp.json()
                self.recetas_pendientes = [r for r in todas if r['estado'] == 'pendiente']
                self.llenar_tabla_recetas(self.recetas_pendientes)
            else:
                self.recetas_pendientes = []
                self.llenar_tabla_recetas([])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando recetas: {e}")

    def llenar_tabla_recetas(self, datos):
        self.tabla_recetas.setRowCount(len(datos))
        for i, r in enumerate(datos):
            paciente_str = "Desconocido"
            if r.get('paciente'):
                paciente_str = f"{r['paciente']['nombre']} {r['paciente']['apellido']}"
            
            # CHECKBOX
            item_check = QTableWidgetItem()
            item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item_check.setCheckState(Qt.CheckState.Unchecked)
            self.tabla_recetas.setItem(i, 0, item_check)
            
            self.tabla_recetas.setItem(i, 1, QTableWidgetItem(str(r['id'])))
            self.tabla_recetas.setItem(i, 2, QTableWidgetItem(paciente_str))
            self.tabla_recetas.setItem(i, 3, QTableWidgetItem(r['fecha_emision']))
            self.tabla_recetas.setItem(i, 4, QTableWidgetItem(r['estado']))
            self.tabla_recetas.setItem(i, 5, QTableWidgetItem(str(len(r['detalles']))))

    def cargar_inventario(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.get(f"{self.api_url}/medicamentos/", headers=headers)
            if resp.status_code == 200:
                self.todas_las_ubicaciones = resp.json()
                self.llenar_tabla_inventario(self.todas_las_ubicaciones)
            else:
                self.todas_las_ubicaciones = []
                self.llenar_tabla_inventario([])
        except Exception:
            self.todas_las_ubicaciones = []
            self.llenar_tabla_inventario([])

    def llenar_tabla_inventario(self, datos):
        self.tabla_inventario.setRowCount(len(datos))
        for i, m in enumerate(datos):
            nombre_med = m['catalogo']['nombre'] if m.get('catalogo') else "Sin Catalogo"
            self.tabla_inventario.setItem(i, 0, QTableWidgetItem(str(m['id'])))
            self.tabla_inventario.setItem(i, 1, QTableWidgetItem(nombre_med))
            self.tabla_inventario.setItem(i, 2, QTableWidgetItem(m['ubicacion']))
            self.tabla_inventario.setItem(i, 3, QTableWidgetItem(m['lote']))
            self.tabla_inventario.setItem(i, 4, QTableWidgetItem(str(m['stock_actual'])))

    def cargar_pedidos_pendientes(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.get(f"{self.api_url}/pedidos/", headers=headers)
            if resp.status_code == 200:
                self.pedidos_pendientes = resp.json()
                self.llenar_tabla_pedidos(self.pedidos_pendientes)
            else:
                self.pedidos_pendientes = []
                self.llenar_tabla_pedidos([])
        except Exception:
            self.pedidos_pendientes = []
            self.llenar_tabla_pedidos([])

    def llenar_tabla_pedidos(self, datos):
        self.tabla_pedidos.setRowCount(len(datos))
        for i, p in enumerate(datos):
            self.tabla_pedidos.setItem(i, 0, QTableWidgetItem(str(p['id'])))
            self.tabla_pedidos.setItem(i, 1, QTableWidgetItem(p['descripcion']))
            self.tabla_pedidos.setItem(i, 2, QTableWidgetItem(p['estado']))
            self.tabla_pedidos.setItem(i, 3, QTableWidgetItem(str(len(p['detalles']))))

    def cargar_estado_kardex(self):
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.get(f"{self.api_url}/kardex/status/", headers=headers)
            if resp.status_code == 200:
                self.lista_kardex_estado = resp.json()
                
                estilos = {
                    "operativo": "color: green; font-weight: bold; border: 2px solid green;",
                    "en_falla": "color: white; background-color: #dc3545; font-weight: bold; border: 2px solid red;",
                    "en_mantencion": "color: black; background-color: #ffc107; font-weight: bold; border: 2px solid orange;"
                }

                for k in self.lista_kardex_estado:
                    texto = f"{k['nombre']}: {k['estado'].upper()}"
                    style = estilos.get(k['estado'], "color: gray;")
                    
                    if k['identificador'] == "K1":
                        self.lbl_status_k1.setText(texto)
                        self.lbl_status_k1.setStyleSheet(f"font-size: 16px; padding: 10px; margin: 5px; {style}")
                    elif k['identificador'] == "K2":
                        self.lbl_status_k2.setText(texto)
                        self.lbl_status_k2.setStyleSheet(f"font-size: 16px; padding: 10px; margin: 5px; {style}")
            else:
                self.lista_kardex_estado = []
        except Exception as e:
            print(f"Error cargando Kardex: {e}")

    def iniciar_dispensacion(self):
        # 1. Identificar recetas marcadas
        rows = []
        for i in range(self.tabla_recetas.rowCount()):
            item_check = self.tabla_recetas.item(i, 0)
            if item_check.checkState() == Qt.CheckState.Checked:
                rows.append(i)
        
        if len(rows) == 0:
            QMessageBox.warning(self, "Alerta", "Seleccione al menos una receta marcando su casilla (checkbox).")
            return

        # Cargar inventario fresco antes de empezar
        self.cargar_inventario()

        exitos = 0
        fallos = 0
        cancelados = 0
        errores_log = []

        # 2. Bucle secuencial manual
        for row in rows:
            receta_data = self.recetas_pendientes[row]
            
            # Abrir dialogo para esta receta especifica
            dialogo = DialogoDispensacion(
                token=self.token,
                api_url=self.api_url,
                receta=receta_data,
                todas_las_ubicaciones=self.todas_las_ubicaciones, # Pasamos el stock actual (que iremos actualizando)
                parent=self
            )
            
            resultado = dialogo.exec()
            
            if resultado: # Si el usuario pulsa Confirmar
                mapeo = dialogo.obtener_mapeo()
                if mapeo:
                    # Enviar a API (Silencioso para no mostrar 20 popups de exito)
                    if self._enviar_dispensacion(receta_data['id'], mapeo, silencioso=True):
                        exitos += 1
                        
                        # ACTUALIZACION LOCAL DEL STOCK PARA LA SIGUIENTE RECETA
                        # Esto es clave: si la Receta 1 gasta stock, la Receta 2 debe saberlo
                        # aunque no recarguemos todo desde la API (por velocidad).
                        for det_id, ubic_id in mapeo.items():
                            # Buscar detalle original para saber cantidad
                            detalle = next((d for d in receta_data['detalles'] if str(d['id']) == det_id), None)
                            if detalle:
                                cantidad_gastada = detalle['cantidad']
                                # Buscar ubicacion en memoria y restar
                                for u in self.todas_las_ubicaciones:
                                    if u['id'] == ubic_id:
                                        u['stock_actual'] -= cantidad_gastada
                                        break
                    else:
                        fallos += 1
                        errores_log.append(f"Receta #{receta_data['id']}: Error en API")
                else:
                    cancelados += 1 # Confirmo pero vacio? Raro, pero posible
            else:
                cancelados += 1
                errores_log.append(f"Receta #{receta_data['id']}: Cancelada por usuario")

        # 3. Resumen Final
        mensaje_final = f"Proceso Finalizado.\n\n- Exitosas: {exitos}\n- Fallidas: {fallos}\n- Canceladas/Omitidas: {cancelados}"
        if errores_log:
            mensaje_final += "\n\nDetalles:\n" + "\n".join(errores_log[:5])
        
        QMessageBox.information(self, "Resumen de Lote", mensaje_final)
        
        # Recargar todo limpio desde la base de datos
        self.cargar_recetas()
        self.cargar_inventario()

    def _enviar_dispensacion(self, receta_id, mapeo, silencioso=False):
        try:
            headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
            resp = requests.post(
                f"{self.api_url}/recetas/{receta_id}/dispensar/",
                headers=headers,
                json=mapeo
            )
            if resp.status_code == 200:
                if not silencioso:
                    datos_resp = resp.json()
                    alertas = datos_resp.get("alertas", [])
                    msg = f"Receta #{receta_id} dispensada exitosamente."
                    if alertas:
                        QMessageBox.warning(self, "Alertas de Stock", msg + "\n" + "\n".join(alertas))
                    else:
                        QMessageBox.information(self, "Exito", msg)
                    self.cargar_recetas()
                    self.cargar_inventario()
                return True
            else:
                if not silencioso:
                    err = resp.json().get('detail', 'Error desconocido')
                    QMessageBox.critical(self, "Error", f"Fallo la dispensacion #{receta_id}: {err}")
                return False
        except Exception as e:
            if not silencioso:
                QMessageBox.critical(self, "Error", f"Error de conexion: {e}")
            return False

    def abrir_dialogo_devolucion(self):
        self._abrir_transaccion("devolucion")

    def abrir_dialogo_reposicion(self):
        self._abrir_transaccion("reposicion_servicio")

    def _abrir_transaccion(self, tipo):
        if not self.todas_las_ubicaciones:
            self.cargar_inventario()
            
        dialogo = DialogoTransaccion(
            token=self.token,
            api_url=self.api_url,
            tipo_transaccion=tipo,
            todas_las_ubicaciones=self.todas_las_ubicaciones,
            parent=self
        )
        
        if dialogo.exec():
            payload = dialogo.obtener_datos()
            try:
                headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
                resp = requests.post(
                    f"{self.api_url}/inventario/transaccion/",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    QMessageBox.information(self, "Exito", "Transaccion registrada.")
                    self.cargar_inventario()
                else:
                    err = resp.json().get('detail', 'Error')
                    QMessageBox.critical(self, "Error", err)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error de conexion: {e}")

    def abrir_dialogo_recepcion(self):
        row = self.tabla_pedidos.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Alerta", "Seleccione un pedido pendiente.")
            return

        pedido_data = self.pedidos_pendientes[row]
        
        dialogo = DialogoRecepcion(
            token=self.token,
            api_url=self.api_url,
            pedido=pedido_data,
            todas_las_ubicaciones=self.todas_las_ubicaciones,
            parent=self
        )
        
        if dialogo.exec():
            payload = dialogo.obtener_payload()
            try:
                headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
                resp = requests.post(
                    f"{self.api_url}/pedidos/{pedido_data['id']}/recepcionar/",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    QMessageBox.information(self, "Exito", "Pedido recepcionado y stock actualizado.")
                    self.cargar_pedidos_pendientes()
                    self.cargar_inventario()
                else:
                    err = resp.json().get('detail', 'Error')
                    QMessageBox.critical(self, "Error", err)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error de conexion: {e}")

    def abrir_dialogo_falla(self):
        if not self.lista_kardex_estado:
            self.cargar_estado_kardex()

        dialogo = DialogoIncidencia(lista_kardex=self.lista_kardex_estado, parent=self)
        
        if dialogo.exec():
            datos = dialogo.obtener_datos()
            try:
                headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
                resp = requests.post(
                    f"{self.api_url}/kardex/reportar-falla/",
                    headers=headers,
                    json=datos
                )
                if resp.status_code == 200:
                    QMessageBox.information(self, "Reporte Enviado", "La falla ha sido reportada. El equipo quedara 'En Falla'.")
                    self.cargar_estado_kardex()
                else:
                    err = resp.json().get('detail', 'Error')
                    QMessageBox.critical(self, "Error", err)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error de conexion: {e}")