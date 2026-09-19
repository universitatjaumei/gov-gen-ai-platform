@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ==========================================================
echo   PRUEBAS MANUALES - BLOQUE DIN (apartados que se mantienen)
echo ==========================================================
echo.
echo El ciclo completo ya se verifico en navegador contra un portal
echo controlado: seccion creada por la interfaz con su patron probado,
echo pagina nueva que entra sola, cambiada que se reingiere, borrada que
echo se retira del corpus, y el resto del sitio intacto. El diario lo
echo cuenta con el ambito de cada pasada.
echo.
echo Aqui queda SOLO lo que no se puede comprobar sin una persona.
echo.
echo ----------------------------------------------------------
echo  1. UN APARTADO REAL DEL PORTAL DE LA UJI
echo ----------------------------------------------------------
echo.
echo Lo verificado usa un portal de prueba servido en local. Contra
echo www.uji.es hay dos cosas que decide una persona y no un agente:
echo.
echo   a) QUE APARTADO. Elige uno que se actualice de verdad
echo      (jornadas, eventos, becas) y quien es su responsable.
echo   b) EL robots.txt. El del portal excluye rastreadores; rastrearlo
echo      con "respetar robots.txt" desmarcado es una decision de quien
echo      gestiona el portal, no del agente.
echo.
echo Con eso decidido, la receta paso a paso esta en
echo docs\SECCIONES_DINAMICAS.md (apartado 2). Al terminar la primera
echo pasada, revisa los hallazgos uno a uno ANTES de poner la seccion
echo en modo automatico: ahi es donde se calibran los criterios.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  2. LA CADUCIDAD EDITORIAL: UNA PREGUNTA, NO UN BOTON
echo ----------------------------------------------------------
echo.
echo Un evento que ya ocurrio sigue publicado, asi que para la
echo plataforma no ha desaparecido y el asistente puede citarlo como si
echo viniera. NO esta implementado a proposito: depende de quien publica.
echo.
echo La pregunta que hay que llevarle al propietario del contenido es
echo "cuando deja de ser cierto lo que publicas". Las cuatro opciones,
echo con su precio, estan en docs\SECCIONES_DINAMICAS.md (apartado 6).
echo.
pause
echo.
echo ----------------------------------------------------------
echo  3. JUICIO SOBRE LA PANTALLA
echo ----------------------------------------------------------
echo.
echo Abre http://localhost:5173/curation/sites y despliega
echo "Secciones del sitio" en una fila.
echo.
echo   - La cadencia dice si es propia o heredada del sitio. Se
echo     entiende de un vistazo?
echo   - El diario de pasadas, con su ambito y sus contadores: dice
echo     lo que necesitas saber, o sobra o falta alguna columna?
echo   - Los textos en valenciano y en ingles (selector de idioma
echo     abajo a la izquierda): suenan a lenguaje institucional?
echo.
pause
