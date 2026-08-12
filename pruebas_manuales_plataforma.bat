@echo off
chcp 1252 > nul
title Pruebas manuales - Plataforma completa (MAN.2)
setlocal enabledelayedexpansion

if "%~1"=="" goto MENU
if "%~1"=="0" goto SMOKE
if "%~1"=="1" goto CAMINO1
if "%~1"=="2" goto CAMINO2
if "%~1"=="3" goto CAMINO3
if "%~1"=="4" goto CAMINO4
goto MENU

:MENU
echo.
echo ============================================================
echo   PRUEBAS MANUALES - PLATAFORMA COMPLETA (MAN.2)
echo ============================================================
echo.
echo Cada camino cruza varios modulos. Nadie los ha recorrido
echo enteros hasta MAN.2. Elige uno (tambien puedes pasar el
echo numero como parametro: pruebas_manuales_plataforma.bat 2):
echo.
echo   1. Organizacion nueva -^> dos chatbots -^> temas -^> widget
echo   2. Corpus ingerido -^> consulta -^> cita -^> feedback -^> hueco
echo   3. Plantilla de redaccion -^> borrador -^> anonimizacion -^> export
echo   4. Script propuesto -^> sandbox -^> aprobacion -^> agente local
echo   0. Solo comprobar que los servicios responden (smoke check)
echo.
set "OPCION="
set /p OPCION="Elige un numero: "
if "%OPCION%"=="1" goto CAMINO1
if "%OPCION%"=="2" goto CAMINO2
if "%OPCION%"=="3" goto CAMINO3
if "%OPCION%"=="4" goto CAMINO4
if "%OPCION%"=="0" goto SMOKE
echo Opcion no reconocida.
goto :EOF

:REQUISITOS
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS (comunes a los 4 caminos)
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha, y la BD arriba:
echo       docker compose up -d db
echo  2. Migraciones al dia (desde server\):
echo       uv run alembic upgrade head
echo  3. Backend (desde la raiz, tarda ~80s en arrancar):
echo       uv run --project server uvicorn server.app.main:app --port 8000
echo  4. Frontend (desde frontend\):
echo       npm run dev
echo  5. Sesion iniciada en http://localhost:5173/login como
echo     fabra@uji.es (SuperAdmin) o el admin de desarrollo.
echo.
pause
goto :EOF

:SMOKE
call :REQUISITOS
echo ------------------------------------------------------------
echo  SMOKE CHECK
echo ------------------------------------------------------------
curl -s -o nul -w "  backend  /health              -> %%{http_code}\n" http://127.0.0.1:8000/health
curl -s -o nul -w "  frontend /                     -> %%{http_code}\n" http://localhost:5173/
curl -s -o nul -w "  /hub/chatbots (sin sesion)      -> %%{http_code} (401 esperado)\n" http://127.0.0.1:8000/api/v1/hub/chatbots
curl -s -o nul -w "  /hub/sites (sin sesion)         -> %%{http_code} (401 esperado)\n" http://127.0.0.1:8000/api/v1/hub/sites
curl -s -o nul -w "  /hub/redaccion/templates (sin sesion) -> %%{http_code} (401 esperado)\n" http://127.0.0.1:8000/api/v1/hub/redaccion/templates
echo.
echo QUE DEBES VER: backend y frontend en 200; los tres endpoints
echo de la API en 401 (sin sesion todo pide login antes que nada).
echo.
pause
goto MENU

:CAMINO1
call :REQUISITOS
echo ============================================================
echo  CAMINO 1 - Organizacion nueva -^> dos chatbots -^> temas -^> widget
echo ============================================================
echo.
echo  a) Abre http://localhost:5173/hub/organizaciones
echo     Pulsa "Nueva organizacion". Nombre: "Organizacion Camino 1".
echo     Admin ID: cualquier texto, p.ej. "admin_camino1".
echo     Deja "Configuracion de tema (JSON)" como esta: ese campo
echo     escribe HubOrganizacion.theme_config, que MAN.2 descubrio que
echo     es una columna huerfana - nadie la lee. El tema de verdad se
echo     crea y se aplica en el paso (c).
echo     QUE DEBES VER: la organizacion aparece en la lista con 0 chatbots.
echo.
echo  b) Ve a http://localhost:5173/hub/chatbots -^> "Nuevo chatbot".
echo     Crea DOS chatbots bajo "Organizacion Camino 1":
echo       "Chatbot Camino1 A" y "Chatbot Camino1 B".
echo     QUE DEBES VER: ambos en la lista, modo Vectorial RAG, Activo.
echo.
echo  c) CAMBIO DESDE MAN.2: el widget YA aplica el tema del chatbot.
echo     El hallazgo #3 se arreglo el 2026-08-10 y SEC.8.6 movio los
echo     temas del disco a la BD. Todavia NO hay pantalla de temas en
echo     el panel (queda para un prompt propio), asi que va por API.
echo     Necesitas el chatbot_id (copialo de la URL al editar el
echo     chatbot) y tu token de sesion (F12 -^> Application -^>
echo     Local Storage). Luego, sustituyendo TOKEN y los ids:
echo.
echo   curl -X POST http://127.0.0.1:8000/api/v1/hub/themes -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d "{\"name\":\"Tema Camino 1\",\"organizacion_id\":\"ORG_ID\",\"config\":{\"colors\":{\"primary\":\"#c026d3\"}}}"
echo.
echo   curl -X POST -H "Authorization: Bearer TOKEN" http://127.0.0.1:8000/api/v1/hub/themes/THEME_ID/apply/CHATBOT_ID
echo.
echo     QUE DEBES VER: 201 al crear y 200 al aplicar. El apply guarda
echo     {"theme_id":...} en HubChatbot.theme_config, que es el puntero
echo     que lee el widget.
echo.
echo  d) El widget necesita una credencial de sitio, no un token de
echo     admin. SEC.8.5 retiro el Bearer privilegiado: el widget manda
echo     la cabecera X-Widget-Key y el atributo data-token de
echo     widget.html YA NO SE LEE. Emite la credencial:
echo.
echo   curl -X POST -H "Authorization: Bearer TOKEN" http://127.0.0.1:8000/api/v1/hub/chatbots/CHATBOT_ID/widget-keys
echo.
echo     Copia la clave que devuelve (se muestra una sola vez). Luego,
echo     desde frontend\ y en dos pasos (^&^& no existe en PowerShell):
echo       cd frontend
echo       npm run build:widget
echo     Abre frontend/widget.html y pon TU chatbot_id en
echo     data-chatbot-id y la clave en data-widget-key. Sirvelo con
echo     http://localhost:5173/widget.html
echo     QUE DEBES VER: el cuadro de chat carga Y sale pintado con el
echo     color del paso (c) - comprueba en F12 -^> Elements que :root
echo     tiene --color-primary: #c026d3. Sin credencial valida,
echo     preguntar da 401: eso es SEC.8.5 funcionando, no un fallo.
echo     OJO: el chatbot debe tener access_mode public_anon.
echo.
pause
goto MENU

:CAMINO2
call :REQUISITOS
echo ============================================================
echo  CAMINO 2 - Corpus -^> consulta -^> cita -^> feedback -^> hueco
echo ============================================================
echo.
echo  a) Abre http://localhost:5173/hub/documents, elige un chatbot
echo     con modo Vectorial (RAG) y arrastra un fichero .md.
echo     OJO - CAMBIO DE EXT.1: al corpus YA NO se sube un PDF. Solo
echo     entra Markdown conforme al contrato, porque lo que el
echo     asistente cita ante un ciudadano tiene que venir del pipeline
echo     de curacion, donde la conversion se revisa. Un PDF ahora da
echo     415 con un mensaje que lo explica: probarlo tambien vale.
echo     Coge un .md de la carpeta md_contracte del proyecto de
echo     curacion del corpus.
echo     QUE DEBES VER: aparece en "Jobs (tecnico)" como "Procesando"
echo     y luego pasa a la tabla "Documentos del corpus" con su
echo     recuento de tokens.
echo.
echo  b) IMPORTANTE - por que este paso usa el chat real y NO
echo     Escenarios de prueba: se comprobo en MAN.2 que "Ejecutar" en
echo     /hub/test-scenarios llama a un endpoint que fija
echo     fallback_reason=None a proposito (hub_test_scenarios_router.py
echo     linea 256) porque es para revision humana, no para alimentar
echo     la deteccion de huecos. Sin una fila real en HubInteraction
echo     con fallback_reason, el paso (e) de abajo nunca encontrara
echo     nada. Usa el chat de verdad: el widget (ver Camino 1d) o,
echo     si tienes Postman/curl con tu token de sesion, un POST a
echo       /api/v1/hub/chat/{chatbot_id}
echo.
echo  c) Pregunta algo relacionado con la norma cargada.
echo     QUE DEBES VER: la respuesta cita el documento (fuente
echo     enlazada). Al venir de un .md curado el texto es limpio, asi
echo     que la cita deberia salir con su articulo.
echo.
echo  d) Repite una pregunta MUY parecida 3 veces (o mas) SIN corpus
echo     que la responda, para forzar un hueco real.
echo.
echo  e) Ve a http://localhost:5173/curation/findings, elige el mismo
echo     chatbot, pulsa "Buscar huecos".
echo     QUE DEBES VER: un hueco con el recuento de consultas, las
echo     fechas y los terminos que las relacionan. Vuelve a pulsar:
echo     el recuento NO debe duplicarse.
echo.
echo  f) Da feedback bajo (puntuacion <= 2) a una respuesta real desde
echo     el widget o via /api/v1/hub/feedback, y comprueba en
echo     http://localhost:5173/hub/reports que aparece en el listado.
echo.
pause
goto MENU

:CAMINO3
call :REQUISITOS
echo ============================================================
echo  CAMINO 3 - Plantilla de redaccion -^> borrador -^> anonimizacion -^> export
echo ============================================================
echo.
echo  BLOQUEADO - BUG REAL DESTAPADO EN MAN.2, PENDIENTE DE ARREGLAR:
echo    GET /api/v1/hub/redaccion/templates devuelve 500 para
echo    CUALQUIER sesion cuyo user_id no sea un UUID valido. El
echo    SuperAdmin de desarrollo tiene admin_id entero (ej. "1") y
echo    el Admin de desarrollo tiene partner_id de texto libre
echo    (ej. "admin_dev"); ninguno de los dos es un UUID, y
echo    hub_redaccion_router.py hace uuid.UUID(user.user_id) sin
echo    comprobarlo en 6 sitios distintos (listar, crear plantilla,
echo    crear workspace...). El frontend no muestra el error: la
echo    pantalla /redaccion/wizard se queda en blanco sin avisar.
echo.
echo    Antes de intentar este camino, comprueba si ya esta arreglado:
curl -s -o nul -w "  /hub/redaccion/templates -> %%{http_code} (500 = bug aun presente)\n" -H "Authorization: Bearer TU_TOKEN" http://127.0.0.1:8000/api/v1/hub/redaccion/templates
echo.
echo    Si sigue en 500, este camino no se puede recorrer todavia.
echo    Si ya da 200, sigue con:
echo      a) /redaccion/wizard -^> crear plantilla -^> generar borrador LLM
echo      b) anonimizar un documento con datos sinteticos (nunca
echo         reales) desde el flujo de redaccion
echo      c) exportar a DOCX/PDF y abrirlo en Word/Adobe reales
echo.
pause
goto MENU

:CAMINO4
call :REQUISITOS
echo ============================================================
echo  CAMINO 4 - Script propuesto -^> sandbox -^> aprobacion -^> agente local
echo ============================================================
echo.
echo  Este camino no vive en un unico navegador: cruza el backend,
echo  el contenedor script-sandbox y el proceso de escritorio
echo  client_app hablando por WebSocket. MAN.2 no lo automatiza
echo  completo; son los pasos para que un humano lo recorra:
echo.
echo  a) Con docker-compose.prod.yml (ver pruebas_manuales_promptSBX_4.bat
echo     para el aislamiento de red del sandbox), propone un script:
echo       POST /api/v1/redaccion/scripts/propose
echo  b) Pideselo probar en el sandbox:
echo       POST /api/v1/redaccion/scripts/{id}/test
echo     QUE DEBES VER: docker compose -f docker-compose.prod.yml logs
echo     script-sandbox muestra la peticion a /execute-extraction.
echo  c) Aprueba el script desde el panel (revision de scripts).
echo  d) Arranca client_app en tu maquina (ver client_app/README o
echo     docs/) y comprueba que recibe la orden de ejecucion por
echo     WebSocket y la ejecuta localmente - el cloud orquesta, el
echo     edge ejecuta, nunca al reves.
echo.
pause
goto MENU
