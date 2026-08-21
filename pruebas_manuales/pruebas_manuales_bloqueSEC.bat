@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque SEC
echo.
echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE SEC (endurecimiento de seguridad)
echo ============================================================
echo.
echo Solo estan aqui las comprobaciones que NO cubren los tests.
echo.
echo IMPORTANTE: el servidor tiene que estar REINICIADO despues de
echo los cambios del bloque. Un proceso viejo no tiene el limitador
echo ni las cabeceras, y los pasos 2, 3 y 4 daran resultados
echo enganyosos. El paso 0 lo comprueba.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. docker compose up -d db
echo  3. En server\: uv run alembic upgrade head
echo  4. REINICIA el servidor (Ctrl+C y arrancarlo de nuevo).
echo  5. Frontend en http://localhost:5173 (Vite recarga solo).
echo.
pause
echo.
echo ------------------------------------------------------------
echo  0/5  EL SERVIDOR TIENE EL CODIGO DEL BLOQUE
echo ------------------------------------------------------------
echo  Se pide una ruta que SOLO existe desde SEC.4.
echo  401 o 422 = el servidor esta al dia, sigue adelante.
echo  404       = el proceso es anterior al bloque: PARA, reinicia
echo              el servidor y vuelve a ejecutar este archivo.
echo.
curl -s -o nul -w "  /hub/usage/me -> %%{http_code}\n" "http://localhost:8000/api/v1/hub/usage/me?chatbot_id=00000000-0000-0000-0000-000000000001"
echo.
pause
echo.
echo ------------------------------------------------------------
echo  1/5  MIGRACIONES DEL BLOQUE APLICADAS
echo ------------------------------------------------------------
echo  Debe salir s6b7c8d9e0f1 (head).
echo.
cd server
call uv run alembic current
cd ..
echo.
pause
echo.
echo ------------------------------------------------------------
echo  2/5  EL LOGIN AGUANTA LA FUERZA BRUTA (SEC.4)
echo ------------------------------------------------------------
echo  QUE DEBES VER: los 10 primeros dan 401 y del undecimo en
echo  adelante 429. Todos 401 = el servidor es viejo (ver paso 0).
echo.
for /L %%i in (1,1,12) do @curl -s -o nul -w "  intento %%i -> %%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/admin/login -H "Content-Type: application/json" -d "{\"email\":\"noexiste@uji.es\",\"password\":\"x\"}"
echo.
echo  NOTA: el limitador cuenta en la memoria del proceso. Para
echo  repetir este paso desde cero hay que reiniciar el servidor o
echo  esperar un minuto.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  3/5  CABECERAS DE SEGURIDAD (SEC.7)
echo ------------------------------------------------------------
echo  QUE DEBES VER, entre las cabeceras de abajo:
echo    x-content-type-options: nosniff
echo    x-frame-options: DENY
echo    referrer-policy: strict-origin-when-cross-origin
echo    content-security-policy: ... frame-ancestors 'none'
echo  Y NO debe aparecer strict-transport-security (es solo de
echo  produccion; en desarrollo obligaria a HTTPS en localhost).
echo.
curl -s -D - -o nul http://localhost:8000/api/v1/hub/themes/presets
echo.
pause
echo.
echo ------------------------------------------------------------
echo  4/5  LEER UN TEMA EXIGE SESION (SEC.5)
echo ------------------------------------------------------------
echo  QUE DEBES VER: 401. Antes del bloque esto era publico y
echo  respondia 200 o 404, o sea que servia el nombre y los colores
echo  de la organizacion a quien preguntara.
echo.
curl -s -o nul -w "  tema sin sesion -> %%{http_code}\n" "http://localhost:8000/api/v1/hub/themes/00000000-0000-0000-0000-000000000001"
echo.
echo  NOTA: la travesia de rutas (dos puntos y barra) no se
echo  comprueba aqui porque sin sesion todo responde 401 antes de
echo  llegar a la ruta. La cubren 15 tests automaticos en
echo  tests/api/test_themes_security.py.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  5/5  EN LA INTERFAZ (SEC.4.1)
echo ------------------------------------------------------------
echo  a) Entra en http://localhost:5173/hub/chatbots
echo  b) La tabla debe tener una columna Disponibilidad. Con la
echo     configuracion actual todos salen como Disponible (verde).
echo  c) Pulsa un chatbot para editarlo. Abajo, sobre el boton de
echo     guardar, hay un bloque Disponibilidad con cuatro campos:
echo     Disponible desde, Disponible hasta, Presupuesto total
echo     (tokens) y Mensaje cuando no esta disponible.
echo  d) Pon en Disponible hasta una fecha de AYER, escribe un
echo     mensaje (por ejemplo: El plazo termino ayer.) y guarda.
echo  e) En la lista, ese chatbot debe salir ahora como Caducado
echo     (rojo).
echo  f) Intenta conversar con el desde el panel: debe responder
echo     403 con TU mensaje, no un Forbidden generico.
echo  g) Vuelve a editarlo, vacia el campo de fecha y guarda: debe
echo     volver a Disponible (es lo que arreglo FIX.3: antes el null
echo     se ignoraba y la fecha se quedaba puesta).
echo.
echo  OJO en el paso f: si el chatbot ya esta Disponible y al
echo  conversar sale un 500 en vez de una respuesta, NO es del
echo  bloque. En la BD de desarrollo hay chatbots que apuntan a un
echo  proveedor openai_compatible sin API key, y eso falla por su
echo  cuenta. Lo que este paso comprueba es el 403 con tu mensaje
echo  cuando esta caducado.
echo.
echo  SSO SAML real contra el IdP institucional: sigue pendiente y
echo  no se puede probar en local.
echo.
pause
echo.
echo PRUEBAS COMPLETADAS
pause
