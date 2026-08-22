@echo off
chcp 65001 > nul
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - Marca institucional por cascada
echo ============================================================
echo.
echo Que se cambio: el panel de administracion importaba el logotipo
echo de la UJI como codigo fuente. Ahora la marca la resuelve la
echo cascada visual del servidor (plataforma -^> organizacion) y el
echo panel solo la pinta.
echo.
echo Lo que ya verifico el agente en navegador:
echo   - Con marca configurada: el logotipo se pinta desde
echo     /api/v1/hub/themes/{id}/logo y carga (181x29 px).
echo   - Sin marca: sale "Gov Gen AI Platform" como texto.
echo   - Consola limpia, /resolved 200, logo 200.
echo.
echo Lo que necesita una persona: subir una marca y juzgar si se ve
echo bien. Eso todavia no tiene interfaz: se hace por API.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. docker compose up -d postgres
echo  3. Servidor:  uvicorn server.app.main:app --port 8000
echo     (desde la RAIZ del proyecto, no desde server\)
echo  4. Frontend:  cd frontend  y  npm run dev
echo.
echo No hay migracion: la marca vive dentro de la columna JSONB
echo hub_themes.config, asi que no hay que ejecutar alembic.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 1 - el servidor responde
echo ------------------------------------------------------------
curl -s -o nul -w "  /health -^> %%{http_code}\n" http://localhost:8000/health
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 2 - subir la marca de una organizacion
echo ------------------------------------------------------------
echo Necesitas un token de administrador de esa organizacion y el
echo id de su tema (tabla hub_themes).
echo.
echo Si la organizacion no tiene tema todavia, creale uno:
echo.
echo   curl -X POST http://localhost:8000/api/v1/hub/themes
echo        -H "Authorization: Bearer TU_TOKEN"
echo        -H "Content-Type: application/json"
echo        -d "{\"name\":\"Institucional\",\"organizacion_id\":\"TU_ORG\",\"config\":{\"name\":\"institucional\"}}"
echo.
echo Y luego sube el logotipo (PNG o JPEG, maximo 1 MB):
echo.
echo   curl -X POST http://localhost:8000/api/v1/hub/themes/ID_TEMA/logo
echo        -H "Authorization: Bearer TU_TOKEN"
echo        -F "file=@ruta\a\tu\logotipo.png;type=image/png"
echo        -F "logoAlt=Nombre de la institucion"
echo.
echo Debe contestar 200 con logoUrl y logoAlt.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PASOS EN LA INTERFAZ
echo ------------------------------------------------------------
echo  1. Abre http://localhost:5173 y entra con una cuenta de
echo     administrador de esa organizacion.
echo  2. Mira la esquina superior izquierda de la barra lateral azul.
echo.
echo  QUE DEBES VER:
echo   - El logotipo que acabas de subir, a 32 px de alto, nitido,
echo     legible sobre el azul del panel y sin deformarse.
echo   - Si la organizacion no tiene marca: el texto
echo     "Gov Gen AI Platform" en su lugar, no un hueco.
echo.
echo  JUICIO QUE SOLO PUEDES HACER TU:
echo   - Si el logotipo se lee bien sobre el fondo azul. Un logotipo
echo     con letras oscuras o con fondo blanco recortado puede pasar
echo     todos los tests y verse mal.
echo   - Si el texto alternativo describe la institucion como toca
echo     (lo lee un lector de pantalla).
echo.
pause
echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE
echo ------------------------------------------------------------
echo  [ ] Sube un SVG: debe rechazarlo con 415. Un SVG lleva guion
echo      dentro y se serviria desde el origen de la API.
echo  [ ] Sube un .png que en realidad sea otra cosa: debe rechazarlo
echo      con 415 (manda la firma real, no la extension).
echo  [ ] Sube algo de mas de 1 MB: debe rechazarlo con 413.
echo  [ ] Como admin de la organizacion A, intenta subir la marca del
echo      tema de la organizacion B: debe dar 403.
echo  [ ] Como admin (no superadmin), intenta subir la marca de un
echo      tema de plataforma (sin organizacion): debe dar 403.
echo  [ ] Abre la URL del logotipo en una ventana de incognito, sin
echo      sesion: debe servir la imagen. Una etiqueta img no manda
echo      cabecera de autorizacion, y en el widget publico no hay
echo      sesion ninguna que exigir.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PARA TERMINAR
echo ------------------------------------------------------------
echo  Corta el servidor y el frontend con Ctrl+C en sus terminales.
echo  Para parar la base de datos:  docker compose stop postgres
echo.
echo PRUEBAS COMPLETADAS
pause
