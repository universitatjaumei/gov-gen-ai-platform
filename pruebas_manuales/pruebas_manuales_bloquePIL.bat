@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque PIL (los dos asistentes del piloto)

echo ============================================================
echo  PRUEBAS MANUALES - BLOQUE PIL
echo  Los dos asistentes del piloto con el corpus normativo real
echo ============================================================
echo.
echo  Lo que el agente YA ha verificado (no hay que repetirlo):
echo   - Los dos asistentes creados con su configuracion, vista en el panel.
echo   - Corpus cargado: Normativa UJI 297 docs / 23.306 fragmentos,
echo     Gerencia 124 docs / 14.198 fragmentos, todos con embeddings de Vertex.
echo   - Consulta real por la credencial de widget: respuesta correcta,
echo     con cita al articulo y aviso de vigencia desplazada.
echo   - Consulta real autenticada contra Gerencia: cita con ancla.
echo.
echo  Lo que queda aqui es lo que una maquina no puede juzgar.
echo.
pause

echo.
echo ============================================================
echo  REQUISITOS PREVIOS
echo ============================================================
echo   1. Docker Desktop arrancado.
echo   2. Base de datos de desarrollo:  docker compose up -d postgres
echo   3. Backend en el puerto 8000 y frontend en el 5173.
echo.
pause

echo.
echo ============================================================
echo  1. COMPROBACION DE QUE TODO RESPONDE
echo ============================================================
echo.
curl -s -o nul -w "  backend: HTTP %%{http_code}\n" http://127.0.0.1:8000/health
curl -s -o nul -w "  frontend: HTTP %%{http_code}\n" http://localhost:5173/
echo.
echo  Si alguno no da 200, revisa los requisitos previos antes de seguir.
echo.
pause

echo.
echo ============================================================
echo  2. CALIDAD DE LAS RESPUESTAS (juicio humano - lo principal)
echo ============================================================
echo.
echo  Abre  http://localhost:5173/hub/chatbots  y entra en cada asistente.
echo.
echo  Haz 5 o 6 preguntas REALES de tu trabajo a cada uno y valora:
echo    - La respuesta dice lo que dice la norma, sin anadir nada?
echo    - La cita apunta al articulo correcto?
echo    - Cuando no sabe, lo dice, en vez de improvisar?
echo    - El tono sirve a un ciudadano (publico) y a un gestor (Gerencia)?
echo.
echo  Un caso concreto que conviene repetir a mano, porque es el que mas cuesta:
echo.
echo    Pregunta: Quants anys dura el mandat del Sindic de Greuges?
echo.
echo    Debe responder SEIS anos (Estatutos de 2025), NO cinco, y explicar
echo    que el articulo 9 del Reglamento esta desplazado. Si dice cinco,
echo    es un fallo grave: avisa.
echo.
pause

echo.
echo ============================================================
echo  3. IDENTIDAD VISUAL DEL WIDGET
echo ============================================================
echo.
echo  Requiere la credencial de sitio del asistente publico, que se emite
echo  en el panel del chatbot y SOLO SE MUESTRA UNA VEZ.
echo.
echo    - El widget se ve como algo de la Universitat, o como algo pegado?
echo    - Tipografia, colores y espaciado sobre la web institucional real.
echo.
pause

echo.
echo ============================================================
echo  4. ACCESIBILIDAD CON LECTOR DE PANTALLA
echo ============================================================
echo.
echo  Con NVDA o el Narrador de Windows, sobre el widget publico:
echo    - Se anuncia la respuesta cuando termina de generarse?
echo    - Se alcanzan las citas con el teclado?
echo    - El campo de escribir dice lo que es?
echo.
pause

echo.
echo ============================================================
echo  5. LO QUE NO SE PUEDE PROBAR EN LOCAL
echo ============================================================
echo.
echo  Queda para el despliegue, y esta dicho a proposito:
echo    - Gerencia en modo restricted con el grupo SAML real. En local no hay IdP.
echo    - El widget incrustado en la web institucional de verdad.
echo.
pause


echo.
echo ============================================================
echo  PRUEBAS COMPLETADAS
echo ============================================================
echo.
echo  Anota lo que falle con la pregunta exacta y la respuesta recibida:
echo  sin la pregunta literal no se puede reproducir.
echo.
pause
