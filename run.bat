@echo off
title TaskControl - Servidor Local
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo              Iniciando TaskControl...
echo ========================================================
echo.

set "FLASK_APP=src.taskcontrol:create_app()"
set "FLASK_ENV=development"
set "PYTHONPATH=%~dp0;%~dp0src"

REM Activar entorno virtual si existe
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    call "%~dp0venv\Scripts\activate.bat"
)

REM Ejecutar aplicacion con Flask
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m flask run --host 127.0.0.1 --port 5000
) else if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" -m flask run --host 127.0.0.1 --port 5000
) else (
    python -m flask run --host 127.0.0.1 --port 5000
)

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se detuvo con errores.
    pause
) else (
    echo.
    echo Servidor detenido correctamente.
    pause
)
