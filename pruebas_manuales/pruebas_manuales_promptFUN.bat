@echo off
chcp 1252 >nul
setlocal

echo =========================================================================
echo  Bloque FUN - Catalogo de funciones - PRUEBAS MANUALES
echo =========================================================================
echo.
echo Solo hay TRES cosas aqui, y ninguna es una comprobacion tecnica: el ciclo
echo completo ya se recorrio contra la base de desarrollo y las pantallas se
echo verificaron en navegador dentro del bloque (consola y red limpias).
echo.
echo Lo que queda es juicio humano y una decision que no es de la plataforma.
echo.
echo -------------------------------------------------------------------------
echo  1. LA PANTALLA DE REVISION POSTERIOR NO PUEDE PARECER UNA BANDEJA DE
echo     APROBACIONES
echo -------------------------------------------------------------------------
echo.
echo  Abre  http://localhost:5173/redaccion/funciones/revision
echo.
echo  Es la pantalla de la UADTI y del administrador de organizacion. El
echo  invariante de todo el bloque es que las versiones que salen ahi YA SE
echo  ESTAN EJECUTANDO: revisarlas no las autoriza, las corrige, las
echo  reclasifica o las detiene.
echo.
echo  La pantalla lo dice con el distintivo verde "En uso" y con la frase de
echo  cabecera. Pero si al mirarla de golpe da la sensacion de que hay que
echo  aprobar algo, la pantalla esta mal - y eso no lo puede medir un test.
echo.
echo  PREGUNTA: al abrirla sin contexto, entiendes que esas funciones ya
echo  funcionan, o parece que esperan tu visto bueno?
echo.
echo  Si parece lo segundo, dilo: hay que cambiar el texto o el orden, porque
echo  una persona que crea que su firma autoriza el uso esta haciendo una
echo  aprobacion previa con otro nombre, que es justo lo que la Instruccio
echo  02/2026 prohibe en el nivel 2.
echo.
echo -------------------------------------------------------------------------
echo  2. LOS CUATRO RESULTADOS DE REVISION, EN EL LENGUAJE DE QUIEN REVISA
echo -------------------------------------------------------------------------
echo.
echo  En la misma pantalla, los botones de resultado son:
echo.
echo     Conforme  /  Pedir correcciones  /  Reclasificar el alcance  /  Suspender
echo.
echo  "Aprobada" NO esta, y no esta a proposito: en el nivel 2 no hay nada que
echo  aprobar.
echo.
echo  PREGUNTA: son esas cuatro palabras las que usaria la UADTI? "Reclasificar
echo  el alcance" es la que mas dudas me da: significa "esto excede el nivel 2
echo  y deberia valorarse como nivel 3", y no se si se entiende sola.
echo.
echo -------------------------------------------------------------------------
echo  3. LA DECISION QUE NO ES DE LA PLATAFORMA (UADTI + OIATI)
echo -------------------------------------------------------------------------
echo.
echo  Esto no se prueba: se decide, y no lo puede decidir el codigo.
echo.
echo  La Instruccio 02/2026 preve, para el desarrollo ciudadano, que el codigo
echo  se quede EN EL EQUIPO DE LA PERSONA. En el catalogo no ocurre eso: el
echo  codigo se registra en la plataforma y corre en el nodo institucional,
echo  sobre los datos institucionales.
echo.
echo  Es un regimen DISTINTO, no una interpretacion laxa:
echo.
echo    A favor - pasa por auditoria estatica, corre en sandbox, queda
echo    versionado con su hash, tiene declaracion responsable, entra en una
echo    cola de revision y deja rastro en el registro de actividad de IA. Nada
echo    de eso existe cuando el script vive en un portatil.
echo.
echo    En contra - los datos que trata son los institucionales y no una copia
echo    en un equipo personal, y el codigo lo puede usar cualquiera de la
echo    organizacion sin que su autora lo sepa.
echo.
echo  La comparacion completa esta en docs\CATALOGO_FUNCIONES.md, seccion 4.
echo.
echo  HACE FALTA UN "SI" EXPLICITO de la UADTI y de la OIATI, no un silencio.
echo  La plataforma no puede decidir por su cuenta que su regimen equivale al
echo  que la Instruccio describe.
echo.
echo  Y de paso, en la misma conversacion: las reglas del auditor AST (los 16
echo  modulos permitidos, las 63 capacidades denegadas y las 6 reglas de
echo  docs\CATALOGO_FUNCIONES.md seccion 5) se escribieron desde el analisis
echo  del riesgo de un script de extraccion, NO desde la norma. Hay que
echo  contrastarlas con el ANEXO III.3 del Reglamento —que es el que la seccion
echo  8.4 de la Instruccio cita para el analisis estatico— y con las Guias
echo  Operativas Tecnicas. Si alguna es mas estricta en algo, manda la norma.
echo.
echo =========================================================================
echo  LO QUE NO HACE FALTA QUE COMPRUEBES
echo =========================================================================
echo.
echo  Ya verificado en navegador o contra la base de desarrollo dentro del
echo  bloque, con su evidencia en el informe de cierre:
echo.
echo   - Catalogo con nivel, origen, declaracion y hallazgos del auditor.
echo   - Botones generados desde acciones_permitidas (y un test que lo fija en
echo     los dos sentidos).
echo   - Suspender con motivo: 200, el motivo visible, y el bloque anclado
echo     fallando con ese motivo.
echo   - Reactivar en vivo, sin recargar, conservando el motivo como historia.
echo   - Solicitar y resolver la promocion como superadministrador.
echo   - Otra organizacion: ve las publicadas con solo "adoptar version" y
echo     recibe 404 sobre la no publicada.
echo   - Publicar v2 sin tocar las plantillas ancladas a v1, adoptar v2 en una
echo     sola, y ver el arreglo solo ahi.
echo   - El paquete demo instalado y desinstalado de verdad: se registra al
echo     arrancar y pasa a "no instalada" sin borrarse.
echo   - La API con PAT: 401 sin token, 422 sin version, 423 con el motivo si
echo     esta suspendida, y el evento en el registro sin payloads.
echo.
echo =========================================================================
echo.
pause
endlocal
