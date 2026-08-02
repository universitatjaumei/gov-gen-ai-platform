@echo off
chcp 65001 > nul
title Pruebas manuales - Bloque SEC
echo.
echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE SEC (endurecimiento de seguridad)
echo ============================================================
echo.
echo Solo estan aqui las comprobaciones que NO se pueden automatizar
echo ni verificar desde los tests. Todo lo demas ya esta cubierto por
echo la suite (1662 tests) y por el gate de CI.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. docker compose up -d db
echo  3. cd server ^&^& uv run alembic upgrade head
echo  4. Servidor en http://localhost:8000 y frontend en http://localhost:5173
echo.
pause
echo.
echo ------------------------------------------------------------
echo  1/5  MIGRACIONES DEL BLOQUE APLICADAS
echo ------------------------------------------------------------
echo  Deben aparecer q4z5a6b7c8d9, r5a6b7c8d9e0 y s6b7c8d9e0f1.
echo  La ultima (s6b7c8d9e0f1) debe estar marcada como (head).
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
echo  Se lanzan 12 intentos con contrasena incorrecta.
echo  QUE DEBES VER: los primeros responden 401 y a partir del
echo  undecimo responden 429. Si todos dan 401, el limitador no esta
echo  actuando.
echo.
for /L %%i in (1,1,12) do @curl -s -o nul -w "intento %%i -> %%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/admin/login -H "Content-Type: application/json" -d "{\"email\":\"noexiste@uji.es\",\"password\":\"x\"}"
echo.
pause
echo.
echo ------------------------------------------------------------
echo  3/5  CABECERAS DE SEGURIDAD (SEC.7)
echo ------------------------------------------------------------
echo  QUE DEBES VER: x-content-type-options: nosniff,
echo  x-frame-options: DENY y referrer-policy.
echo  Strict-Transport-Security NO debe aparecer en desarrollo.
echo.
curl -s -D - -o nul http://localhost:8000/api/v1/hub/themes/presets
echo.
pause
echo.
echo ------------------------------------------------------------
echo  4/5  RUTAS DE TEMAS ACOTADAS (SEC.5)
echo ------------------------------------------------------------
echo  QUE DEBES VER: 400 o 404 en los dos, NUNCA 200 ni 500.
echo.
curl -s -o nul -w "traversal  -> %%{http_code}\n" "http://localhost:8000/api/v1/hub/themes/..%%2Fsenuelo"
curl -s -o nul -w "sin sesion -> %%{http_code}\n" "http://localhost:8000/api/v1/hub/themes/00000000-0000-0000-0000-000000000001"
echo  (el segundo debe ser 401: leer un tema ya exige sesion)
echo.
pause
echo.
echo ------------------------------------------------------------
echo  5/5  EN LA INTERFAZ (lo que el agente no pudo verificar)
echo ------------------------------------------------------------
echo  El permiso del navegador para localhost fue denegado durante
echo  el desarrollo, asi que esto queda por comprobar a mano:
echo.
echo  a) Entra en http://localhost:5173/admin/chatbots
echo  b) La tabla debe tener una columna nueva: Disponibilidad.
echo     Con la configuracion actual todos los chatbots deben salir
echo     como Disponible (verde).
echo  c) Abre un chatbot, ponle una fecha de fin en el pasado y
echo     guarda. Al volver a la lista debe salir Caducado (rojo).
echo  d) Intenta conversar con ese chatbot: debe responder 403 con
echo     el mensaje que hayas escrito, no un error generico.
echo  e) Deja la fecha de fin vacia otra vez para restaurarlo.
echo.
echo  SSO SAML real contra el IdP institucional: sigue pendiente y
echo  no se puede probar en local (SEC.2.1 fija la organizacion del
echo  IdP con SAML_ORGANIZACION_ID).
echo.
pause
echo.
echo PRUEBAS COMPLETADAS
pause