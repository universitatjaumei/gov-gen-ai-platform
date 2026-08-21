@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - Bloque RAG (prompts RAG.6a a RAG.14)
echo ============================================================
echo.
echo Lo que el agente YA verifico solo (no hace falta repetirlo):
echo   - Suite backend completa en verde tras cada prompt.
echo   - Los 6 endpoints de escenarios responden y exigen sesion.
echo   - 220 tests de frontend y TypeScript sin errores.
echo   - CLI de re-embedding en seco y en real contra el corpus de prueba.
echo.
echo Lo que NO pudo verificar y por eso estas aqui:
echo   - La pantalla de escenarios en el navegador. La extension de
echo     Chrome pidio permiso y se denego, asi que la revision visual
echo     queda para ti.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  ANTES DE EMPEZAR
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha (icono verde).
echo  2. Base de datos arriba:  docker compose up -d db
echo  3. Migraciones al dia:    cd server  y luego  uv run alembic upgrade head
echo  4. Backend:   uv run --project server uvicorn server.app.main:app --port 8000
echo     (tarda ~80 segundos en arrancar: carga los modelos)
echo  5. Frontend:  cd frontend  y luego  npm run dev
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 1 - Los servicios responden
echo ------------------------------------------------------------
curl -s -o nul -w "backend  salud   -^> %%{http_code}\n" http://127.0.0.1:8000/health
curl -s -o nul -w "frontend inicio  -^> %%{http_code}\n" http://localhost:5173/
echo.
echo Los dos deben decir 200. Si el backend da 000, sigue arrancando.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 2 - Los endpoints nuevos existen y estan cerrados
echo ------------------------------------------------------------
curl -s -o nul -w "sin sesion -^> %%{http_code} (debe ser 401)\n" http://127.0.0.1:8000/api/v1/hub/chatbots/00000000-0000-0000-0000-000000000100/test-scenarios
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 3 - Escenarios de prueba en la interfaz
echo ------------------------------------------------------------
echo  Abre http://localhost:5173/hub/test-scenarios y entra como admin.
echo.
echo  a) Elige un chatbot en el desplegable de arriba.
echo  b) Pulsa "Nuevo escenario" y rellena:
echo        Nombre:        Dieta a Madrid
echo        Consulta:      quant cobro de dieta per anar a Madrid?
echo        Que se espera: Debe citar el reglamento de indemnizaciones.
echo     Guarda.
echo.
echo  c) Marca la casilla "Capturar el contexto".
echo  d) Pulsa "Ejecutar" en el escenario. Tarda unos segundos: llama al LLM.
echo  e) Debe aparecer debajo una ejecucion con la respuesta y, si el
echo     chatbot tiene corpus, una o varias fuentes enlazadas.
echo  f) Despliega "Contexto capturado": debe verse el system prompt y la
echo     configuracion resuelta del chatbot.
echo  g) Pulsa "Correcta". El boton se queda marcado y aparece tu correo
echo     junto a "Juzgado por".
echo.
echo  QUE DEBES VER
echo   - Ninguna cadena en ingles ni ningun texto tipo hub.test_scenarios.x
echo   - Cambia el idioma de la interfaz a valenciano y vuelve a mirar:
echo     todo traducido.
echo   - La consola del navegador (F12) sin errores en rojo.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE
echo ------------------------------------------------------------
echo   [ ] Chatbot sin escenarios: mensaje "Todavia no hay escenarios",
echo       no una lista vacia sin explicacion.
echo   [ ] Ejecutar SIN marcar "Capturar el contexto": sale la respuesta
echo       pero NO el desplegable de contexto.
echo   [ ] Eliminar un escenario borra tambien sus ejecuciones.
echo   [ ] Crea un escenario en un chatbot y comprueba que NO aparece al
echo       seleccionar otro chatbot distinto.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 4 - Huecos de corpus (RAG.14)
echo ------------------------------------------------------------
echo  Abre http://localhost:5173/curation/findings (CUR.2 lo movio fuera
echo  del Hub) y baja del todo, a la seccion "Huecos de corpus".
echo.
echo  a) Elige el mismo chatbot con el que has estado probando.
echo  b) Pulsa "Buscar huecos".
echo  c) Si has hecho varias preguntas parecidas que el asistente no
echo     supo responder, deben aparecer agrupadas en un solo hueco, con
echo     el recuento, las fechas y los terminos que las relacionan.
echo  d) Vuelve a pulsar "Buscar huecos": NO debe duplicarse el hueco,
echo     solo actualizarse el recuento.
echo.
echo  Si no aparece nada es correcto cuando no hay al menos 3 preguntas
echo  parecidas sin responder en los ultimos 30 dias. Para forzarlo,
echo  pregunta 3 o 4 veces por algo que no este en el corpus.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PARA TERMINAR
echo ------------------------------------------------------------
echo   Cierra las dos ventanas de terminal (backend y frontend) con Ctrl+C.
echo   La base de datos puedes dejarla encendida si vas a seguir.
echo.
echo PRUEBAS COMPLETADAS
pause
