@echo off
chcp 65001 > nul

echo ============================================================
echo  PRUEBAS MANUALES - Prompt 9CBis.8
echo  IngestionWatcher crea HubDocument; chunks solo si vector
echo ============================================================
echo.
echo REQUISITOS PREVIOS:
echo   1. Docker Desktop en marcha (icono verde en la barra de tareas)
echo   2. Servidor levantado: docker compose up -d
echo   3. Migracion aplicada: cd server ^& uv run alembic upgrade head
echo.
pause

echo.
echo [PASO 1] Verificar que el servidor responde...
curl -s -o nul -w "Estado HTTP: %%{http_code}" http://localhost:8000/health
echo.
pause

echo.
echo [PASO 2] Suite de tests unitarios (debe mostrar 173+ PASSED)...
cd /d "%~dp0server"
uv run pytest tests/modules/agents_hub/unit/ --no-cov -q
echo.
pause

echo.
echo [PASO 3] Tests especificos del Prompt 9CBis.8...
uv run pytest tests/modules/agents_hub/integration/test_ingestion_creates_documents.py --no-cov -v
echo.
pause

echo.
echo [PASO 4] Verificar endpoint GET /hub/ingestion/{chatbot_id}/documents...
echo   (Necesitas un chatbot_id real. Copia uno de la BD o de la UI admin.)
echo   Ejemplo:
echo   curl -H "Authorization: Bearer TU_TOKEN" ^
echo        http://localhost:8000/api/v1/hub/ingestion/UUID_DEL_CHATBOT/documents
echo.
pause

echo.
echo [PASO 5] Subir un PDF via upload y verificar que se crea HubDocument...
echo   1. Ve a http://localhost:5173/admin/chatbots
echo   2. Entra en un chatbot y sube un PDF desde la pestaña Documentos
echo   3. Verifica que aparece en la lista de documentos con titulo extraido
echo   4. Verifica que el modo Long Context NO genera chunks (0 en logs)
echo.
pause

echo.
echo ============================================================
echo  QUE DEBES VER
echo ============================================================
echo   - GET /documents devuelve lista de HubDocument con id, title, canonical_url
echo   - Modo "vector": se crean chunks (n_chunks >= 1 en logs)
echo   - Modo "long_context" o "agentic": n_chunks = 0, sin embeddings
echo   - Reingestión del mismo contenido: mismo document_id (idempotencia)
echo   - DELETE job borra el HubDocument asociado
echo   - DELETE chunks borra todos los HubDocuments del chatbot
echo ============================================================
echo.

echo PRUEBAS COMPLETADAS
pause
