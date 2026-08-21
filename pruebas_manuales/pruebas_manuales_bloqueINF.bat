@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque INF
echo.
echo ==========================================================
echo   PRUEBAS MANUALES - BLOQUE INF (modulo de Informes)
echo ==========================================================
echo.
echo Lo que el agente ya comprobo en navegador NO se repite aqui.
echo Aqui queda lo que solo puede juzgar una persona.
echo.
echo REQUISITOS PREVIOS
echo   1. Docker Desktop en marcha.
echo   2. Base de datos, SOLO ese servicio:
echo        docker compose up -d postgres
echo   3. La migracion de INF.7 ya esta aplicada en tu base. Si trabajas
echo      sobre otra, aplicala:
echo        cd server
echo        uv run alembic upgrade head
echo   4. Backend y frontend:
echo        arranque.bat  (opcion 1)
echo      OJO: el backend tarda 2-4 minutos (carga torch). Hasta que no
echo      escriba "Application startup complete" no responde.
echo      Desde INF.8 escucha en 127.0.0.1 y no en toda la red.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 1 - Los servicios responden
echo ----------------------------------------------------------
echo.
findstr /I "VITE_API_TARGET=" frontend\.env.local
echo.
curl -s -o nul -w "   backend 8000 health: %%{http_code}\n" http://localhost:8000/health
curl -s -o nul -w "   frontend 5173:       %%{http_code}\n" http://localhost:5173/
curl -s -o nul -w "   5173 hacia la API:   %%{http_code}\n" http://localhost:5173/api/v1/hub/sites
echo.
echo QUE DEBES VER: health 200, frontend 200 y la API 401 (pide sesion).
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 2 - Un informe de punta a punta, con TUS datos
echo ----------------------------------------------------------
echo.
echo Esto es lo que en las pruebas anteriores no se pudo terminar.
echo.
echo   1. Entra en Informes y elige tu plantilla de doctorado.
echo   2. En "Datos de partida" veras una zona de arrastre con su texto
echo      en tu idioma. Sube el .md de verdad (el del programa 90162).
echo   3. Pulsa Continuar. Debe subir el fichero y arrancar la generacion.
echo   4. Cuando acabe, aprueba los dos apartados de IA en el panel de
echo      revision, y despues Vista previa y Exportar a Word.
echo.
echo LO QUE HAY QUE JUZGAR, y no puede juzgarlo un test:
echo   - El texto que escribio la IA sobre TUS tablas: dice algo cierto?
echo   - El DOCX descargado: se lee? las tablas estan bien formadas?
echo   - Si no subes fichero y pulsas Continuar, el aviso te dice cual
echo     falta de forma que se entienda?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 3 - Un informe nuevo con IA sobre un CSV tuyo
echo ----------------------------------------------------------
echo.
echo   1. Informes - "Generar propuesta".
echo   2. Sube el CSV de saldos ANTES de escribir el prompt. Debajo debe
echo      aparecer el nombre del fichero, el numero de filas y las columnas.
echo   3. Escribe tu peticion de tesoreria por ano y mes.
echo   4. Pulsa Generar propuesta.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Las columnas que la pantalla dice que va a enviar son las tuyas
echo     y NO aparece ningun valor de las filas: son datos que salen de
echo     la organizacion hacia un modelo, y eso lo decides tu.
echo   - La estructura propuesta sirve? La plantilla viene marcada como
echo     recomendada: te parece la eleccion correcta para este caso?
echo   - Si aun sale algun error rojo, se entiende y hay boton para
echo     corregirlo sin reescribir el prompt?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 4 - Permisos por modulo (INF.7)
echo ----------------------------------------------------------
echo.
echo Esto necesita DOS cuentas y por eso no lo puede hacer un test.
echo.
echo   1. Con tu superadmin: entras en todo. No necesita concesion.
echo   2. Crea o usa una cuenta de trabajador y concedele SOLO informes:
echo.
echo        docker exec -i govgenai-dev-postgres-1 psql -U govgenai -d govgenai -c ^
echo        "insert into hub_module_grants (subject_id, module_code) values ('EL-UUID', 'informes');"
echo.
echo      (el UUID es uuid5 del user_id; si no lo sabes, mira que devuelve
echo       /api/v1/auth/me con esa sesion)
echo.
echo   3. Entra con esa cuenta.
echo.
echo QUE DEBES VER:
echo   - El menu lateral SOLO muestra Informes. Ni Chatbots ni Curacion.
echo   - Al escribir http://localhost:5173/hub a mano, no entra.
echo   - Aterriza directamente en Informes, no en Chatbots.
echo   - Y lo importante: esa cuenta ya no puede editar los chatbots
echo     institucionales ni la configuracion de LLM.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 5 - El copiloto y el cajon
echo ----------------------------------------------------------
echo.
echo   1. Con un informe abierto que tenga algo pendiente, abre el
echo      copiloto y preguntale: "no se donde aprobar los bloques".
echo   2. Cierra el cajon con el aspa. Y otra vez con la tecla Escape.
echo.
echo QUE DEBES VER:
echo   - El copiloto responde hablando de ESTE informe: que apartado hay
echo      que aprobar y donde. Antes no respondia nada.
echo   - El cajon tiene UNA pestana (Copiloto). Las tres en blanco ya no
echo     estan; volveran cuando tengan contenido.
echo   - Se cierra con el aspa y con Escape.
echo.
pause
echo.
echo ==========================================================
echo   PRUEBAS COMPLETADAS
echo ==========================================================
echo.
echo Para terminar: Ctrl+C en las ventanas del backend y del frontend,
echo y si quieres  docker compose down
echo.
pause
