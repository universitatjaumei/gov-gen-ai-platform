@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE MT (fase 1)
echo   Multitenencia: el esquema, antes del piloto
echo ============================================================
echo.
echo Este bloque es CASI TODO BACKEND y SIN cambio de comportamiento:
echo la fase 1 mete el esquema y deja la vista y los permisos para
echo despues del piloto. Con una sola organizacion, la UJI, todo
echo tiene que funcionar EXACTAMENTE como antes.
echo.
echo Por eso aqui no hay pasos de interfaz nuevos: lo que se
echo comprueba es que NADA se ha roto, y una cosa que solo puedes
echo valorar tu.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   ANTES DE EMPEZAR
echo ------------------------------------------------------------
echo.
echo   1. Abre Docker Desktop y espera el icono verde.
echo   2. En una terminal:  docker compose up -d
echo   3. Aplica las migraciones del bloque:
echo        cd server
echo        uv run alembic upgrade head
echo      Tienen que aplicarse cinco:
echo        q7j8k9l0m1n2  credenciales por organizacion
echo        r8k9l0m1n2o3  informes ganan la organizacion
echo        s9l0m1n2o3p4  el permiso dice donde
echo        t0m1n2o3p4q5  prompts de actividad heredables
echo   4. Arranca el servidor y el frontend como siempre.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   1. QUE LA MIGRACION NO HAYA MOVIDO NADA
echo ------------------------------------------------------------
echo.
echo Comprueba la revision aplicada:
echo.
echo   cd server
echo   uv run alembic current
echo.
echo Debe decir: t0m1n2o3p4q5 (head)
echo.
pause

echo.
echo Que los datos siguen ahi lo compruebas en el punto 2, abriendo
echo las pantallas: es mas fiable que contar filas por consola.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   2. QUE SIGA FUNCIONANDO IGUAL (lo que de verdad importa)
echo ------------------------------------------------------------
echo.
echo Recorre estas pantallas y comprueba que ves lo de siempre:
echo.
echo   http://localhost:5173/plataforma/modelos
echo      - Los 7 modelos LLM, con su nivel y su proveedor.
echo      - El de Vertex para embeddings sigue marcado por defecto.
echo.
echo   http://localhost:5173/informes
echo      - Las 23 plantillas de informe (20 de plataforma).
echo      - Los 29 informes de prueba.
echo.
echo   http://localhost:5173/plataforma/prompts-actividad
echo      - Las 4 actividades y los prompts base de los 4 asistentes.
echo.
echo   http://localhost:5173/plataforma/modulos
echo      - Las concesiones de modulo, como estaban.
echo.
echo Si algo falta o cambia, es un fallo del bloque: la fase 1 no
echo debia cambiar comportamiento.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   3. UN CAMBIO DE COMPORTAMIENTO QUE SI ES A PROPOSITO
echo ------------------------------------------------------------
echo.
echo Se cerro un agujero: cualquier administrador podia RENOMBRAR o
echo ARCHIVAR una plantilla de informe de plataforma (la que ven
echo todos) o la personal de otra persona. Solo se comprobaba el
echo rol, nunca de quien era la plantilla.
echo.
echo Ahora, sobre una plantilla de plataforma:
echo   - Como superadministrador: puedes renombrarla y archivarla.
echo   - Como administrador de una organizacion: 403, y la pantalla
echo     te dice que la bifurques si quieres una version propia.
echo.
echo Con una sola organizacion y entrando como superadministrador
echo NO deberias notar nada. Si notas que no puedes tocar algo que
echo antes si, dimelo: seria un ajuste de mas.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   4. LO UNICO QUE NECESITA TU JUICIO
echo ------------------------------------------------------------
echo.
echo Nada de este bloque exige criterio subjetivo, salvo esto:
echo.
echo   Lee docs/MULTITENENCIA.md de arriba abajo.
echo.
echo Es el inventario de que esta acotado por organizacion y que
echo no, y lo mantiene honesto un test. Lo que hace falta que
echo valides tu es si el reparto de ambitos es el que quieres:
echo.
echo   - hub_providers como CATALOGO de plataforma (Google es Google
echo     en todos los municipios) y la credencial por organizacion.
echo   - hub_users heredable: una cuenta puede no pertenecer a
echo     ninguna organizacion.
echo   - Las concesiones de modulo sin organizacion siguen valiendo
echo     EN TODAS, que es lo que significan hoy.
echo.
echo Si alguno no te encaja, es mejor cambiarlo ahora que despues
echo del piloto: es la razon por la que la fase 1 va antes.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PARA TERMINAR
echo ------------------------------------------------------------
echo.
echo   docker compose down     (si quieres parar los servicios)
echo.
echo ============================================================
echo   PRUEBAS COMPLETADAS
echo ============================================================
echo.
pause
