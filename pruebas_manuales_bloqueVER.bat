@echo off
chcp 65001 > nul
title Pruebas manuales - Bloque VER (Informes y Curacion)

echo ============================================================
echo  PRUEBAS MANUALES - BLOQUE VER
echo  Informes y Curacion, lo que el agente NO puede comprobar
echo ============================================================
echo.
echo El agente ya recorrio en navegador los seis caminos completos:
echo   - plantilla propuesta con IA y contrato de UI
echo   - informe de punta a punta (Excel -^> extraccion -^> IA -^> revision -^> ensamblado)
echo   - cola de aprobacion de scripts contra el sandbox real
echo   - sitios, rastreo, hallazgos, informe de calidad y publicacion
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
echo  1. En el informe ensamblado, pulsa Vista previa y luego exporta.
echo  2. Abre el DOCX en Word: cabeceras, tablas, saltos de pagina.
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
