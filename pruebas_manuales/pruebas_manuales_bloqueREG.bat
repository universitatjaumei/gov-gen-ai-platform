@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo  BLOQUE REG - Registro de actividad IA y servicios hacia fuera
echo ============================================================
echo.
echo Lo que sigue es SOLO lo que el agente no puede comprobar por su
echo cuenta: hace falta un token real y una herramienta de verdad
echo conectandose desde fuera.
echo.
echo Ya verificado por el agente en el navegador (no se repite aqui):
echo   - La pantalla /registro con 5 eventos sembrados, en castellano
echo     y en valenciano, con la consola limpia.
echo   - El filtro por herramienta llegando al servidor:
echo     GET /api/v1/actividad?page=1^&size=25^&herramienta=claude-cowork -^> 200
echo   - El boton de exportar llamando a /api/v1/actividad/export con
echo     el filtro puesto -^> 200.
echo   - El mensaje distinto cuando el filtro no encuentra nada.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 0 - Requisitos previos
echo ------------------------------------------------------------
echo.
echo   1. Docker Desktop en marcha.
echo   2. La base de datos arriba:  docker compose up -d postgres
echo   3. La migracion aplicada:    cd server ^&^& uv run alembic upgrade head
echo   4. El servidor respondiendo en http://localhost:8000
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 1 - Que el servidor esta en pie
echo ------------------------------------------------------------
echo.
curl -s -o nul -w "GET /health -> %%{http_code}\n" http://localhost:8000/health
echo.
echo Se espera 200. Si sale 000, el servidor no esta arrancado.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 2 - Emitir el token (en el navegador)
echo ------------------------------------------------------------
echo.
echo   1. Entra en  http://localhost:5173/plataforma/tokens
echo   2. "Crear token", nombre "prueba-registro".
echo   3. Marca los dos permisos nuevos:
echo        actividad:write
echo        anonimizacion:use
echo   4. Copia el token EN CLARO: se muestra una sola vez.
echo   5. Pegalo aqui abajo cuando lo pida.
echo.
set /p PAT="Pega el token (pat_...): "
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 3 - Registrar un uso de IA (lo que hara la herramienta)
echo ------------------------------------------------------------
echo.
curl -s -w "\n-> %%{http_code}\n" -X POST http://localhost:8000/api/v1/actividad ^
  -H "Authorization: Bearer %PAT%" ^
  -H "Content-Type: application/json" ^
  -d "{\"ocurrido_en\":\"2026-09-03T12:00:00Z\",\"actor\":\"prueba-manual\",\"herramienta\":\"prueba-bat\",\"finalidad\":\"Comprobacion manual del bloque REG\",\"modelo_usado\":\"claude-opus-5\",\"categorias_datos\":[\"datos_identificativos\"]}"
echo.
echo Se espera 201 con un "id" y un "registrado_en".
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 4 - Que el contenido NO se puede colar
echo ------------------------------------------------------------
echo.
echo Esta es la regla dura del bloque: el registro guarda metadatos,
echo nunca el texto. Mandar un "prompt" tiene que FALLAR.
echo.
curl -s -o nul -w "con campo prompt -> %%{http_code} (se espera 422)\n" -X POST http://localhost:8000/api/v1/actividad ^
  -H "Authorization: Bearer %PAT%" ^
  -H "Content-Type: application/json" ^
  -d "{\"ocurrido_en\":\"2026-09-03T12:00:00Z\",\"actor\":\"prueba-manual\",\"herramienta\":\"prueba-bat\",\"finalidad\":\"x\",\"prompt\":\"texto que no debe entrar\"}"
echo.
echo Si aqui sale 201, el contrato se ha roto: para y avisa.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 5 - La anonimizacion como servicio
echo ------------------------------------------------------------
echo.
curl -s -w "\n-> %%{http_code}\n" -X POST http://localhost:8000/api/v1/anonimizacion/replace ^
  -H "Authorization: Bearer %PAT%" ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Solicitud de Manuela Ferrer, DNI 12345678Z, correo manuela@example.org\"}"
echo.
echo Se espera 200, con el DNI y el correo SUSTITUIDOS en
echo "text_anonimizado" y la lista de "spans_aplicados".
echo.
echo Comprueba tambien que el DNI 12345678Z NO aparece en la consola
echo donde corre el servidor: el texto no se registra en ningun sitio.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 6 - Que una sesion de navegador NO puede escribir
echo ------------------------------------------------------------
echo.
echo Sin credencial ninguna:
curl -s -o nul -w "sin token -> %%{http_code} (se espera 401)\n" -X POST http://localhost:8000/api/v1/actividad ^
  -H "Content-Type: application/json" -d "{}"
echo.
echo (Con una sesion del panel el servidor responde 403 PAT_REQUIRED.
echo  La escritura es para clientes maquina: si se pudiera escribir
echo  desde el navegador, se podrian fabricar entradas del registro.)
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 7 - Verlo en el panel
echo ------------------------------------------------------------
echo.
echo   1. Entra en  http://localhost:5173/registro
echo   2. Tiene que aparecer el evento del PASO 3:
echo        herramienta  prueba-bat
echo        finalidad    Comprobacion manual del bloque REG
echo   3. Escribe "prueba-bat" en el filtro Herramienta: debe quedar
echo      ese solo.
echo   4. Pulsa "Exportar a CSV" y abre el fichero descargado:
echo      la primera linea son los nombres del contrato
echo      (ocurrido_en, registrado_en, actor, herramienta, agente,
echo       finalidad, modelo_usado, categorias_datos, payload_hash).
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PASO 8 - El MCP remoto (opcional, y solo tras desplegar)
echo ------------------------------------------------------------
echo.
echo El servicio esta DECLARADO en la pila de la VM pero todavia no
echo desplegado. Cuando el bloque pase a main:
echo.
echo   claude mcp add --transport http govgenai https://normativa.uji.es/mcp ^
echo       --header "Authorization: Bearer pat_..."
echo.
echo Y en una sesion de Claude Code, pedirle que registre una actividad:
echo tienen que aparecer las tres herramientas (registrar_actividad,
echo detectar_pii, anonimizar_texto).
echo.
echo Si responde 421, falta el nombre del dominio en
echo GOVGENAI_MCP_ALLOWED_HOSTS. Si responde 502, el contenedor no
echo esta arrancado.
echo.
pause

echo.
echo ============================================================
echo  PRUEBAS COMPLETADAS
echo ============================================================
echo.
echo Si algo no ha salido como dice el guion, apunta el paso y el
echo codigo que devolvio: con eso se localiza sin adivinar.
echo.
pause