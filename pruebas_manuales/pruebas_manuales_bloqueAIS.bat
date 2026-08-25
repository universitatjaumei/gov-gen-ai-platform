@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ==========================================================
echo   PRUEBAS MANUALES - BLOQUE AIS (aislamiento del nucleo)
echo ==========================================================
echo.
echo El bloque AIS es casi todo estructura: direccion de imports,
echo gobernanza, higiene del arranque. Eso lo cubren los tests.
echo Aqui esta solo lo que necesita ojos humanos.
echo.
echo Lo que YA se verifico en navegador durante el bloque:
echo   - AIS.1: la paleta del panel en modo claro y oscuro, con los
echo     contrastes medidos pixel a pixel (pasan AA en los dos).
echo     Consola limpia en dos pantallas.
echo.
pause

echo.
echo ---------- 1. REQUISITOS PREVIOS ----------
echo.
echo   a) Docker Desktop en marcha.
echo   b) docker compose up -d postgres
echo   c) cd server  y luego  uv run alembic upgrade head
echo   d) cd server  y luego  uv run uvicorn app.main:app --port 8000
echo   e) cd frontend  y luego  npm run dev
echo.
pause

echo.
echo ---------- 2. LA MIGRACION DE AIS.5 ----------
echo.
cd server
call uv run alembic current
cd ..
echo.
echo   DEBE decir: v2o3p4q5r6s7 (head)
echo.
echo   Anade hub_organizaciones.anonymization_mode, nullable.
echo   Nulo = esta organizacion no ha fijado politica, y entonces
echo   manda el valor del codigo. El piloto no nota nada.
echo.
pause

echo.
echo ---------- 3. EL ARRANQUE SE LEE ----------
echo.
echo   Mira la terminal donde corre uvicorn.
echo.
echo   QUE DEBES VER:
echo     - Lineas con fecha, hora y nivel, del estilo:
echo       2026-08-25 10:12:03 INFO     govgenai - Refrescando...
echo     - NINGUNA linea suelta del estilo "[STARTUP] ...".
echo.
echo   Antes de AIS.8 el servidor hablaba por print: sin nivel y sin
echo   hora. Si ves ese formato viejo, algo no se aplico.
echo.
pause

echo.
echo ---------- 4. EL ENLACE AL CODIGO FUENTE (parrafo 13 AGPL) ----------
echo.
echo Sin configurar, no debe aparecer nada. Comprobamos el endpoint:
echo.
curl -s http://localhost:8000/api/v1/instancia
echo.
echo.
echo   Se espera: {"source_url":null}
echo.
echo   AHORA, para verlo funcionando:
echo   1. Para el servidor (Ctrl+C).
echo   2. Anade a server\.env esta linea:
echo        SOURCE_URL=https://github.com/ModestoFabra/gov-gen-ai-platform
echo   3. Arranca el servidor otra vez.
echo   4. Recarga el panel: http://localhost:5173
echo.
echo   QUE DEBES VER:
echo     - Abajo del todo del menu lateral, debajo de "Cerrar sesion",
echo       un enlace "Codigo fuente" que abre en pestana nueva.
echo.
echo   5. Abre tambien el widget publico (frontend\widget.html o la
echo      pagina donde lo tengas incrustado).
echo.
echo   QUE DEBES VER:
echo     - El mismo enlace al pie del widget, debajo del aviso de IA.
echo       ESTE es el caso importante: la ciudadania que usa el chatbot
echo       tambien son usuarios a los que la licencia obliga.
echo.
pause

echo.
echo ---------- 5. LA IDENTIDAD NO CAMBIA AL CAMBIAR DE MODO ----------
echo.
echo   1. En el panel, activa el modo oscuro del sistema operativo
echo      (o anade la clase "dark" al elemento html desde F12).
echo.
echo   QUE DEBES VER:
echo     - El lateral y los botones siguen siendo AZULES, mas claros
echo       para el fondo oscuro.
echo     - NO deben volverse turquesa: eso era la marca de otra
echo       institucion, y era el defecto que AIS.1 corrigio.
echo     - El texto se lee comodo sobre el fondo en los dos modos.
echo.
echo   Esto ya se midio (contrastes AA en ambos modos), pero el
echo   juicio de si "se ve bien" es tuyo.
echo.
pause

echo.
echo ---------- 6. LA ANONIMIZACION SE PUEDE ELEGIR ----------
echo.
echo   1. Abre un informe en Informes.
echo   2. Busca el panel de anonimizacion.
echo.
echo   QUE DEBES VER:
echo     - El panel CARGA. Antes de AIS.4 no funcionaba nunca:
echo       llamaba sin credencial y recibia 401.
echo     - Puedes elegir entre los cuatro modos y guardar.
echo.
echo   Y la regla de AIS.5, si quieres comprobarla:
echo     - Sin politica de organizacion, puedes elegir cualquier modo,
echo       incluido "off". La anonimizacion es configurable.
echo     - Si un superadministrador fija una politica en la
echo       organizacion, un informe puede ENDURECERLA pero no
echo       relajarla, y la respuesta explica por que.
echo.
pause

echo.
echo ==========================================================
echo   PRUEBAS COMPLETADAS
echo ==========================================================
echo.
echo Si anadiste SOURCE_URL a server\.env solo para la prueba,
echo acuerdate de quitarlo o dejarlo puesto a conciencia.
echo.
echo Para detener los servicios:
echo   - Ctrl+C en las terminales del backend y del frontend.
echo   - docker compose stop postgres
echo.
pause
