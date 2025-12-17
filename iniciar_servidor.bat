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

:: Inicia el servidor (SIN BORRAR LA BASE DE DATOS)
ECHO Iniciando servidor Uvicorn en http://127.0.0.1:8000
uvicorn main:aplicacion --reload

:: Mantiene la ventana abierta al finalizar
pause