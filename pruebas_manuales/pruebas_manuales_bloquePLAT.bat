@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE PLAT
echo   La administracion de la plataforma, separada de Chatbots
echo ============================================================
echo.
echo Casi todo el bloque ya lo verifico el agente en navegador:
echo la seccion Plataforma y sus cinco pantallas, la frontera de
echo modulos por API, la identidad visual en los tres niveles con
echo su cascada, y la retirada del tema en JSON.
echo.
echo Aqui queda SOLO lo que necesita a una persona: mirar si la
echo marca se LEE bien, que ningun test automatico puede juzgar.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo.
echo  1. Docker Desktop en marcha.
echo  2. La base de datos levantada:  docker compose up -d postgres
echo  3. La migracion de PLAT.7 aplicada. Se comprueba abajo.
echo  4. El servidor arrancado DESDE LA RAIZ del proyecto:
echo       uv run uvicorn server.app.main:app --port 8000
echo  5. El frontend arrancado:  cd frontend  y luego  npm run dev
echo.
pause

echo.
echo ------------------------------------------------------------
echo   COMPROBACION 1 - La migracion esta aplicada
echo ------------------------------------------------------------
echo.
echo Ejecutando: alembic current
cd server
call .venv\Scripts\python.exe -m alembic current
cd ..
echo.
echo Debe decir:  o5h6i7j8k9l0 (head)
echo Si dice otra cosa, ejecuta:  cd server  y luego  uv run alembic upgrade head
echo.
pause

echo.
echo ------------------------------------------------------------
echo   COMPROBACION 2 - El servidor responde
echo ------------------------------------------------------------
echo.
curl -s -o nul -w "  /health -> %%{http_code}
" http://localhost:8000/health
echo.
echo Debe decir 200. Si no, el servidor no esta arrancado.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PRUEBA A - El logotipo se LEE sobre el azul del panel
echo ------------------------------------------------------------
echo.
echo Esta es la razon de ser de esta prueba: un logotipo con letras
echo oscuras pasa todos los tests automaticos y se lee fatal sobre
echo el fondo de la barra lateral. Eso lo juzga una persona.
echo.
echo  1. Abre  http://localhost:5173/plataforma/identidad-visual
echo  2. Deja el Nivel en "Plataforma".
echo  3. En "Fichero del logotipo", sube un PNG con el logotipo de
echo     tu institucion (hasta 1 MB).
echo  4. Mira el recuadro "Vista previa": es el fondo REAL de la
echo     barra lateral.
echo.
echo QUE DEBES VER: el logotipo legible sobre el azul, sin que las
echo letras se pierdan y sin un rectangulo blanco alrededor.
echo.
echo Si no se lee, prueba con la version del logotipo en negativo.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PRUEBA B - La cascada, mirada por una persona
echo ------------------------------------------------------------
echo.
echo  1. Sigues en la misma pantalla, Nivel = Plataforma.
echo  2. Cambia el color "primary" y pulsa Guardar.
echo  3. Cambia el Nivel a "Organizacion" y elige una.
echo  4. Mira la fila "primary".
echo.
echo QUE DEBES VER: el color que acabas de poner, con el texto
echo "Heredado de Plataforma" al lado.
echo.
echo  5. Cambia el "primary" DE LA ORGANIZACION y pulsa Guardar.
echo  6. La etiqueta "Heredado de" desaparece de esa fila.
echo  7. Vuelve al nivel Plataforma, cambia "secondary" y guarda.
echo  8. Vuelve al nivel Organizacion.
echo.
echo QUE DEBES VER: "secondary" con el color nuevo y "Heredado de
echo Plataforma"; "primary" con el suyo propio y sin etiqueta.
echo Es decir: lo que la organizacion NO decide le sigue llegando.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PRUEBA C - Un fichero que el servidor rechazaria
echo ------------------------------------------------------------
echo.
echo  1. En "Fichero del logotipo", elige "Todos los archivos" en
echo     el dialogo y selecciona un SVG cualquiera.
echo.
echo QUE DEBES VER: un aviso en rojo que dice que solo se aceptan
echo PNG y JPEG y explica por que el SVG queda fuera. NO una
echo pantalla en blanco ni un error crudo.
echo.
echo  2. Prueba ahora con una imagen de mas de 1 MB.
echo.
echo QUE DEBES VER: un aviso que menciona el limite de 1 MB.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PRUEBA D - Identidad visual como la ve un administrador
echo ------------------------------------------------------------
echo.
echo Esta necesita una cuenta con rol "admin" (no superadmin) que
echo tenga concedido el modulo "plataforma".
echo.
echo  1. Entra con esa cuenta.
echo  2. Abre  http://localhost:5173/plataforma/identidad-visual
echo.
echo QUE DEBES VER: en el desplegable "Nivel" NO aparece
echo "Plataforma", solo "Organizacion" y "Asistente". Un tema de
echo plataforma lo hereda todo el mundo, y eso es de superadmin.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   CASOS LIMITE
echo ------------------------------------------------------------
echo.
echo  [ ] Con el idioma en Valencia y en English, la pantalla de
echo      identidad visual no muestra ninguna clave sin traducir
echo      (nada del estilo "plataforma.identidad_visual.titulo").
echo.
echo  [ ] http://localhost:5173/hub/reports YA NO existe: te lleva
echo      a otra pantalla. La revision de interacciones esta ahora
echo      en http://localhost:5173/hub/revision
echo.
echo  [ ] En Chatbots ^> Organizaciones, el dialogo de "Nueva
echo      organizacion" tiene tres campos y NINGUNO pide JSON.
echo.
echo  [ ] Cada fila de esa tabla tiene un enlace "Identidad visual"
echo      que abre la pantalla con esa organizacion ya elegida.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PARA TERMINAR
echo ------------------------------------------------------------
echo.
echo Si has subido un logotipo de prueba y no quieres conservarlo,
echo sube encima el definitivo: no hay boton de quitar, y eso es
echo a proposito (un panel sin marca ninguna se ve roto).
echo.
echo Para detener los servicios: Ctrl+C en cada terminal, y
echo   docker compose down
echo.
echo PRUEBAS COMPLETADAS
echo.
pause
