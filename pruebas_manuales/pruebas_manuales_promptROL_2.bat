@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
echo ============================================
echo   PRUEBAS MANUALES - Prompt ROL.2 (Frontend)
echo   Renombrado: SuperAdmin / Admin / Organizacion
echo ============================================
echo.
echo [Requisitos previos]
echo  1. Docker Desktop en marcha (icono verde).
echo  2. docker compose up -d   (backend + BD)
echo  3. Migracion ROL.1 ya aplicada (alembic upgrade head).
echo  4. En frontend/: npm run dev
echo.
pause
echo.
echo [Smoke check backend] Endpoints renombrados (ROL.1):
curl -s -o nul -w "  /api/v1/hub/organizaciones -> HTTP %%{http_code} (401 sin token = OK)\n" http://localhost:8000/api/v1/hub/organizaciones
curl -s -o nul -w "  /api/v1/auth/superadmin/login -> HTTP %%{http_code} (405/422 = OK)\n" http://localhost:8000/api/v1/auth/superadmin/login
curl -s -o nul -w "  /api/v1/auth/admin/login -> HTTP %%{http_code} (405/422 = OK)\n" http://localhost:8000/api/v1/auth/admin/login
echo.
pause
echo.
echo [Pasos en la interfaz - navegador]
echo  1. Abre http://localhost:5173/login
echo  2. Login como SuperAdmin: fabra@uji.es / admin1234
echo     -^> Entra. En el sub-nav del Hub aparece "Organizaciones" (no "Clientes").
echo  3. Ve a http://localhost:5173/hub/organizaciones
echo     -^> Lista de organizaciones. Boton "Nueva organizacion".
echo     -^> El formulario muestra la etiqueta "Admin ID" (no "Partner ID").
echo  4. Ve a /hub/access-tokens: como SuperAdmin ves el scope chatbots:write.
echo  5. Cierra sesion. Login como Admin: dev@automatia.local / (cualquier password).
echo     -^> En Access Tokens NO aparece chatbots:write (techo de admin).
echo.
pause
echo.
echo [Que debes ver]
echo  - Sub-nav "Organizaciones"; ruta /hub/organizaciones operativa.
echo  - Etiqueta "Admin ID" en el formulario (no "Partner ID").
echo  - Ningun texto "Cliente" / "Partner" en la UI del Hub.
echo.
echo [Casos limite]
echo  - [ ] La ruta antigua /hub/clients ya NO resuelve.
echo  - [ ] Un usuario con rol 'user' no obtiene scopes de admin.
echo.
echo PRUEBAS COMPLETADAS
pause
