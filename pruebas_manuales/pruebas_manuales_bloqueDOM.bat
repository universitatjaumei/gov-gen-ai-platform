@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title Pruebas manuales - Bloque DOM (el dominio institucional)

echo ==========================================================================
echo  BLOQUE DOM - normativa.uji.es sirve lo publico y el panel vive en /panel/
echo ==========================================================================
echo.
echo  Lo que el agente YA verifico en navegador (no hace falta repetirlo):
echo.
echo   - La raiz del dominio muestra la portada, no el login.
echo   - La portada, el cercador y las fichas se sirven por el dominio.
echo   - El asistente responde y sus citas abren la ficha en el articulo.
echo   - El panel entra por https://normativa.uji.es/panel/ y navega, tambien
echo     recargando en una ruta profunda.
echo   - El nombre provisional sigue sirviendo lo mismo, panel incluido.
echo   - Consola del navegador limpia en todos los pasos.
echo.
echo  Aqui queda SOLO lo que una persona tiene que juzgar o decidir.
echo.
pause

echo.
echo ==========================================================================
echo  1. COMPROBACION RAPIDA DE QUE TODO RESPONDE
echo ==========================================================================
echo.
echo  Codigo 200 en las cuatro y no hace falta mirar nada mas.
echo.
echo  --^> portada
curl -s -o nul -w "     %%{http_code}  https://normativa.uji.es/\n" https://normativa.uji.es/
echo  --^> cercador (redireccion 301 a cercador.html)
curl -s -o nul -w "     %%{http_code}  https://normativa.uji.es/cercador\n" https://normativa.uji.es/cercador
echo  --^> salud de la aplicacion
curl -s -o nul -w "     %%{http_code}  https://normativa.uji.es/health\n" https://normativa.uji.es/health
echo  --^> panel
curl -s -o nul -w "     %%{http_code}  https://normativa.uji.es/panel/\n" https://normativa.uji.es/panel/
echo.
echo  Si alguna da 000, no hay red o el servicio esta caido.
echo  Si la portada da 404, mira CORPUS_BUCKET en el despliegue.
echo.
pause

echo.
echo ==========================================================================
echo  2. EL TEXTO DE LA PORTADA - esto es lo que hay que leer y aprobar
echo ==========================================================================
echo.
echo  Es texto institucional publico y nuevo, asi que lo aprueba una persona,
echo  no un programa. Abre las dos versiones:
echo.
echo     https://normativa.uji.es/?lang=ca
echo     https://normativa.uji.es/?lang=es
echo.
echo  Lee los dos parrafos de presentacion y decide si el tono es el que
echo  quieres publicar. En concreto:
echo.
echo   - El primer parrafo dice que es el sitio (313 documentos, texto
echo     consolidado, unidades citables).
echo   - El segundo dice que hay un asistente, que cita el articulo exacto,
echo     que esta EN FASE DE PRUEBA y que lo que vale es el texto oficial.
echo     Esa frase es la que protege a la Universidad de una respuesta mala.
echo   - Las dos tarjetas: normativa y economico-administrativo.
echo   - El pie: "Gestion del sitio", que lleva al panel.
echo.
echo  Si algo hay que cambiar, se cambia en el generador del corpus
echo  (build_cercador.py, tabla TP) y se vuelve a publicar. NO se edita el
echo  HTML a mano: se pierde en la regeneracion siguiente.
echo.
pause

echo.
echo ==========================================================================
echo  3. EL SELECTOR DE LENGUA
echo ==========================================================================
echo.
echo  Arriba a la derecha, "Valencia" y "Castellano", como en el resto del
echo  sitio. Comprueba que:
echo.
echo   - Al cambiar, TODA la pagina cambia de lengua: titulo, cifras,
echo     presentacion, tarjetas y pie. No debe quedar nada en la otra.
echo   - El chat tambien: la cabecera y los botones del asistente.
echo   - Si entras despues en el cercador, se abre en la lengua que elegiste
echo     (comparten la misma preferencia guardada).
echo.
pause

echo.
echo ==========================================================================
echo  4. DOS DECISIONES QUE SON TUYAS
echo ==========================================================================
echo.
echo  a) EL NOMBRE PROVISIONAL (34-175-38-129.sslip.io) NO se ha retirado.
echo     Sigue sirviendo exactamente lo mismo, panel incluido. Apuntan a el:
echo       - el paso de comprobacion del despliegue en deploy.yml,
echo       - la comprobacion de tiempo de actividad y su alerta,
echo       - cualquier enlace que ya hayas enviado por correo.
echo     Recomendacion: dejarlo un mes y retirarlo cuando nadie lo use.
echo.
echo  b) EL CERTIFICADO DE normativa.uji.es CADUCA EL 19 DE MARZO DE 2027
echo     y NO se renueva solo (el del nombre provisional si). Hay que pedir
echo     la renovacion a desarrollo, cargarla en Secret Manager y reiniciar.
echo     Un certificado caducado es indistinguible de un servicio caido.
echo.
pause

echo.
echo PRUEBAS COMPLETADAS
echo.
pause
