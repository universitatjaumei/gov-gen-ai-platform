@echo off
chcp 65001 > nul
echo ============================================================
echo  PRUEBAS MANUALES — Prompt 9C.3
echo  StorageService integrado en el flujo de ingestion de PDFs
echo ============================================================
echo.

echo REQUISITOS PREVIOS:
echo  1. Docker Desktop arrancado (icono verde en la barra de tareas)
echo  2. Servicios del proyecto levantados con Docker Compose
echo  3. El servidor FastAPI respondiendo en http://localhost:8000
echo.
pause

echo.
echo [1/4] Comprobando que el servidor esta levantado...
curl -s -o nul -w "HTTP %%{http_code}" http://localhost:8000/health
echo.
echo     Si ves HTTP 200 continua. Si ves error, arranca el servidor primero.
echo     Comando: docker compose up -d
echo.
pause

echo.
echo [2/4] Ejecutando la suite de tests de 9C.3 (StorageService)...
echo     Incluye: test_storage_service.py y test_ingestion_storage.py
echo.
cd /d "%~dp0server"
uv run pytest tests/modules/agents_hub/unit/test_storage_service.py tests/modules/agents_hub/unit/test_ingestion_storage.py -v
echo.
echo     Resultado esperado: 19 passed, 0 failed
echo.
pause

echo.
echo [3/4] Smoke test manual — subida de PDF via API...
echo.
echo     Se necesita un token JWT valido. Si no tienes uno, obtienlo con:
echo     curl -X POST http://localhost:8000/api/v1/auth/token -d "username=admin&password=admin"
echo.
echo     Crea un chatbot de prueba en el panel admin (http://localhost:5173/admin)
echo     y copia su UUID. Luego ajusta el comando curl de abajo.
echo.
echo     Ejemplo (sustituye <TOKEN> y <CHATBOT_UUID>):
echo     curl -X POST http://localhost:8000/api/v1/hub/ingestion/upload ^
echo          -H "Authorization: Bearer ^<TOKEN^>" ^
echo          -F "chatbot_id=^<CHATBOT_UUID^>" ^
echo          -F "file=@C:\ruta\a\documento.pdf;type=application/pdf" ^
echo          -F "canonical_url=https://ejemplo.es/documento.pdf"
echo.
echo     Resultado esperado: HTTP 202 con job_id; source_url debe ser
echo     "ingestion/<chatbot_id>/<job_id>.pdf" (clave de storage, no ruta /tmp)
echo.
pause

echo.
echo [4/4] Verificacion adicional — el PDF permanece en storage...
echo.
echo     Tras el upload, comprueba que el fichero existe en el backend de storage:
echo     - Backend local (desarrollo): revisa la carpeta STORAGE_BUCKET
echo       (por defecto /tmp/govgenai en Linux o C:\tmp\govgenai en Windows)
echo       Debe existir el fichero ingestion\^<chatbot_id^>\^<job_id^>.pdf
echo.
echo     - Backend MinIO: accede a http://localhost:9001 con credenciales
echo       minioadmin/minioadmin y verifica el objeto en el bucket configurado.
echo.
echo     El fichero NO debe borrarse automaticamente tras la ingestion.
echo.
pause

echo.
echo ============================================================
echo  REGRESIONES A VERIFICAR
echo ============================================================
echo  [ ] El chat del widget sigue respondiendo (http://localhost:5173)
echo  [ ] La pantalla de Documentos del admin lista los jobs correctamente
echo  [ ] El borrado de un job desde el admin elimina tambien el PDF de storage
echo  [ ] El scheduler de fuentes web sigue comprobando URLs periodicamente
echo.
pause

echo.
echo ============================================================
echo  PRUEBAS COMPLETADAS — Prompt 9C.3
echo ============================================================
pause
