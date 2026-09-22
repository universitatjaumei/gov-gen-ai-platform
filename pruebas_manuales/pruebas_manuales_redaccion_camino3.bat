@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Redaccion, camino 3
echo.
echo ==========================================================
echo   REDACCION - CAMINO 3
echo   Borrador con IA, anonimizacion y exportacion real
echo ==========================================================
echo.
echo POR QUE ESTE GUION EXISTE
echo.
echo   Los caminos 1 y 2 del modulo de redaccion se recorrieron con
echo   datos reales. El tercero no, y es el que junta las tres cosas
echo   que ningun test puede juzgar:
echo.
echo     1. Un borrador REAL con bloques AI_ASSISTED_TEXT, aprobado
echo        como espacio de trabajo.
echo     2. La anonimizacion ejercitada de punta a punta, con datos
echo        sinteticos.
echo     3. La exportacion abierta en Word y en Adobe REALES, no solo
echo        comprobando que el fichero se genera.
echo.
echo   Que el fichero se genere lo comprueba un test. Que se abra sin
echo   avisos y se lea bien, no.
echo.
echo REQUISITOS PREVIOS
echo   1. Docker Desktop en marcha y la base levantada:
echo        docker compose up -d postgres
echo   2. La base migrada:
echo        cd server
echo        uv run alembic upgrade head
echo   3. Backend y frontend:
echo        arranque.bat  (opcion 1)
echo      OJO: el backend tarda 2-4 minutos (carga torch).
echo   4. Word y Adobe Reader instalados de verdad. Un visor del
echo      navegador NO sirve para el paso 5.
echo   5. Datos SINTETICOS con pinta de personales: nombres, DNI,
echo      direcciones, telefonos, correos. Inventados. Si usas datos
echo      reales para probar la anonimizacion, ya has perdido.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 1 - Los servicios responden
echo ----------------------------------------------------------
echo.
curl -s -o nul -w "   backend 8000 health: %%{http_code}\n" http://localhost:8000/health
curl -s -o nul -w "   frontend 5173:       %%{http_code}\n" http://localhost:5173/
echo.
echo QUE DEBES VER: 200 en las dos.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 2 - Un borrador real con bloques de IA
echo ----------------------------------------------------------
echo.
echo   1. Entra en Redaccion y arranca un borrador nuevo.
echo   2. Pide una estructura que incluya apartados de texto redactado
echo      por IA, no solo tablas ni texto fijo.
echo   3. Revisa la propuesta: los bloques AI_ASSISTED_TEXT tienen que
echo      aparecer marcados como tales.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - La pantalla distingue con claridad que apartados los escribe
echo     la IA y cuales no? Quien firme el documento tiene que saberlo
echo     sin adivinarlo.
echo   - La estructura propuesta sirve para el documento que querias?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 3 - Aprobar como espacio de trabajo
echo ----------------------------------------------------------
echo.
echo   1. Aprueba el borrador como espacio de trabajo.
echo   2. Entra en el espacio y recorre los apartados.
echo   3. Aprueba los bloques de IA uno a uno en el panel de revision.
echo   4. Ensambla el informe.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - El texto que escribio la IA DICE ALGO CIERTO sobre tus datos?
echo     Es el juicio central del modulo y no lo puede hacer nadie mas.
echo   - Se puede editar antes de aprobar, o solo aceptar o rechazar?
echo   - Si dejas un bloque sin aprobar, el ensamblado te lo dice de
echo     forma que se entienda cual falta?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 4 - Anonimizacion de punta a punta
echo ----------------------------------------------------------
echo.
echo   Con los datos sinteticos del requisito 5.
echo.
echo   1. Mete en el documento nombres, DNI, direcciones, telefonos y
echo      correos inventados.
echo   2. Ejecuta la anonimizacion.
echo   3. Lee el resultado ENTERO, sin saltarte parrafos.
echo.
echo LO QUE HAY QUE JUZGAR, y hay que mirarlo en los dos sentidos:
echo   - SE ESCAPO ALGO? Un DNI, un telefono, un nombre en un pie de
echo     tabla o en una nota al pie. Ahi es donde se esconden.
echo   - SE LLEVO POR DELANTE ALGO QUE NO DEBIA? Nombres de organos,
echo     de normas o de unidades administrativas que no son datos
echo     personales. Una anonimizacion que borra de mas deja un
echo     documento que no se entiende, y eso no lo detecta ningun
echo     contador de aciertos.
echo   - El documento sigue siendo legible despues?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 5 - Exportar, y ABRIR de verdad
echo ----------------------------------------------------------
echo.
echo   Este paso no vale si te limitas a comprobar que el fichero se
echo   descarga. Hay que abrirlo.
echo.
echo   1. Exporta a Word. Abrelo en Word, no en el visor del navegador
echo      ni en Google Docs.
echo   2. Exporta a PDF. Abrelo en Adobe Reader.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Word avisa de algo al abrirlo? Un aviso de formato o de
echo     recuperacion significa que el fichero esta mal formado aunque
echo     se vea.
echo   - Las tablas estan bien formadas, con sus cabeceras, y no se
echo     parten de forma absurda entre paginas?
echo   - Los acentos y la enye salen bien? Y si el documento es
echo     bilingue, las dos lenguas?
echo   - En el PDF: se puede seleccionar y copiar el texto, o es una
echo     imagen? Un PDF de texto no seleccionable no es accesible.
echo   - El aviso de contenido generado por IA aparece en los dos
echo     formatos exportados, no solo en la pantalla?
echo.
pause
echo.
echo ==========================================================
echo   PRUEBAS COMPLETADAS
echo ==========================================================
echo.
echo Lo que hayas encontrado, conviertelo en issues propias.
echo.
echo Para terminar: Ctrl+C en las ventanas del backend y del frontend,
echo y si quieres  docker compose down
echo.
pause
