@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - Prompt AUTH.4 (Login SSO + PAT)
echo ============================================================
echo.
echo [ANTES DE EMPEZAR]
echo  1. Abre Docker Desktop (icono verde).
echo  2. docker compose up -d   (API en :8000, frontend en :5173)
echo  3. Migracion aplicada (tabla hub_personal_access_tokens):
echo       cd server  y  uv run alembic upgrade head
echo.
pause
echo.
echo [SMOKE CHECK] El endpoint de PAT existe (401 sin token = correcto)
curl -s -o nul -w "  /api/v1/auth/pats HTTP %%{http_code} (esperado 401)" http://localhost:8000/api/v1/auth/pats
echo.
echo.
pause
echo.
echo [PASOS EN LA INTERFAZ]
echo  1. Abre http://localhost:5173/login
echo  2. Entra como admin (email mas contrasena).
echo  3. Ve a Hub, pestana "Tokens de acceso" en /hub/access-tokens
echo  4. "Crear token": nombre mcp, marca "Plantillas: lectura", pulsa Crear.
echo  5. El token (pat_...) se muestra UNA vez. Pulsa "Copiar".
echo  6. Pulsa "Cerrar": el token desaparece y no vuelve a mostrarse.
echo  7. En la tabla, pulsa "Revocar" y confirma. Estado pasa a "Revocado".
echo.
echo [SSO SAML - opcional, requiere IdP configurado]
echo  - Con VITE_SAML_ENABLED=true y SAML_ENABLED=true mas metadata del IdP,
echo    el boton "Entrar con SSO institucional" aparece en login, redirige
echo    al IdP y al volver entra por /auth/callback al Hub.
echo.
echo [QUE DEBES VER]
echo  - El token en claro solo una vez, con aviso de copia unica.
echo  - Tras revocar, ese token deja de autenticar (401).
echo.
echo PRUEBAS COMPLETADAS
pause
