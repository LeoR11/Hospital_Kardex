document.addEventListener('DOMContentLoaded', () => {
    const urlBaseApi = 'http://127.0.0.1:8000';

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
                window.location.href = 'panel.html';
            } catch (error) {
                mensajeError.textContent = error.message;
            }
        });
    }
    const panelContenido = document.getElementById('contenido-principal');
    if (panelContenido) {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'index.html';
            return;
        }

        const btnLogout = document.getElementById('btn-logout');
        btnLogout.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        });

        // --- Lógica específica para el formulario de recetas ---
        const formularioReceta = document.getElementById('formulario-receta');
        if (formularioReceta) {
            const selectProfesional = document.getElementById('profesional_id');
            const inputFecha = document.getElementById('fecha_emision');
            const contenedorDetalles = document.getElementById('contenedor-detalles');
            const btnAgregar = document.getElementById('btn-agregar-medicamento');
            const mensaje = document.getElementById('mensaje');

            let medicamentosDisponibles = [];

            // 1. Cargar datos necesarios al iniciar la página
            async function cargarDatosIniciales() {
                try {
                    // Cargar profesionales
                    const respProfesionales = await fetch(`${urlBaseApi}/profesionales/`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const profesionales = await respProfesionales.json();
                    profesionales.forEach(p => {
                        const option = document.createElement('option');
                        option.value = p.id;
                        option.textContent = `${p.nombre} (${p.run})`;
                        selectProfesional.appendChild(option);
                    });

                    // Cargar medicamentos
                    const respMedicamentos = await fetch(`${urlBaseApi}/medicamentos/`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    medicamentosDisponibles = await respMedicamentos.json();
                    
                    // Poner la fecha actual por defecto
                    inputFecha.value = new Date().toISOString().split('T')[0];
                    
                    // Agregar la primera línea de medicamento por defecto
                    agregarLineaMedicamento();

                } catch (error) {
                    mensaje.textContent = `Error al cargar datos: ${error.message}`;
                    mensaje.style.color = 'red';
                }
            }
            
            // 2. Función para agregar una nueva fila de medicamento
            function agregarLineaMedicamento() {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'detalle-item';
                
                const selectMedicamento = document.createElement('select');
                selectMedicamento.required = true;
                medicamentosDisponibles.forEach(m => {
                    const option = document.createElement('option');
                    option.value = m.id;
                    option.textContent = `${m.nombre} (Stock: ${m.stock_actual})`;
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
            
            // 3. Lógica para enviar el formulario completo
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
                    detallesPayload.push({
                        medicamento_id: parseInt(item.querySelector('select').value),
                        cantidad: parseInt(item.querySelector('input').value)
                    });
                });

                const recetaPayload = {
                    id_paciente: document.getElementById('id_paciente').value,
                    profesional_id: parseInt(selectProfesional.value),
                    fecha_emision: inputFecha.value,
                    detalles: detallesPayload
                };

                try {
                    const respuesta = await fetch(`${urlBaseApi}/recetas/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
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
                    agregarLineaMedicamento();
                    inputFecha.value = new Date().toISOString().split('T')[0];

                } catch (error) {
                    mensaje.textContent = error.message;
                    mensaje.style.color = 'red';
                }
            });

            cargarDatosIniciales();
        }
    }
});