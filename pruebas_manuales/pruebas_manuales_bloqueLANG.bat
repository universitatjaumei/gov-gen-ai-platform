@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title Pruebas manuales - Bloque LANG (politica de idioma configurable)

echo ==========================================================================
echo  BLOQUE LANG - politica de idioma configurable: monolingue y respuesta fija
echo ==========================================================================
echo.
echo  Lo que el agente YA verifico en navegador y contra el servidor real
echo  (no hace falta repetirlo):
echo.
echo   - El desplegable "Modo de idioma" del chatbot trae los TRES modos del
echo     servidor, y ya no ofrece "strict", que no hacia nada.
echo   - Al elegir "Responder siempre en un idioma" aparece el segundo
echo     desplegable con Valencia / Castellano / English.
echo   - Los valores por defecto de organizacion ya no sugieren "neutral",
echo     que no era un valor valido.
echo   - Un valor inventado (language_mode="strict") da 422 con los modos
echo     enumerados en el mensaje.
echo   - La MISMA pregunta en catalan, contra Normativa UJI:
echo       con prefer   -^> responde en catalan
echo       con fixed:es -^> responde en castellano
echo     Las dos con su evento de cierre. El chatbot quedo devuelto a prefer.
echo   - Consola del navegador limpia.
echo.
echo  Aqui queda SOLO lo que una persona tiene que valorar.
echo.
pause

echo.
echo ==========================================================================
echo  1. JUICIO SOBRE EL TEXTO DE LA RESPUESTA FIJADA
echo ==========================================================================
echo.
echo  Requisitos previos:
echo    - Docker Desktop en marcha.
echo    - El servidor y el panel levantados (arranque.bat, opcion 1).
echo.
echo  Lo que el agente NO puede juzgar: si el castellano que sale al fijar el
echo  idioma suena a lengua institucional o a traduccion automatica de una
echo  norma escrita en valenciano. Eso hay que leerlo.
echo.
echo  En http://localhost:5173/hub/chatbots:
echo.
echo   1. Pincha en la fila de un asistente de pruebas (NO en Normativa UJI,
echo      que esta en el piloto).
echo   2. Baja hasta "Modo de idioma" y elige "Responder siempre en un idioma".
echo   3. En "Idioma de la respuesta" elige Castellano. Guarda.
echo   4. Preguntale algo EN VALENCIANO desde el widget.
echo   5. Lee la respuesta entera, no solo la primera frase:
echo        - Los nombres de organos y de normas, ^¿estan en castellano o
echo          quedan en valenciano a medias?
echo        - Las citas, ^¿apuntan a la version que toca?
echo.
echo  DECISION TUYA: si el resultado vale para un despliegue monolingue tal
echo  como esta, o si hace falta ajustar el prompt del sistema del asistente.
echo.
pause

echo.
echo ==========================================================================
echo  2. QUE IDIOMAS OFRECER (y con que codigo)
echo ==========================================================================
echo.
echo  El catalogo lo sirve el servidor con el codigo del CORPUS: "val" para el
echo  valenciano, no "ca". Es a proposito: con "ca" la preferencia no casaria
echo  con ninguna version de ninguna norma, y no daria ningun error.
echo.
echo  Hoy se ofrecen tres: val, es, en.
echo.
echo  DECISION TUYA: si al primer despliegue para otra administracion hay que
echo  anadir alguno (gallego, euskera...). El codigo se anade en
echo  server\app\routers\hub_opciones_router.py; la validacion ya acepta
echo  cualquier codigo de 2 o 3 letras, asi que no hay que tocar nada mas.
echo.
pause

echo.
echo ==========================================================================
echo  3. EL DEFECTO DE CADA ORGANIZACION
echo ==========================================================================
echo.
echo  En http://localhost:5173/hub/valores-por-defecto, con una organizacion
echo  elegida, el campo "default_language_mode" ofrece ahora:
echo    prefer, none, fixed:val, fixed:es, fixed:en
echo.
echo  DECISION TUYA: si alguna organizacion del piloto deberia nacer con un
echo  defecto distinto de "prefer". Hoy todas heredan "prefer" y eso no ha
echo  cambiado.
echo.
pause

echo.
echo ==========================================================================
echo PRUEBAS COMPLETADAS
echo ==========================================================================
echo.
echo  Para detener los servicios, cierra las ventanas del servidor y del panel.
echo.
pause
