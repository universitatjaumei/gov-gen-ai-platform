@echo off
chcp 65001 > nul
title Pruebas manuales - Bloque SEG (informe de seguimiento)

echo ============================================================
echo  BLOQUE SEG - Informe anual de seguimiento de un programa
echo  de doctorado: la valoracion anclada a su tabla
echo ============================================================
echo.
echo Lo mecanico ya esta verificado por el agente en navegador:
echo  - Las 42 tablas del informe real se extraen con su codigo.
echo  - Cada apartado de IA recibe SU tabla y solo esa.
echo  - Ninguna valoracion usa cifras que no esten en el origen.
echo  - Las celdas "No hay valor" se conservan y se dicen.
echo  - La vista previa monta 3 secciones, 9 tablas y 9 valoraciones.
echo  - La exportacion entrega un DOCX de unos 41 KB con las tablas.
echo.
echo Lo que queda es UNA sola cosa, y no la puede hacer una maquina:
echo decidir si la valoracion propuesta le sirve a quien firma el informe.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha (base de datos).
echo  2. Backend arrancado.
echo  3. Frontend arrancado (npm run dev en la carpeta frontend).
echo.
echo  Comprueba a mano que responden abriendo estas dos direcciones
echo  en el navegador antes de seguir:
echo    http://localhost:8000/docs
echo    http://localhost:5173/
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PRUEBA UNICA - Sirve la valoracion que propone la IA?
echo ------------------------------------------------------------
echo.
echo  1. Abre http://localhost:5173/redaccion
echo  2. Entra en el informe "Informe anual de seguimiento - Doctorado
echo     (criterios 1 y 2)" o crea uno nuevo con esa plantilla.
echo  3. Sube el fichero .md con los datos del programa.
echo  4. Espera a que el informe quede en revision, unos 3 minutos:
echo     son nueve valoraciones, una por tabla.
echo  5. En el panel de revision, para CADA apartado:
echo       - Mira la linea "Valora: ..." y comprueba que apunta a la
echo         tabla de ese apartado.
echo       - Lee la valoracion con la tabla delante.
echo.
echo  Y ahora el juicio, que es lo que se te pide:
echo.
echo       a) La valoracion dice algo que un coordinador firmaria?
echo       b) Le sobra texto? Le falta?
echo       c) Cuando en la tabla hay "No hay valor", lo dice en vez
echo          de inventarlo o de tratarlo como un cero?
echo       d) Las sugerencias de mejora estan en tono neutro, sin
echo          imperativos ni reproches?
echo.
echo  6. Edita al menos una valoracion y guardala. Comprueba que:
echo       - Aparece "Editado por ti".
echo       - El texto original de la IA sigue consultable.
echo  7. Aprueba las nueve y abre la vista previa.
echo  8. Descarga el DOCX y abrelo en Word.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  QUE DEBES VER
echo ------------------------------------------------------------
echo  - En la vista previa: cada tabla con sus bordes y sus cifras
echo    alineadas, y justo debajo su valoracion, en prosa corrida
echo    y sin asteriscos.
echo  - En el DOCX: las tablas como tablas de Word, no como texto.
echo  - Al final del DOCX: el anexo de auditoria con el hash del
echo    documento y los apartados escritos por la IA.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE (opcionales, pero interesantes)
echo ------------------------------------------------------------
echo  [ ] Sube un .md sin ninguna tabla: debe avisar, no salir vacio.
echo  [ ] Pide otra propuesta con "Regenerar" en un apartado y compara.
echo  [ ] Rechaza una valoracion y comprueba que la vista previa se
echo      niega a montarse mientras quede algo sin aprobar.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PARA TERMINAR
echo ------------------------------------------------------------
echo  Si quieres parar los servicios: cierra las ventanas del backend
echo  y del frontend, y si no vas a seguir, docker compose down.
echo.
echo PRUEBAS COMPLETADAS
pause
