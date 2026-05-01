@echo off
title Lanzador de Pruebas - GovGenAI Widget
echo ====================================================
echo   INICIANDO ENTORNO DE PRUEBAS PARA EL WIDGET
echo ====================================================

:: 1. Entrar en la carpeta frontend
cd frontend

echo [1/3] Construyendo el Widget (Borrando errores de desarrollo)...
call npm run build:widget

echo [2/3] Lanzando el servidor estatico en una ventana nueva...
:: Lanzamos el servidor en una ventana aparte para que no bloquee esta
start cmd /k "npx serve ."

echo [3/3] Abriendo el navegador...
:: Esperamos 3 segundos para dar tiempo al servidor a arrancar
timeout /t 3 /nobreak > nul
start http://localhost:3000/test_widget.html

echo.
echo ====================================================
echo TODO LISTO:
echo 1. Verifica que Docker (Backend) este encendido.
echo 2. No cierres la ventana negra que dice 'serve'.
echo 3. Si haces cambios en el codigo, cierra todo y 
echo    vuelve a ejecutar este archivo .bat.
echo ====================================================
pause