@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque CUR
echo.
echo ==========================================================
echo   PRUEBAS MANUALES - BLOQUE CUR (curacion vista por quien cura)
echo ==========================================================
echo.
echo Lo que el agente ya comprobo en el navegador NO se repite aqui.
echo Aqui solo queda lo que una persona tiene que juzgar.
echo.
echo REQUISITOS PREVIOS (hazlos antes de seguir)
echo   1. Docker Desktop en marcha.
echo   2. Base de datos arriba, SOLO ese servicio:
echo        docker compose up -d postgres
echo      (el servicio se llama "postgres". Un "up -d" completo choca en
echo       9000/9001 con el MinIO del stack de produccion si esta levantado)
echo   3. Backend arrancado desde la raiz del proyecto, en el puerto 8000:
echo        cd C:\Users\fabra\Documents\AI_agents_hub
echo        set CRAWLER_CONTACT=fabra@uji.es
echo        uv run --project server uvicorn server.app.main:app --port 8000
echo      OJO: tarda 2-4 minutos en arrancar (carga torch). Hasta que no
echo      escriba "Application startup complete" no responde.
echo      Si da WinError 10048, el 8000 lo retiene el arbol de procesos de
echo      un uvicorn anterior que fallo al arrancar. NO cambies de puerto:
echo        Get-NetTCPConnection -LocalPort 8000
echo        Stop-Process -Id (los PID del arbol entero) -Force
echo   4. Frontend:  cd frontend  y luego  npm run dev
echo      Vite imprime su puerto al arrancar. Normalmente el 5173; si estaba
echo      ocupado usara el 5174. Usa el que imprima en las URLs de abajo.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 1 - Los servicios responden
echo ----------------------------------------------------------
echo.
echo A que puerto apunta el frontend (debe decir 8000):
findstr /I "VITE_API_TARGET=" frontend\.env.local
echo.
echo Backend:
curl -s -o nul -w "   puerto 8000 health: %%{http_code}\n" http://localhost:8000/health
echo.
echo Frontend y su proxy al backend:
curl -s -o nul -w "   frontend 5173:      %%{http_code}\n" http://localhost:5173/
curl -s -o nul -w "   5173 hacia la API:  %%{http_code}\n" http://localhost:5173/api/v1/hub/sites
echo.
echo QUE DEBES VER:
echo   - El backend responde 200 en health, en el 8000.
echo   - El frontend responde 200 (en el puerto que imprimio Vite).
echo   - "hacia la API" responde 401. Eso es CORRECTO: significa que el
echo     backend contesta y pide sesion. Si sale 000 o 502, el backend no
echo     esta levantado, o VITE_API_TARGET no apunta a su puerto.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 2 - Revisar los 13 duplicados semanticos uno a uno
echo ----------------------------------------------------------
echo.
echo Esto es criterio humano: el modelo propone y una persona decide.
echo.
echo   1. Abre  http://localhost:5173/curation/findings
echo   2. Elige el sitio "Escola de Doctorat (RAS.5)"
echo   3. En el filtro de tipo elige "Duplicada"
echo   4. Para cada fila: abre las dos URLs (son enlaces) y decide
echo        - Confirmar  si de verdad sobra una de las dos
echo        - Descartar  si son cosas distintas
echo.
echo   Los cuatro primeros son los importantes: la misma pagina bajo
echo   dos rutas del portal. Eso hay que decirselo a quien gestiona
echo   el portal, no arreglarlo desde aqui.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 3 - El texto que iria al asistente
echo ----------------------------------------------------------
echo.
echo   1. En cualquier hallazgo, pulsa "Ver texto guardado"
echo   2. Comprueba que NO aparecen el menu ni el pie del portal
echo   3. Comprueba que SI aparece el contenido de la pagina
echo   4. Compara con la pagina real abriendo "Ver la pagina original"
echo.
echo Esto es lo unico que no se puede automatizar: si el recorte se
echo llevo algo que hacia falta, lo ve una persona leyendo.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 4 - Descargar el informe y abrirlo
echo ----------------------------------------------------------
echo.
echo   1. Abre  http://localhost:5173/curation/audit
echo   2. Elige el sitio y pulsa "Descargar DOCX"
echo   3. Abre el fichero en Word: comprueba que se lee y que las
echo      secciones tienen sus URLs
echo.
echo NOTA: "Descargar PDF" guarda un .docx a proposito. Este equipo no
echo tiene LibreOffice, y el servidor lo dice en vez de entregar un PDF
echo falso. Con LibreOffice instalado saldria PDF de verdad.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 5 - Publicar un apartado al asistente
echo ----------------------------------------------------------
echo.
echo   1. Abre  http://localhost:5173/curation/publish
echo   2. Elige el sitio y un chatbot de pruebas
echo   3. Marca 3 o 4 paginas y pulsa "Ingerir las marcadas"
echo   4. Recarga: deben aparecer como "Ya ingerida" y sin casilla
echo   5. Ve al chatbot y preguntale algo que solo este en esas
echo      paginas. Juzga si la respuesta cita bien.
echo.
echo El paso 5 es el que decide si la curacion sirve para algo.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 6 - Hablar con quien gestiona el portal
echo ----------------------------------------------------------
echo.
echo Esto no es software. De los hallazgos salen dos cosas que
echo conviene trasladar a quien mantiene www.uji.es:
echo.
echo   - La misma seccion es alcanzable bajo dos prefijos de ruta
echo     (/centres/escola-doctorat/ y /estudis/centres/escola-doctorat/)
echo   - Hay paginas servidas con y sin barra final, y una errata
echo     en una ruta: "internalitzacio" en vez de "internacionalitzacio"
echo.
echo Y sigue pendiente pedir permiso para rastrear /seu/.
echo.
pause
echo.
echo ==========================================================
echo   PRUEBAS COMPLETADAS
echo ==========================================================
echo.
echo Para terminar: cierra el backend y el frontend con Ctrl+C en
echo sus ventanas, y si quieres  docker compose down
echo.
pause
