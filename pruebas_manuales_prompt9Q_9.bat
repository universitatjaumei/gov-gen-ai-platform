@echo off
chcp 65001 > nul
echo PRUEBAS MANUALES - Prompt 9Q.9 - Calidad de contenido web
echo.
echo REQUISITOS: Docker Desktop corriendo + docker compose up -d
echo.
pause
echo PASO 1: Smoke check
curl -s -o NUL -w "HTTP: %%{http_code}" http://localhost:8000/api/v1/hub/sites
echo.
pause
echo PASO 2: Abrir http://localhost:5173/hub/sites
echo   - Pulsa "Nuevo sitio"
echo   - Nombre: Portal Prueba, URL raiz: https://ej.es
echo   - Guarda. ESPERADO: sitio en tabla con estado active
echo.
pause
echo PASO 3: Rastrear el sitio
echo   - Pulsa "Rastrear ahora" en la fila del sitio
echo   - ESPERADO: mensaje de encolado
echo.
pause
echo PASO 4: Crear seleccion de corpus (prefijo de ruta, ej. tramites)
echo   - Clic en fila del sitio, panel de mapeo, "Nueva seleccion"
echo   - ESPERADO: seleccion listada con el prefijo indicado
echo.
pause
echo PASO 5: Ingerir una pagina candidata
echo   - En "Paginas candidatas" pulsa "Ingerir"
echo   - ESPERADO: Toast de ingestion encolada
echo.
pause
echo PASO 6: Analizar en http://localhost:5173/hub/content-quality
echo   - Selecciona el sitio - "Analizar ahora"
echo   - ESPERADO: hallazgos en la tabla tras refrescar
echo.
pause
echo PASO 7: Confirmar un hallazgo
echo   - Pulsa "Confirmar" en un hallazgo
echo   - ESPERADO: estado cambia a Confirmado
echo.
pause
echo PASO 8: Ver informe y descargar
echo   - Pulsa "Informe de auditoria" - revisa totales y secciones
echo   - Pulsa "Descargar DOCX" y "Descargar PDF"
echo   - ESPERADO: ficheros descargados
echo.
pause
echo CASOS LIMITE:
echo   [ ] Sitio sin hallazgos: mensaje No hay hallazgos activos
echo   [ ] Candidata sin regla: boton Ingerir disponible
echo.
echo PRUEBAS COMPLETADAS
pause