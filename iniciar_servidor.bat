@echo off
TITLE Servidor Backend del Kardex
ECHO Iniciando el servidor del Kardex...

:: Navega al disco D: (por si acaso)
D:

:: Navega a la carpeta del proyecto
cd "D:\Proyecto integrado\hospital_kardex"

:: Activa el entorno virtual
ECHO Activando entorno virtual...
CALL .\backend\venv\Scripts\activate

:: Navega a la carpeta del backend
cd backend

:: Crea los kardex si no existen
ECHO Creando/Verificando la base de datos (K1, K2)...
python crear_base_de_datos.py

:: Inicia el servidor
ECHO Iniciando servidor Uvicorn en http://127.0.0.1:8000
uvicorn main:aplicacion --reload

:: Mantiene la ventana abierta al finalizar
pause

:: Ruta por defecto D:\Proyecto integrado\hospital_kardex\backend (cambiar si es necesario)
::Joaco weko