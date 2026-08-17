@echo off
chcp 65001 > nul
title Pruebas manuales - Bloques VER y PRO (Informes y Curacion)

echo ============================================================
echo  PRUEBAS MANUALES - BLOQUES VER y PRO
echo  Informes y Curacion, lo que el agente NO puede comprobar
echo ============================================================
echo.
echo El agente ya recorrio en navegador los seis caminos completos:
echo   - plantilla propuesta con IA y contrato de UI
echo   - informe de punta a punta (Excel -^> extraccion -^> IA -^> revision -^> ensamblado)
echo   - cola de aprobacion de scripts contra el sandbox real
echo   - sitios, rastreo, hallazgos, informe de calidad y publicacion
echo Y en el bloque PRO recorrio, con modelos reales:
echo   - script escrito por el modelo, auditado y ejecutado en el sandbox
echo   - script aprobado extrayendo datos dentro de un informe
echo   - transformacion de datos (determinista y por IA) y grafico en el informe
echo   - exportacion a DOCX con tablas e imagenes de verdad
echo   - el copiloto respondiendo con citas a ficheros reales de docs\
echo Nada de eso se repite aqui. Ver docs\PRUEBAS_MANUALES.md.
echo.
echo Lo que queda es criterio humano y entornos que aqui no hay.
echo.
pause

echo.
echo ============================================================
echo  REQUISITOS PREVIOS
echo ============================================================
echo.
echo  1. Docker Desktop en marcha (icono verde en la barra de tareas).
echo  2. Base de datos de desarrollo:      docker compose up -d db
echo  3. Backend:   cd server ^&^& uv run uvicorn server.app.main:app --port 8001
echo  4. Frontend:  cd frontend ^&^& npm run dev
echo.
echo  Nota: el backend del bloque VER se probo en el puerto 8001 porque el 8000
echo  quedo retenido por un proceso huerfano. El proxy de desarrollo lee el
echo  destino de frontend\.env.local (VITE_API_TARGET).
echo.
pause

echo.
echo ============================================================
echo  COMPROBACION 1 - Los servicios responden
echo ============================================================
echo.
curl -s -o nul -w "backend  : %%{http_code}\n" http://localhost:8001/health
curl -s -o nul -w "frontend : %%{http_code}\n" http://localhost:5173/
echo.
echo Se espera 200 en los dos. Si el backend da 000, no esta arrancado.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA A - Calidad editorial del informe generado
echo ============================================================
echo.
echo  Esto no lo puede juzgar una regla: hace falta criterio de redaccion.
echo.
echo  1. Abre  http://localhost:5173/redaccion/draft
echo  2. Describe un informe que conozcas bien, por ejemplo:
echo     "Informe trimestral de ejecucion del presupuesto de un servicio,
echo      con una tabla de importes por capitulo y un resumen ejecutivo".
echo  3. Pulsa Generar propuesta, revisa las secciones y bloques propuestos
echo     y aprueba la plantilla.
echo  4. Ve a Nuevo informe, crea el informe desde esa plantilla, sube una
echo     hoja de calculo con datos reales de tu servicio y pulsa Generar.
echo  5. Cuando el bloque de IA quede en revision, LEELO.
echo.
echo  QUE VALORAR:
echo   - El texto usa los datos de tu hoja, sin inventar cifras ni fechas.
echo   - El tono es el de un informe institucional, no comercial.
echo   - Si falta un dato, lo dice en vez de rellenarlo.
echo   - Aprobar y Rechazar hacen lo que dicen.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA B - Exportacion abierta en Word y en Adobe reales
echo ============================================================
echo.
echo  El agente comprueba que el fichero baja y que no esta vacio.
echo  Que se VEA bien solo lo puede decir alguien con Office instalado.
echo.
echo  1. En la pantalla del informe pulsa "Exportar a Word". Desde PRO.5 la
echo     descarga existe de verdad; antes no habia de donde bajar nada.
echo     Tambien vale a mano:
echo       GET /api/v1/redaccion/workspaces/ID_DEL_INFORME/export
echo  2. Abre el DOCX en Word: cabeceras, tablas (tienen que ser TABLAS, no
echo     texto), la imagen del grafico y los saltos de pagina.
echo  3. Si tienes LibreOffice instalado, exporta tambien a PDF y abrelo
echo     en Adobe. Sin LibreOffice, la aplicacion devuelve un DOCX y lo
echo     dice en el nombre del fichero: eso es correcto, no un fallo.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA C - Anonimizacion sobre datos personales reales
echo ============================================================
echo.
echo  El agente no procesa datos personales reales. Esta prueba solo
echo  tiene sentido con un documento que puedas usar legitimamente.
echo.
echo  1. Crea un informe cuya plantilla pida un documento con nombres.
echo  2. Subelo y genera.
echo  3. Comprueba en el panel de anonimizacion que los nombres se han
echo     sustituido, y que el texto final vuelve a llevar los originales.
echo.
echo  Si no tienes un documento autorizado, SALTA esta prueba y dilo.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA D - Rastreo de una web institucional real
echo ============================================================
echo.
echo  El sitio local del corpus pinta sus fichas con JavaScript, asi que
echo  un rastreador estatico solo alcanza el indice y el buscador. Para
echo  medir profundidad real hace falta una web con enlaces en el HTML.
echo.
echo  1. Abre  http://localhost:5173/curation/sites
echo  2. Nuevo sitio: nombre "UJI web", URL raiz  https://www.uji.es/
echo  3. Pulsa Rastrear ahora y espera un minuto.
echo  4. Comprueba que el estado queda "active" y que aparecen paginas.
echo.
echo  QUE VALORAR:
echo   - Cuantas paginas trae y si son las que esperarias.
echo   - Que no se sale del dominio.
echo   - Si el sitio tarda o limita peticiones, anotalo: es informacion
echo     de despliegue, no un fallo de la aplicacion.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA E - Chatbot real con clave de API y coste
echo ============================================================
echo.
echo  Cada consulta gasta cuota de tu proyecto de GCP. El agente no
echo  gasta cuota ajena sin permiso, asi que esto es tuyo.
echo.
echo  1. Abre el asistente de Gerencia y su gemelo agentico
echo     ("Gerencia - assistent agentic (proves)") y haz la MISMA
echo     pregunta a los dos.
echo  2. Compara: quien cita mejor, quien se inventa menos, quien tarda.
echo.
echo  QUE VALORAR:
echo   - Si el gemelo agentico busca en las normas externas en vez de
echo     intentar leerlas enteras.
echo   - Si las citas abren el articulo correcto.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA F - Calidad del script sobre un fichero real de la UJI
echo ============================================================
echo.
echo  ESTA ES LA IMPORTANTE DEL BLOQUE PRO.
echo.
echo  El agente comprobo que el modelo escribe un script, que la auditoria
echo  lo acepta, que el sandbox lo ejecuta y que devuelve una tabla. Lo que
echo  NO puede comprobar es si esa tabla es la que se pedia: sus pruebas van
echo  con un Excel sintetico cuyas columnas invento el propio agente.
echo.
echo  1. Coge un fichero REAL de tu unidad: ejecucion presupuestaria, un
echo     listado de gasto, lo que uses de verdad. Con sus cabeceras en dos
echo     filas, sus totales intercalados y sus celdas combinadas.
echo  2. Ve a Informes -^> "Pedir un script".
echo  3. Describe con tus palabras que hay que extraer.
echo  4. Sube ESE fichero como datos de prueba y ejecuta la prueba.
echo.
echo  QUE VALORAR (y esto es lo que nadie mas puede decir):
echo   - Si las cifras de la tabla son las correctas.
echo   - Si el script se ha comido una fila de totales creyendo que es un dato.
echo   - Si la revision del modelo auditor te avisa de algo real ("asume que
echo     las columnas se llaman asi") o si es palabreria.
echo   - Si el codigo que ves es el que le ensenarias a un colega.
echo.
echo  Si el script se equivoca, anota QUE pediste y QUE salio: eso es lo que
echo  afina el prompt, y el prompt se edita sin desplegar en
echo  /hub/activity-prompts.
echo.
pause

echo.
echo ============================================================
echo  PRUEBA G - Si el copiloto es util o solo correcto
echo ============================================================
echo.
echo  El agente comprobo que cita ficheros reales de docs\ y que la cita
echo  sostiene la frase. Si la respuesta RESUELVE tu duda, lo dices tu.
echo.
echo  1. Abre un informe y pulsa el boton "Copiloto" (a la derecha).
echo  2. Pregunta algo que te haga falta de verdad, no una prueba.
echo  3. La primera pregunta tarda ~1 minuto: construye el indice de docs\.
echo     Las siguientes van en segundos. Si la primera tarda siempre, eso
echo     es un fallo y hay que anotarlo.
echo.
echo  QUE VALORAR:
echo   - Si te responde o te recita el documento.
echo   - Si la cita que da es donde tu habrias buscado.
echo   - Si cuando no sabe algo lo dice, en vez de inventarlo.
echo.
pause

echo.
echo ============================================================
echo  PARA TERMINAR
echo ============================================================
echo.
echo  Detener el frontend y el backend: Ctrl+C en sus terminales.
echo  La base de datos puede quedarse en marcha:  docker compose stop db
echo.
echo  Si algo de A-E no se comporta como se describe, anotalo con la URL
echo  y lo que viste: eso es lo que el agente no puede ver por si mismo.
echo.
echo PRUEBAS COMPLETADAS
pause
