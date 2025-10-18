document.addEventListener('DOMContentLoaded', () => {

    const urlBaseApi = 'http://127.0.0.1:8000';

    // --- (index.html) ---
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
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: new URLSearchParams({
                        'username': nombreUsuario,
                        'password': clave
                    })
                });

                if (!respuesta.ok) {
                    const error = await respuesta.json();
                    throw new Error(error.detail || 'Usuario o contraseña incorrectos.');
                }
                
                const data = await respuesta.json();
                // guarda el token 
                localStorage.setItem('token', data.access_token);
                // mandaal panel principal
                window.location.href = 'panel.html';

            } catch (error) {
                mensajeError.textContent = error.message;
            }
        });
    }

    // --- (panel.html) ---
    const panelContenido = document.getElementById('contenido-principal');
    if (panelContenido) {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'index.html'; // Si no hay token, el usuario no está autenticado.
            return;
        }

        const btnInventario = document.getElementById('btn-inventario');
        const btnLogout = document.getElementById('btn-logout');

        // mostrar la tabla de inventario
        async function cargarInventario() {
            try {
                const respuesta = await fetch(`${urlBaseApi}/medicamentos/`, {
                    headers: { 
                        'Authorization': `Bearer ${token}` 
                    }
                });
                if (!respuesta.ok) {
                    throw new Error('No se pudo cargar el inventario. Por favor, inicie sesión de nuevo.');
                }

                const medicamentos = await respuesta.json();
                
                let tablaHtml = `
                    <h1>Gestión de Inventario</h1>
                    <table>
                        <thead>
                            <tr>
                                <th>Medicamento</th>
                                <th>Código</th>
                                <th>Stock Actual</th>
                                <th>Ubicación</th>
                                <th>Umbral Mínimo</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                medicamentos.forEach(med => {
                    const estado = med.stock_actual < med.umbral_minimo 
                        ? '<span class="estado-bajo">Bajo Stock</span>' 
                        : 'OK';
                    
                    tablaHtml += `
                        <tr>
                            <td>${med.nombre}</td>
                            <td>${med.id}</td> <td>${med.stock_actual}</td>
                            <td>-</td> <td>${med.umbral_minimo}</td>
                            <td>${estado}</td>
                        </tr>
                    `;
                });

                tablaHtml += `</tbody></table>`;
                panelContenido.innerHTML = tablaHtml;

            } catch (error) {
                panelContenido.innerHTML = `<p style="color:red;">${error.message}</p>`;
            }
        }

        // --- Event Listeners para los botones ---
        btnInventario.addEventListener('click', cargarInventario);
        
        btnLogout.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        });

        cargarInventario();
    }
});