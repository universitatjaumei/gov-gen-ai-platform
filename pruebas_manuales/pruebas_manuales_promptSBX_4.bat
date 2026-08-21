@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - PROMPT SBX.4
echo  Hardening Docker + aislamiento de red del sandbox
echo ============================================================
echo.

echo REQUISITOS PREVIOS
echo ------------------
echo 1. Docker Desktop en marcha (icono verde en la barra de tareas)
echo 2. Imagen del sandbox construida:
echo    docker compose -f docker-compose.prod.yml build script-sandbox app
echo 3. Stack levantado:
echo    docker compose -f docker-compose.prod.yml up -d
echo.
pause

echo.
echo ============================================================
echo  CHECK 1: El sandbox NO puede resolver postgres
echo  (debe fallar con socket.gaierror)
echo ============================================================
docker compose -f docker-compose.prod.yml exec script-sandbox ^
  python -c "import socket; print(socket.gethostbyname('postgres'))"
echo.
echo RESULTADO ESPERADO: socket.gaierror (Name or service not known)
echo Si aparece una IP, el aislamiento de red NO funciona correctamente.
echo.
pause

echo.
echo ============================================================
echo  CHECK 2: El sandbox NO puede salir a internet
echo  (debe fallar con URLError / OSError)
echo ============================================================
docker compose -f docker-compose.prod.yml exec script-sandbox ^
  python -c "import urllib.request; urllib.request.urlopen('https://www.google.com', timeout=3).read()"
echo.
echo RESULTADO ESPERADO: urllib.error.URLError o OSError (Network unreachable)
echo Si se descarga HTML de Google, el egress NO esta bloqueado.
echo.
pause

echo.
echo ============================================================
echo  CHECK 3: El API SI puede hablar con el sandbox
echo  (debe responder: {"status":"healthy"})
echo ============================================================
docker compose -f docker-compose.prod.yml exec app ^
  curl -s http://script-sandbox:5000/health
echo.
echo RESULTADO ESPERADO: {"status":"healthy"}
echo.
pause

echo.
echo ============================================================
echo  CHECK 4: El sandbox NO puede hablar con el API
echo  (debe fallar con URLError / OSError)
echo ============================================================
docker compose -f docker-compose.prod.yml exec script-sandbox ^
  python -c "import urllib.request; urllib.request.urlopen('http://app:8000/health', timeout=3).read()"
echo.
echo RESULTADO ESPERADO: urllib.error.URLError o OSError (Network unreachable)
echo.
pause

echo.
echo ============================================================
echo  CHECK 5: Inspeccionar capacidades del contenedor
echo ============================================================
echo CapDrop (debe ser ["ALL"]):
docker inspect govgenai_script_sandbox --format "{{json .HostConfig.CapDrop}}"
echo.
echo SecurityOpt (debe incluir no-new-privileges:true):
docker inspect govgenai_script_sandbox --format "{{json .HostConfig.SecurityOpt}}"
echo.
echo ReadonlyRootfs (debe ser true):
docker inspect govgenai_script_sandbox --format "{{.HostConfig.ReadonlyRootfs}}"
echo.
pause

echo.
echo ============================================================
echo  SMOKE E2E: Ejecutar un script en el sandbox
echo ============================================================
echo Comprobando el healthcheck del sandbox via curl en el host...
curl -s http://localhost:5001/health
echo.
echo RESULTADO ESPERADO: {"status":"healthy"}
echo (El sandbox expone el puerto 5001 en el host SOLO en docker-compose.yml dev)
echo.
echo Para el smoke E2E completo con el API:
echo   1. Crea un proposal con POST /api/v1/redaccion/scripts/propose
echo   2. Ejecuta POST /api/v1/redaccion/scripts/{id}/test
echo   3. Comprueba: docker compose -f docker-compose.prod.yml logs script-sandbox
echo      Debes ver la linea de acceso al endpoint /execute-extraction
echo.
pause

echo.
echo ============================================================
echo  PARA TERMINAR
echo ============================================================
echo   docker compose -f docker-compose.prod.yml down
echo.
echo PRUEBAS COMPLETADAS
pause