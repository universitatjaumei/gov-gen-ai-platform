@echo off
chcp 1252 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque Fase 11 (Autoinstalacion)
echo.
echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE FASE 11 (Autoinstalacion)
echo ============================================================
echo.
echo Este bloque verifica la instalacion "one-click" completa.
echo Es lo unico que el agente no puede comprobar por si mismo:
echo construye 6 servicios y ocupa los puertos 80 y 443 de tu
echo maquina, que es una decision tuya.
echo.
echo REQUISITOS PREVIOS
echo   1. Docker Desktop arrancado (icono verde).
echo   2. Puertos 80, 443 y 5432 LIBRES.
echo      Si tienes la BD de desarrollo levantada, parala antes:
echo         docker compose -f docker-compose.yml down
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 1 - Generar la configuracion desde cero
echo ------------------------------------------------------------
echo Ejecuta en una terminal Git Bash, en la raiz del proyecto:
echo.
echo     bash scripts/generate_env.sh --mode local --force
echo.
echo QUE DEBES VER: se crean o actualizan .env, server/.env y
echo frontend/.env, cada uno con secretos distintos.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 2 - Ensayo en seco de la instalacion
echo ------------------------------------------------------------
echo     bash scripts/setup.sh --dry-run
echo.
echo QUE DEBES VER: comprueba docker y los tres puertos, y lista
echo el plan con el prefijo [DRY-RUN]. NO debe crear nada.
echo Si algun puerto sale OCUPADO, liberalo antes de seguir.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 3 - Instalacion real (tarda varios minutos)
echo ------------------------------------------------------------
echo     bash scripts/setup.sh
echo.
echo Te pedira correo, nombre y contrasena del SuperAdmin.
echo La contrasena NO debe aparecer en pantalla al escribirla.
echo.
echo QUE DEBES VER al terminar:
echo   - 5/5 Instalacion completada
echo   - las URLs del frontend y del panel
echo   - lineas [creado] para SuperAdmin, organizacion, chatbot
echo     y los tres prompts (es, ca, en)
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 4 - Comprobar que el stack responde
echo ------------------------------------------------------------
echo Estado de los servicios:
echo.
docker compose -f docker-compose.prod.yml ps
echo.
echo Comprobando endpoints...
curl -s -o nul -w "  backend  -> HTTP %%{http_code}\n" http://localhost:8000/health
curl -s -o nul -w "  frontend -> HTTP %%{http_code}\n" http://localhost/
echo.
echo QUE DEBES VER: ambos HTTP 200, y en la tabla de arriba los
echo servicios app, frontend, postgres, minio y script-sandbox
echo en estado healthy.
echo El servicio ollama NO debe aparecer (es opcional).
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 5 - En el navegador
echo ------------------------------------------------------------
echo   1. Abre http://localhost/
echo      QUE DEBES VER: carga la interfaz, sin pagina en blanco
echo      ni error de nginx.
echo.
echo   2. Abre http://localhost/hub
echo      Entra con el correo y la contrasena del SuperAdmin.
echo      QUE DEBES VER: el panel de administracion.
echo.
echo   3. Ve a la lista de chatbots.
echo      QUE DEBES VER: aparece "Chatbot de Ejemplo".
echo.
echo   4. Abre ese chatbot y mira sus prompts.
echo      QUE DEBES VER: tres prompts de bienvenida (es, ca, en)
echo      con texto DISTINTO en cada idioma.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASO 6 - Idempotencia (el criterio de aceptacion)
echo ------------------------------------------------------------
echo Vuelve a ejecutar la instalacion:
echo.
echo     bash scripts/setup.sh --skip-stack
echo.
echo QUE DEBES VER: todas las lineas dicen [ya existia] y al final
echo "Nada que hacer: la instalacion ya estaba sembrada".
echo.
echo Y en el panel: sigue habiendo UN solo "Chatbot de Ejemplo"
echo y TRES prompts. Si hay duplicados, la prueba ha fallado.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE (opcionales)
echo ------------------------------------------------------------
echo   [ ] Ocupa el puerto 80 con otra cosa y lanza setup.sh:
echo       debe listar los puertos ocupados y abortar sin tocar
echo       nada.
echo.
echo   [ ] Cambia la contrasena del SuperAdmin desde el panel y
echo       reejecuta setup.sh --skip-stack: la contrasena NUEVA
echo       debe seguir funcionando (no se revierte).
echo.
echo   [ ] Lanza setup.sh --non-interactive sin definir
echo       SUPERADMIN_EMAIL: debe abortar diciendo que falta.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PARA TERMINAR
echo ------------------------------------------------------------
echo Detener el stack de produccion conservando los datos:
echo     docker compose -f docker-compose.prod.yml down
echo.
echo Volver al entorno de desarrollo:
echo     docker compose -f docker-compose.yml up -d postgres
echo.
echo PRUEBAS COMPLETADAS
pause
