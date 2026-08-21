@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque RAS (rastreo del portal)

echo ============================================================
echo  BLOQUE RAS - Rastreo y curacion del apartado de la
echo  Escuela de Doctorado de www.uji.es
echo ============================================================
echo.
echo Lo mecanico ya esta verificado por el agente:
echo  - Cortesia medida: pausa por host, robots.txt leido una vez,
echo    User-Agent identificable con contacto, presupuesto de tiempo.
echo  - Coste medido del rastreo: 2 s de pausa + 1,4 s que tarda el
echo    propio portal en responder. Unos 3,4 s por pagina, asi que un
echo    apartado de 400 paginas son unos 23 minutos.
echo  - /seu/ queda fuera por el robots.txt del portal, sin tocar nada.
echo  - Sondeo del apartado sin navegador: 0 paginas necesitan JavaScript.
echo  - El formulario de alta ofrece el filtro del apartado y la cortesia.
echo  - Un enlace roto ya no tumba el rastreo (paso de 0 paginas a rastreo
echo    completo con el 404 registrado como hallazgo).
echo.
echo Lo que queda es criterio humano, y son tres cosas.
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
echo  Comprueba a mano que responden abriendo estas dos direcciones:
echo    http://localhost:8000/docs
echo    http://localhost:5173/
echo.
pause

echo.
echo ------------------------------------------------------------
echo  ANTES DE NADA - el alcance de la auditoria semantica
echo ------------------------------------------------------------
echo.
echo  Para depurar duplicados y contradicciones ANTES de ingerir, el
echo  apartado tiene que estar en alcance "Completo". El valor por
echo  defecto es "Solo ingerido", que solo compara lo que ya esta en
echo  el corpus: barato, pero no sirve para depurar antes.
echo.
echo  [ ] En Curacion - Sitios, comprueba que el apartado de la
echo      Escuela de Doctorado tiene "Alcance de auditoria semantica"
echo      = Completo.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PRUEBA 1 - Los hallazgos son ciertos?
echo ------------------------------------------------------------
echo.
echo  Esta es la prueba que decide si el modulo sirve, y solo la puede
echo  hacer alguien que conozca el apartado.
echo.
echo  1. Abre http://localhost:5173/curation/sites
echo  2. Entra en "Hallazgos" y filtra por el sitio de la Escuela
echo     de Doctorado.
echo  3. Para CADA tipo de hallazgo, mira dos o tres ejemplos y decide:
echo.
echo       [ ] thin (contenido pobre): es pobre de verdad, o es una
echo           pagina indice que esta bien como esta?
echo       [ ] stale (antiguo): la fecha que usa el sistema corresponde
echo           al contenido, o es la de la plantilla del portal?
echo       [ ] superseded (version nueva publicada, vieja sin retirar):
echo           es cierto? Las dos URLs son el mismo recurso?
echo       [ ] crawl_error con causa "not_found": el enlace apunta de
echo           verdad a algo que ya no existe?
echo       [ ] needs_javascript, si aparece alguno: esa pagina se ve
echo           bien en el navegador pero no se puede leer sin el?
echo.
echo  Anota los que sean falsos positivos: con eso se ajustan los
echo  umbrales, que hoy son de laboratorio y no de este portal.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PRUEBA 2 - El rastreo se ha portado bien con el servidor?
echo ------------------------------------------------------------
echo.
echo  Esto no lo puede comprobar el agente: hay que preguntarlo.
echo.
echo  [ ] Pregunta a quien gestiona el portal si el rastreo aparece en
echo      sus registros y si le ha causado alguna molestia. El
echo      User-Agent con el que se identifica es:
echo        GovGenAI-Curacion/1.0 (+el contacto configurado)
echo  [ ] Confirma con ellos que el apartado se puede rastrear con esa
echo      identidad, y pregunta por la linea del robots.txt que excluye
echo      a ClaudeBot de todo el portal.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  PRUEBA 3 - Que paginas merecen entrar en el asistente?
echo ------------------------------------------------------------
echo.
echo  Es una decision humana por diseno: el sistema propone candidatas
echo  y nadie las publica por ti.
echo.
echo  1. En "Publicacion", elige el chatbot y el sitio.
echo  2. Revisa la lista de candidatas y selecciona una o dos que de
echo     verdad sirvan para responder preguntas (por ejemplo, la de
echo     becas o la de tramites de tesis).
echo  3. Ingierelas.
echo  4. Ve al chat del asistente y pregunta algo que solo pueda
echo     responderse con esa pagina.
echo.
echo  [ ] La respuesta cita la pagina ingerida, con su enlace?
echo  [ ] El texto citado es contenido de la pagina, y no el menu del
echo      portal repetido?
echo.
pause

echo.
echo ------------------------------------------------------------
echo  QUE DEBES VER
echo ------------------------------------------------------------
echo  - En "Sitios": el apartado con su ultimo rastreo y estado activo.
echo  - En "Auditoria": el informe de calidad del apartado, descargable.
echo  - En "Hallazgos": los hallazgos agrupados, con su severidad.
echo  - En el chat: una respuesta que cita una pagina del portal.
echo.
pause

echo.
echo ------------------------------------------------------------
echo  UN LIMITE CONOCIDO, PARA QUE NO TE SORPRENDA
echo ------------------------------------------------------------
echo  Cada pagina del portal repite el menu completo (unos 2 KB de
echo  texto de navegacion). Eso viaja al corpus junto con el contenido
echo  de la pagina. No es un fallo del rastreo: es como sirve el portal
echo  sus paginas. Quitar el menu (boilerplate) no esta hecho todavia y
echo  esta anotado como pendiente.
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
