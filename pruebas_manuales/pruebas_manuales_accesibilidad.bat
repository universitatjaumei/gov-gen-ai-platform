@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Accesibilidad e identidad visual
echo.
echo ==========================================================
echo   PRUEBAS MANUALES - ACCESIBILIDAD E IDENTIDAD VISUAL
echo ==========================================================
echo.
echo POR QUE ESTE GUION EXISTE
echo.
echo   La auditoria automatica de accesibilidad (WCAG 2.2 AA) corre en
echo   CI y esta verde. Eso cubre lo comprobable por reglas: contraste,
echo   etiquetas, roles, orden de tabulacion.
echo.
echo   NO cubre si la navegacion tiene sentido cuando se oye, ni si el
echo   texto institucional suena como debe. Eso es juicio de una
echo   persona, y es lo unico que hay aqui.
echo.
echo REQUISITOS PREVIOS
echo   1. Un lector de pantalla REAL instalado. En Windows, NVDA es
echo      gratuito: https://www.nvaccess.org/download/
echo      No vale la simulacion del navegador ni la vista de
echo      accesibilidad de las herramientas de desarrollo.
echo   2. La aplicacion en marcha:
echo        arranque.bat  (opcion 1)
echo      OJO: el backend tarda 2-4 minutos (carga torch). Hasta que no
echo      escriba "Application startup complete" no responde.
echo   3. Dos cuentas si quieres cubrir tambien el panel: una de
echo      trabajador y una de administracion.
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
echo QUE DEBES VER: health 200 y frontend 200.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 2 - Entrar, oyendolo
echo ----------------------------------------------------------
echo.
echo   1. Arranca el lector de pantalla ANTES de abrir el navegador.
echo   2. Ve a http://localhost:5173 y APAGA LA PANTALLA, o cierra los
echo      ojos. Es la unica forma de que la prueba valga: si ves la
echo      pantalla, tu cabeza rellena lo que el lector no dice.
echo   3. Entra con tu cuenta usando solo el teclado.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Al cargar, el lector dice donde estas? O empieza a leer menus
echo     sin decir que pagina es?
echo   - Los campos de usuario y contrasena se anuncian con su nombre,
echo     o solo como "cuadro de edicion"?
echo   - Si la contrasena falla, TE ENTERAS? El aviso de error se
echo     anuncia solo, o hay que ir a buscarlo con el cursor?
echo   - El boton de entrar con Google se entiende al oirlo?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 3 - Preguntar al asistente, oyendolo
echo ----------------------------------------------------------
echo.
echo   Sigue con la pantalla apagada.
echo.
echo   1. Abre el asistente y escribe una pregunta de normativa.
echo   2. Espera la respuesta sin mirar.
echo.
echo LO QUE HAY QUE JUZGAR, y es lo mas importante de este guion:
echo   - Te enteras de que esta pensando? O hay un silencio en el que no
echo     sabes si se ha colgado?
echo   - Cuando termina, se anuncia la respuesta sola, o hay que ir a
echo     buscarla?
echo   - LAS CITAS: se distinguen del cuerpo de la respuesta al oirlas?
echo     Puedes llegar a un enlace de una cita y saber a que norma va,
echo     o el lector solo dice "enlace"?
echo   - El aviso de contenido generado por IA se oye? Si solo se ve,
echo     no cumple su funcion para quien no ve.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 4 - Un formulario largo, oyendolo
echo ----------------------------------------------------------
echo.
echo   Elige uno de los dos, el que uses mas:
echo     - Informes: crear un informe desde plantilla.
echo     - Curacion: dar de alta un portal.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Cada campo dice que espera ANTES de escribir, o te enteras al
echo     fallar?
echo   - Los campos obligatorios se anuncian como obligatorios?
echo   - Al enviar con algo mal, el lector te lleva al campo del error?
echo   - La zona de arrastre de ficheros: se puede usar SOLO con
echo     teclado? Si no se puede, esta rota para quien no usa raton.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 5 - Solo teclado, ya con la pantalla encendida
echo ----------------------------------------------------------
echo.
echo   Desenchufa el raton. En serio: dejarlo a un lado no basta.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Se ve SIEMPRE donde esta el foco? Un foco invisible es una
echo     aplicacion inusable sin raton.
echo   - Los cajones y ventanas modales: atrapan el foco mientras estan
echo     abiertos, y lo devuelven al cerrarse con Escape?
echo   - Hay forma de saltarse el menu para ir al contenido, o hay que
echo     tabular por todo el menu en cada pagina?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 6 - Identidad visual y tono institucional
echo ----------------------------------------------------------
echo.
echo   Esto es juicio subjetivo y por eso no lo hace ningun test.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - La tipografia y los colores: parecen de la institucion, o
echo     parecen una plantilla generica?
echo   - El tono de los textos: suena a administracion publica seria, o
echo     suena a producto comercial? Mira sobre todo los mensajes de
echo     error y los avisos, que es donde se cuela el tono equivocado.
echo   - Los textos en valenciano y en castellano: alguno suena a
echo     traduccion automatica?
echo   - En movil (reduce la ventana a 400px de ancho): se puede usar,
echo     o hay que desplazarse en horizontal?
echo.
pause
echo.
echo ==========================================================
echo   PRUEBAS COMPLETADAS
echo ==========================================================
echo.
echo Lo que hayas encontrado, conviertelo en issues propias. Un
echo hallazgo de accesibilidad anotado en un cuaderno no lo arregla
echo nadie.
echo.
echo Para terminar: Ctrl+C en las ventanas del backend y del frontend.
echo.
pause
