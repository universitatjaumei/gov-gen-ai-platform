@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
echo ============================================================
echo  PRUEBAS MANUALES - Prompt FIX.1
echo ============================================================
echo.
echo Lo que el agente ya verifico solo:
echo   - Backend: 67 tests de API en verde, 6 nuevos para este arreglo.
echo   - Frontend: 239 tests en verde, TypeScript sin errores.
echo   - Promover una configuracion por defecto: HTTP 200 y queda UNA sola.
echo   - Ejecutar un escenario en el chatbot demo: HTTP 201.
echo.
echo Lo que NO pudo verificar y por eso estas aqui:
echo   - La pantalla. La extension de Chrome pidio permiso y se denego.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  ANTES DE EMPEZAR
echo ------------------------------------------------------------
echo  1. Docker Desktop en marcha.
echo  2. Backend:  uv run --project server uvicorn server.app.main:app --port 8000
echo  3. Frontend: cd frontend  y luego  npm run dev
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 1 - Los servicios responden
echo ------------------------------------------------------------
curl -s -o nul -w "backend  http %%{http_code}" http://127.0.0.1:8000/health
echo.
curl -s -o nul -w "frontend http %%{http_code}" http://localhost:5173/
echo.
echo Los dos deben decir 200.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 2 - Elegir el modelo de un chatbot
echo ------------------------------------------------------------
echo  Abre http://localhost:5173/hub/chatbots y entra como fabra@uji.es
echo.
echo  a) Pulsa sobre "Chatbot Demo" para editarlo.
echo  b) Debe haber un desplegable "Modelo de lenguaje" y debe venir
echo     marcado en:  google . gemini-2.5-flash (por defecto)
echo  c) Cambia el nombre a "Chatbot Demo 2" y guarda SIN tocar el modelo.
echo  d) Vuelve a abrirlo: el modelo DEBE seguir siendo gemini-2.5-flash.
echo     Antes de este arreglo, guardar reasignaba el modelo en silencio.
echo  e) Devuelve el nombre a "Chatbot Demo".
echo.
echo  LO IMPORTANTE: abre "Chatbot de Ejemplo", que usa ollama . llama3.1:8b.
echo  El desplegable debe mostrar ESE modelo, no el de Gemini.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 3 - Editar un escenario de prueba
echo ------------------------------------------------------------
echo  Abre http://localhost:5173/hub/test-scenarios
echo.
echo  a) Elige "Chatbot Demo" y crea un escenario cualquiera.
echo  b) Ahora debe aparecer un boton "Editar" junto a "Ejecutar".
echo  c) Pulsalo: el formulario se abre RELLENO con lo que escribiste.
echo  d) Cambia el nombre y guarda. La lista debe mostrar el nombre nuevo.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  COMPROBACION 4 - Un fallo de ejecucion ahora se ve
echo ------------------------------------------------------------
echo  a) Elige "Chatbot de Ejemplo", el de Ollama, que no esta arrancado.
echo  b) Crea un escenario y pulsa "Ejecutar".
echo  c) DEBE aparecer un mensaje de error en rojo.
echo     Antes no pasaba absolutamente nada: ese era el sintoma original.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  CASOS LIMITE
echo ------------------------------------------------------------
echo   [ ] Configuracion de modelos: marca otra como "por defecto".
echo       Debe funcionar a la primera, sin el error de que ya existe una.
echo   [ ] Cambia el idioma a valenciano y vuelve a mirar las pantallas:
echo       nada en castellano ni claves tipo hub.chatbot_model.
echo   [ ] Consola del navegador (F12) sin errores en rojo.
echo.
pause
echo.
echo ------------------------------------------------------------
echo  NOTA SOBRE EL CORPUS
echo ------------------------------------------------------------
echo  El "Chatbot Demo" tiene 0 documentos, asi que las respuestas diran
echo  que no hay informacion suficiente. Eso es correcto y no es un fallo:
echo  sin corpus el sistema no llama al modelo. Para ver respuestas reales
echo  hay que cargar corpus antes.
echo.
echo PRUEBAS COMPLETADAS
pause
