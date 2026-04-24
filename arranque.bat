@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo       GOV GEN AI PLATFORM
echo ========================================
echo.
echo  1. Servidor FastAPI (desarrollo)
echo  2. Aplicacion NiceGUI legacy
echo.
set /p OPCION="Selecciona [1/2]: "

if "%OPCION%"=="1" goto :servidor
if "%OPCION%"=="2" goto :legacy

echo [ERROR] Opcion no valida.
pause
exit /b 1

:servidor
echo.
echo [INFO] Verificando que Docker Desktop esta corriendo (PostgreSQL + MinIO)...
echo [INFO] Levantando servidor FastAPI en http://localhost:8000
echo [INFO] Swagger UI en http://localhost:8000/docs
echo.
set PYTHONUNBUFFERED=1
cd /d "%~dp0server"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd /d "%~dp0"
goto :fin

:legacy
echo.
echo [INFO] Iniciando aplicacion NiceGUI (modo legacy)...
set PYTHONUNBUFFERED=1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    uv run main.py
)
goto :fin

:fin
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La aplicacion se cerro con errores.
    pause
)
