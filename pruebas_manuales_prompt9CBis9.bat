@echo off
chcp 65001 > nul

echo ============================================================
echo  PRUEBAS MANUALES - Prompt 9CBis.9
echo  Documentos: vista unificada HubDocument + multi-idioma
echo ============================================================
echo.
echo REQUISITOS PREVIOS:
echo   1. Docker Desktop en marcha (icono verde en la barra de tareas)
echo   2. Servidor y frontend levantados: docker compose up -d
echo   3. Abre http://localhost:5173/admin y entra con tus credenciales
echo.
pause

echo.
echo [PASO 1] Verificar que el servidor responde...
curl -s -o nul -w "Estado HTTP: %%{http_code}" http://localhost:8000/health
echo.
pause

echo.
echo [PASO 2] Verificar la pagina de Documentos...
echo   Ve a http://localhost:5173/admin/documents
echo   Deberias ver:
echo     - Una tabla "Documentos del corpus" (no historial de jobs)
echo     - Banner azul con el modo de retrieval del chatbot
echo     - Tab "Documentos" y tab "Fuentes web"
echo     - Seccion "Jobs (tecnico)" plegada al final (haz clic para expandir)
echo.
pause

echo.
echo [PASO 3] Verificar las columnas de la tabla de documentos...
echo   Si hay documentos ingestados, comprueba:
echo     - Columna Titulo con icono segun tipo (PDF o Web)
echo     - Columna Fuente con badge "PDF" o "Web"
echo     - Columna Idioma con badge de color (ES = amarillo, CA = rojo, EN = azul)
echo     - Columna Tokens con formato compacto (ej. "4.7 k")
echo     - Columna Fecha
echo     - Tres botones de accion: ojo (ver), flecha arriba (sustituir), papelera (eliminar)
echo.
pause

echo.
echo [PASO 4] Verificar el filtro de idioma...
echo   Si hay documentos en varios idiomas:
echo     - Debe aparecer un selector de idioma encima de la tabla
echo     - Selecciona "ES": solo deben mostrarse los documentos en espanol
echo     - Selecciona "CA": solo documentos en catalan
echo     - Selecciona "Todos los idiomas": vuelven todos
echo.
pause

echo.
echo [PASO 5] Verificar el modal de preview...
echo   Haz clic en el icono de ojo de cualquier documento
echo   Deberias ver un modal con el contenido markdown del documento
echo   Cierra el modal con la "x" de la esquina superior derecha
echo.
pause

echo.
echo [PASO 6] Verificar la sustitucion de documento...
echo   Haz clic en el icono de flecha arriba (sustituir) de un documento
echo   Deberias ver que:
echo     - Aparece un banner amarillo indicando que ests sustituyendo ese documento
echo     - La URL canonica y el idioma se rellenan automaticamente
echo     - Puedes subir un nuevo PDF para reemplazarlo
echo   Cancela con el boton "Cancelar" del banner
echo.
pause

echo.
echo [PASO 7] Verificar coexistencia de idiomas (si tienes PDFs de prueba)...
echo   Sube el mismo PDF dos veces: una con idioma "Espanol" y otra con "Catala"
echo   Ambos deben aparecer en la tabla como documentos separados con badges ES y CA
echo.
pause

echo.
echo [PASO 8] Verificar que la tab "Fuentes web" no ha cambiado...
echo   Haz clic en la tab "Fuentes web"
echo   Debe mostrar el formulario de anhadir fuente y la lista de fuentes, igual que antes
echo.
pause

echo.
echo ============================================================
echo  QUE DEBES VER
echo ============================================================
echo   - Tabla de documentos con columnas: Titulo, Fuente, Idioma, Tokens, Fecha, Acciones
echo   - Banner azul con modo retrieval y tokens totales
echo   - Filtro de idioma (solo visible si hay mas de un idioma)
echo   - Modal de preview con contenido markdown
echo   - Sustitucion pre-rellena URL y idioma del doc original
echo   - Dos PDFs con la misma URL pero distinto idioma coexisten (no se sobreescriben)
echo   - Tab "Fuentes web" sin cambios
echo   - Jobs plegados en seccion "Jobs (tecnico)"
echo ============================================================
echo.
echo PRUEBAS COMPLETADAS
pause