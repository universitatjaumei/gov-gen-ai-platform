@echo off
chcp 65001 > nul
echo ============================================================
echo  PRUEBAS MANUALES - Prompt 9CBis.11
echo  Widget renderiza citas como pills clicables
echo ============================================================
echo.

echo [REQUISITOS PREVIOS]
echo 1. Docker Desktop en marcha (icono verde en la barra de tareas)
echo 2. Servidor FastAPI corriendo en http://localhost:8000
echo 3. El widget construido (dist/widget/widget.iife.js existe)
echo.

echo [VERIFICANDO dist/widget/widget.iife.js...]
if exist "frontend\dist\widget\widget.iife.js" (
    echo OK - El archivo del widget existe
) else (
    echo ERROR - Falta frontend\dist\widget\widget.iife.js
    echo Ejecuta: cd frontend ^&^& npm run build:widget
    pause
    exit /b 1
)
echo.

echo [VERIFICANDO que el servidor responde...]
curl -s -o nul -w "Status HTTP: %%{http_code}" http://localhost:8000/health
echo.
echo Si obtienes 200, el servidor esta OK. Si obtienes error, levanta Docker primero.
echo.
pause

echo ============================================================
echo  PASOS EN LA INTERFAZ
echo ============================================================
echo.
echo 1. Abre en el navegador: http://localhost:5173/widget.html
echo    (o abre directamente el archivo frontend/widget.html con Live Server)
echo.
echo 2. Escribe una pregunta sobre normativa universitaria y pulsa Enviar
echo.
echo 3. QUE DEBES VER:
echo    a) El mensaje del asistente se renderiza con formato Markdown
echo       (si responde con **negrita**, aparece en negrita real, no como asteriscos)
echo    b) Debajo del mensaje, aparecen pills azules redondeadas con el
echo       titulo de cada documento citado
echo    c) Al hacer clic en una pill, se abre el documento en una nueva pestana
echo    d) Si el chatbot no usa fuentes (respuesta sin RAG), no aparece
echo       ninguna pill - el mensaje termina limpiamente
echo.
echo CASOS LIMITE:
echo    [ ] Respuesta sin fuentes: no debe aparecer ninguna pill ni etiqueta extra
echo    [ ] Respuesta con 3+ fuentes: todas las pills aparecen en fila (con wrap si no caben)
echo    [ ] URL larga en la pill: el texto del titulo se muestra completo, no la URL
echo.

pause

echo ============================================================
echo  THEMING DE PILLS (opcional)
echo ============================================================
echo.
echo Las pills usan variables CSS personalizables:
echo   --source-pill-bg     (fondo, default: azul claro #e0f2fe)
echo   --source-pill-fg     (texto, default: azul oscuro #0369a1)
echo   --source-pill-border (borde, default: azul medio #7dd3fc)
echo.
echo Para probar theming: en widget.html, modifica las variables CSS
echo del bloque #govgenai-widget { --source-pill-bg: ... }
echo y recarga la pagina - los colores deben cambiar sin recompilar.
echo.

pause
echo.
echo ============================================================
echo  PRUEBAS COMPLETADAS - Prompt 9CBis.11
echo ============================================================
pause