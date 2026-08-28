@echo off
chcp 65001 > nul
cd /d "%~dp0.."
echo ================================================================
echo   PRUEBAS MANUALES - BLOQUE ACT (actualizacion del corpus)
echo ================================================================
echo.
echo Lo que ya esta comprobado y NO hay que repetir:
echo   - El corpus del 27-08 esta ingerido en los cuatro asistentes.
echo   - Segunda pasada a cero: nada se reescribe si nada ha cambiado.
echo   - La regla de lengua, medida sobre el corpus real: 0 parejas
echo     devuelven las dos versiones, en ninguna de las dos lenguas.
echo   - 1914 tests en verde.
echo.
echo Lo que falta es lo unico que yo no puedo ver: como queda la
echo RESPUESTA del asistente en pantalla.
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  ANTES DE EMPEZAR
echo ---------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. IMPORTANTE: reinicia el servidor. El que este corriendo
echo     tiene el codigo de antes del bloque.
echo        cd server
echo        uv run uvicorn app.main:app --port 8000
echo  3. En otra terminal:  cd frontend  ^&^&  npm run dev
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  COMPROBACION 1 - El servidor responde
echo ---------------------------------------------------------------
curl -s -o nul -w "  /docs -> %%{http_code}\n" http://localhost:8000/docs
curl -s -o nul -w "  frontend -> %%{http_code}\n" http://localhost:5173/
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  COMPROBACION 2 - La misma norma en las dos lenguas
echo ---------------------------------------------------------------
echo  Entra en http://localhost:5173/login
echo     usuario: fabra@uji.es    contrasena: admin1234
echo  Abre el asistente "Normativa UJI" y pregunta DOS VECES lo mismo:
echo.
echo     (en castellano)  Que dice el reglamento sobre teletrabajo del PTGAS?
echo     (en valenciano)  Que diu el reglament sobre teletreball del PTGAS?
echo.
echo  QUE DEBES VER:
echo    - En castellano, la norma citada en CASTELLANO.
echo    - En valenciano, la MISMA norma citada en VALENCIANO.
echo    - NUNCA las dos versiones de la misma norma en una respuesta.
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  COMPROBACION 3 - El aviso de traduccion dice el idioma
echo ---------------------------------------------------------------
echo  Pregunta en CASTELLANO por una norma que solo existe en
echo  valenciano, por ejemplo:
echo.
echo     Que dice el reglamento del Claustro?
echo.
echo  QUE DEBES VER:
echo    - Un aviso que dice "esta en VALENCIANO".
echo    - NUNCA "esta en val" (el codigo crudo). Ese era el defecto.
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  COMPROBACION 4 - Las directrices del curso pasado no contestan
echo ---------------------------------------------------------------
echo  Pregunta:  Cuantas convocatorias de evaluacion tengo por asignatura?
echo.
echo  QUE DEBES VER:
echo    - Cita las Directrices del curso 2026/2027 (DIR-001 o DIR-009).
echo    - NO cita las del curso 2025/2026 (DIR-003 / DIR-004).
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  COMPROBACION 5 - Las normas externas ya no tapan a las propias
echo ---------------------------------------------------------------
echo  En "Normativa UJI" pregunta:  Como se tramita un contrato menor?
echo.
echo  QUE DEBES VER:
echo    - Cita normativa DE LA UJI (instrucciones, circulares).
echo    - NO cita la Ley de Contratos del Sector Publico.
echo  Y en el asistente de Gerencia, la misma pregunta SI puede citarla:
echo  alli las externas siguen dentro a proposito.
echo.
pause
echo.
echo ---------------------------------------------------------------
echo  CASOS LIMITE (marca lo que compruebes)
echo ---------------------------------------------------------------
echo  [ ] Preguntar en valenciano por una norma que solo existe en
echo      castellano: contesta con ella y avisa "esta en CASTELLANO".
echo  [ ] Preguntar por una norma derogada (RES-006): no deberia
echo      contestarla como vigente.
echo  [ ] Una pregunta fuera del corpus: deberia declinar.
echo.
echo ---------------------------------------------------------------
echo  PARA TERMINAR
echo ---------------------------------------------------------------
echo  Ctrl+C en las dos terminales. Docker puede quedarse en marcha.
echo.
echo PRUEBAS COMPLETADAS
pause