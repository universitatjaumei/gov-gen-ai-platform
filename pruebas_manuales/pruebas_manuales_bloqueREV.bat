@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Bloque REV (revision de respuestas)

echo ============================================================
echo   BLOQUE REV - Revision humana de las respuestas
echo ============================================================
echo.
echo Lo que el agente YA verifico (no hace falta repetirlo):
echo   - La pantalla /hub/reports carga con los filtros nuevos,
echo     el contador "Pendientes de revisar" y los botones de
echo     veredicto por fila, en catalan.
echo   - Contra Postgres real: 422 sin nota, 200 con nota firmando
echo     quien y cuando, la cola baja al revisar, los filtros
echo     devuelven lo esperado y otra organizacion recibe 403.
echo.
echo Lo que queda es lo que el agente NO puede hacer: una
echo conversacion de verdad con un modelo real.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PASO 0 - REINICIA EL BACKEND (IMPORTANTE)
echo ------------------------------------------------------------
echo.
echo El backend que tenias en marcha sirve codigo ANTERIOR a este
echo bloque: la ruta nueva no existe en el. Parala con Ctrl+C y
echo vuelve a arrancarla antes de seguir.
echo.
pause

echo.
echo Comprobando que el backend responde y tiene la ruta nueva...
curl -s -o nul -w "  /health -> %%{http_code}\n" http://localhost:8000/health
curl -s http://localhost:8000/openapi.json | findstr /C:"interactions/{interaction_id}/review" > nul
if errorlevel 1 (
  echo   [FALLO] La ruta de revision NO esta. El backend sigue con el codigo viejo.
) else (
  echo   [OK] La ruta de revision esta registrada.
)
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PASO 1 - Genera una conversacion real
echo ------------------------------------------------------------
echo.
echo 1. Abre http://localhost:5173/hub/chatbots y elige un chatbot
echo    que tenga configurado un modelo con clave real.
echo 2. Hazle DOS preguntas: una que sepa responder y otra que no
echo    (algo fuera de su corpus). La segunda es la que interesa.
echo.
echo Ojo: "Ejecutar" en Escenarios de prueba NO sirve aqui. Esas
echo ejecuciones no cuentan como conversacion real.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PASO 2 - Revisa las respuestas
echo ------------------------------------------------------------
echo.
echo 1. Abre http://localhost:5173/hub/reports y elige ese chatbot.
echo 2. "Pendientes de revisar" debe marcar 2.
echo 3. En la respuesta buena, pulsa "Adecuada".
echo    -^> La fila desaparece de la lista (el filtro es "Sin revisar")
echo       y el contador baja a 1.
echo 4. En la respuesta mala, pulsa "Inadecuada" SIN escribir nada.
echo    -^> No debe pasar nada: la nota es obligatoria ahi.
echo 5. Escribe en la nota que habria que cambiar y pulsa
echo    "Inadecuada" otra vez.
echo    -^> Ahora si. El contador baja a 0.
echo 6. Cambia el filtro a "Revisadas".
echo    -^> Salen las dos, con su veredicto y tu correo.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   PASO 3 - El CSV que se lleva Gerencia
echo ------------------------------------------------------------
echo.
echo 1. Con el filtro en "Todas", pulsa CSV.
echo 2. Abre el fichero descargado.
echo    -^> Debe traer las columnas review_verdict, review_note,
echo       review_by y review_at, rellenas en las dos filas.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   CASOS LIMITE
echo ------------------------------------------------------------
echo.
echo [ ] Un chatbot sin conversaciones: la tabla dice que no hay
echo     interacciones y el contador marca 0, sin error.
echo [ ] Cambiar de chatbot en el desplegable recarga la lista.
echo [ ] Filtro "Cualquier veredicto" combinado con "Revisadas"
echo     devuelve las dos; con "Inadecuada", solo una.
echo.
echo ============================================================
echo   PRUEBAS COMPLETADAS
echo ============================================================
pause