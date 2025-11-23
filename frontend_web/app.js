document.addEventListener('DOMContentLoaded', () => {
    const urlBaseApi = 'http://127.0.0.1:8000';
    const token = localStorage.getItem('token');
    const rol = localStorage.getItem('rol');

    // --- LOGICA DE LOGIN ---
    const formularioLogin = document.getElementById('formulario-login');
    if (formularioLogin) {
        formularioLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            const nombreUsuario = document.getElementById('nombre_usuario').value;
            const clave = document.getElementById('clave').value;
            const mensajeError = document.getElementById('mensaje-error');
            
            try {
                const respuesta = await fetch(`${urlBaseApi}/token`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({ 'username': nombreUsuario, 'password': clave })
                });

                if (!respuesta.ok) {
                    const error = await respuesta.json();
                    throw new Error(error.detail || 'Usuario o contraseña incorrectos.');
                }
                
                const data = await respuesta.json();
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('rol', data.rol);

                if (data.rol === "administrador") {
                    window.location.href = 'admin.html';
                } else if (data.rol === "funcionario") {
                    window.location.href = 'panel_funcionario.html'; 
                } else {
                    throw new Error("Rol de usuario no reconocido.");
                }

            } catch (error) {
                localStorage.clear();
                mensajeError.textContent = error.message;
            }
        });
    }

    // --- LOGICA PANEL FUNCIONARIO ---
    const panelFuncionario = document.getElementById('contenido-funcionario');
    if (panelFuncionario) {
        if (!token || rol !== "funcionario") {
            localStorage.clear();
            window.location.href = 'index.html';
            return;
        }

        document.getElementById('btn-panel-func').addEventListener('click', () => window.location.reload());
        document.getElementById('btn-nueva-receta').addEventListener('click', () => window.location.href = 'nueva_receta.html');
        document.getElementById('btn-logout').addEventListener('click', () => {
            localStorage.clear();
            window.location.href = 'index.html';
        });

        async function cargarEstadisticas() {
            const labelNumPendientes = document.getElementById('num-recetas-pendientes');
            const labelNumDispensadas = document.getElementById('num-recetas-dispensadas');
            const labelNumStockCritico = document.getElementById('num-stock-critico');
            const dotKardex1 = document.getElementById('kardex-1-status');
            const dotKardex2 = document.getElementById('kardex-2-status');

            try {
                const headers = { 'Authorization': `Bearer ${token}` };
                
                // Cargar Recetas
                const respuestaRecetas = await fetch(`${urlBaseApi}/recetas/`, { headers });
                if (!respuestaRecetas.ok) throw new Error('No se pudieron cargar las recetas.');
                const recetas = await respuestaRecetas.json();
                const pendientes = recetas.filter(r => r.estado === 'pendiente');
                const dispensadas = recetas.filter(r => r.estado === 'completada');
                labelNumPendientes.textContent = pendientes.length;
                labelNumDispensadas.textContent = dispensadas.length;

                // Cargar Stock Critico
                const respuestaMeds = await fetch(`${urlBaseApi}/medicamentos/`, { headers });
                if (!respuestaMeds.ok) throw new Error('No se pudo cargar el inventario.');
                const medicamentos = await respuestaMeds.json(); 
                
                const medsAgrupados = {};
                medicamentos.forEach(m => {
                    const nombreCatalogo = m.catalogo.nombre; 
                    if (!medsAgrupados[nombreCatalogo]) {
                        medsAgrupados[nombreCatalogo] = { esCritico: false };
                    }
                    if (m.stock_actual < m.umbral_minimo) {
                        medsAgrupados[nombreCatalogo].esCritico = true;
                    }
                });
                const numCriticos = Object.values(medsAgrupados).filter(m => m.esCritico).length;
                labelNumStockCritico.textContent = numCriticos;
                // Llama al endpoint que lee la BD que devuelve una lista
                const respuestaKardex = await fetch(`${urlBaseApi}/kardex/status/`, { headers });
                if (!respuestaKardex.ok) throw new Error('No se pudo cargar el estado del Kardex.');
                const estadoKardexLista = await respuestaKardex.json();
                
                //busca en la lista
                const getEstado = (id) => estadoKardexLista.find(k => k.identificador === id)?.estado || 'en_falla';

                const estadoK1 = getEstado("K1");
                dotKardex1.className = 'status-dot';
                if (estadoK1 === 'operativo') dotKardex1.classList.add('status-operativo');
                else if (estadoK1 === 'en_mantencion') dotKardex1.classList.add('status-recarga'); 
                else dotKardex1.classList.add('status-error'); 
                const estadoK2 = getEstado("K2");
                dotKardex2.className = 'status-dot';
                if (estadoK2 === 'operativo') dotKardex2.classList.add('status-operativo');
                else if (estadoK2 === 'en_mantencion') dotKardex2.classList.add('status-recarga');
                else dotKardex2.classList.add('status-error');

            } catch (error) {
                console.error(error);
                labelNumPendientes.textContent = "Error";
                labelNumDispensadas.textContent = "Error";
                labelNumStockCritico.textContent = "Error";
            }
        }
        cargarEstadisticas();
    }


    // --- LOGICA CREAR RECETA ---
    const formularioReceta = document.getElementById('formulario-receta');
    if (formularioReceta) {
        if (!token || rol !== "funcionario") {
            localStorage.clear();
            window.location.href = 'index.html';
            return;
        }
        document.getElementById('btn-panel-func').addEventListener('click', () => window.location.href = 'panel_funcionario.html');
        document.getElementById('btn-nueva-receta').addEventListener('click', () => {});
        document.getElementById('btn-logout').addEventListener('click', () => {
            localStorage.clear();
            window.location.href = 'index.html';
        });

        const selectProfesional = document.getElementById('profesional_id');
        const inputFecha = document.getElementById('fecha_emision');
        const contenedorDetalles = document.getElementById('contenedor-detalles');
        const btnAgregar = document.getElementById('btn-agregar-medicamento');
        const mensaje = document.getElementById('mensaje');
        
        let catalogoDisponible = []; 

        async function cargarDatosIniciales() {
            try {
                const headers = { 'Authorization': `Bearer ${token}` };
                
                const respProfesionales = await fetch(`${urlBaseApi}/profesionales/`, { headers });
                if (!respProfesionales.ok) throw new Error('Error al cargar profesionales.');
                const profesionales = await respProfesionales.json();
                selectProfesional.innerHTML = ''; 
                profesionales.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.id;
                    option.textContent = `${p.nombre} (${p.run})`;
                    selectProfesional.appendChild(option);
                });

                const respCatalogo = await fetch(`${urlBaseApi}/catalogo/`, { headers });
                if (!respCatalogo.ok) throw new Error('Error al cargar catalogo de medicamentos.');
                catalogoDisponible = await respCatalogo.json();
                
                inputFecha.value = new Date().toISOString().split('T')[0];
                agregarLineaMedicamento(); 
            } catch (error) {
                mensaje.textContent = `Error al cargar datos: ${error.message}`;
                mensaje.style.color = 'red';
            }
        }
        
        function agregarLineaMedicamento() {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'detalle-item';
            
            const selectMedicamento = document.createElement('select');
            selectMedicamento.required = true;
            
            selectMedicamento.innerHTML = '<option value="">Seleccione un medicamento...</option>';
            catalogoDisponible.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id; 
                option.textContent = c.nombre; 
                selectMedicamento.appendChild(option);
            });

            const inputCantidad = document.createElement('input');
            inputCantidad.type = 'number';
            inputCantidad.value = 1;
            inputCantidad.min = 1;
            inputCantidad.required = true;
            
            const btnEliminar = document.createElement('button');
            btnEliminar.textContent = 'X';
            btnEliminar.className = 'btn-eliminar-detalle';
            btnEliminar.type = 'button';
            btnEliminar.onclick = () => itemDiv.remove();
            
            itemDiv.appendChild(selectMedicamento);
            itemDiv.appendChild(inputCantidad);
            itemDiv.appendChild(btnEliminar);
            contenedorDetalles.appendChild(itemDiv);
        }

        btnAgregar.addEventListener('click', agregarLineaMedicamento);
        
        formularioReceta.addEventListener('submit', async (e) => {
            e.preventDefault();
            mensaje.textContent = '';
            const detallesItems = contenedorDetalles.querySelectorAll('.detalle-item');
            if (detallesItems.length === 0) {
                mensaje.textContent = 'Debe agregar al menos un medicamento.';
                mensaje.style.color = 'red';
                return;
            }
            
            const detallesPayload = [];
            
            detallesItems.forEach(item => {
                const select = item.querySelector('select');
                const input = item.querySelector('input');
                const catalogoId = parseInt(select.value);
                const cantidadPedida = parseInt(input.value);

                if (catalogoId) { 
                    detallesPayload.push({
                        catalogo_id: catalogoId, 
                        cantidad: cantidadPedida
                    });
                }
            });

            if (detallesPayload.length === 0) {
                mensaje.textContent = 'Debe seleccionar un medicamento valido.';
                mensaje.style.color = 'red';
                return;
            }

            const recetaPayload = {
                id_paciente: document.getElementById('id_paciente').value,
                profesional_id: parseInt(selectProfesional.value),
                fecha_emision: inputFecha.value,
                detalles: detallesPayload 
            };
            
            try {
                const respuesta = await fetch(`${urlBaseApi}/recetas/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(recetaPayload)
                });
                if (!respuesta.ok) {
                    const errorData = await respuesta.json();
                    throw new Error(errorData.detail || 'Error al registrar la receta.');
                }
                const nuevaReceta = await respuesta.json();
                mensaje.textContent = `¡Receta #${nuevaReceta.id} registrada exitosamente!`;
                mensaje.style.color = 'green';
                formularioReceta.reset();
                contenedorDetalles.innerHTML = '';
                
                await cargarDatosIniciales();
                
            } catch (error) {
                mensaje.textContent = error.message;
                mensaje.style.color = 'red';
            }
        });
        
        cargarDatosIniciales();
    }


    // --- LOGICA PANEL DE ADMIN ---
    const panelAdmin = document.getElementById('contenido-admin');
    if (panelAdmin) {
        if (!token || rol !== "administrador") {
            localStorage.clear();
            window.location.href = 'index.html';
            return;
        }

        let cacheIncidencias = [];
        const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
        
        function setBotonActivo(botonActivoId) {
            document.querySelectorAll('.panel-navegacion .nav-button').forEach(btn => {
                btn.classList.remove('active');
                if (btn.id === botonActivoId) {
                    btn.classList.add('active');
                }
            });
        }
        
        // --- Navegacion ---
        document.getElementById('btn-cuentas').addEventListener('click', cargarVistaCuentas);
        document.getElementById('btn-profesionales').addEventListener('click', cargarVistaProfesionales);
        document.getElementById('btn-catalogo').addEventListener('click', cargarVistaCatalogo);
        document.getElementById('btn-ubicaciones').addEventListener('click', cargarVistaUbicaciones);
        document.getElementById('btn-crear-pedido').addEventListener('click', cargarVistaCrearPedido);
        document.getElementById('btn-gestion-kardex').addEventListener('click', cargarVistaIncidencias);
        document.getElementById('btn-reportes').addEventListener('click', cargarVistaReportes);
        document.getElementById('btn-logout').addEventListener('click', () => {
            localStorage.clear();
            window.location.href = 'index.html';
        });
        
        // --- VISTA 1: GESTION DE CUENTAS ---
        function cargarVistaCuentas() {
            setBotonActivo('btn-cuentas');
            panelAdmin.innerHTML = `
                <h1>Gestion de Cuentas de Usuario Farmacia Unidosis</h1>
                <div class="admin-seccion">
                    <h2>Buscar Usuario</h2>
                    <div class="admin-busqueda">
                        <input type="text" id="admin-search-input" placeholder="Buscar por nombre...">
                        <button id="admin-search-btn">Buscar</button>
                        <button id="admin-showall-btn">Ver Todos</button>
                    </div>
                    <table class="admin-table">
                        <thead><tr><th>ID</th><th>Nombre de Usuario</th><th>Nombre Completo</th><th>Rol</th><th>Accion</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
                <div class="admin-seccion">
                    <h2>Crear Nuevo Usuario</h2>
                    <form id="admin-create-form" class="form-grid">
                        <div class="form-group">
                            <label for="new-nombre">Nombre</label>
                            <input type="text" id="new-nombre" required>
                        </div>
                        <div class="form-group">
                            <label for="new-apellido">Apellido</label>
                            <input type="text" id="new-apellido" required>
                        </div>
                        <div class="form-group">
                            <label for="new-username">Nombre de Usuario (Login)</label>
                            <input type="text" id="new-username" required>
                        </div>
                        <div class="form-group">
                            <label for="new-password">Contraseña</label>
                            <input type="password" id="new-password" required>
                        </div>
                        <div class="form-group">
                            <label for="new-role">Rol</label>
                            <select id="new-role" required>
                                <option value="funcionario">Funcionario (Ventanilla)</option>
                                <option value="administrador">Administrador</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-submit-admin">Crear Usuario</button>
                    </form>
                    <p id="admin-mensaje"></p>
                </div>
            `;
            document.getElementById('admin-search-btn').addEventListener('click', () => buscarUsuarios(false));
            document.getElementById('admin-showall-btn').addEventListener('click', () => buscarUsuarios(true));
            document.getElementById('admin-create-form').addEventListener('submit', crearUsuario);
            buscarUsuarios(true);
        }
        async function buscarUsuarios(verTodos = false) {
            const input = document.getElementById('admin-search-input');
            const tablaBody = document.querySelector('.admin-table tbody');
            let url = `${urlBaseApi}/usuarios/`;
            if (!verTodos && input.value) { url += `?search=${encodeURIComponent(input.value)}`; }
            try {
                const respuesta = await fetch(url, { headers });
                if (!respuesta.ok) throw new Error('Error al buscar usuarios.');
                const usuarios = await respuesta.json();
                tablaBody.innerHTML = '';
                usuarios.forEach(u => {
                    let botonEliminar = (u.rol === 'funcionario') ? `<button class="btn-eliminar" data-id="${u.id}">Eliminar</button>` : '';
                    tablaBody.innerHTML += `<tr>
                        <td>${u.id}</td><td>${u.nombre_usuario}</td><td>${u.nombre} ${u.apellido}</td><td>${u.rol}</td><td>${botonEliminar}</td>
                    </tr>`;
                });
                document.querySelectorAll('.admin-table .btn-eliminar').forEach(btn => {
                    btn.addEventListener('click', () => eliminarUsuario(btn.dataset.id));
                });
            } catch (error) {
                tablaBody.innerHTML = `<tr><td colspan="5" style="color:red;">${error.message}</td></tr>`;
            }
        }
        async function crearUsuario(e) {
            e.preventDefault();
            const mensaje = document.getElementById('admin-mensaje');
            const payload = {
                nombre_usuario: document.getElementById('new-username').value,
                clave: document.getElementById('new-password').value,
                rol: document.getElementById('new-role').value,
                nombre: document.getElementById('new-nombre').value,
                apellido: document.getElementById('new-apellido').value
            };
            try {
                const respuesta = await fetch(`${urlBaseApi}/usuarios/`, { method: 'POST', headers: headers, body: JSON.stringify(payload) });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al crear usuario.');
                }
                mensaje.textContent = 'Usuario creado con exito.';
                mensaje.style.color = 'green';
                document.getElementById('admin-create-form').reset();
                buscarUsuarios(true);
            } catch (error) {
                mensaje.textContent = error.message;
                mensaje.style.color = 'red';
            }
        }
        async function eliminarUsuario(id) {
            if (!confirm(`¿Estas seguro de que quieres eliminar al usuario con ID ${id}?`)) return;
            try {
                const respuesta = await fetch(`${urlBaseApi}/usuarios/${id}`, { method: 'DELETE', headers: headers });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al eliminar usuario.');
                }
                alert('Usuario eliminado con exito.');
                buscarUsuarios(true);
            } catch (error) {
                alert(error.message);
            }
        }

        // --- VISTA 2: PROFESIONALES ---
        function cargarVistaProfesionales() {
            setBotonActivo('btn-profesionales');
            panelAdmin.innerHTML = `
                <h1>Profesionales del Hospital</h1>
                <div class="admin-seccion">
                    <h2>Buscar Profesional</h2>
                    <div class="admin-busqueda">
                        <input type="text" id="prof-search-input" placeholder="Buscar por nombre...">
                        <button id="prof-search-btn">Buscar</button>
                        <button id="prof-showall-btn">Ver Todos</button>
                    </div>
                    <table class="admin-table">
                        <thead><tr><th>ID</th><th>Nombre</th><th>RUN</th><th>Profesion</th><th>Accion</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
                <div class="admin-seccion">
                    <h2>Crear Nuevo Profesional</h2>
                    <form id="prof-create-form" class="form-grid">
                        <div class="form-group">
                            <label for="new-prof-nombre">Nombre Completo</label>
                            <input type="text" id="new-prof-nombre" required>
                        </div>
                        <div class="form-group">
                            <label for="new-prof-run">RUT</label>
                            <input type="text" id="new-prof-run" required>
                        </div>
                        <div class="form-group">
                            <label for="new-prof-profesion">Profesion</label>
                            <input type="text" id="new-prof-profesion" value="Medico Cirujano" required>
                        </div>
                        <button type="submit" class="btn-submit-admin">Crear Profesional</button>
                    </form>
                    <p id="admin-mensaje"></p>
                </div>
            `;
            document.getElementById('prof-search-btn').addEventListener('click', () => buscarProfesionales(false));
            document.getElementById('prof-showall-btn').addEventListener('click', () => buscarProfesionales(true));
            document.getElementById('prof-create-form').addEventListener('submit', crearProfesional);
            buscarProfesionales(true);
        }
        async function buscarProfesionales(verTodos = false) {
            const input = document.getElementById('prof-search-input');
            const tablaBody = document.querySelector('.admin-table tbody');
            let url = `${urlBaseApi}/profesionales/`;
            if (!verTodos && input.value) { url += `?search=${encodeURIComponent(input.value)}`; }
            try {
                const respuesta = await fetch(url, { headers });
                if (!respuesta.ok) throw new Error('Error al buscar profesionales.');
                const profesionales = await respuesta.json();
                tablaBody.innerHTML = '';
                profesionales.forEach(p => {
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${p.id}</td><td>${p.nombre}</td><td>${p.run}</td><td>${p.profesion}</td>
                            <td><button class="btn-eliminar" data-id="${p.id}">Eliminar</button></td>
                        </tr>
                    `;
                });
                document.querySelectorAll('.admin-table .btn-eliminar').forEach(btn => {
                    btn.addEventListener('click', () => eliminarProfesional(btn.dataset.id));
                });
            } catch (error) {
                tablaBody.innerHTML = `<tr><td colspan="5" style="color:red;">${error.message}</td></tr>`;
            }
        }
        async function crearProfesional(e) {
            e.preventDefault();
            const mensaje = document.getElementById('admin-mensaje');
            const payload = {
                nombre: document.getElementById('new-prof-nombre').value,
                run: document.getElementById('new-prof-run').value,
                profesion: document.getElementById('new-prof-profesion').value
            };
            try {
                const respuesta = await fetch(`${urlBaseApi}/profesionales/`, { method: 'POST', headers: headers, body: JSON.stringify(payload) });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al crear profesional.');
                }
                mensaje.textContent = 'Profesional creado con éxito.';
                mensaje.style.color = 'green';
                document.getElementById('prof-create-form').reset();
                buscarProfesionales(true);
            } catch (error) {
                mensaje.textContent = error.message;
                mensaje.style.color = 'red';
            }
        }
        async function eliminarProfesional(id) {
            if (!confirm(`¿Estas seguro de que quieres eliminar al profesional con ID ${id}?`)) return;
            try {
                const respuesta = await fetch(`${urlBaseApi}/profesionales/${id}`, { method: 'DELETE', headers: headers });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al eliminar profesional.');
                }
                alert('Profesional eliminado con éxito.');
                buscarProfesionales(true);
            } catch (error) {
                alert(error.message);
            }
        }
        
        // --- VISTA 3: CATÁLOGO (IA Pasiva) ---
        function cargarVistaCatalogo() {
            setBotonActivo('btn-catalogo');
            panelAdmin.innerHTML = `
                <h1>Catálogo de medicamentos (Panel Inteligente)</h1>
                <p>Panel de estado del inventario.</p>
                <div class="admin-seccion">
                    <h2>Catalogo y Estado de Stock</h2>
                    <table class="admin-table" id="tabla-catalogo-ia">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Nombre (Medicamento)</th>
                                <th>Stock Total Actual</th>
                                <th>Demanda Estimada (30 dias)</th>
                                <th>Estado (proporcinado por IA)</th>
                                <th>Accion</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6">Cargando datos de IA...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="admin-seccion">
                    <h2>Crear Nuevo Item de Catalogo</h2>
                    <form id="cat-create-form" class="form-grid">
                        <div class="form-group">
                            <label for="new-cat-nombre">Nombre (Unico)</label>
                            <input type="text" id="new-cat-nombre" required>
                        </div>
                        <div class="form-group">
                            <label for="new-cat-desc">Descripcion (Opcional)</label>
                            <input type="text" id="new-cat-desc">
                        </div>
                        <button type="submit" class="btn-submit-admin">Crear en Catalogo</button>
                    </form>
                    <p id="admin-mensaje"></p>
                </div>
            `;
            
            document.getElementById('cat-create-form').addEventListener('submit', crearItemCatalogo);
            buscarCatalogoDashboard();
        }
        async function buscarCatalogoDashboard() {
            const tablaBody = document.querySelector('#tabla-catalogo-ia tbody');
            try {
                const respuesta = await fetch(`${urlBaseApi}/catalogo/dashboard/`, { headers });
                if (!respuesta.ok) throw new Error('Error al buscar catálogo inteligente.');
                const catalogoItems = await respuesta.json();
                
                tablaBody.innerHTML = '';
                if (catalogoItems.length === 0) {
                     tablaBody.innerHTML = `<tr><td colspan="6">No hay items en el catalogo. Cree uno nuevo.</td></tr>`;
                     return;
                }
                
                catalogoItems.forEach(c => {
                    let estadoClass = "estado-ia-datos";
                    if (c.estado_ia === "OK") {
                        estadoClass = "estado-ia-ok";
                    } else if (c.estado_ia === "REQUIERE PEDIDO") {
                        estadoClass = "estado-ia-requiere";
                    }
                    const demandaTexto = c.demanda_estimada_30_dias !== null ? c.demanda_estimada_30_dias.toFixed(0) : 'N/A';
                    
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${c.id}</td>
                            <td>${c.nombre}</td>
                            <td>${c.stock_total}</td>
                            <td>${demandaTexto}</td>
                            <td class="${estadoClass}">${c.estado_ia}</td>
                            <td><button class="btn-eliminar" data-id="${c.id}">Eliminar</button></td>
                        </tr>
                    `;
                });
                
                document.querySelectorAll('#tabla-catalogo-ia .btn-eliminar').forEach(btn => {
                    btn.addEventListener('click', () => eliminarItemCatalogo(btn.dataset.id));
                });
            } catch (error) {
                tablaBody.innerHTML = `<tr><td colspan="6" style="color:red;">${error.message}</td></tr>`;
            }
        }
        async function crearItemCatalogo(e) {
            e.preventDefault();
            const mensaje = document.getElementById('admin-mensaje');
            const payload = {
                nombre: document.getElementById('new-cat-nombre').value,
                descripcion: document.getElementById('new-cat-desc').value || null
            };
            try {
                const respuesta = await fetch(`${urlBaseApi}/catalogo/`, {
                    method: 'POST', headers: headers, body: JSON.stringify(payload)
                });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al crear item.');
                }
                mensaje.textContent = 'Item de catalogo creado con exito.';
                mensaje.style.color = 'green';
                document.getElementById('cat-create-form').reset();
                buscarCatalogoDashboard();
            } catch (error) {
                mensaje.textContent = error.message;
                mensaje.style.color = 'red';
            }
        }
        async function eliminarItemCatalogo(id) {
            if (!confirm(`¿Estas seguro de que quieres eliminar el item ID ${id} del catalogo?\nSolo se puede eliminar si no tiene ubicaciones fisicas asociadas.`)) {
                return;
            }
            try {
                const respuesta = await fetch(`${urlBaseApi}/catalogo/${id}`, {
                    method: 'DELETE', headers: headers
                });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al eliminar item.');
                }
                alert('Item de catalogo eliminado con exito.');
                buscarCatalogoDashboard();
            } catch (error) {
                alert(error.message);
            }
        }

        // --- VISTA 4: UBICACIONES (para el kardex)---
        async function cargarVistaUbicaciones() {
            setBotonActivo('btn-ubicaciones');
            panelAdmin.innerHTML = `
                <h1>Gestión de Ubicaciones Físicas</h1>
                <p>Creacion de los espacios fisicos del kardex (ej. A05) que se asocian a un item del catalogo.</p>
                <div class="admin-seccion">
                    <h2>Ubicaciones Existentes</h2>
                    <table class="admin-table">
                        <thead><tr><th>ID (Ubic.)</th><th>Nombre (Catálogo)</th><th>Ubicación</th><th>Lote</th><th>Vencimiento</th><th>Stock</th><th>Umbral</th><th>Accion</th></tr></thead>
                        <tbody></tbody>
                    </table>
                </div>
                <div class="admin-seccion">
                    <h2>Crear Nueva Ubicacion</h2>
                    <form id="med-create-form" class="form-grid">
                        <div class="form-group">
                            <label for="new-med-catalogo">Item del Catalogo</label>
                            <select id="new-med-catalogo" required><option value="">Cargando catalogo...</option></select>
                        </div>
                        <div class="form-group">
                            <label for="new-med-ubicacion">Ubicacion (ej. A05, K12)</label>
                            <input type="text" id="new-med-ubicacion" placeholder="A01" required>
                        </div>
                        <div class="form-group">
                            <label for="new-med-lote">Lote</label>
                            <input type="text" id="new-med-lote" required>
                        </div>
                        <div class="form-group">
                            <label for="new-med-vencimiento">Fecha Vencimiento</label>
                            <input type="date" id="new-med-vencimiento" required>
                        </div>
                        <div class="form-group">
                            <label for="new-med-stock">Stock Actual</label>
                            <input type="number" id="new-med-stock" value="0" min="0" required>
                        </div>
                        <div class="form-group">
                            <label for="new-med-umbral">Umbral Minimo</label>
                            <input type="number" id="new-med-umbral" value="10" min="0" required>
                        </div>
                        <button type="submit" class="btn-submit-admin">Crear Ubicacion</button>
                    </form>
                    <p id="admin-mensaje"></p>
                </div>
            `;
            
            document.getElementById('med-create-form').addEventListener('submit', crearUbicacion);
            
            try {
                const respCat = await fetch(`${urlBaseApi}/catalogo/`, { headers }); 
                if (!respCat.ok) throw new Error('No se pudo cargar el catalogo para el formulario.');
                const catalogo = await respCat.json();
                
                const selectCatalogo = document.getElementById('new-med-catalogo');
                selectCatalogo.innerHTML = '<option value="">Seleccione un item...</option>';
                catalogo.forEach(c => {
                    selectCatalogo.innerHTML += `<option value="${c.id}">${c.nombre}</option>`;
                });

                buscarUbicaciones(); 

            } catch (error) {
                document.getElementById('admin-mensaje').textContent = error.message;
                document.getElementById('admin-mensaje').style.color = 'red';
            }
        }
        async function buscarUbicaciones() {
            const tablaBody = document.querySelector('.admin-table tbody');
            try {
                const respuesta = await fetch(`${urlBaseApi}/medicamentos/`, { headers }); 
                if (!respuesta.ok) throw new Error('Error al buscar ubicaciones.');
                const ubicaciones = await respuesta.json();
                
                tablaBody.innerHTML = '';
                ubicaciones.forEach(m => {
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${m.id}</td>
                            <td>${m.catalogo.nombre}</td>
                            <td>${m.ubicacion}</td>
                            <td>${m.lote}</td>
                            <td>${m.fecha_vencimiento}</td>
                            <td>${m.stock_actual}</td>
                            <td>${m.umbral_minimo}</td>
                            <td><button class="btn-eliminar" data-id="${m.id}">Eliminar</button></td>
                        </tr>
                    `;
                });
                
                document.querySelectorAll('.admin-table .btn-eliminar').forEach(btn => {
                    btn.addEventListener('click', () => eliminarUbicacion(btn.dataset.id));
                });
            } catch (error) {
                tablaBody.innerHTML = `<tr><td colspan="8" style="color:red;">${error.message}</td></tr>`;
            }
        }
        async function crearUbicacion(e) {
            e.preventDefault();
            const mensaje = document.getElementById('admin-mensaje');
            const ubicacionInput = document.getElementById('new-med-ubicacion').value.toUpperCase();
            
            const ubicacionRegex = /^[A-R][0-9]+$/; 
            if (!ubicacionRegex.test(ubicacionInput)) {
                mensaje.textContent = 'Error: El formato de ubicación es invalido. Debe ser una letra (A-R) seguida de números (ej. A01, C23, K10).';
                mensaje.style.color = 'red';
                return;
            }

            const payload = {
                catalogo_id: parseInt(document.getElementById('new-med-catalogo').value),
                lote: document.getElementById('new-med-lote').value,
                fecha_vencimiento: document.getElementById('new-med-vencimiento').value,
                stock_actual: parseInt(document.getElementById('new-med-stock').value),
                umbral_minimo: parseInt(document.getElementById('new-med-umbral').value),
                ubicacion: ubicacionInput
            };

            if (!payload.catalogo_id) {
                mensaje.textContent = 'Debe seleccionar un item del catalogo.';
                mensaje.style.color = 'red';
                return;
            }
            if (!payload.fecha_vencimiento) {
                mensaje.textContent = 'La fecha de vencimiento es obligatoria.';
                mensaje.style.color = 'red';
                return;
            }

            try {
                const respuesta = await fetch(`${urlBaseApi}/medicamentos/`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(payload)
                });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    let errorMsg = err.detail || 'Error al crear ubicacion.';
                    if (errorMsg.includes("ubicacion")) { 
                        errorMsg = "Error: Esa ubicación ya esta ocupada por otro medicamento.";
                    }
                    throw new Error(errorMsg);
                }
                mensaje.textContent = 'Ubicacion creada con exito.';
                mensaje.style.color = 'green';
                document.getElementById('med-create-form').reset();
                buscarUbicaciones(); 
            } catch (error) {
                mensaje.textContent = error.message;
                mensaje.style.color = 'red';
            }
        }
        async function eliminarUbicacion(id) {
            if (!confirm(`¿Estas seguro de que quieres eliminar esta ubicación (ID ${id})?\nEsta accion no se puede deshacer.`)) {
                return;
            }
            try {
                const respuesta = await fetch(`${urlBaseApi}/medicamentos/${id}`, {
                    method: 'DELETE',
                    headers: headers
                });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al eliminar ubicacion.');
                }
                alert('Ubicación eliminada con exito.');
                buscarUbicaciones(); 
            } catch (error) {
                alert(error.message);
            }
        }
        
        // --- VISTA 5: PEDIDOS ---
        function cargarVistaCrearPedido() {
            setBotonActivo('btn-crear-pedido');
            const hoy = new Date().toISOString().split('T')[0];
            
            panelAdmin.innerHTML = `
                <h1>Crear Pedido a Bodega (Asistente IA)</h1>
                <p>Cree un nuevo pedido para la bodega central. Puede usar el asistente de IA para autocompletar el pedido con los medicamentos que (segun la prediccion de la ia) se necesitaran en los proximos 30 días.</p>           
                <form id="form-crear-pedido">
                    <div class="admin-seccion">
                        <h2>1. Descripcion del Pedido</h2>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="pedido-descripcion">Descripcion</label>
                                <input type="text" id="pedido-descripcion" value="Pedido Bodega ${hoy}" required>
                            </div>
                        </div>
                    </div>
                    
                    <div class="admin-seccion">
                        <h2>2. Asistente de IA</h2>
                        <button type="button" id="btn-ia-autocompletar">Autocompletar Pedido con Sugerencias de de la IA</button>
                        <p id="ia-pedido-mensaje"></p>
                    </div>

                    <div class="admin-seccion">
                        <h2>3. Detalles del Pedido</h2>
                        <div id="contenedor-detalles-pedido">
                        </div>
                    </div>
                    
                    <hr>
                    <button type="submit" id="btn-enviar-pedido">Enviar Pedido a Bodega</button>
                    <p id="pedido-mensaje-final"></p>
                </form>
            `;
            
            document.getElementById('btn-ia-autocompletar').addEventListener('click', autocompletarPedidoIA);
            document.getElementById('form-crear-pedido').addEventListener('submit', enviarPedidoBodega);
        }
        async function autocompletarPedidoIA() {
            const boton = document.getElementById('btn-ia-autocompletar');
            const mensaje = document.getElementById('ia-pedido-mensaje');
            const contenedor = document.getElementById('contenedor-detalles-pedido');
            boton.textContent = 'Consultar IA...';
            boton.disabled = true;
            mensaje.textContent = '';
            try {
                const respuesta = await fetch(`${urlBaseApi}/ia/sugerencias-pedido/`, { headers });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al obtener sugerencias de IA.');
                }
                const sugerencias = await respuesta.json();
                contenedor.innerHTML = ''; 
                if (sugerencias.length === 0) {
                    mensaje.textContent = 'La IA no tiene sugerencias. El stock parece esta al dia segun la demanda de hoy';
                    mensaje.style.color = 'green';
                    return;
                }
                sugerencias.forEach(sug => {
                    agregarLineaPedido(sug.catalogo_id, sug.nombre_medicamento, Math.ceil(sug.cantidad_sugerida_a_pedir));
                });
                mensaje.textContent = `Se añadieron ${sugerencias.length} medicamentos al pedido. Revise las cantidades y envie.`;
                mensaje.style.color = 'green';
            } catch (error) {
                mensaje.textContent = `Error: ${error.message}`;
                mensaje.style.color = 'red';
            } finally {
                boton.textContent = 'Autocompletar Pedido con Sugerencias de IA';
                boton.disabled = false;
            }
        }
        function agregarLineaPedido(catalogoId, nombre, cantidad) {
            const contenedor = document.getElementById('contenedor-detalles-pedido');
            const itemDiv = document.createElement('div');
            itemDiv.className = 'pedido-item';
            itemDiv.dataset.id = catalogoId; 
            const labelNombre = document.createElement('label');
            labelNombre.textContent = nombre;
            const inputCantidad = document.createElement('input');
            inputCantidad.type = 'number';
            inputCantidad.value = cantidad;
            inputCantidad.min = 1;
            inputCantidad.required = true;
            const btnEliminar = document.createElement('button');
            btnEliminar.textContent = 'X';
            btnEliminar.className = 'btn-eliminar-detalle';
            btnEliminar.type = 'button';
            btnEliminar.onclick = () => itemDiv.remove();
            itemDiv.appendChild(labelNombre);
            itemDiv.appendChild(inputCantidad);
            itemDiv.appendChild(btnEliminar);
            contenedor.appendChild(itemDiv);
        }
        async function enviarPedidoBodega(e) {
            e.preventDefault();
            const mensaje = document.getElementById('pedido-mensaje-final');
            const boton = document.getElementById('btn-enviar-pedido');
            const descripcion = document.getElementById('pedido-descripcion').value;
            const itemsPedido = document.querySelectorAll('#contenedor-detalles-pedido .pedido-item');
            if (!descripcion) {
                mensaje.textContent = 'Debe añadir una descripcion al pedido.';
                mensaje.style.color = 'red';
                return;
            }
            if (itemsPedido.length === 0) {
                mensaje.textContent = 'Debe añadir al menos un medicamento al pedido.';
                mensaje.style.color = 'red';
                return;
            }
            const detallesPayload = [];
            itemsPedido.forEach(item => {
                detallesPayload.push({
                    catalogo_id: parseInt(item.dataset.id),
                    cantidad: parseInt(item.querySelector('input[type="number"]').value)
                });
            });
            const payloadFinal = {
                descripcion: descripcion,
                detalles: detallesPayload
            };
            boton.textContent = 'Enviando...';
            boton.disabled = true;
            mensaje.textContent = '';
            try {
                const respuesta = await fetch(`${urlBaseApi}/pedidos/`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(payloadFinal)
                });
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al crear el pedido.');
                }
                const nuevoPedido = await respuesta.json();
                mensaje.textContent = `¡Pedido #${nuevoPedido.id} creado y enviado a bodega exitosamente!`;
                mensaje.style.color = 'green';
                document.getElementById('form-crear-pedido').reset();
                document.getElementById('contenedor-detalles-pedido').innerHTML = '';
            } catch (error) {
                mensaje.textContent = `Error: ${error.message}`;
                mensaje.style.color = 'red';
            } finally {
                boton.textContent = 'Enviar Pedido a Bodega';
                boton.disabled = false;
            }
        }

        // --- ¡VISTA 6 incidencias de kardex y estado---
        function cargarVistaIncidencias() {
            setBotonActivo('btn-gestion-kardex');
            panelAdmin.innerHTML = `
                <h1>Gestion de Incidencias de Kardex</h1>
                <p>Revise y resuelva las fallas reportadas por los operarios.</p>
                
                <div class="admin-seccion">
                    <h2>Incidencias Abiertas</h2>
                    <table class="admin-table" id="tabla-incidencias-abiertas">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Kardex</th>
                                <th>Fecha Reporte</th>
                                <th>Reportado Por</th>
                                <th>Descripcion de Falla</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6">Cargando incidencias...</td></tr>
                        </tbody>
                    </table>
                </div>

                <!-- Formulario para Resolver (se muestra al hacer clic) -->
                <div id="form-resolver-seccion" class="admin-seccion" style="display:none;">
                    <h2>Resolver Incidencia <span id="resolver-incidencia-id"></span></h2>
                    <div class="incidencia-reporte-bloque">
                        <span>Reporte del Operario:</span>
                        <p id="resolver-reporte-texto"></p>
                    </div>
                    <form id="form-resolver-incidencia" class="form-grid">
                        <input type="hidden" id="resolver-id-hidden">
                        <div class="form-group">
                            <label for="resolver-respuesta">Respuesta y Plan de Accion</label>
                            <textarea id="resolver-respuesta" rows="3" required></textarea>
                        </div>
                        <div class="form-group">
                            <label for="resolver-fecha-programada">Fecha Resolucion Programada (Opcional)</label>
                            <input type="datetime-local" id="resolver-fecha-programada">
                        </div>
                        <div class="form-group">
                            <label for="resolver-estado">Actualizar Estado</label>
                            <select id="resolver-estado" required>
                                <option value="en_mantencion">En Mantencion (Sigue abierta)</option>
                                <option value="resuelta">Resuelta (Poner operativa)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-submit-admin">Guardar Resolucion</button>
                        <button type="button" id="btn-cancelar-resolucion" style="background-color: #6c757d; color: white;">Cancelar</button>
                    </form>
                    <p id="resolver-mensaje"></p>
                </div>
            `;
            
            document.getElementById('form-resolver-incidencia').addEventListener('submit', enviarResolucion);
            document.getElementById('btn-cancelar-resolucion').addEventListener('click', () => {
                document.getElementById('form-resolver-seccion').style.display = 'none';
            });
            
            buscarIncidencias();
        }

        async function buscarIncidencias() {
            const tablaBody = document.querySelector('#tabla-incidencias-abiertas tbody');
            try {
                // Busca las incidencias abiertas
                const respuesta = await fetch(`${urlBaseApi}/kardex/incidencias/?estado=abierta`, { headers });
                if (!respuesta.ok) throw new Error('Error al buscar incidencias.');
                
                cacheIncidencias = await respuesta.json(); // Guardar en cache
                
                tablaBody.innerHTML = '';
                if (cacheIncidencias.length === 0) {
                    tablaBody.innerHTML = `<tr><td colspan="6">No hay incidencias abiertas.</td></tr>`;
                    return;
                }
                
                cacheIncidencias.forEach(inc => {
                    // Formatea fecha
                    const fecha = new Date(inc.fecha_reporte).toLocaleString('es-CL');
                    
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${inc.id}</td>
                            <td>${inc.kardex.identificador} (${inc.kardex.nombre})</td>
                            <td>${fecha}</td>
                            <td>${inc.usuario_reporta.nombre_usuario}</td>
                            <td>${inc.reporte_operario}</td>
                            <td><button class="btn-resolver" data-id="${inc.id}">Resolver</button></td>
                        </tr>
                    `;
                });
                
                document.querySelectorAll('.btn-resolver').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const id = e.target.dataset.id;
                        // Busca la incidencia en el cach
                        const incidencia = cacheIncidencias.find(i => i.id == id);
                        if (incidencia) {
                            mostrarFormularioResolver(incidencia);
                        }
                    });
                });
            } catch (error) {
                tablaBody.innerHTML = `<tr><td colspan="6" style="color:red;">${error.message}</td></tr>`;
            }
        }
        
        function mostrarFormularioResolver(incidencia) {
            document.getElementById('form-resolver-seccion').style.display = 'block';
            document.getElementById('resolver-incidencia-id').textContent = `(ID: ${incidencia.id})`;
            document.getElementById('resolver-reporte-texto').textContent = incidencia.reporte_operario;
            document.getElementById('resolver-id-hidden').value = incidencia.id;
            
            // Limpiar campos
            document.getElementById('resolver-respuesta').value = '';
            document.getElementById('resolver-fecha-programada').value = '';
            document.getElementById('resolver-estado').value = 'en_mantencion';
            document.getElementById('resolver-mensaje').textContent = '';
            
            document.getElementById('form-resolver-seccion').scrollIntoView({ behavior: 'smooth' });
        }

        async function enviarResolucion(e) {
            e.preventDefault();
            const mensaje = document.getElementById('resolver-mensaje');
            const boton = e.target.querySelector('button[type="submit"]');
            const incidenciaId = document.getElementById('resolver-id-hidden').value;
            
            let fechaProgramada = document.getElementById('resolver-fecha-programada').value;
            if (!fechaProgramada) {
                fechaProgramada = null;
            }

            const payload = {
                respuesta_admin: document.getElementById('resolver-respuesta').value,
                fecha_resolucion_programada: fechaProgramada,
                estado_incidencia: document.getElementById('resolver-estado').value
            };

            boton.textContent = 'Guardando...';
            boton.disabled = true;
            mensaje.textContent = '';
            
            try {
                const respuesta = await fetch(`${urlBaseApi}/kardex/incidencias/${incidenciaId}/resolver/`, {
                    method: 'PUT',
                    headers: headers,
                    body: JSON.stringify(payload)
                });

                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al resolver la incidencia.');
                }

                mensaje.textContent = 'Incidencia actualizada exitosamente';
                mensaje.style.color = 'green';
                
                // Ocultar el formulario y recargar la lista
                document.getElementById('form-resolver-seccion').style.display = 'none';
                await buscarIncidencias();

            } catch (error) {
                mensaje.textContent = `Error: ${error.message}`;
                mensaje.style.color = 'red';
            } finally {
                boton.textContent = 'Guardar Resolución';
                boton.disabled = false;
            }
        }

        // --- VISTA 7: REPORTES ---
        function cargarVistaReportes() {
            setBotonActivo('btn-reportes'); 
            const hoy = new Date().toISOString().split('T')[0];
            
            panelAdmin.innerHTML = `
                <h1>Reportes y Trazabilidad de la Farmacia Unidosis</h1>
                <p>Seleccione un rango de fechas y descargue los registros completos del sistema.</p>
                
                <div class="admin-seccion">
                    <h2>Reporte de Trazabilidad de Inventario (CSV)</h2>
                    <p>Contiene todos los movimientos de stock (entradas, salidas, ajustes) con detalle de lote y vencimiento.</p>
                    <form id="form-reporte-trazabilidad" class="form-grid">
                        <div class="form-group">
                            <label for="traz-fecha-inicio">Fecha de Inicio</label>
                            <input type="date" id="traz-fecha-inicio" value="${hoy}" required>
                        </div>
                        <div class="form-group">
                            <label for="traz-fecha-fin">Fecha de Fin</label>
                            <input type="date" id="traz-fecha-fin" value="${hoy}" required>
                        </div>
                        <button type="submit" class="btn-submit-admin" id="btn-descargar-trazabilidad">Descargar Reporte</button>
                    </form>
                    <p id="traz-mensaje"></p>
                </div>

                <hr>

                <div class="admin-seccion">
                    <h2>Reporte de Auditoria del Sistema</h2>
                    <p>Contiene un registro completo de todas las acciones (logins, creación de usuarios, recetas, errores, etc.).</p>
                    <form id="form-reporte-auditoria" class="form-grid">
                        <div class="form-group">
                            <label for="audit-fecha-inicio">Fecha de Inicio</label>
                            <input type="date" id="audit-fecha-inicio" value="${hoy}" required>
                        </div>
                        <div class="form-group">
                            <label for="audit-fecha-fin">Fecha de Fin</label>
                            <input type="date" id="audit-fecha-fin" value="${hoy}" required>
                        </div>
                        <button type="submit" class="btn-submit-admin" id="btn-descargar-auditoria">Descargar Reporte</button>
                    </form>
                    <p id="audit-mensaje"></p>
                </div>
            `;
            
            document.getElementById('form-reporte-trazabilidad').addEventListener('submit', descargarReporteTrazabilidad);
            document.getElementById('form-reporte-auditoria').addEventListener('submit', descargarReporteAuditoria);
        }
        async function descargarReporteTrazabilidad(e) {
            e.preventDefault();
            const mensaje = document.getElementById('traz-mensaje');
            const boton = document.getElementById('btn-descargar-trazabilidad');
            const fechaInicio = document.getElementById('traz-fecha-inicio').value;
            const fechaFin = document.getElementById('traz-fecha-fin').value;

            if (!fechaInicio || !fechaFin) {
                mensaje.textContent = 'Debe seleccionar una fecha de inicio y fin.';
                mensaje.style.color = 'red';
                return;
            }

            boton.textContent = 'Generando...';
            boton.disabled = true;
            mensaje.textContent = '';

            try {
                const url = `${urlBaseApi}/reportes/trazabilidad-inventario/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
                const respuesta = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
                
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al generar el reporte.');
                }
                
                const blob = await respuesta.blob();
                
                const linkDescarga = document.createElement('a');
                linkDescarga.href = window.URL.createObjectURL(blob);
                linkDescarga.download = `reporte_trazabilidad_${fechaInicio}_a_${fechaFin}.csv`;
                document.body.appendChild(linkDescarga);
                linkDescarga.click();
                document.body.removeChild(linkDescarga);

                mensaje.textContent = 'Reporte descargado exitosamente.';
                mensaje.style.color = 'green';

            } catch (error) {
                mensaje.textContent = `Error: ${error.message}`;
                mensaje.style.color = 'red';
            } finally {
                boton.textContent = 'Descargar Reporte';
                boton.disabled = false;
            }
        }
        async function descargarReporteAuditoria(e) {
            e.preventDefault();
            const mensaje = document.getElementById('audit-mensaje');
            const boton = document.getElementById('btn-descargar-auditoria');
            const fechaInicio = document.getElementById('audit-fecha-inicio').value;
            const fechaFin = document.getElementById('audit-fecha-fin').value;

            if (!fechaInicio || !fechaFin) {
                mensaje.textContent = 'Debe seleccionar una fecha de inicio y fin.';
                mensaje.style.color = 'red';
                return;
            }
            
            boton.textContent = 'Generando...';
            boton.disabled = true;
            mensaje.textContent = '';

            try {
                const url = `${urlBaseApi}/reportes/auditoria-sistema/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
                const respuesta = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
                
                if (!respuesta.ok) {
                    const err = await respuesta.json();
                    throw new Error(err.detail || 'Error al generar el reporte.');
                }
                
                const blob = await respuesta.blob();
                
                const linkDescarga = document.createElement('a');
                linkDescarga.href = window.URL.createObjectURL(blob);
                linkDescarga.download = `reporte_auditoria_${fechaInicio}_a_${fechaFin}.csv`;
                document.body.appendChild(linkDescarga);
                linkDescarga.click();
                document.body.removeChild(linkDescarga);

                mensaje.textContent = 'Reporte descargado exitosamente.';
                mensaje.style.color = 'green';

            } catch (error) {
                mensaje.textContent = `Error: ${error.message}`;
                mensaje.style.color = 'red';
            } finally {
                boton.textContent = 'Descargar Reporte';
                boton.disabled = false;
            }
        }
        
        // Carga la vista de cuentas por defecto al iniciar
        cargarVistaCuentas();
    }
});