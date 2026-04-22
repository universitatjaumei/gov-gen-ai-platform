@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo       INICIANDO GOV GEN AI
echo       (Modo Nativo Desktop)
echo ========================================
echo.
echo [INFO] Cargando entorno...
echo [INFO] Por favor espere...
echo.

:: Forzar salida de logs inmediata (Debug)
set PYTHONUNBUFFERED=1

:: Ejecutar aplicacion con Python del entorno virtual
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo [INFO] No se encontro .venv local. Intentando ejecutar mediante 'uv run'...
    uv run main.py
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion se cerro con errores.
    pause
)