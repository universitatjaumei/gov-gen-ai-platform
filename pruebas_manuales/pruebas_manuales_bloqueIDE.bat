@echo off
chcp 65001 > nul
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - Bloque IDE (identidad y permisos)
echo  + PLAT.1 y PLAT.2 (seccion Plataforma)
echo ============================================================
echo.
echo Que se hizo:
echo   PLAT.1  A quien tenia `chatbots` se le concede `plataforma`.
echo   PLAT.2  Cuarta seccion del menu: Plataforma. Se mueven ahi
echo           Modelos LLM, Prompts de actividad y Tokens.
echo   IDE.1   El alta por SSO deja de pisar el rol puesto a mano.
echo   IDE.2   hub_sso_users pasa a hub_users, con origen.
echo   IDE.3   Alta manual de personas; el SSO las reconoce.
echo   IDE.4   Pantalla de personas.
echo   IDE.5   Conceder modulos a una persona O a un grupo del IdP.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  LO QUE YA VERIFICO EL AGENTE EN NAVEGADOR
echo ------------------------------------------------------------
echo  - Con solo el modulo `plataforma`: aterriza en
echo    /plataforma/modelos y GET /hub/llm-configs responde 200.
echo    Ese caso era IMPOSIBLE antes.
echo  - Con solo `chatbots`: la seccion queda cortada, su
echo    subnavegacion ya no lleva los tres tabs movidos, y
echo    /hub/llm-configs no resuelve.
echo  - Alta de persona desde el formulario: Verif@UJI.es queda
echo    como verif@uji.es, rol Administrador, origen Alta manual,
echo    "Nunca ha entrado". Desactivar la deja en el listado.
echo  - Concesion al grupo PDI del modulo informes, y una persona
echo    con el grupo `pdi` EN MINUSCULA y sin concesion propia
echo    obtiene `informes` en /auth/me.
echo  - Consola limpia en las tres pantallas.
echo.
echo  Nada de eso hay que repetirlo aqui.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. docker compose up -d postgres
echo  3. HAY MIGRACIONES. Desde la raiz:
echo        cd server
echo        uv run alembic upgrade head
echo     (deben quedar aplicadas hasta n4g5h6i7j8k9)
echo  4. Servidor:  uvicorn server.app.main:app --port 8000
echo     desde la RAIZ del proyecto, no desde server\
echo  5. Frontend:  cd frontend  y  npm run dev
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
echo ============================================================
echo  LO QUE SOLO PUEDES PROBAR TU: SSO SAML REAL
echo ============================================================
echo.
echo Esto es lo unico irreducible del bloque. El agente lo probo
echo con aserciones firmadas de prueba, nunca contra el IdP de la
echo UJI, que es el que de verdad importa.
echo.
echo  PASO 1 - Que emite vuestro IdP
echo    Entra por SSO con tu cuenta y mira el log del servidor.
echo    Si la asercion trae un atributo de rol, veras una linea:
echo      "El IdP declara role=... y se ignora:
echo       IDENTITY_ROLE_AUTHORITY=app"
echo    Esa linea es el inventario que hoy no teneis: dice que
echo    esta configurando la Unidad de Desarrollo.
echo    Si NO aparece, el IdP no manda rol y no hay nada que
echo    ignorar. Las dos respuestas son informacion util.
echo.
echo  PASO 2 - Que grupos llegan
echo    En el mismo log o en /api/v1/auth/me, mira `saml_groups`.
echo    Ahi deberian salir los colectivos (estudiante, PDI,
echo    PTGAS) y quiza el puesto. APUNTA LOS NOMBRES EXACTOS:
echo    son los que hay que teclear en Plataforma - Modulos.
echo.
echo  PASO 3 - El rol puesto a mano sobrevive
echo    a) En Plataforma - Personas, da de alta tu correo
echo       institucional con rol Administrador, ANTES de entrar
echo       por SSO con esa cuenta.
echo    b) Entra por SSO.
echo    c) Comprueba en /api/v1/auth/me que sigues siendo admin.
echo       Antes de IDE.1 el SSO te habria degradado a `user`.
echo.
echo  PASO 4 - Los permisos por grupo, con un grupo real
echo    a) En Plataforma - Modulos, concede un modulo al grupo
echo       que apuntaste en el PASO 2.
echo    b) Entra por SSO con una cuenta de ese colectivo que NO
echo       tenga concesion propia.
echo    c) Debe ver ese modulo en su menu.
echo    Esto es la puerta al modelo del ERP: si funciona aqui,
echo    funciona cuando los permisos los reparta el ERP.
echo.
echo  PASO 5 - Desactivar cierra la puerta
echo    a) Desactiva en Plataforma - Personas una cuenta de
echo       prueba que ya haya entrado.
echo    b) Intenta entrar por SSO con ella.
echo    c) Debe dar 403 con code USER_INACTIVE, no un 401.
echo       Antes de IDE.3 entraba igual.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  JUICIO QUE SOLO PUEDES HACER TU
echo ------------------------------------------------------------
echo  [ ] El texto de la seccion Plataforma se entiende sin
echo      conocer el codigo.
echo  [ ] La nota de que el listado de personas NO son todas las
echo      cuentas se lee y no se pasa por alto.
echo  [ ] La advertencia de "Retirar a todo el grupo" da bastante
echo      miedo como para no pulsarla por error.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE
echo ------------------------------------------------------------
echo  [ ] Da de alta dos veces el mismo correo: 409, no dos filas.
echo  [ ] Da de alta con MAYUSCULAS y espacios: se guarda limpio.
echo  [ ] Como admin (no superadmin), abre Plataforma - Personas:
echo      no debes poder.
echo  [ ] Concede un modulo retirado del catalogo: 400, porque no
echo      daria acceso a nada.
echo  [ ] Pon IDENTITY_ROLE_AUTHORITY=erp en el .env y arranca:
echo      el servidor debe NEGARSE a arrancar, no adivinar.
echo  [ ] Pon IDENTITY_ROLE_AUTHORITY=idp y abre Personas: debe
echo      aparecer el aviso de que el rol lo decide el IdP.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  PARA TERMINAR
echo ------------------------------------------------------------
echo  Ctrl+C en las terminales del servidor y del frontend.
echo  Para parar la base de datos: docker compose stop postgres
echo.
echo  SI ALGO DEL PASO 2 TE SORPRENDE (nombres de grupo distintos
echo  de los previstos), dilo: condiciona como se configuran las
echo  concesiones en produccion.
echo.
echo PRUEBAS COMPLETADAS
pause
