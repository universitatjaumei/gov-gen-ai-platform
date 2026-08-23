@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE REV
echo   Primer vistazo a Plataforma: correcciones de bajo riesgo
echo ============================================================
echo.
echo Este bloque se verifico entero en navegador durante el desarrollo.
echo Lo que queda aqui es SOLO lo que una persona tiene que juzgar:
echo el aspecto. Si el criterio visual no te convence, se cambia.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo.
echo  1. Docker Desktop en marcha.
echo  2. Base de datos de desarrollo arrancada:
echo        docker start govgenai-dev-postgres-1
echo  3. Servidor:   cd server ^&^& uv run uvicorn app.main:app --reload
echo  4. Frontend:   cd frontend ^&^& npm run dev
echo.
pause

echo.
echo ------------------------------------------------------------
echo   COMPROBACION AUTOMATICA DE SERVICIOS
echo ------------------------------------------------------------
echo.
curl -s -o nul -w "API  /health  ->  %%{http_code}\n" --max-time 5 http://127.0.0.1:8000/health
curl -s -o nul -w "Front  :5173  ->  %%{http_code}\n" --max-time 5 http://127.0.0.1:5173/
echo.
echo Los dos deben dar 200. Si no, revisa los requisitos previos.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   1. EL ASPECTO DE LOS MENUS   (REV.3)
echo ------------------------------------------------------------
echo.
echo Abre:  http://localhost:5173/plataforma/identidad-visual
echo.
echo QUE MIRAR:
echo   - En el menu azul de la izquierda, "Plataforma" va en negrita
echo     y blanco, con una barra vertical blanca a su izquierda.
echo     NO debe haber ningun recuadro de fondo.
echo   - En la fila de pestanas de arriba, "Identidad visual" va en
echo     negrita con un subrayado que continua la linea gris.
echo   - Cambia de seccion varias veces: el menu NO debe moverse
echo     ni un pixel.
echo.
echo ESTO ES UNA DECISION DE GUSTO. Si prefieres otra cosa (barra mas
echo gruesa, otro color, subrayado en vez de barra lateral), dilo.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   2. EL BOTON DEL LOGOTIPO   (REV.4)
echo ------------------------------------------------------------
echo.
echo En la misma pantalla, con Nivel = "Plataforma":
echo.
echo QUE MIRAR:
echo   - "Elegir fichero..." se ve como un boton con borde azul,
echo     y se puede pulsar (antes salia gris e inerte).
echo   - Debajo, en su propia linea, pone "Ningun fichero seleccionado".
echo   - Pulsa y elige un PNG o JPEG de menos de 1 MB.
echo   - El nombre del fichero aparece en esa segunda linea y el
echo     logotipo sale en "Vista previa", sobre el azul del panel.
echo.
echo AVISO: subir un logotipo en el nivel Plataforma lo pone como marca
echo de TODO el panel. Si solo estas probando, borra despues el tema
echo desde la pantalla o pideme que lo retire.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   3. LOS VALORES POR DEFECTO SE PUEDEN CAMBIAR   (REV.2)
echo ------------------------------------------------------------
echo.
echo Abre:  http://localhost:5173/hub/valores-por-defecto
echo.
echo QUE MIRAR:
echo   - Organizacion = "Universitat Jaume I".
echo   - Cada valor tiene ahora su control: cajas de numero, casilla
echo     para el reranker, area de texto para la plantilla.
echo   - Cambia "Resultados minimos por defecto" de 2 a 3, haz clic
echo     fuera del campo y RECARGA la pagina: debe seguir en 3.
echo   - Devuelvelo a 2.
echo   - En "Modo de retrieval por defecto", empieza a escribir: deben
echo     salir sugerencias (RAG, MD_LONG_CONTEXT, MD_AGENT_SELECTOR).
echo   - Abajo, los campos que ponen "Heredado de la plataforma" tienen
echo     un enlace "Establecer valor propio" que despliega su control.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   4. LA COLA DE VIGENCIA YA NO TE MANDA A INFORMES   (REV.5)
echo ------------------------------------------------------------
echo.
echo Abre:  http://localhost:5173/hub/vigencia
echo.
echo QUE MIRAR:
echo   - Elige el chatbot que tenga corpus normativo.
echo   - Los documentos del corpus (los que vienen de fichero .md)
echo     salen como texto negro, SIN enlace y sin el iconito.
echo   - Los que tienen URL real (BOE, DOGV) siguen siendo enlaces
echo     azules y abren la pagina oficial en otra pestana.
echo.
echo CASO LIMITE - la direccion inventada:
echo   Pega esto en la barra del navegador:
echo   http://localhost:5173/hub/esto-no-existe
echo   Debe salir "Esta direccion no existe" con un enlace
echo   "Ir al inicio". ANTES te llevaba a Informes sin avisar.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   LO QUE NO ESTA EN ESTE BLOQUE
echo ------------------------------------------------------------
echo.
echo Del mismo repaso quedan abiertos, y NO se han tocado:
echo   - Los colores de "Identidad visual" no pintan nada todavia:
echo     la cascada solo la consume el logotipo.
echo   - Personas: sin borrar, sin el superadministrador principal
echo     y sin organizacion.
echo   - Buscador en los prompts de actividad.
echo   - Selector global de organizacion.
echo   - Validar la vigencia desde la pantalla (no hay endpoint).
echo.
pause

echo.
echo ============================================================
echo   PRUEBAS COMPLETADAS
echo ============================================================
echo.
pause